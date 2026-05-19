"""VnTester - evaluator for Vietnamese price prediction.

Operates in K VND (5-1000) to match English recipe scale ($5-$999).
Computes MAE, RMSLE, R2, MSE and draws scatter + error-trend charts.

Adapted from English evaluator at
scraping_data_tv/Data_processing_for_English_data/Code_Fine_tune/evaluator.py
"""
import re
import math
from itertools import accumulate
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.metrics import mean_squared_error, r2_score
from tqdm.notebook import tqdm

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
COLOR_MAP = {"red": RED, "orange": YELLOW, "green": GREEN}

WORKERS = 5
DEFAULT_SIZE = 200


def _rmsle(truths: list, guesses: list) -> float:
    t = np.array(truths, dtype=float)
    g = np.maximum(np.array(guesses, dtype=float), 0.0)
    return float(np.sqrt(np.mean((np.log1p(g) - np.log1p(t)) ** 2)))


class VnTester:
    """Evaluate a price predictor on Vietnamese product data.

    Args:
        predictor: callable(Item) -> str | float, returns price in K VND
        data:      list[Item] with .price (K VND) and .title
        title:     display name for charts
        size:      number of items to evaluate (default 200)
        workers:   ThreadPoolExecutor workers (default 5)
    """

    def __init__(self, predictor, data, title=None, size=DEFAULT_SIZE, workers=WORKERS):
        self.predictor = predictor
        self.data = data
        self.title = title or getattr(predictor, "__name__", "Model")
        self.size = min(size, len(data))
        self.workers = workers
        self.titles: list[str] = []
        self.guesses: list[float] = []   # K VND
        self.truths: list[float] = []    # K VND
        self.errors: list[float] = []    # K VND absolute error
        self.colors: list[str] = []

    @staticmethod
    def post_process(value) -> float:
        """Parse model output to float in K VND."""
        if isinstance(value, (int, float)):
            return float(value)
        m = re.search(r"[-+]?\d*\.?\d+", str(value).strip())
        return float(m.group()) if m else 0.0

    def color_for(self, error: float, truth: float) -> str:
        if error < 40 or (truth > 0 and error / truth < 0.2):
            return "green"
        elif error < 80 or (truth > 0 and error / truth < 0.4):
            return "orange"
        return "red"

    def run_datapoint(self, i: int):
        dp = self.data[i]
        guess = self.post_process(self.predictor(dp))
        truth = dp.price  # K VND
        error = abs(guess - truth)
        color = self.color_for(error, truth)
        title = dp.title[:40] + "..." if len(dp.title) > 40 else dp.title
        return title, guess, truth, error, color

    def chart(self, title: str):
        df = pd.DataFrame({
            "truth": self.truths, "guess": self.guesses,
            "title": self.titles, "error": self.errors, "color": self.colors,
        })
        df["hover"] = [
            f"{t}\nGuess={g:,.0f}K  Actual={y:,.0f}K VND"
            for t, g, y in zip(df["title"], df["guess"], df["truth"])
        ]
        max_val = float(max(df["truth"].max(), df["guess"].max()))
        fig = px.scatter(
            df, x="truth", y="guess", color="color",
            color_discrete_map={"green": "green", "orange": "orange", "red": "red"},
            title=title,
            labels={"truth": "Actual Price (K VND)", "guess": "Predicted Price (K VND)"},
            width=1000, height=800,
        )
        for tr in fig.data:
            mask = df["color"] == tr.name
            tr.customdata = df.loc[mask, ["hover"]].to_numpy()
            tr.hovertemplate = "%{customdata[0]}<extra></extra>"
            tr.marker.update(size=6)
        fig.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val], mode="lines",
            line=dict(width=2, dash="dash", color="deepskyblue"),
            hoverinfo="skip", showlegend=False,
        ))
        fig.update_xaxes(range=[0, max_val])
        fig.update_yaxes(range=[0, max_val])
        fig.update_layout(showlegend=False)
        fig.show()

    def error_trend_chart(self):
        n = len(self.errors)
        running_sums = list(accumulate(self.errors))
        x = list(range(1, n + 1))
        running_means = [s / i for s, i in zip(running_sums, x)]
        running_squares = list(accumulate(e * e for e in self.errors))
        running_stds = [
            math.sqrt((sq / i) - (m ** 2)) if i > 1 else 0.0
            for i, sq, m in zip(x, running_squares, running_means)
        ]
        ci = [1.96 * sd / math.sqrt(i) if i > 1 else 0.0 for i, sd in zip(x, running_stds)]
        upper = [m + c for m, c in zip(running_means, ci)]
        lower = [m - c for m, c in zip(running_means, ci)]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x + x[::-1], y=upper + lower[::-1],
            fill="toself", fillcolor="rgba(128,128,128,0.2)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=x, y=running_means, mode="lines",
            line=dict(width=3, color="firebrick"),
            name="Cumulative Avg Error",
            customdata=list(zip(ci)),
            hovertemplate="n=%{x}<br>Avg=%{y:,.1f}K VND<br>+/-95% CI=%{customdata[0]:,.1f}K<extra></extra>",
        ))
        final_mean, final_ci = running_means[-1], ci[-1]
        fig.update_layout(
            title=f"{self.title}  Error: {final_mean:,.1f}K VND +/- {final_ci:,.1f}K",
            xaxis_title="Number of Datapoints",
            yaxis_title="Average Absolute Error (K VND)",
            width=1000, height=360,
            template="plotly_white", showlegend=False,
        )
        fig.show()

    def report(self):
        mae_k = sum(self.errors) / self.size
        mse = mean_squared_error(self.truths, self.guesses)
        r2 = r2_score(self.truths, self.guesses) * 100
        rmsle = _rmsle(self.truths, self.guesses)
        title = (
            f"{self.title} results<br>"
            f"<b>MAE:</b> {mae_k:,.1f}K VND ({mae_k * 1000:,.0f} VND)  "
            f"<b>RMSLE:</b> {rmsle:.4f}  "
            f"<b>MSE:</b> {mse:,.0f}  "
            f"<b>R2:</b> {r2:.1f}%"
        )
        self.error_trend_chart()
        self.chart(title)

    def run(self):
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            for t, g, y, e, c in tqdm(
                ex.map(self.run_datapoint, range(self.size)), total=self.size
            ):
                self.titles.append(t)
                self.guesses.append(g)
                self.truths.append(y)
                self.errors.append(e)
                self.colors.append(c)
                print(f"{COLOR_MAP[c]}{e:.0f}K ", end="")
        print(RESET)
        self.report()


def evaluate(predictor, data, size=DEFAULT_SIZE, workers=WORKERS):
    """Shortcut: evaluate(fn, items) - run Tester and show charts."""
    VnTester(predictor, data, size=size, workers=workers).run()
