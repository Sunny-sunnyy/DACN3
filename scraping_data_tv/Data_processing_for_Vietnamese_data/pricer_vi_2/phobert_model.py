"""PhoBERT fine-tune (top-K layers) + regression head — Vietnamese price prediction.

Requires Underthesea word segmentation before PhoBERT tokenizer.
Reuses BERTFineTuneRegressor, freeze_bottom_layers, build_llrd_param_groups
from bert_finetune_model.py — only PhoBERTRunner is new here.

Techniques: LLRD + EMA(0.999) + HuberLoss(delta=1.0) + AMP + CosineWarmup + aux category head.
Target: log1p(price) → z-normalize → HuberLoss. De-norm: exp(pred*std+mean)-1.
history keys: train_loss, val_loss, val_mae, lr — compatible with evaluator.plot_training_history.
"""

import time
import joblib
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from torch.utils.data import DataLoader
from torch.amp import autocast, GradScaler
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn
from sklearn.preprocessing import LabelEncoder
from transformers import AutoTokenizer, get_cosine_schedule_with_warmup
from tqdm import tqdm

from pricer_vi_2.bert_finetune_model import (
    BERTFineTuneRegressor,
    freeze_bottom_layers,
    build_llrd_param_groups,
    _MultiTaskDataset,
)

PHOBERT_BASE = "vinai/phobert-base-v2"
PHOBERT_LARGE = "vinai/phobert-large"


def word_segment(texts, cache_path=None):
    """Word-segment Vietnamese texts with Underthesea. Load from cache if exists.

    Args:
        texts: list[str] — raw Vietnamese summaries
        cache_path: Path or None — pkl cache location

    Returns:
        list[str] — word-segmented texts (words joined by space)
    """
    if cache_path is not None and Path(cache_path).exists():
        print(f"Loading word-segment cache: {cache_path}")
        return joblib.load(cache_path)

    from underthesea import word_tokenize
    print(f"Word-segmenting {len(texts):,} texts (Underthesea)...")
    segmented = [word_tokenize(t, format="text") for t in tqdm(texts, desc="word_segment")]

    if cache_path is not None:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(segmented, cache_path)
        print(f"Cached to {cache_path}")

    return segmented


class PhoBERTRunner:
    """Fine-tune PhoBERT (top-K layers) for Vietnamese price regression.

    Identical training loop to BERTFinetuneRunner but adds Underthesea
    word segmentation before tokenization (required by PhoBERT).

    Usage:
        runner = PhoBERTRunner(train, val)
        runner.setup(PHOBERT_BASE, keep_top_layers=4,
                     train_seg_cache=Path("cache/seg_train.pkl"),
                     val_seg_cache=Path("cache/seg_val.pkl"))
        history = runner.train(epochs=10, patience=3)
        val_preds = runner.val_predictions()
        test_preds = runner.test_predictions(test, seg_cache=Path("cache/seg_test.pkl"))
        runner.save("weights/phobert_base_top4.pth")
    """

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
        self._keep_top_layers = None
        self._cat_label_encoder = None
        self._batch_size = None
        self._max_length = None
        self._base_lr = None
        self._weight_decay = None
        self._llrd_decay = None

        np.random.seed(42)
        torch.manual_seed(42)

    def setup(self, model_name=PHOBERT_BASE, keep_top_layers=4, batch_size=64,
              max_length=256, base_lr=2e-5, weight_decay=0.02, llrd_decay=0.9,
              dropout=0.2, train_seg_cache=None, val_seg_cache=None):
        """Word-segment → tokenize all data → build PhoBERT model with LLRD param groups.

        Args:
            train_seg_cache: Path or None — pkl cache for word-segmented train texts
            val_seg_cache:   Path or None — pkl cache for word-segmented val texts
        """
        self._model_name = model_name
        self._keep_top_layers = keep_top_layers
        self._batch_size = batch_size
        self._max_length = max_length
        self._base_lr = base_lr
        self._weight_decay = weight_decay
        self._llrd_decay = llrd_decay

        # Category label encoding for aux head
        self._cat_label_encoder = LabelEncoder()
        cat_train = self._cat_label_encoder.fit_transform([i.category for i in self.train_items])
        cat_val = self._cat_label_encoder.transform([i.category for i in self.val_items])
        num_categories = len(self._cat_label_encoder.classes_)
        print(f"Categories ({num_categories}): {list(self._cat_label_encoder.classes_)}")

        # Word segmentation (mandatory for PhoBERT)
        train_texts = word_segment(
            [i.summary for i in self.train_items], cache_path=train_seg_cache
        )
        val_texts = word_segment(
            [i.summary for i in self.val_items], cache_path=val_seg_cache
        )

        # Tokenize
        print(f"Loading tokenizer: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        print(f"Tokenizing train ({len(train_texts):,}) — ~2-3 min ...")
        self._train_enc = self.tokenizer(
            train_texts, truncation=True, padding="max_length",
            max_length=max_length, return_tensors="pt",
        )
        print(f"Tokenizing val ({len(val_texts):,}) ...")
        self._val_enc = self.tokenizer(
            val_texts, truncation=True, padding="max_length",
            max_length=max_length, return_tensors="pt",
        )

        # Target: log1p + z-normalize (mirrors bert_finetune_model.py)
        y_train = torch.FloatTensor([i.price for i in self.train_items]).unsqueeze(1)
        y_val = torch.FloatTensor([i.price for i in self.val_items]).unsqueeze(1)
        y_train_log = torch.log(y_train + 1)
        self.y_mean = y_train_log.mean()
        self.y_std = y_train_log.std()
        self._y_train_norm = (y_train_log - self.y_mean) / self.y_std
        self._y_val = y_val
        self._y_val_norm = (torch.log(y_val + 1) - self.y_mean) / self.y_std
        print(f"Target: mean={self.y_mean:.4f}, std={self.y_std:.4f} | "
              f"norm range [{self._y_train_norm.min():.2f}, {self._y_train_norm.max():.2f}]")

        self._cat_train_t = torch.LongTensor(cat_train)
        self._cat_val_t = torch.LongTensor(cat_val)

        # Model: reuse BERTFineTuneRegressor from bert_finetune_model.py
        print(f"Loading model: {model_name}")
        self.model = BERTFineTuneRegressor(model_name, num_categories, dropout=dropout)
        freeze_bottom_layers(self.model, keep_top_n=keep_top_layers)
        n_trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        n_total = sum(p.numel() for p in self.model.parameters())
        num_layers = len(self.model.bert.encoder.layer)
        print(f"Params: {n_trainable:,}/{n_total:,} trainable | "
              f"top {keep_top_layers}/{num_layers} layers unfrozen | "
              f"hidden={self.model.bert.config.hidden_size}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Device: {self.device}")
        self.model.to(self.device)

    def train(self, epochs=10, patience=3, huber_delta=1.0, aux_alpha=0.1,
              ema_decay=0.999, warmup_ratio=0.1, max_grad_norm=1.0, r_drop_alpha=0.0):
        """Train with LLRD + EMA + Huber + AMP + CosineWarmup. Early stop on val MAE.

        r_drop_alpha > 0 enables R-Drop: forward twice per step, add MSE consistency
        loss between the two predictions to improve robustness against dropout noise.
        """
        dataset = _MultiTaskDataset(
            self._train_enc["input_ids"], self._train_enc["attention_mask"],
            self._y_train_norm, self._cat_train_t,
        )
        train_loader = DataLoader(
            dataset, batch_size=self._batch_size,
            shuffle=True, num_workers=0, pin_memory=True,
        )

        param_groups = build_llrd_param_groups(
            self.model, base_lr=self._base_lr,
            decay=self._llrd_decay, weight_decay=self._weight_decay,
        )
        optimizer = torch.optim.AdamW(param_groups)
        total_steps = len(train_loader) * epochs
        warmup_steps = int(total_steps * warmup_ratio)
        scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

        self.ema_model = AveragedModel(self.model, multi_avg_fn=get_ema_multi_avg_fn(ema_decay))
        self.ema_model.to(self.device)

        huber_fn = nn.HuberLoss(delta=huber_delta)
        ce_fn = nn.CrossEntropyLoss()
        scaler = GradScaler("cuda") if self.device.type == "cuda" else None

        num_layers = len(self.model.bert.encoder.layer)
        emb_lr = self._base_lr * (self._llrd_decay ** num_layers)
        print(f"Train: batch={self._batch_size} | steps/ep={len(train_loader)} | "
              f"total={total_steps} | warmup={warmup_steps}")
        print(f"LLRD: base={self._base_lr:.1e}, decay={self._llrd_decay}, "
              f"emb_lr={emb_lr:.2e} | EMA={ema_decay} | Huber delta={huber_delta} | R-Drop={r_drop_alpha}")

        self.history = {"train_loss": [], "val_loss": [], "val_mae": [], "lr": []}
        best_val_mae = float("inf")
        best_ema_state = None
        patience_counter = 0

        val_ids = self._val_enc["input_ids"]
        val_mask = self._val_enc["attention_mask"]
        y_val_norm_dev = self._y_val_norm.to(self.device)

        for epoch in range(1, epochs + 1):
            t0 = time.time()
            self.model.train()
            epoch_losses = []

            pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{epochs}", leave=False)
            for ids, mask, price_lbl, cat_lbl in pbar:
                ids, mask = ids.to(self.device), mask.to(self.device)
                price_lbl, cat_lbl = price_lbl.to(self.device), cat_lbl.to(self.device)

                optimizer.zero_grad()
                if scaler:
                    with autocast(device_type="cuda"):
                        pred, cat_logits = self.model(ids, mask)
                        if r_drop_alpha > 0:
                            pred2, cat_logits2 = self.model(ids, mask)
                            loss = (
                                0.5 * (huber_fn(pred, price_lbl) + huber_fn(pred2, price_lbl))
                                + aux_alpha * 0.5 * (ce_fn(cat_logits, cat_lbl) + ce_fn(cat_logits2, cat_lbl))
                                + r_drop_alpha * ((pred - pred2) ** 2).mean()
                            )
                        else:
                            loss = huber_fn(pred, price_lbl) + aux_alpha * ce_fn(cat_logits, cat_lbl)
                    scaler.scale(loss).backward()
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        [p for p in self.model.parameters() if p.requires_grad], max_grad_norm,
                    )
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    pred, cat_logits = self.model(ids, mask)
                    if r_drop_alpha > 0:
                        pred2, cat_logits2 = self.model(ids, mask)
                        loss = (
                            0.5 * (huber_fn(pred, price_lbl) + huber_fn(pred2, price_lbl))
                            + aux_alpha * 0.5 * (ce_fn(cat_logits, cat_lbl) + ce_fn(cat_logits2, cat_lbl))
                            + r_drop_alpha * ((pred - pred2) ** 2).mean()
                        )
                    else:
                        loss = huber_fn(pred, price_lbl) + aux_alpha * ce_fn(cat_logits, cat_lbl)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(
                        [p for p in self.model.parameters() if p.requires_grad], max_grad_norm,
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
                for i in range(0, len(val_ids), 64):
                    b_ids = val_ids[i:i + 64].to(self.device)
                    b_mask = val_mask[i:i + 64].to(self.device)
                    b_price = y_val_norm_dev[i:i + 64]
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
            print(f"Epoch {epoch:2d}/{epochs} ({elapsed:.0f}s) | "
                  f"train_loss={np.mean(epoch_losses):.4f} | "
                  f"val_loss={val_loss:.4f} | val_mae={val_mae:.2f}k | "
                  f"lr={current_lr:.2e}")

            if val_mae < best_val_mae:
                best_val_mae = val_mae
                best_ema_state = {k: v.cpu().clone() for k, v in self.ema_model.state_dict().items()}
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
        """Predict on full val set (3926) using stored tokenized tensors. Returns list[float]."""
        self.ema_model.eval()
        val_ids = self._val_enc["input_ids"]
        val_mask = self._val_enc["attention_mask"]
        preds = []
        with torch.no_grad():
            for i in tqdm(range(0, len(val_ids), 64), desc="val_predictions", leave=False):
                b_ids = val_ids[i:i + 64].to(self.device)
                b_mask = val_mask[i:i + 64].to(self.device)
                if self.device.type == "cuda":
                    with autocast(device_type="cuda"):
                        pred, _ = self.ema_model(b_ids, b_mask)
                else:
                    pred, _ = self.ema_model(b_ids, b_mask)
                pred_orig = (torch.exp(pred.float() * self.y_std + self.y_mean) - 1).clamp(min=0)
                preds.extend(pred_orig.cpu().squeeze().tolist())
        return preds

    def test_predictions(self, test_items, seg_cache=None):
        """Word-segment + tokenize test set, then predict. Returns list[float]."""
        test_texts = word_segment([i.summary for i in test_items], cache_path=seg_cache)
        test_enc = self.tokenizer(
            test_texts, truncation=True, padding="max_length",
            max_length=self._max_length, return_tensors="pt",
        )
        self.ema_model.eval()
        test_ids, test_mask = test_enc["input_ids"], test_enc["attention_mask"]
        preds = []
        with torch.no_grad():
            for i in tqdm(range(0, len(test_ids), 64), desc="test_predictions", leave=False):
                b_ids = test_ids[i:i + 64].to(self.device)
                b_mask = test_mask[i:i + 64].to(self.device)
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
            "keep_top_layers": self._keep_top_layers,
            "cat_classes": self._cat_label_encoder.classes_.tolist(),
        }, path)

    def load(self, path):
        """Load EMA weights + normalization stats. Call after setup()."""
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self.ema_model.load_state_dict(ckpt["ema_state_dict"])
        self.y_mean = ckpt["y_mean"]
        self.y_std = ckpt["y_std"]
        self.ema_model.to(self.device)

    def inference(self, item):
        """Predict price for single item. Returns float (k VND)."""
        from underthesea import word_tokenize
        self.ema_model.eval()
        text = word_tokenize(item.summary, format="text")
        enc = self.tokenizer(
            [text], truncation=True, padding="max_length",
            max_length=self._max_length, return_tensors="pt",
        )
        with torch.no_grad():
            pred, _ = self.ema_model(
                enc["input_ids"].to(self.device),
                enc["attention_mask"].to(self.device),
            )
            return max(5.0, (torch.exp(pred.float() * self.y_std + self.y_mean) - 1).item())
