"""Training utilities for Qwen V2 Vietnamese price fine-tuning.

Contains: BnB 4-bit config, LoRA config, SFTConfig tuned for RTX 5090 32GB,
DataCollatorCompletionOnly (replacement for TRL's removed DataCollatorForCompletionOnlyLM),
and MaeEvalCallback that picks best checkpoint by generative MAE on val set.
"""
import re

import numpy as np
import torch
from peft import LoraConfig
from transformers import BitsAndBytesConfig, TrainerCallback
from trl import SFTConfig

# Hyperparameters - English recipe (proven), tuned for RTX 5090 32GB
LORA_R = 64
LORA_ALPHA = 128          # 2 x r
LORA_DROPOUT = 0.1
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj",
                  "gate_proj", "up_proj", "down_proj"]
MAX_SEQ_LENGTH = 192
EPOCHS = 3
LEARNING_RATE = 2e-4
WARMUP_RATIO = 0.03
WEIGHT_DECAY = 0.001
MAX_GRAD_NORM = 0.3
PER_DEVICE_BATCH = 32     # 5090 32GB allows 2x of 3090Ti
GRAD_ACCUM = 2            # effective batch = 64 (same as English recipe)
LOG_STEPS = 10
SAVE_STEPS = 500
EVAL_MAE_STEPS = 500
VAL_EVAL_SIZE = 500       # val samples for MAE callback
MAX_NEW_TOKENS = 8        # Qwen tokenizes digit-by-digit; +space/newline safety

# Token sequence after which completion "55" begins; data collator masks
# everything before this with -100 so loss only flows through completion tokens.
RESPONSE_TEMPLATE = "\nGiá là: "


def get_bnb_config() -> BitsAndBytesConfig:
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4",
    )


def get_lora_config() -> LoraConfig:
    return LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        bias="none",
        task_type="CAUSAL_LM",
    )


def get_sft_config(output_dir: str, hub_model_id: str | None = None) -> SFTConfig:
    return SFTConfig(
        output_dir=output_dir,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=PER_DEVICE_BATCH,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=GRAD_ACCUM,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="paged_adamw_32bit",
        save_strategy="steps",
        save_steps=SAVE_STEPS,
        save_total_limit=6,
        logging_steps=LOG_STEPS,
        learning_rate=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        bf16=True,
        fp16=False,
        max_grad_norm=MAX_GRAD_NORM,
        warmup_ratio=WARMUP_RATIO,
        lr_scheduler_type="cosine",
        report_to="wandb",
        max_length=MAX_SEQ_LENGTH,
        eval_strategy="no",
        push_to_hub=False,
        hub_model_id=hub_model_id,
    )


class DataCollatorCompletionOnly:
    """Mask prompt tokens with -100; compute loss only on completion tokens.

    Replaces DataCollatorForCompletionOnlyLM which was removed from TRL 0.24.
    Finds RESPONSE_TEMPLATE in each sequence; everything before set to -100.
    """

    def __init__(self, tokenizer, response_template: str = RESPONSE_TEMPLATE):
        self.tokenizer = tokenizer
        self.template_ids: list[int] = tokenizer.encode(
            response_template, add_special_tokens=False
        )

    def _find_response_start(self, seq: list[int]) -> int | None:
        tpl = self.template_ids
        n = len(tpl)
        for j in range(len(seq) - n + 1):
            if seq[j:j + n] == tpl:
                return j + n
        return None

    def __call__(self, features: list[dict]) -> dict:
        batch = self.tokenizer.pad(
            [{"input_ids": f["input_ids"],
              "attention_mask": f["attention_mask"]} for f in features],
            return_tensors="pt",
            padding=True,
        )
        labels = batch["input_ids"].clone()
        for i, seq in enumerate(batch["input_ids"]):
            resp_start = self._find_response_start(seq.tolist())
            if resp_start is None:
                labels[i] = torch.full_like(labels[i], -100)
            else:
                labels[i, :resp_start] = -100
        batch["labels"] = labels
        return batch


class MaeEvalCallback(TrainerCallback):
    """Eval generative MAE on val_items every eval_steps.

    Saves best checkpoint (by MAE) to output_dir/best_mae_checkpoint.
    Records history: step -> mae K VND.

    Toggles use_cache=True temporarily during generate (training keeps
    use_cache=False for gradient checkpointing).
    """

    def __init__(
        self,
        model,
        tokenizer,
        val_items,
        output_dir: str,
        eval_steps: int = EVAL_MAE_STEPS,
        max_new_tokens: int = MAX_NEW_TOKENS,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.val_items = val_items
        self.output_dir = output_dir
        self.eval_steps = eval_steps
        self.max_new_tokens = max_new_tokens
        self.best_mae = float("inf")
        self.best_step = 0
        self.history: list[tuple[int, float]] = []

    def _predict_k(self, prompt: str) -> float:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        prompt_len = inputs["input_ids"].shape[1]
        text = self.tokenizer.decode(
            out[0, prompt_len:], skip_special_tokens=True
        ).strip()
        m = re.search(r"\d+\.?\d*", text)
        return float(m.group()) if m else 0.0

    def on_step_end(self, args, state, control, **kwargs):
        if state.global_step == 0 or state.global_step % self.eval_steps != 0:
            return
        prev_cache = self.model.config.use_cache
        self.model.config.use_cache = True
        self.model.eval()
        try:
            errors = [
                abs(self._predict_k(item.prompt) - item.price)
                for item in self.val_items
            ]
            mae = float(np.mean(errors))
            self.history.append((state.global_step, mae))
            print(
                f"\n[MAE callback] step={state.global_step:>5}  "
                f"mae={mae:.2f}K VND  ({mae * 1000:,.0f} VND)"
            )
            if mae < self.best_mae:
                self.best_mae = mae
                self.best_step = state.global_step
                best_path = f"{self.output_dir}/best_mae_checkpoint"
                self.model.save_pretrained(best_path)
                print(f"  -> New best! Saved to {best_path}")
        finally:
            self.model.train()
            self.model.config.use_cache = prev_cache
