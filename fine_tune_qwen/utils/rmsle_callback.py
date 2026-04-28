"""RMSLE generative eval callback cho Trainer (Day 5 v4).

Chay generative eval tren mot subset val co dinh moi `eval_steps`, tra ve
`eval_rmsle` de Trainer dung cho `metric_for_best_model="eval_rmsle"`.

Ly do ton tai: v3 da chung minh eval CE loss DIVERGE khoi RMSLE (CE day o
step ~2600 nhung RMSLE van improve sang epoch 3). Best ckpt phai chon theo
generative RMSLE, khong theo CE.
"""

from __future__ import annotations

import re
from typing import List, Optional

import numpy as np
import torch
from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments

DEFAULT_PARSE_REGEX = r"[-+]?\d*\.\d+|\d+"


class RMSLEEvalCallback(TrainerCallback):
    """Compute generative RMSLE tren `val_subset` moi lan Trainer goi evaluate.

    - Modify in-place `metrics["eval_rmsle"]` (Trainer su dung cho best-metric tracking).
    - Append entry vao `state.log_history` de notebook extract sau train.
    - Restore model.train() mode sau eval (important neu callback chay giua train).
    """

    def __init__(
        self,
        tokenizer,
        val_subset,
        max_new_tokens: int = 4,
        clamp_min: int = 5,
        clamp_max: int = 1000,
        scale_thousands: int = 1000,
        parse_regex: str = DEFAULT_PARSE_REGEX,
    ) -> None:
        self.tokenizer = tokenizer
        self.val_subset = val_subset
        self.max_new_tokens = max_new_tokens
        self.clamp_min = clamp_min
        self.clamp_max = clamp_max
        self.scale = scale_thousands
        self.parse_regex = parse_regex
        self.history: List[dict] = []

    def _predict_one(self, model, prompt: str) -> int:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            out = model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        gen = self.tokenizer.decode(
            out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        )
        m = re.search(self.parse_regex, gen)
        if not m:
            return 0
        pk = int(float(m.group()))
        return max(self.clamp_min, min(pk, self.clamp_max))

    def _compute_rmsle(self, model) -> float:
        was_training = model.training
        model.eval()
        try:
            preds_vnd: List[float] = []
            trues_vnd: List[float] = []
            for item in self.val_subset:
                pk = self._predict_one(model, item["prompt"])
                preds_vnd.append(pk * self.scale)
                trues_vnd.append(float(item["price_vnd_true"]))
        finally:
            if was_training:
                model.train()

        y_true = np.asarray(trues_vnd, dtype=float)
        y_pred = np.clip(np.asarray(preds_vnd, dtype=float), 0, None)
        return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))

    def on_evaluate(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        metrics: Optional[dict] = None,
        model=None,
        **kwargs,
    ) -> TrainerControl:
        if model is None:
            return control
        rmsle_val = self._compute_rmsle(model)
        if metrics is not None:
            metrics["eval_rmsle"] = rmsle_val
        entry = {"step": int(state.global_step), "eval_rmsle": rmsle_val}
        if state.epoch is not None:
            entry["epoch"] = float(state.epoch)
        state.log_history.append(entry)
        self.history.append(entry)
        print(
            f"[RMSLEEvalCallback] step={state.global_step} "
            f"epoch={state.epoch:.2f} eval_rmsle={rmsle_val:.4f} "
            f"(n={len(self.val_subset)})"
            if state.epoch is not None
            else f"[RMSLEEvalCallback] step={state.global_step} "
            f"eval_rmsle={rmsle_val:.4f} (n={len(self.val_subset)})"
        )
        return control
