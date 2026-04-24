import numpy as np
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
        "r2": float(r2_score(y_true, y_pred)),
    }
