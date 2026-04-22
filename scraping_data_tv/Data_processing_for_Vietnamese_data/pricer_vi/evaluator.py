"""Evaluator for Vietnamese price prediction models.

Adapted from English evaluator (ed-donner) with:
- VND formatting (int, 1K-50M)
- RMSLE as primary metric (Kaggle standard for price prediction)
- MAPE-based color thresholds
- Support size="all" for full test set evaluation
"""

import re
import math
from itertools import accumulate
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.metrics import mean_absolute_error, r2_score
from tqdm.auto import tqdm

def _tick_step(max_val):
    """Pick a round VND tick step that gives ~8-12 ticks."""
    steps = [50_000, 100_000, 200_000, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000]
    for s in steps:
        if max_val / s <= 12:
            return s
    return steps[-1]


GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
COLOR_MAP = {"red": RED, "orange": YELLOW, "green": GREEN}

WORKERS = 5
DEFAULT_SIZE = 200
SEED = 42


def rmsle(y_true, y_pred):
    """Root Mean Squared Logarithmic Error — primary metric."""
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    y_pred = np.clip(y_pred, 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def mape(y_true, y_pred):
    """Mean Absolute Percentage Error (%)."""
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    mask = y_true > 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


class Tester:
    def __init__(self, predictor, data, title=None, size=DEFAULT_SIZE, workers=WORKERS):
        self.predictor = predictor
        self.data = data
        self.title = title or self.make_title(predictor)
        self.size = len(data) if size == "all" else min(size, len(data))
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
        """Convert prediction to numeric VND value."""
        if isinstance(value, str):
            value = value.replace("VND", "").replace(",", "").replace(".", "").strip()
            match = re.search(r"[-+]?\d+", value)
            return float(match.group()) if match else 0
        return float(value)

    def color_for(self, error, truth):
        """Color based on MAPE thresholds."""
        if truth == 0:
            return "red"
        pct = error / truth
        if pct < 0.2:
            return "green"
        elif pct < 0.4:
            return "orange"
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
        """Scatter plot: x = predicted, y = actual price (VND)."""
        df = pd.DataFrame({
            "truth": self.truths,
            "guess": self.guesses,
            "title": self.titles,
            "error": self.errors,
            "color": self.colors,
        })

        df["hover"] = [
            f"{t}\nDu doan: {g:,.0f} VND\nThuc te: {y:,.0f} VND"
            for t, g, y in zip(df["title"], df["guess"], df["truth"])
        ]

        max_val = float(max(df["truth"].max(), df["guess"].max()))

        fig = px.scatter(
            df,
            x="guess",
            y="truth",
            color="color",
            color_discrete_map={"green": "green", "orange": "orange", "red": "red"},
            title=title,
            labels={"guess": "Gia du doan (VND)", "truth": "Gia thuc te (VND)"},
            width=1000,
            height=800,
        )

        for tr in fig.data:
            mask = df["color"] == tr.name
            tr.customdata = df.loc[mask, ["hover"]].to_numpy()
            tr.hovertemplate = "%{customdata[0]}<extra></extra>"
            tr.marker.update(size=6)

        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode="lines",
                line=dict(width=2, dash="dash", color="deepskyblue"),
                name="y = x",
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # VND tick format: 100k, 200k, ... 1000k
        step = _tick_step(max_val)
        tick_vals = list(range(0, int(max_val) + step, step))
        tick_text = [f"{v // 1000:,}k" if v > 0 else "0" for v in tick_vals]

        fig.update_xaxes(range=[0, max_val], tickvals=tick_vals, ticktext=tick_text)
        fig.update_yaxes(range=[0, max_val], tickvals=tick_vals, ticktext=tick_text)
        fig.update_layout(showlegend=False)
        fig.show()

    def error_trend_chart(self):
        """Cumulative average error with 95% confidence interval."""
        n = len(self.errors)

        running_sums = list(accumulate(self.errors))
        x = list(range(1, n + 1))
        running_means = [s / i for s, i in zip(running_sums, x)]

        running_squares = list(accumulate(e * e for e in self.errors))
        running_stds = [
            math.sqrt((sq_sum / i) - (mean**2)) if i > 1 else 0
            for i, sq_sum, mean in zip(x, running_squares, running_means)
        ]

        ci = [1.96 * (sd / math.sqrt(i)) if i > 1 else 0 for i, sd in zip(x, running_stds)]
        upper = [m + c for m, c in zip(running_means, ci)]
        lower = [m - c for m, c in zip(running_means, ci)]

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=x + x[::-1],
                y=upper + lower[::-1],
                fill="toself",
                fillcolor="rgba(128,128,128,0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                showlegend=False,
                name="95% CI",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=x,
                y=running_means,
                mode="lines",
                line=dict(width=3, color="firebrick"),
                name="Cumulative Avg Error",
                customdata=list(zip(ci)),
                hovertemplate=(
                    "n=%{x}<br>"
                    "Avg Error=%{y:,.0f} VND<br>"
                    "+/-95% CI=%{customdata[0]:,.0f} VND<extra></extra>"
                ),
            )
        )

        final_mean = running_means[-1]
        final_ci = ci[-1]
        title = f"{self.title} Error: {final_mean:,.0f} +/- {final_ci:,.0f} VND"

        # VND tick format for y-axis
        y_max = max(upper) if upper else final_mean * 2
        step = _tick_step(y_max)
        tick_vals = list(range(0, int(y_max) + step, step))
        tick_text = [f"{v // 1000:,}k" if v > 0 else "0" for v in tick_vals]

        fig.update_layout(
            title=title,
            xaxis_title="Number of Datapoints",
            yaxis_title="Average Absolute Error (VND)",
            width=1000,
            height=360,
            template="plotly_white",
            showlegend=False,
        )
        fig.update_yaxes(tickvals=tick_vals, ticktext=tick_text)

        fig.show()

    def report(self):
        """Print metrics and show charts."""
        mae_val = mean_absolute_error(self.truths, self.guesses)
        rmsle_val = rmsle(self.truths, self.guesses)
        mape_val = mape(self.truths, self.guesses)
        r2_val = r2_score(self.truths, self.guesses) * 100

        print(f"\n{self.title} Results ({self.size} items):")
        print(f"  RMSLE:  {rmsle_val:.4f}")
        print(f"  MAE:    {mae_val:,.0f} VND")
        print(f"  MAPE:   {mape_val:.1f}%")
        print(f"  R2:     {r2_val:.1f}%")

        title = (
            f"{self.title} ({self.size} items)<br>"
            f"<b>RMSLE:</b> {rmsle_val:.4f} "
            f"<b>MAE:</b> {mae_val:,.0f} VND "
            f"<b>MAPE:</b> {mape_val:.1f}% "
            f"<b>R2:</b> {r2_val:.1f}%"
        )
        self.error_trend_chart()
        self.chart(title)

        return {"rmsle": rmsle_val, "mae": mae_val, "mape": mape_val, "r2": r2_val}

    def run(self):
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            for title, guess, truth, error, color in tqdm(
                ex.map(self.run_datapoint, range(self.size)), total=self.size
            ):
                self.titles.append(title)
                self.guesses.append(guess)
                self.truths.append(truth)
                self.errors.append(error)
                self.colors.append(color)
                print(f"{COLOR_MAP[color]}{error:,.0f} ", end="")
        return self.report()


def evaluate(function, data, size=DEFAULT_SIZE, workers=WORKERS):
    """Evaluate a predictor function on data. Returns metrics dict."""
    return Tester(function, data, size=size, workers=workers).run()


def plot_predictions(y_true, y_pred, title="Model", names=None, plot_size=200):
    """Plot scatter (predicted vs actual) + error trend from pre-computed arrays.

    Args:
        y_true: array of actual prices (VND)
        y_pred: array of predicted prices (VND)
        title: model name for chart titles
        names: optional list of product names for hover text
        plot_size: number of points to display in charts (metrics computed on full set)
    Returns:
        dict with rmsle, mae, mape, r2
    """
    y_true = np.array(y_true, dtype=float)
    y_pred = np.clip(np.array(y_pred, dtype=float), 0, None)
    n = len(y_true)

    errors = np.abs(y_true - y_pred)
    pct_errors = np.where(y_true > 0, errors / y_true, 1.0)
    colors = np.where(pct_errors < 0.2, "green", np.where(pct_errors < 0.4, "orange", "red"))

    # Metrics on full dataset
    rmsle_val = rmsle(y_true, y_pred)
    mae_val = float(mean_absolute_error(y_true, y_pred))
    mape_val = mape(y_true, y_pred)
    r2_val = r2_score(y_true, y_pred) * 100

    subtitle = (
        f"<b>RMSLE:</b> {rmsle_val:.4f}  "
        f"<b>MAE:</b> {mae_val:,.0f} VND  "
        f"<b>MAPE:</b> {mape_val:.1f}%  "
        f"<b>R2:</b> {r2_val:.1f}%"
    )

    # Sample for chart display only (metrics already computed above)
    if plot_size is not None and plot_size < n:
        rng = np.random.default_rng(SEED)
        idx = rng.choice(n, plot_size, replace=False)
        y_true_plot = y_true[idx]
        y_pred_plot = y_pred[idx]
        errors_plot = errors[idx]
        colors_plot = colors[idx]
        names_plot = [names[i] for i in idx] if names is not None else None
        n_plot = plot_size
    else:
        y_true_plot, y_pred_plot = y_true, y_pred
        errors_plot, colors_plot = errors, colors
        names_plot = names
        n_plot = n

    # --- Scatter plot ---
    if names_plot is None:
        names_plot = [f"Item {i}" for i in range(n_plot)]
    hover = [
        f"{nm}\nDu doan: {g:,.0f} VND\nThuc te: {t:,.0f} VND"
        for nm, g, t in zip(names_plot, y_pred_plot, y_true_plot)
    ]

    max_val = float(max(y_true.max(), y_pred.max()))

    df_scatter = pd.DataFrame({
        "truth": y_true_plot, "guess": y_pred_plot, "color": colors_plot, "hover": hover,
    })

    fig1 = go.Figure()
    for c, color_val in [("green", "green"), ("orange", "orange"), ("red", "red")]:
        mask = df_scatter["color"] == c
        if mask.sum() == 0:
            continue
        sub = df_scatter[mask]
        fig1.add_trace(go.Scatter(
            x=sub["guess"], y=sub["truth"], mode="markers",
            marker=dict(size=5, color=color_val, opacity=0.6),
            name=c, customdata=sub[["hover"]].to_numpy(),
            hovertemplate="%{customdata[0]}<extra></extra>",
        ))
    fig1.add_trace(go.Scatter(
        x=[0, max_val], y=[0, max_val], mode="lines",
        line=dict(width=2, dash="dash", color="deepskyblue"),
        name="y=x", hoverinfo="skip", showlegend=False,
    ))

    step = _tick_step(max_val)
    tick_vals = list(range(0, int(max_val) + step, step))
    tick_text = [f"{v // 1000:,}k" if v > 0 else "0" for v in tick_vals]
    fig1.update_xaxes(title="Gia du doan (VND)", range=[0, max_val], tickvals=tick_vals, ticktext=tick_text)
    fig1.update_yaxes(title="Gia thuc te (VND)", range=[0, max_val], tickvals=tick_vals, ticktext=tick_text)
    fig1.update_layout(
        title=f"{title} ({n} items, chart: {n_plot})<br>{subtitle}",
        width=800, height=700, showlegend=False, template="plotly_white",
    )
    fig1.show()

    # --- Error trend chart (sampled set for visual clarity) ---
    running_sums = np.cumsum(errors_plot)
    x = np.arange(1, n_plot + 1)
    running_means = running_sums / x
    running_sq = np.cumsum(errors_plot ** 2)
    running_stds = np.sqrt(np.maximum(running_sq / x - running_means ** 2, 0))
    ci = np.where(x > 1, 1.96 * running_stds / np.sqrt(x), 0)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=np.concatenate([x, x[::-1]]),
        y=np.concatenate([running_means + ci, (running_means - ci)[::-1]]),
        fill="toself", fillcolor="rgba(128,128,128,0.2)",
        line=dict(color="rgba(255,255,255,0)"), hoverinfo="skip", showlegend=False,
    ))
    fig2.add_trace(go.Scatter(
        x=x, y=running_means, mode="lines",
        line=dict(width=3, color="firebrick"), name="Cumulative Avg Error",
    ))

    y_max = float((running_means + ci).max()) if n_plot > 0 else 1
    step_e = _tick_step(y_max)
    tv = list(range(0, int(y_max) + step_e, step_e))
    tt = [f"{v // 1000:,}k" if v > 0 else "0" for v in tv]

    fig2.update_layout(
        title=f"{title} Error Trend: {running_means[-1]:,.0f} +/- {ci[-1]:,.0f} VND",
        xaxis_title="Datapoints", yaxis_title="Avg Absolute Error (VND)",
        width=900, height=360, template="plotly_white", showlegend=False,
    )
    fig2.update_yaxes(tickvals=tv, ticktext=tt)
    fig2.show()

    return {"rmsle": rmsle_val, "mae": mae_val, "mape": mape_val, "r2": r2_val}
