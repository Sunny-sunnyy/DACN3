import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.metrics import mean_absolute_error, r2_score


def rmsle(y_true, y_pred) -> float:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.clip(np.array(y_pred, dtype=float), 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def compute_metrics(y_true, y_pred) -> dict:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.clip(np.array(y_pred, dtype=float), 0, None)
    return {
        "rmsle": rmsle(y_true, y_pred),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mape": float(np.mean(np.abs(y_pred - y_true) / y_true) * 100),
        "r2": float(r2_score(y_true, y_pred)) * 100,
    }


def plot_predictions(y_true, y_pred, title="Model", names=None) -> None:
    """Scatter predicted vs actual (day4 style) + cumulative error trend."""
    y_true = np.array(y_true, dtype=float)
    y_pred = np.clip(np.array(y_pred, dtype=float), 0, None)
    n = len(y_true)

    errors = np.abs(y_true - y_pred)
    pct_err = np.where(y_true > 0, errors / y_true, 1.0)
    colors = np.where(pct_err < 0.2, "green", np.where(pct_err < 0.4, "orange", "red"))

    metrics = compute_metrics(y_true, y_pred)
    subtitle = (
        f"<b>RMSLE:</b> {metrics['rmsle']:.4f}  "
        f"<b>MAE:</b> {metrics['mae']:,.0f} VND  "
        f"<b>MAPE:</b> {metrics['mape']:.1f}%  "
        f"<b>R2:</b> {metrics['r2']:.1f}%"
    )

    hover_names = names if names is not None else [f"Item {i}" for i in range(n)]
    hover = [
        f"{nm}<br>Pred: {g:,.0f} VND<br>True: {t:,.0f} VND"
        for nm, g, t in zip(hover_names, y_pred, y_true)
    ]
    max_val = float(max(y_true.max(), y_pred.max()))
    df = pd.DataFrame({"truth": y_true, "guess": y_pred, "color": colors, "hover": hover})

    # --- Scatter: predicted vs actual ---
    fig1 = go.Figure()
    for c, cv in [("green", "green"), ("orange", "orange"), ("red", "red")]:
        sub = df[df["color"] == c]
        if len(sub) == 0:
            continue
        fig1.add_trace(go.Scatter(
            x=sub["guess"], y=sub["truth"], mode="markers",
            marker=dict(size=5, color=cv, opacity=0.6),
            name=f"{c} (<{'20' if c == 'green' else '40' if c == 'orange' else '40+'}% err)",
            customdata=sub[["hover"]].to_numpy(),
            hovertemplate="%{customdata[0]}<extra></extra>",
        ))
    fig1.add_trace(go.Scatter(
        x=[0, max_val], y=[0, max_val], mode="lines",
        line=dict(width=2, dash="dash", color="deepskyblue"),
        showlegend=False, hoverinfo="skip",
    ))
    step = max(1, int(max_val / 8 / 1000) * 1000)
    ticks = list(range(0, int(max_val) + step, step))
    tick_text = [f"{v // 1000:,}k" if v > 0 else "0" for v in ticks]
    fig1.update_xaxes(title="Gia du doan (VND)", tickvals=ticks, ticktext=tick_text)
    fig1.update_yaxes(title="Gia thuc te (VND)", tickvals=ticks, ticktext=tick_text)
    fig1.update_layout(
        title=f"{title} — {n} items<br>{subtitle}",
        width=800, height=650, template="plotly_white",
    )
    fig1.show()

    # --- Error trend: cumulative average ---
    x = np.arange(1, n + 1)
    running_means = np.cumsum(errors) / x
    running_stds = np.sqrt(np.maximum(
        np.cumsum(errors ** 2) / x - running_means ** 2, 0
    ))
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
    step_e = max(1, int(running_means.max() / 6 / 1000) * 1000)
    te = list(range(0, int((running_means + ci).max()) + step_e, step_e))
    fig2.update_xaxes(title="Sample index")
    fig2.update_yaxes(title="MAE (VND)", tickvals=te, ticktext=[f"{v // 1000:,}k" if v > 0 else "0" for v in te])
    fig2.update_layout(
        title=f"{title} Error Trend: avg {running_means[-1]:,.0f} +/- {ci[-1]:,.0f} VND",
        width=800, height=400, template="plotly_white", showlegend=False,
    )
    fig2.show()
