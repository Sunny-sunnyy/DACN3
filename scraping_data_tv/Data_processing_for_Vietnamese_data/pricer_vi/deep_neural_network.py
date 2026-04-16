"""Deep Neural Network models for Vietnamese price prediction.

Includes:
- ResidualBlock: Skip-connection block for deep networks
- DeepNeuralNetwork: Stacked ResidualBlocks for bag-of-words/embedding input
- MLP: Simple feedforward network for pre-computed embeddings
- plot_training_history: Plotly chart for train/val loss curves
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch.optim.lr_scheduler import CosineAnnealingLR
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class ResidualBlock(nn.Module):
    def __init__(self, hidden_size, dropout_prob=0.2):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(self.block(x) + x)


class DeepNeuralNetwork(nn.Module):
    def __init__(self, input_size, hidden_size=2048, num_layers=10, dropout_prob=0.2):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        self.residual_blocks = nn.ModuleList(
            [ResidualBlock(hidden_size, dropout_prob) for _ in range(num_layers - 2)]
        )
        self.output_layer = nn.Linear(hidden_size, 1)

    def forward(self, x):
        x = self.input_layer(x)
        for block in self.residual_blocks:
            x = block(x)
        return self.output_layer(x)


class MLP(nn.Module):
    """Simple feedforward network for pre-computed embeddings."""

    def __init__(self, input_size, hidden_sizes=(512, 256, 128), dropout_prob=0.3):
        super().__init__()
        layers = []
        prev = input_size
        for h in hidden_sizes:
            layers.extend([nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout_prob)])
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


def train_torch_model(model, X_train, y_train, X_val, y_val, device,
                       epochs=5, batch_size=64, lr=0.001, weight_decay=0.01,
                       use_scheduler=True):
    """Train any torch model (DNN or MLP) with log-normalized target.

    Target transform: log(price+1) -> normalize(mean, std).
    Loss: MSELoss on normalized log-space (directly optimizes RMSLE).
    Returns: trained model, y_mean, y_std, history dict.
    """
    y_train_log = torch.log(y_train + 1)
    y_val_log = torch.log(y_val + 1)
    y_mean = y_train_log.mean()
    y_std = y_train_log.std()
    y_train_norm = (y_train_log - y_mean) / y_std
    y_val_norm = (y_val_log - y_mean) / y_std

    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=max(epochs, 10)) if use_scheduler else None
    loss_fn = nn.MSELoss()

    loader = DataLoader(
        TensorDataset(X_train, y_train_norm), batch_size=batch_size, shuffle=True
    )

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model: {total_params:,} trainable params | Device: {device}")

    history = {"train_loss": [], "val_loss": [], "val_mae": []}

    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for bx, by in loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = loss_fn(model(bx), by)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            losses.append(loss.item())

        model.eval()
        with torch.no_grad():
            val_out = model(X_val.to(device))
            val_loss = loss_fn(val_out, y_val_norm.to(device)).item()
            val_pred_vnd = torch.exp(val_out * y_std + y_mean) - 1
            val_mae = torch.abs(val_pred_vnd - y_val.to(device)).mean().item()

        if scheduler:
            scheduler.step()

        history["train_loss"].append(np.mean(losses))
        history["val_loss"].append(val_loss)
        history["val_mae"].append(val_mae)

        print(
            f"  Epoch {epoch}/{epochs} | "
            f"Train MSE: {np.mean(losses):.4f} | "
            f"Val MSE: {val_loss:.4f} | "
            f"Val MAE: {val_mae:,.0f} VND"
        )

    return model, y_mean, y_std, history


def predict_batch(model, X, y_mean, y_std, device):
    """Predict prices (VND) from features. Inverse log-norm transform."""
    model.eval()
    y_mean = y_mean.to(device)
    y_std = y_std.to(device)
    with torch.no_grad():
        out = model(X.to(device))
        prices = torch.exp(out * y_std + y_mean) - 1
        prices = prices.clamp(min=0).cpu().numpy().flatten()
    return prices


def plot_training_history(history, title="Training History"):
    """Plot train/val loss and val MAE curves using Plotly."""
    epochs = list(range(1, len(history["train_loss"]) + 1))

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Loss (MSE on normalized log-space)", "Val MAE (VND)"),
    )

    fig.add_trace(
        go.Scatter(x=epochs, y=history["train_loss"], mode="lines+markers",
                   name="Train Loss", line=dict(color="steelblue")),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=epochs, y=history["val_loss"], mode="lines+markers",
                   name="Val Loss", line=dict(color="tomato")),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=epochs, y=history["val_mae"], mode="lines+markers",
                   name="Val MAE", line=dict(color="mediumseagreen")),
        row=1, col=2,
    )

    fig.update_xaxes(title_text="Epoch", row=1, col=1)
    fig.update_xaxes(title_text="Epoch", row=1, col=2)
    fig.update_yaxes(title_text="MSE Loss", row=1, col=1)
    fig.update_yaxes(title_text="MAE (VND)", row=1, col=2)

    fig.update_layout(title=title, width=900, height=400, template="plotly_white")
    fig.show()
    return fig
