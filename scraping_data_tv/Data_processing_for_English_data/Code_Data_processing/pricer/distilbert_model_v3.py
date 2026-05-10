"""Model 2 V3: DistilBERT with mean pooling instead of [CLS] token.

Architecture change: average all token embeddings weighted by attention mask.
Training config: same as V2 (batch=64, epochs=15, patience=3).

Mean pooling vs CLS:
- CLS is pretrained for classification (NSP task) — not optimal for regression
- Mean pooling averages all token representations — better distributes information
- SentenceTransformers (all-MiniLM-L6-v2) uses mean pooling and performs well on regression
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.amp import GradScaler
from transformers import DistilBertModel

from pricer.distilbert_model_v2 import DistilBERTRunnerV2


class DistilBERTRegressorV3(nn.Module):
    """DistilBERT encoder + regression head using mean pooling."""

    def __init__(self, dropout_prob=0.1):
        super().__init__()
        self.encoder = DistilBertModel.from_pretrained("distilbert-base-uncased")
        hidden_size = self.encoder.config.hidden_size  # 768
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Linear(hidden_size, 256),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(256, 1),
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        # Mean pooling: average token embeddings, ignoring padding
        mask = attention_mask.unsqueeze(-1).float()
        mean_emb = (outputs.last_hidden_state * mask).sum(1) / mask.sum(1)
        return self.head(mean_emb)


class DistilBERTRunnerV3(DistilBERTRunnerV2):
    """DistilBERT mean pooling — same training config as V2."""

    def setup(self, batch_size=64):
        # V2 setup handles data loading, normalization stats, device
        super().setup(batch_size=batch_size)
        # Replace CLS model with mean-pooling model
        self.model = DistilBERTRegressorV3()
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        encoder_params = sum(p.numel() for p in self.model.encoder.parameters())
        head_params = sum(p.numel() for p in self.model.head.parameters())
        print(f"DistilBERT V3 (mean pooling): {total_params:,} params (encoder: {encoder_params:,}, head: {head_params:,})")
        self.model.to(self.device)
        self.optimizer = optim.AdamW(
            [
                {"params": self.model.encoder.parameters(), "lr": 2e-5},
                {"params": self.model.head.parameters(), "lr": 1e-4},
            ],
            weight_decay=0.01,
        )
        self.scaler = GradScaler(device="cuda") if self.device.type == "cuda" else None
