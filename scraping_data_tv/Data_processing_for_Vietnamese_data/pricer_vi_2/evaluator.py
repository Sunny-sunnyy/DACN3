"""Evaluator for Vietnamese price prediction — Day 3 v2.

Price unit: thousands VND (price = round(price_vnd / 1000), range 5-1000).
Primary metric: MAE (k VND) — aligned with English pipeline.
Metrics reported: MAE (k VND), MSE, R².

Display convention:
  - evaluate() output: "43.9k VND" (k suffix for clarity)
  - Training values:   raw numbers (45, not 45k) — same scale as English
"""

import re
import math
from itertools import accumulate
from concurrent.futures import ThreadPoolExecutor

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


class Tester:
    def __init__(self, predictor, data, title=None, size=DEFAULT_SIZE, workers=WORKERS):
        self.predictor = predictor
        self.data = data
        self.title = title or self.make_title(predictor)
        self.size = size
        self.titles = []
        self.guesses = []
        self.truths = []
        self.errors = []
        self.colors = []
        self.workers = workers

    @staticmethod
    def make_title(predictor) -> str:
        return predictor.__name__.replace("__", ".").replace("_", " ").title()

    @staticmethod
    def post_process(value):
        if isinstance(value, str):
            value = value.replace("k", "").replace("K", "").replace("VND", "").replace(",", "")
            match = re.search(r"[-+]?\d*\.\d+|\d+", value)
            return float(match.group()) if match else 0
        else:
            return value

    def color_for(self, error, truth):
        if error < 40 or error / truth < 0.2:
            return "green"
        elif error < 80 or error / truth < 0.4:
            return "orange"
        else:
            return "red"

    def run_datapoint(self, i):
        datapoint = self.data[i]
        value = self.predictor(datapoint)
        guess = self.post_process(value)
        truth = datapoint.price
        error = abs(guess - truth)
        color = self.color_for(error, truth)
        title = datapoint.title if len(datapoint.title) <= 40 else datapoint.title[:40] + "..."
        return title, guess, truth, error, color

    def chart(self, title):
        df = pd.DataFrame({
            "truth": self.truths,
            "guess": self.guesses,
            "title": self.titles,
            "error": self.errors,
            "color": self.colors,
        })

        df["hover"] = [
            f"{t}\Dự đoán: {g:.1f}k VND  Thực tế: {y:.1f}k VND"
            for t, g, y in zip(df["title"], df["guess"], df["truth"])
        ]

        max_val = float(max(df["truth"].max(), df["guess"].max()))

        fig = px.scatter(
            df,
            x="truth",
            y="guess",
            color="color",
            color_discrete_map={"green": "green", "orange": "orange", "red": "red"},
            title=title,
            labels={"truth": "Giá thực tế (k VND)", "guess": "Giá dự đoán (k VND)"},
            width=1000,
            height=800,
        )

        for tr in fig.data:
            mask = df["color"] == tr.name
            tr.customdata = df.loc[mask, ["hover"]].to_numpy()
            tr.hovertemplate = "%{customdata[0]}<extra></extra>"
            tr.marker.update(size=6)

        fig.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val],
            mode="lines", line=dict(width=2, dash="dash", color="deepskyblue"),
            name="y = x", hoverinfo="skip", showlegend=False,
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
            math.sqrt((sq_sum / i) - (mean ** 2)) if i > 1 else 0
            for i, sq_sum, mean in zip(x, running_squares, running_means)
        ]
        ci = [1.96 * (sd / math.sqrt(i)) if i > 1 else 0 for i, sd in zip(x, running_stds)]
        upper = [m + c for m, c in zip(running_means, ci)]
        lower = [m - c for m, c in zip(running_means, ci)]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x + x[::-1], y=upper + lower[::-1],
            fill="toself", fillcolor="rgba(128,128,128,0.2)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip", showlegend=False, name="95% CI",
        ))

        fig.add_trace(go.Scatter(
            x=x, y=running_means,
            mode="lines", line=dict(width=3, color="firebrick"),
            name="Cumulative Avg Error",
            customdata=list(zip(ci)),
            hovertemplate="n=%{x}<br>Avg Error=%{y:.1f}k VND<br>±95% CI=%{customdata[0]:.1f}k<extra></extra>",
        ))

        final_mean = running_means[-1]
        final_ci = ci[-1]
        fig.update_layout(
            title=f"{self.title} Error: {final_mean:.1f}k ± {final_ci:.1f}k VND",
            xaxis_title="Number of Datapoints",
            yaxis_title="Average Absolute Error (k VND)",
            width=1000, height=360,
            template="plotly_white", showlegend=False,
        )
        fig.show()

    def report(self) -> dict:
        average_error = sum(self.errors) / self.size
        mse = mean_squared_error(self.truths, self.guesses)
        r2 = r2_score(self.truths, self.guesses) * 100
        title = (
            f"{self.title} results<br>"
            f"<b>Error:</b> {average_error:.1f}k VND  "
            f"<b>MSE:</b> {mse:,.0f}  "
            f"<b>R²:</b> {r2:.1f}%"
        )
        self.error_trend_chart()
        self.chart(title)
        return {"mae": average_error, "mse": mse, "r2": r2}

    def run(self) -> dict:
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            for title, guess, truth, error, color in tqdm(
                ex.map(self.run_datapoint, range(self.size)), total=self.size
            ):
                self.titles.append(title)
                self.guesses.append(guess)
                self.truths.append(truth)
                self.errors.append(error)
                self.colors.append(color)
                print(f"{COLOR_MAP[color]}{error:.0f} ", end="")
        print(RESET)
        return self.report()


def evaluate(function, data, size=DEFAULT_SIZE, workers=WORKERS) -> dict:
    """Evaluate a predictor on data. Returns {"mae": float, "mse": float, "r2": float}."""
    return Tester(function, data, size=size, workers=workers).run()


def plot_training_history(history: dict, title: str = "Model") -> None:
    """Plot train/val loss, val MAE (k VND), and learning rate from training history.

    Args:
        history: dict with keys: train_loss, val_loss, val_mae (k VND), lr
        title: model name shown in chart title
    """
    from plotly.subplots import make_subplots

    epochs = list(range(1, len(history["train_loss"]) + 1))

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(
            "Train vs Validation Loss (Normalized)",
            "Validation MAE (k VND)",
            "Learning Rate Schedule",
        ),
        vertical_spacing=0.08,
    )

    fig.add_trace(go.Scatter(
        x=epochs, y=history["train_loss"], mode="lines+markers",
        name="Train Loss", line=dict(color="dodgerblue", width=2), marker=dict(size=8),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=epochs, y=history["val_loss"], mode="lines+markers",
        name="Val Loss", line=dict(color="tomato", width=2), marker=dict(size=8),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=epochs, y=history["val_mae"], mode="lines+markers",
        name="Val MAE (k VND)", line=dict(color="mediumseagreen", width=2), marker=dict(size=8),
        hovertemplate="Epoch %{x}<br>MAE: %{y:.1f}k VND<extra></extra>",
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=epochs, y=history["lr"], mode="lines+markers",
        name="Learning Rate", line=dict(color="mediumpurple", width=2), marker=dict(size=8),
    ), row=3, col=1)

    fig.update_xaxes(title_text="Epoch", row=3, col=1)
    fig.update_yaxes(title_text="Loss", row=1, col=1)
    fig.update_yaxes(title_text="MAE (k VND)", row=2, col=1)
    fig.update_yaxes(title_text="LR", row=3, col=1)

    final_train = history["train_loss"][-1]
    final_val = history["val_loss"][-1]
    final_mae = history["val_mae"][-1]

    fig.update_layout(
        title=f"{title} Training History | Train: {final_train:.4f}  Val: {final_val:.4f}  MAE: {final_mae:.1f}k VND",
        height=900, width=1000, template="plotly_white", showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.show()
