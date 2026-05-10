"""Model 2 V2: DistilBERT CLS pooling, optimized for longer training.

Same architecture as distilbert_model.py (CLS pooling).
Differences: batch_size=64, epochs=15, patience=3, warmup_steps=500.
"""

import torch.optim as optim
from torch.amp import GradScaler

from pricer.distilbert_model import DistilBERTRunner


class DistilBERTRunnerV2(DistilBERTRunner):
    """DistilBERT CLS pooling — longer training config: batch=64, 15 epochs."""

    def setup(self, batch_size=64):
        super().setup(batch_size=batch_size)
        # Re-create optimizer after super().setup() to ensure clean state
        self.optimizer = optim.AdamW(
            [
                {"params": self.model.encoder.parameters(), "lr": 2e-5},
                {"params": self.model.head.parameters(), "lr": 1e-4},
            ],
            weight_decay=0.01,
        )
        self.scaler = GradScaler(device="cuda") if self.device.type == "cuda" else None

    def train(self, epochs=15, patience=3, warmup_steps=500):
        return super().train(epochs=epochs, patience=patience, warmup_steps=warmup_steps)
