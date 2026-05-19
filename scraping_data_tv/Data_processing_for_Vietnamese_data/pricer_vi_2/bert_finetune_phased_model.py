"""Phased gradual unfreezing + PriceBinHead — AITeamVN NB14.

PhasedBERTRegressor: same backbone as BERTFineTuneRegressor but uses price_bin_head
  (5 log-spaced bins) instead of category_head for the aux multi-task signal.

PhasedBERTRunner: 3-phase training with freeze_bottom_layers() at phase boundaries.
  Phase 1 (ep 1-4):  top-4,  lr=2e-5  — encoder adapts gently
  Phase 2 (ep 5-8):  top-8,  lr=1e-5  — deeper adaptation
  Phase 3 (ep 9-12): top-16, lr=5e-6  — near-full encoder fine-tune

Price bins (k VND): [0,50), [50,150), [150,350), [350,650), [650,∞)
Aux signal is directly correlated with target → stronger gradient than category.
"""

import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.amp import autocast, GradScaler
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn
from transformers import AutoModel, AutoTokenizer, get_cosine_schedule_with_warmup
from tqdm import tqdm

from pricer_vi_2.bert_finetune_model import (
    mean_pooling,
    freeze_bottom_layers,
    build_llrd_param_groups,
    _MultiTaskDataset,
)

_BIN_BOUNDARIES = torch.tensor([50.0, 150.0, 350.0, 650.0])


def _price_to_bins(prices_t):
    """prices_t: (N, 1) float → bin labels (N,) long, values 0-4."""
    return torch.bucketize(prices_t.squeeze(1), _BIN_BOUNDARIES)


class PhasedBERTRegressor(nn.Module):
    """AutoModel backbone + mean_pooling + price_head + price_bin_head (5 bins)."""

    def __init__(self, model_name, dropout=0.2):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        h = self.bert.config.hidden_size
        self.price_head = nn.Sequential(
            nn.LayerNorm(h),
            nn.Linear(h, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1),
        )
        self.price_bin_head = nn.Linear(h, 5)
        self._init_heads()

    def _init_heads(self):
        for m in self.price_head:
            if isinstance(m, nn.Linear):
                if m.out_features == 1:
                    nn.init.normal_(m.weight, std=0.01)
                else:
                    nn.init.xavier_normal_(m.weight)
                nn.init.zeros_(m.bias)
        nn.init.xavier_normal_(self.price_bin_head.weight)
        nn.init.zeros_(self.price_bin_head.bias)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = mean_pooling(outputs, attention_mask)
        return self.price_head(pooled), self.price_bin_head(pooled)


class PhasedBERTRunner:
    """3-phase gradual unfreezing + price-bin aux head for Vietnamese price regression.

    Usage:
        runner = PhasedBERTRunner(train, val)
        runner.setup("AITeamVN/Vietnamese_Embedding", batch_size=24, base_lr=2e-5)
        history = runner.train(epochs=12, patience=5)
        val_preds = runner.val_predictions()
        test_preds = runner.test_predictions(test)
        runner.save("weights/aitvn_phased.pth")
    """

    # (ep_start, ep_end, keep_top_layers)
    _PHASES = [(1, 4, 4), (5, 8, 8), (9, 12, 16)]

    def __init__(self, train_items, val_items):
        self.train_items = train_items
        self.val_items = val_items
        self.model = None
        self.ema_model = None
        self.tokenizer = None
        self.device = None
        self.y_mean = None
        self.y_std = None
        self.history = None
        self._train_enc = None
        self._val_enc = None
        self._model_name = None
        self._batch_size = None
        self._max_length = None
        self._base_lr = None
        self._weight_decay = None
        self._llrd_decay = None

        np.random.seed(42)
        torch.manual_seed(42)

    def setup(self, model_name, batch_size=24, max_length=256,
              base_lr=2e-5, weight_decay=0.01, llrd_decay=0.85, dropout=0.2):
        """Load model + tokenize all data. Starts with Phase 1 (top-4 unfrozen)."""
        self._model_name = model_name
        self._batch_size = batch_size
        self._max_length = max_length
        self._base_lr = base_lr
        self._weight_decay = weight_decay
        self._llrd_decay = llrd_decay

        print(f"Loading tokenizer: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        print(f"Tokenizing train ({len(self.train_items):,}) — ~5 min ...")
        self._train_enc = self.tokenizer(
            [item.summary for item in self.train_items],
            truncation=True, padding="max_length",
            max_length=max_length, return_tensors="pt",
        )
        print(f"Tokenizing val ({len(self.val_items):,}) ...")
        self._val_enc = self.tokenizer(
            [item.summary for item in self.val_items],
            truncation=True, padding="max_length",
            max_length=max_length, return_tensors="pt",
        )

        # Target: log1p + z-normalize
        y_train = torch.FloatTensor([item.price for item in self.train_items]).unsqueeze(1)
        y_val = torch.FloatTensor([item.price for item in self.val_items]).unsqueeze(1)
        y_train_log = torch.log(y_train + 1)
        self.y_mean = y_train_log.mean()
        self.y_std = y_train_log.std()
        self._y_train_norm = (y_train_log - self.y_mean) / self.y_std
        self._y_val = y_val
        self._y_val_norm = (torch.log(y_val + 1) - self.y_mean) / self.y_std
        self._bin_train = _price_to_bins(y_train)
        self._bin_val = _price_to_bins(y_val)
        print(f"Target: mean={self.y_mean:.4f}, std={self.y_std:.4f} | "
              f"norm range [{self._y_train_norm.min():.2f}, {self._y_train_norm.max():.2f}]")
        bin_counts = torch.bincount(self._bin_train, minlength=5).tolist()
        print(f"Price bins (train): {bin_counts} → "
              f"[<50k, 50-150k, 150-350k, 350-650k, ≥650k]")

        # Model — Phase 1: unfreeze top-4 layers
        print(f"Loading model: {model_name}")
        self.model = PhasedBERTRegressor(model_name, dropout=dropout)
        freeze_bottom_layers(self.model, keep_top_n=4)
        n_trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        n_total = sum(p.numel() for p in self.model.parameters())
        num_layers = len(self.model.bert.encoder.layer)
        print(f"Params: {n_trainable:,}/{n_total:,} trainable | "
              f"top 4/{num_layers} layers unfrozen (Phase 1 start) | "
              f"hidden={self.model.bert.config.hidden_size}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Device: {self.device}")
        self.model.to(self.device)

    def _build_optimizer_scheduler(self, base_lr, steps_per_epoch, num_epochs, warmup_ratio):
        param_groups = build_llrd_param_groups(
            self.model, base_lr=base_lr,
            decay=self._llrd_decay, weight_decay=self._weight_decay,
        )
        optimizer = torch.optim.AdamW(param_groups)
        total_steps = steps_per_epoch * num_epochs
        warmup_steps = int(total_steps * warmup_ratio)
        scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)
        return optimizer, scheduler

    def train(self, epochs=12, patience=5, huber_delta=1.0, aux_alpha=0.15,
              ema_decay=0.9999, warmup_ratio=0.05, max_grad_norm=1.0, r_drop_alpha=0.3):
        """3-phase training: rebuild optimizer+scheduler at each phase boundary."""
        dataset = _MultiTaskDataset(
            self._train_enc["input_ids"],
            self._train_enc["attention_mask"],
            self._y_train_norm,
            self._bin_train,
        )
        train_loader = DataLoader(
            dataset, batch_size=self._batch_size,
            shuffle=True, num_workers=0, pin_memory=True,
        )

        self.ema_model = AveragedModel(
            self.model, multi_avg_fn=get_ema_multi_avg_fn(ema_decay),
        )
        self.ema_model.to(self.device)

        huber_fn = nn.HuberLoss(delta=huber_delta)
        ce_fn = nn.CrossEntropyLoss()
        scaler = GradScaler("cuda") if self.device.type == "cuda" else None

        self.history = {"train_loss": [], "val_loss": [], "val_mae": [], "lr": []}
        best_val_mae = float("inf")
        best_ema_state = None
        patience_counter = 0

        val_ids = self._val_enc["input_ids"]
        val_mask = self._val_enc["attention_mask"]
        y_val_norm_dev = self._y_val_norm.to(self.device)

        optimizer, scheduler = None, None

        for epoch in range(1, epochs + 1):
            # Phase switch: rebuild optimizer+scheduler at each phase boundary
            for ph_idx, (ph_start, ph_end, ph_layers) in enumerate(self._PHASES):
                if epoch == ph_start:
                    freeze_bottom_layers(self.model, keep_top_n=ph_layers)
                    ph_lr = [self._base_lr, 1e-5, 5e-6][ph_idx]
                    ph_epochs = ph_end - ph_start + 1
                    optimizer, scheduler = self._build_optimizer_scheduler(
                        ph_lr, len(train_loader), ph_epochs, warmup_ratio,
                    )
                    n_trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
                    print(f"\n--- Phase {ph_idx + 1}: top-{ph_layers} unfrozen | "
                          f"{n_trainable:,} trainable | lr={ph_lr:.1e} | "
                          f"steps/ep={len(train_loader)} ---")
                    break

            t0 = time.time()
            self.model.train()
            epoch_losses = []

            pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{epochs}", leave=False)
            for ids, mask, price_lbl, bin_lbl in pbar:
                ids = ids.to(self.device)
                mask = mask.to(self.device)
                price_lbl = price_lbl.to(self.device)
                bin_lbl = bin_lbl.to(self.device)

                optimizer.zero_grad()
                if scaler:
                    with autocast(device_type="cuda"):
                        pred, bin_logits = self.model(ids, mask)
                        if r_drop_alpha > 0:
                            pred2, bin_logits2 = self.model(ids, mask)
                            loss = (
                                0.5 * (huber_fn(pred, price_lbl) + huber_fn(pred2, price_lbl))
                                + aux_alpha * 0.5 * (ce_fn(bin_logits, bin_lbl) + ce_fn(bin_logits2, bin_lbl))
                                + r_drop_alpha * ((pred - pred2) ** 2).mean()
                            )
                        else:
                            loss = (huber_fn(pred, price_lbl)
                                    + aux_alpha * ce_fn(bin_logits, bin_lbl))
                    scaler.scale(loss).backward()
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        [p for p in self.model.parameters() if p.requires_grad],
                        max_grad_norm,
                    )
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    pred, bin_logits = self.model(ids, mask)
                    if r_drop_alpha > 0:
                        pred2, bin_logits2 = self.model(ids, mask)
                        loss = (
                            0.5 * (huber_fn(pred, price_lbl) + huber_fn(pred2, price_lbl))
                            + aux_alpha * 0.5 * (ce_fn(bin_logits, bin_lbl) + ce_fn(bin_logits2, bin_lbl))
                            + r_drop_alpha * ((pred - pred2) ** 2).mean()
                        )
                    else:
                        loss = (huber_fn(pred, price_lbl)
                                + aux_alpha * ce_fn(bin_logits, bin_lbl))
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(
                        [p for p in self.model.parameters() if p.requires_grad],
                        max_grad_norm,
                    )
                    optimizer.step()

                scheduler.step()
                self.ema_model.update_parameters(self.model)
                epoch_losses.append(loss.item())
                pbar.set_postfix(loss=f"{loss.item():.4f}")

            # Eval on full val (3926) with EMA model
            self.ema_model.eval()
            val_preds_list, val_losses_list = [], []
            with torch.no_grad():
                for i in range(0, len(val_ids), 48):
                    b_ids = val_ids[i:i + 48].to(self.device)
                    b_mask = val_mask[i:i + 48].to(self.device)
                    b_price = y_val_norm_dev[i:i + 48]
                    if scaler:
                        with autocast(device_type="cuda"):
                            pred, _ = self.ema_model(b_ids, b_mask)
                    else:
                        pred, _ = self.ema_model(b_ids, b_mask)
                    val_losses_list.append(huber_fn(pred.float(), b_price).item())
                    val_preds_list.append(pred.float().cpu())

            val_preds_t = torch.cat(val_preds_list)
            val_loss = float(np.mean(val_losses_list))
            val_pred_orig = torch.exp(val_preds_t * self.y_std + self.y_mean) - 1
            val_mae = torch.abs(val_pred_orig - self._y_val).mean().item()
            current_lr = scheduler.get_last_lr()[0]

            self.history["train_loss"].append(float(np.mean(epoch_losses)))
            self.history["val_loss"].append(val_loss)
            self.history["val_mae"].append(val_mae)
            self.history["lr"].append(current_lr)

            elapsed = time.time() - t0
            print(
                f"Epoch {epoch:2d}/{epochs} ({elapsed:.0f}s) | "
                f"train_loss={np.mean(epoch_losses):.4f} | "
                f"val_loss={val_loss:.4f} | val_mae={val_mae:.2f}k | "
                f"lr={current_lr:.2e}"
            )

            if val_mae < best_val_mae:
                best_val_mae = val_mae
                best_ema_state = {
                    k: v.cpu().clone() for k, v in self.ema_model.state_dict().items()
                }
                patience_counter = 0
                print(f"  ** best val_mae={best_val_mae:.2f}k")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"  Early stopping at epoch {epoch}. Best val_mae={best_val_mae:.2f}k")
                    break

        self.ema_model.load_state_dict(best_ema_state)
        self.ema_model.to(self.device)
        print(f"Restored best EMA: val_mae={best_val_mae:.2f}k")
        return self.history

    def val_predictions(self):
        """Predict on full val set (3926). Returns list[float]."""
        self.ema_model.eval()
        val_ids = self._val_enc["input_ids"]
        val_mask = self._val_enc["attention_mask"]
        preds = []
        with torch.no_grad():
            for i in tqdm(range(0, len(val_ids), 48), desc="val_predictions", leave=False):
                b_ids = val_ids[i:i + 48].to(self.device)
                b_mask = val_mask[i:i + 48].to(self.device)
                if self.device.type == "cuda":
                    with autocast(device_type="cuda"):
                        pred, _ = self.ema_model(b_ids, b_mask)
                else:
                    pred, _ = self.ema_model(b_ids, b_mask)
                pred_orig = (torch.exp(pred.float() * self.y_std + self.y_mean) - 1).clamp(min=0)
                preds.extend(pred_orig.cpu().squeeze().tolist())
        return preds

    def test_predictions(self, test_items):
        """Tokenize + predict test set. Returns list[float]."""
        self.ema_model.eval()
        test_enc = self.tokenizer(
            [item.summary for item in test_items],
            truncation=True, padding="max_length",
            max_length=self._max_length, return_tensors="pt",
        )
        test_ids = test_enc["input_ids"]
        test_mask = test_enc["attention_mask"]
        preds = []
        with torch.no_grad():
            for i in tqdm(range(0, len(test_ids), 48), desc="test_predictions", leave=False):
                b_ids = test_ids[i:i + 48].to(self.device)
                b_mask = test_mask[i:i + 48].to(self.device)
                if self.device.type == "cuda":
                    with autocast(device_type="cuda"):
                        pred, _ = self.ema_model(b_ids, b_mask)
                else:
                    pred, _ = self.ema_model(b_ids, b_mask)
                pred_orig = (torch.exp(pred.float() * self.y_std + self.y_mean) - 1).clamp(min=0)
                preds.extend(pred_orig.cpu().squeeze().tolist())
        return preds

    def save(self, path):
        torch.save({
            "ema_state_dict": self.ema_model.state_dict(),
            "y_mean": self.y_mean,
            "y_std": self.y_std,
            "model_name": self._model_name,
            "price_bin_boundaries": _BIN_BOUNDARIES.tolist(),
        }, path)

    def load(self, path):
        """Load EMA weights + normalization stats. Call after setup()."""
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self.ema_model.load_state_dict(ckpt["ema_state_dict"])
        self.y_mean = ckpt["y_mean"]
        self.y_std = ckpt["y_std"]
        self.ema_model.to(self.device)

    def inference(self, item):
        """Predict price for a single item. Returns float (k VND)."""
        self.ema_model.eval()
        enc = self.tokenizer(
            [item.summary], truncation=True, padding="max_length",
            max_length=self._max_length, return_tensors="pt",
        )
        with torch.no_grad():
            pred, _ = self.ema_model(
                enc["input_ids"].to(self.device),
                enc["attention_mask"].to(self.device),
            )
            return max(5.0, (torch.exp(pred.float() * self.y_std + self.y_mean) - 1).item())
