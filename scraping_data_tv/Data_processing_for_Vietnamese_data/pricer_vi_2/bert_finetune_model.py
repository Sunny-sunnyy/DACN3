"""BERT fine-tune (top-K layers unfrozen) + regression head — Vietnamese price prediction.

Architecture: AutoModel with bottom layers frozen → mean_pooling
              → price regression head + aux category classification head.
Techniques (Day 4 v7 Vietnamese pipeline, Phase 4 AITeamVN approach):
  - LLRD (Layer-wise Learning Rate Decay, decay=0.9 per layer)
  - EMA (Exponential Moving Average, decay=0.999)
  - Huber Loss (delta=1.0, robust to price outliers)
  - AMP (Automatic Mixed Precision with GradScaler)
  - Cosine LR schedule with linear warmup
  - Multi-task aux category head (alpha=0.1, regularization)
  - Early stopping on full val MAE (3926 samples)

Target: log1p(price) → z-normalize → HuberLoss.
De-normalize: exp(pred * std + mean) - 1 → k VND.
history keys: train_loss, val_loss, val_mae, lr — compatible with evaluator.plot_training_history.
"""

import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torch.amp import autocast, GradScaler
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn
from sklearn.preprocessing import LabelEncoder
from transformers import AutoModel, AutoTokenizer, get_cosine_schedule_with_warmup
from tqdm import tqdm


def mean_pooling(model_output, attention_mask):
    """Mean pool last hidden state over non-padding tokens."""
    token_embeddings = model_output.last_hidden_state
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return (token_embeddings * mask_expanded).sum(1) / mask_expanded.sum(1).clamp(min=1e-9)


class BERTFineTuneRegressor(nn.Module):
    """AutoModel backbone + mean_pooling + price head + aux category head.

    price_head: LayerNorm → Linear(h, 256) → GELU → Dropout → Linear(256, 1)
    category_head: Linear(h, num_categories)  — multi-task regularization
    """

    def __init__(self, model_name, num_categories, dropout=0.2):
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
        self.category_head = nn.Linear(h, num_categories)
        self._init_heads()

    def _init_heads(self):
        for m in self.price_head:
            if isinstance(m, nn.Linear):
                if m.out_features == 1:
                    nn.init.normal_(m.weight, std=0.01)
                else:
                    nn.init.xavier_normal_(m.weight)
                nn.init.zeros_(m.bias)
        nn.init.xavier_normal_(self.category_head.weight)
        nn.init.zeros_(self.category_head.bias)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = mean_pooling(outputs, attention_mask)
        return self.price_head(pooled), self.category_head(pooled)


def freeze_bottom_layers(model, keep_top_n=4):
    """Freeze embeddings + all transformer layers except top N.

    For AITeamVN (24 layers), keep_top_n=4 → ~15M trainable params from encoder.
    """
    bert = model.bert
    for p in bert.embeddings.parameters():
        p.requires_grad = False
    num_layers = len(bert.encoder.layer)
    for i, layer in enumerate(bert.encoder.layer):
        trainable = i >= (num_layers - keep_top_n)
        for p in layer.parameters():
            p.requires_grad = trainable
    if hasattr(bert, "pooler") and bert.pooler is not None:
        for p in bert.pooler.parameters():
            p.requires_grad = False


def build_llrd_param_groups(model, base_lr=2e-5, decay=0.9, weight_decay=0.02):
    """Build AdamW param groups with Layer-wise LR Decay.

    Heads: base_lr. Encoder layer i: base_lr * decay^(num_layers - i - 1).
    Embeddings: base_lr * decay^num_layers (frozen → no group added).
    No-decay params (bias, LayerNorm): weight_decay=0.
    """
    no_decay = ("bias", "LayerNorm.weight")
    groups = []

    # Heads (price + category)
    head_params = list(model.price_head.named_parameters()) + \
                  list(model.category_head.named_parameters())
    groups.append({
        "params": [p for n, p in head_params if not any(nd in n for nd in no_decay)],
        "lr": base_lr, "weight_decay": weight_decay,
    })
    groups.append({
        "params": [p for n, p in head_params if any(nd in n for nd in no_decay)],
        "lr": base_lr, "weight_decay": 0.0,
    })

    # Encoder layers (only unfrozen)
    bert = model.bert
    num_layers = len(bert.encoder.layer)
    for i, layer in enumerate(bert.encoder.layer):
        trainable_params = [(n, p) for n, p in layer.named_parameters() if p.requires_grad]
        if not trainable_params:
            continue
        lr_i = base_lr * (decay ** (num_layers - i - 1))
        groups.append({
            "params": [p for n, p in trainable_params if not any(nd in n for nd in no_decay)],
            "lr": lr_i, "weight_decay": weight_decay,
        })
        groups.append({
            "params": [p for n, p in trainable_params if any(nd in n for nd in no_decay)],
            "lr": lr_i, "weight_decay": 0.0,
        })

    return [g for g in groups if g["params"]]


class _MultiTaskDataset(Dataset):
    def __init__(self, input_ids, attention_mask, price_labels, cat_labels):
        self.input_ids = input_ids
        self.attention_mask = attention_mask
        self.price_labels = price_labels
        self.cat_labels = cat_labels

    def __len__(self):
        return len(self.price_labels)

    def __getitem__(self, idx):
        return (
            self.input_ids[idx],
            self.attention_mask[idx],
            self.price_labels[idx],
            self.cat_labels[idx],
        )


class BERTFinetuneRunner:
    """Fine-tune top-K transformer layers for Vietnamese price regression.

    Usage:
        runner = BERTFinetuneRunner(train, val)
        runner.setup("AITeamVN/Vietnamese_Embedding", keep_top_layers=4, batch_size=32)
        history = runner.train(epochs=10, patience=3)
        val_preds = runner.val_predictions()
        test_preds = runner.test_predictions(test)
        runner.save("weights/aitvn_finetune.pth")
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

        np.random.seed(42)
        torch.manual_seed(42)

    def setup(self, model_name, keep_top_layers=4, batch_size=32, max_length=256,
              base_lr=2e-5, weight_decay=0.02, llrd_decay=0.9, dropout=0.2):
        """Load model + tokenizer, tokenize all data, configure optimizer groups."""
        self._model_name = model_name
        self._keep_top_layers = keep_top_layers
        self._batch_size = batch_size
        self._max_length = max_length
        self._base_lr = base_lr
        self._weight_decay = weight_decay
        self._llrd_decay = llrd_decay

        print(f"Loading tokenizer: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Category label encoding for aux head
        train_cats = [item.category for item in self.train_items]
        self._cat_label_encoder = LabelEncoder()
        cat_train = self._cat_label_encoder.fit_transform(train_cats)
        cat_val = self._cat_label_encoder.transform(
            [item.category for item in self.val_items]
        )
        num_categories = len(self._cat_label_encoder.classes_)
        print(f"Categories ({num_categories}): {list(self._cat_label_encoder.classes_)}")

        # Tokenize (stored as tensors — 269K × 256 × 2 ≈ 550MB)
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
        print(f"Target: mean={self.y_mean:.4f}, std={self.y_std:.4f} | "
              f"norm range [{self._y_train_norm.min():.2f}, {self._y_train_norm.max():.2f}]")

        self._cat_train_t = torch.LongTensor(cat_train)
        self._cat_val_t = torch.LongTensor(cat_val)

        # Model
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
        """Train with LLRD + EMA + Huber + AMP + cosine warmup. Early stop on val MAE.

        r_drop_alpha > 0 enables R-Drop: forward twice per step, add MSE consistency
        loss between the two predictions to improve robustness against dropout noise.
        """
        dataset = _MultiTaskDataset(
            self._train_enc["input_ids"],
            self._train_enc["attention_mask"],
            self._y_train_norm,
            self._cat_train_t,
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

        self.ema_model = AveragedModel(
            self.model, multi_avg_fn=get_ema_multi_avg_fn(ema_decay),
        )
        self.ema_model.to(self.device)

        huber_fn = nn.HuberLoss(delta=huber_delta)
        ce_fn = nn.CrossEntropyLoss()
        scaler = GradScaler("cuda") if self.device.type == "cuda" else None

        num_layers = len(self.model.bert.encoder.layer)
        emb_lr = self._base_lr * (self._llrd_decay ** num_layers)
        print(
            f"Train: batch={self._batch_size} | steps/ep={len(train_loader)} | "
            f"total={total_steps} | warmup={warmup_steps}"
        )
        print(
            f"LLRD: base={self._base_lr:.1e}, decay={self._llrd_decay}, "
            f"emb_lr={emb_lr:.2e} | EMA={ema_decay} | Huber delta={huber_delta} | "
            f"aux_alpha={aux_alpha} | R-Drop={r_drop_alpha}"
        )

        self.history = {"train_loss": [], "val_loss": [], "val_mae": [], "lr": []}
        best_val_mae = float("inf")
        best_ema_state = None
        patience_counter = 0

        val_ids = self._val_enc["input_ids"]
        val_mask = self._val_enc["attention_mask"]
        y_val_norm_dev = self._y_val_norm.to(self.device)
        y_val_dev = self._y_val.to(self.device)

        for epoch in range(1, epochs + 1):
            t0 = time.time()
            self.model.train()
            epoch_losses = []

            pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{epochs}", leave=False)
            for ids, mask, price_lbl, cat_lbl in pbar:
                ids = ids.to(self.device)
                mask = mask.to(self.device)
                price_lbl = price_lbl.to(self.device)
                cat_lbl = cat_lbl.to(self.device)

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
                            loss = (huber_fn(pred, price_lbl)
                                    + aux_alpha * ce_fn(cat_logits, cat_lbl))
                    scaler.scale(loss).backward()
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        [p for p in self.model.parameters() if p.requires_grad],
                        max_grad_norm,
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
                        loss = (huber_fn(pred, price_lbl)
                                + aux_alpha * ce_fn(cat_logits, cat_lbl))
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
