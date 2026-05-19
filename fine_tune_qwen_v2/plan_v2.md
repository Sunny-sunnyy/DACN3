# Qwen V2 — Vietnamese Price Prediction (MAE) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fine-tune Qwen3.5-4B-Base on 269K Vietnamese product descriptions to predict prices (5K–1M VND), optimised for MAE, bám sát English Llama recipe.

**Architecture:** QLoRA 4-bit (r=64, 7 modules) on `Qwen/Qwen3.5-4B-Base`. Dataset `SeanSunny/items_prompts_tv_4` (269K train). Best checkpoint selected by eval generative MAE (every 500 steps on 500 val samples), not CE loss. Final evaluation via `VnTester` on 200 test items — charts show MAE, RMSLE, R², MSE.

**Tech Stack:** Python 3.12, `uv run`, transformers, peft, trl, bitsandbytes, datasets, plotly, sklearn, wandb. All commands: `uv run` never `python3`.

---

## Critical Lessons từ V1 (KHÔNG được bỏ qua)

| Lesson | Action |
|--------|--------|
| `torch_dtype=torch.bfloat16` BẮT BUỘC trong `from_pretrained` | Áp dụng mọi notebook |
| `DataCollatorForCompletionOnlyLM` đã bị xóa khỏi TRL 0.24 | Dùng `DataCollatorCompletionOnly` manual |
| CE loss ≠ generative MAE/RMSLE (hai chỉ số diverge) | Best checkpoint = eval **generative MAE**, KHÔNG phải CE |
| `val_eval_size=200` quá noisy | Dùng 500 val samples cho MAE callback |
| `group_by_length=False` lãng phí 10-15% time | `group_by_length=True` |
| Completion là số nguyên `"55"` (K VND) | `max_new_tokens=4` đủ |

---

## File Map

```
fine_tune_qwen_v2/
├── plan_v2.md                  # File này
├── utils/
│   ├── __init__.py             # empty
│   ├── items_vn.py             # Item dataclass + load_items()
│   ├── evaluator_vn.py         # VnTester: MAE, RMSLE, R², charts (adapted từ English evaluator.py)
│   └── training_utils.py       # BnB config, LoRA config, SFTConfig, DataCollator, MaeEvalCallback
├── 01_zero_shot.ipynb          # Baseline zero-shot MAE (chạy sau khi có thời gian)
├── 02_train_v2.ipynb           # Full training: 269K, 3 epochs, r=64, 7 modules
├── 03_eval_v2.ipynb            # Final eval: load best ckpt, 200 test items, charts
└── results/
    ├── zero_shot_results.json  # (sau khi chạy 01)
    └── v2_results.json         # (sau khi chạy 03)
```

---

## Task 1: `utils/__init__.py` + `utils/items_vn.py`

**Files:**
- Create: `fine_tune_qwen_v2/utils/__init__.py`
- Create: `fine_tune_qwen_v2/utils/items_vn.py`

- [ ] **Step 1: Tạo `__init__.py` rỗng**

```bash
touch /home/hieu0606sunny/price2026wsl/tech2ai/fine_tune_qwen_v2/utils/__init__.py
```

- [ ] **Step 2: Viết `items_vn.py`**

```python
# fine_tune_qwen_v2/utils/items_vn.py
import re
from dataclasses import dataclass
from datasets import load_dataset

DATASET_NAME = "SeanSunny/items_prompts_tv_4"


@dataclass
class Item:
    title: str
    price: float    # K VND — e.g. 55.0 for 55,000 VND
    price_vnd: int  # raw VND — e.g. 55000
    prompt: str


def _parse_title(prompt: str) -> str:
    m = re.search(r"Tiêu đề:\s*(.+)", prompt)
    return m.group(1).strip() if m else "Unknown"


def load_items(split: str, size: int | None = None) -> list[Item]:
    """Load HuggingFace split → list[Item].

    Args:
        split: "train", "validation", or "test"
        size:  max items (None = all)
    """
    ds = load_dataset(DATASET_NAME, split=split)
    if size is not None:
        ds = ds.select(range(min(size, len(ds))))
    return [
        Item(
            title=_parse_title(row["prompt"]),
            price=int(row["price_vnd_true"]) / 1000,
            price_vnd=int(row["price_vnd_true"]),
            prompt=row["prompt"],
        )
        for row in ds
    ]
```

- [ ] **Step 3: Smoke-test items_vn.py**

```python
# chạy trong Python REPL hoặc notebook cell
import sys; sys.path.insert(0, ".")
from utils.items_vn import load_items
items = load_items("test", size=5)
assert len(items) == 5
assert items[0].price == items[0].price_vnd / 1000
assert "Tiêu đề" not in items[0].title
print(items[0])
```

Expected: `Item(title='...', price=55.0, price_vnd=55000, prompt='...')`

- [ ] **Step 4: Commit**

```bash
git add fine_tune_qwen_v2/utils/
git commit -m "feat(qwen-v2): add items_vn.py — Item dataclass + load_items"
```

---

## Task 2: `utils/evaluator_vn.py`

**Files:**
- Create: `fine_tune_qwen_v2/utils/evaluator_vn.py`
- Reference: `scraping_data_tv/Data_processing_for_English_data/Code_Fine_tune/evaluator.py`

**Thay đổi so với English evaluator.py:**
- Thêm RMSLE vào `report()`
- Label axes: `K VND` thay vì `$`
- `post_process`: không cần strip `$`, parse integer/float string
- `color_for`: ngưỡng 40/80 K VND (≈ $40/$80, cùng scale)
- In lỗi dưới dạng: `55K` thay vì `$55`

- [ ] **Step 1: Viết `evaluator_vn.py`**

```python
# fine_tune_qwen_v2/utils/evaluator_vn.py
import re
import math
import numpy as np
from itertools import accumulate
from concurrent.futures import ThreadPoolExecutor
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from tqdm.notebook import tqdm

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
COLOR_MAP = {"red": RED, "orange": YELLOW, "green": GREEN}

WORKERS = 5
DEFAULT_SIZE = 200


def _rmsle(truths: list, guesses: list) -> float:
    t = np.array(truths, dtype=float)
    g = np.maximum(np.array(guesses, dtype=float), 0.0)
    return float(np.sqrt(np.mean((np.log1p(g) - np.log1p(t)) ** 2)))


class VnTester:
    """Evaluate a price predictor on Vietnamese product data.

    Operates in K VND (5–1000) to match English recipe scale.
    Computes MAE, RMSLE, R², MSE and draws scatter + error-trend charts.

    Args:
        predictor: callable(Item) -> str | float, returns price in K VND
        data:      list[Item] with .price (K VND) and .title
        title:     display name for charts
        size:      number of items to evaluate (default 200)
        workers:   ThreadPoolExecutor workers (default 5)
    """

    def __init__(self, predictor, data, title=None, size=DEFAULT_SIZE, workers=WORKERS):
        self.predictor = predictor
        self.data = data
        self.title = title or getattr(predictor, "__name__", "Model")
        self.size = min(size, len(data))
        self.workers = workers
        self.titles: list[str] = []
        self.guesses: list[float] = []   # K VND
        self.truths: list[float] = []    # K VND
        self.errors: list[float] = []    # K VND absolute error
        self.colors: list[str] = []

    @staticmethod
    def post_process(value) -> float:
        """Parse model output to float in K VND."""
        if isinstance(value, (int, float)):
            return float(value)
        m = re.search(r"[-+]?\d*\.?\d+", str(value).strip())
        return float(m.group()) if m else 0.0

    def color_for(self, error: float, truth: float) -> str:
        if error < 40 or (truth > 0 and error / truth < 0.2):
            return "green"
        elif error < 80 or (truth > 0 and error / truth < 0.4):
            return "orange"
        return "red"

    def run_datapoint(self, i: int):
        dp = self.data[i]
        guess = self.post_process(self.predictor(dp))
        truth = dp.price  # K VND
        error = abs(guess - truth)
        color = self.color_for(error, truth)
        title = dp.title[:40] + "..." if len(dp.title) > 40 else dp.title
        return title, guess, truth, error, color

    def chart(self, title: str):
        df = pd.DataFrame({
            "truth": self.truths, "guess": self.guesses,
            "title": self.titles, "error": self.errors, "color": self.colors,
        })
        df["hover"] = [
            f"{t}\nGuess={g:,.0f}K  Actual={y:,.0f}K VND"
            for t, g, y in zip(df["title"], df["guess"], df["truth"])
        ]
        max_val = float(max(df["truth"].max(), df["guess"].max()))
        fig = px.scatter(
            df, x="truth", y="guess", color="color",
            color_discrete_map={"green": "green", "orange": "orange", "red": "red"},
            title=title,
            labels={"truth": "Actual Price (K VND)", "guess": "Predicted Price (K VND)"},
            width=1000, height=800,
        )
        for tr in fig.data:
            mask = df["color"] == tr.name
            tr.customdata = df.loc[mask, ["hover"]].to_numpy()
            tr.hovertemplate = "%{customdata[0]}<extra></extra>"
            tr.marker.update(size=6)
        fig.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val], mode="lines",
            line=dict(width=2, dash="dash", color="deepskyblue"),
            hoverinfo="skip", showlegend=False,
        ))
        fig.update_xaxes(range=[0, max_val])
        fig.update_yaxes(range=[0, max_val])
        fig.update_layout(showlegend=False)
        fig.show()

    def error_trend_chart(self):
        n = len(self.errors)
        running_sums = list(accumulate(self.errors))
        x = list(range(1, n + 1))
        running_means = [s / i for s, i in zip(running_sums, x)]
        running_squares = list(accumulate(e * e for e in self.errors))
        running_stds = [
            math.sqrt((sq / i) - (m ** 2)) if i > 1 else 0.0
            for i, sq, m in zip(x, running_squares, running_means)
        ]
        ci = [1.96 * sd / math.sqrt(i) if i > 1 else 0.0 for i, sd in zip(x, running_stds)]
        upper = [m + c for m, c in zip(running_means, ci)]
        lower = [m - c for m, c in zip(running_means, ci)]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x + x[::-1], y=upper + lower[::-1],
            fill="toself", fillcolor="rgba(128,128,128,0.2)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=x, y=running_means, mode="lines",
            line=dict(width=3, color="firebrick"),
            name="Cumulative Avg Error",
            customdata=list(zip(ci)),
            hovertemplate="n=%{x}<br>Avg=%{y:,.1f}K VND<br>±95% CI=%{customdata[0]:,.1f}K<extra></extra>",
        ))
        final_mean, final_ci = running_means[-1], ci[-1]
        fig.update_layout(
            title=f"{self.title}  Error: {final_mean:,.1f}K VND ± {final_ci:,.1f}K",
            xaxis_title="Number of Datapoints",
            yaxis_title="Average Absolute Error (K VND)",
            width=1000, height=360,
            template="plotly_white", showlegend=False,
        )
        fig.show()

    def report(self):
        mae_k = sum(self.errors) / self.size
        mse = mean_squared_error(self.truths, self.guesses)
        r2 = r2_score(self.truths, self.guesses) * 100
        rmsle = _rmsle(self.truths, self.guesses)
        title = (
            f"{self.title} results<br>"
            f"<b>MAE:</b> {mae_k:,.1f}K VND ({mae_k * 1000:,.0f} VND)  "
            f"<b>RMSLE:</b> {rmsle:.4f}  "
            f"<b>MSE:</b> {mse:,.0f}  "
            f"<b>R²:</b> {r2:.1f}%"
        )
        self.error_trend_chart()
        self.chart(title)

    def run(self):
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            for t, g, y, e, c in tqdm(
                ex.map(self.run_datapoint, range(self.size)), total=self.size
            ):
                self.titles.append(t)
                self.guesses.append(g)
                self.truths.append(y)
                self.errors.append(e)
                self.colors.append(c)
                print(f"{COLOR_MAP[c]}{e:.0f}K ", end="")
        print(RESET)
        self.report()


def evaluate(predictor, data, size=DEFAULT_SIZE, workers=WORKERS):
    """Shortcut: evaluate(fn, items) → run Tester and show charts."""
    VnTester(predictor, data, size=size, workers=workers).run()
```

- [ ] **Step 2: Smoke-test evaluator_vn.py**

```python
# notebook cell hoặc REPL
import sys; sys.path.insert(0, ".")
from utils.items_vn import load_items
from utils.evaluator_vn import VnTester

items = load_items("test", size=10)

def dummy_predictor(item):
    return item.price  # perfect predictions

tester = VnTester(dummy_predictor, items, title="Dummy Perfect", size=10, workers=1)
tester.run()
# Expected: tất cả errors = 0, MAE = 0.0K VND, RMSLE = 0.0000
```

- [ ] **Step 3: Commit**

```bash
git add fine_tune_qwen_v2/utils/evaluator_vn.py
git commit -m "feat(qwen-v2): add evaluator_vn.py — VnTester with MAE/RMSLE/R2/charts"
```

---

## Task 3: `utils/training_utils.py`

**Files:**
- Create: `fine_tune_qwen_v2/utils/training_utils.py`

Chứa: BnB config, LoRA config, SFTConfig, `DataCollatorCompletionOnly`, `MaeEvalCallback`.

- [ ] **Step 1: Viết `training_utils.py`**

```python
# fine_tune_qwen_v2/utils/training_utils.py
import torch
import numpy as np
from transformers import BitsAndBytesConfig, TrainerCallback
from peft import LoraConfig
from trl import SFTConfig

# ─── Hyperparameters (English recipe, proven) ────────────────────────────────
LORA_R = 64
LORA_ALPHA = 128          # 2 × r
LORA_DROPOUT = 0.1
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj",
                  "gate_proj", "up_proj", "down_proj"]
MAX_SEQ_LENGTH = 192
EPOCHS = 3
LEARNING_RATE = 2e-4
WARMUP_RATIO = 0.03
WEIGHT_DECAY = 0.001
MAX_GRAD_NORM = 0.3
PER_DEVICE_BATCH = 16
GRAD_ACCUM = 4            # effective batch = 64
LOG_STEPS = 10
SAVE_STEPS = 500
EVAL_MAE_STEPS = 500
VAL_EVAL_SIZE = 500       # val samples cho MAE callback

# Response template — token sequence sau đó là completion "55"
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


def get_sft_config(output_dir: str, hub_model_id: str) -> SFTConfig:
    return SFTConfig(
        output_dir=output_dir,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=PER_DEVICE_BATCH,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=GRAD_ACCUM,
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
        group_by_length=True,
        lr_scheduler_type="cosine",
        report_to="wandb",
        max_length=MAX_SEQ_LENGTH,
        eval_strategy="no",   # custom MAE callback thay thế CE eval
        push_to_hub=True,
        hub_model_id=hub_model_id,
    )


class DataCollatorCompletionOnly:
    """Mask prompt tokens với -100; chỉ tính loss trên completion tokens.

    Thay thế DataCollatorForCompletionOnlyLM (đã bị xóa khỏi TRL 0.24).
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
            if seq[j : j + n] == tpl:
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
    """Eval generative MAE trên val_items mỗi eval_steps bước.

    Lưu best checkpoint (theo MAE) vào output_dir/best_mae_checkpoint.
    In history để theo dõi: step → mae K VND.
    """

    def __init__(
        self,
        model,
        tokenizer,
        val_items,                      # list[Item] từ items_vn.load_items
        output_dir: str,
        eval_steps: int = EVAL_MAE_STEPS,
        max_new_tokens: int = 4,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.val_items = val_items
        self.output_dir = output_dir
        self.eval_steps = eval_steps
        self.max_new_tokens = max_new_tokens
        self.best_mae = float("inf")
        self.best_step = 0
        self.history: list[tuple[int, float]] = []   # [(step, mae_k), ...]

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
        try:
            return float(text)
        except ValueError:
            return 0.0

    def on_step_end(self, args, state, control, **kwargs):
        if state.global_step == 0 or state.global_step % self.eval_steps != 0:
            return
        self.model.eval()
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
        self.model.train()
```

- [ ] **Step 2: Verify import thành công**

```bash
cd /home/hieu0606sunny/price2026wsl/tech2ai && uv run python -c "
import sys; sys.path.insert(0, 'fine_tune_qwen_v2')
from utils.training_utils import (
    get_bnb_config, get_lora_config, get_sft_config,
    DataCollatorCompletionOnly, MaeEvalCallback
)
print('OK — all imports successful')
"
```

Expected: `OK — all imports successful`

- [ ] **Step 3: Commit**

```bash
git add fine_tune_qwen_v2/utils/training_utils.py
git commit -m "feat(qwen-v2): add training_utils.py — LoRA/BnB config, DataCollator, MaeEvalCallback"
```

---

## Task 4: `02_train_v2.ipynb` — Full Training

**Files:**
- Create: `fine_tune_qwen_v2/02_train_v2.ipynb`

Mỗi cell dưới đây là một Jupyter cell. Chạy tuần tự từ đầu đến cuối.

- [ ] **Step 1: Cell 1 — Imports + constants**

```python
# Cell 1: Imports + constants
import os, sys, torch, wandb
sys.path.insert(0, os.path.abspath(".."))          # để import từ fine_tune_qwen_v2/utils/

from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

from utils.items_vn import load_items, DATASET_NAME
from utils.training_utils import (
    get_bnb_config, get_lora_config, get_sft_config,
    DataCollatorCompletionOnly, MaeEvalCallback,
    MAX_SEQ_LENGTH, VAL_EVAL_SIZE, RESPONSE_TEMPLATE,
)

BASE_MODEL    = "Qwen/Qwen3.5-4B-Base"
OUTPUT_DIR    = "outputs/qwen_v2"
HUB_MODEL_ID  = "SeanSunny/qwen3.5-4b-vn-pricer-v2"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Verify GPU
print(f"CUDA: {torch.cuda.is_available()}")
print(f"GPU:  {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

- [ ] **Step 2: Cell 2 — Load tokenizer**

```python
# Cell 2: Load tokenizer
# BẮT BUỘC: torch_dtype=bfloat16 trong from_pretrained — thiếu sẽ crash inference
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print(f"Vocab size: {tokenizer.vocab_size:,}")
print(f"Eos token:  '{tokenizer.eos_token}' (id={tokenizer.eos_token_id})")

# Verify response template tokenizes correctly
template_ids = tokenizer.encode(RESPONSE_TEMPLATE, add_special_tokens=False)
print(f"RESPONSE_TEMPLATE ids: {template_ids}")
print(f"RESPONSE_TEMPLATE decoded: '{tokenizer.decode(template_ids)}'")
```

- [ ] **Step 3: Cell 3 — Load + format + tokenize dataset**

```python
# Cell 3: Load + format + tokenize
def format_and_tokenize(example):
    text = example["prompt"] + example["completion"] + tokenizer.eos_token
    return tokenizer(
        text,
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
        padding=False,
    )

print("Loading train split...")
raw_train = load_dataset(DATASET_NAME, split="train")
print(f"  Raw train: {len(raw_train):,} rows")

train_ds = raw_train.map(
    format_and_tokenize,
    batched=True,
    remove_columns=raw_train.column_names,
    desc="Tokenising train",
)
print(f"  Tokenised train: {len(train_ds):,} rows")

# Sanity check: verify prompt masking works
sample = train_ds[0]
print(f"  input_ids length sample: {len(sample['input_ids'])}")
```

- [ ] **Step 4: Cell 4 — Load model (4-bit)**

```python
# Cell 4: Load model
# BẮT BUỘC: torch_dtype=torch.bfloat16 — thiếu sẽ crash conv1d ở inference
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=get_bnb_config(),
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
model = prepare_model_for_kbit_training(model)
model.config.use_cache = False          # cần tắt khi dùng gradient_checkpointing

print(f"Model loaded. VRAM used: {torch.cuda.memory_allocated()/1e9:.2f} GB")
```

- [ ] **Step 5: Cell 5 — Apply LoRA**

```python
# Cell 5: Apply LoRA
lora_cfg = get_lora_config()
model = get_peft_model(model, lora_cfg)
model.print_trainable_parameters()
# Expected output: trainable params: ~18M (0.45% of 4B)
```

- [ ] **Step 6: Cell 6 — Load val items cho MAE callback**

```python
# Cell 6: Val items
print(f"Loading {VAL_EVAL_SIZE} val items for MAE callback...")
val_items = load_items("validation", size=VAL_EVAL_SIZE)
print(f"  Loaded: {len(val_items)} items")
print(f"  Price range: {min(i.price for i in val_items):.0f}K – {max(i.price for i in val_items):.0f}K VND")
```

- [ ] **Step 7: Cell 7 — Build callback + collator + trainer**

```python
# Cell 7: Build trainer components
mae_callback = MaeEvalCallback(
    model=model,
    tokenizer=tokenizer,
    val_items=val_items,
    output_dir=OUTPUT_DIR,
)
collator = DataCollatorCompletionOnly(tokenizer)
sft_cfg  = get_sft_config(OUTPUT_DIR, HUB_MODEL_ID)

trainer = SFTTrainer(
    model=model,
    train_dataset=train_ds,
    data_collator=collator,
    args=sft_cfg,
    callbacks=[mae_callback],
)
print("Trainer ready.")
```

- [ ] **Step 8: Cell 8 — W&B init + train**

```python
# Cell 8: Train
wandb.init(project="qwen-vn-pricer-v2", name="v2-full-run")

trainer.train()

print("\n=== MAE History ===")
for step, mae in mae_callback.history:
    marker = " <-- BEST" if step == mae_callback.best_step else ""
    print(f"  step={step:>5}  mae={mae:.2f}K VND  ({mae*1000:,.0f} VND){marker}")
print(f"\nBest checkpoint at step {mae_callback.best_step}: MAE={mae_callback.best_mae:.2f}K VND")
```

- [ ] **Step 9: Cell 9 — Push final adapter + log**

```python
# Cell 9: Push to Hub
trainer.model.push_to_hub(HUB_MODEL_ID, private=True)
print(f"Pushed to: https://huggingface.co/{HUB_MODEL_ID}")
print(f"Best MAE checkpoint locally: {OUTPUT_DIR}/best_mae_checkpoint")
wandb.finish()
```

- [ ] **Step 10: Commit notebook**

```bash
git add fine_tune_qwen_v2/02_train_v2.ipynb
git commit -m "feat(qwen-v2): add 02_train_v2.ipynb — full training 269K, MAE callback"
```

---

## Task 5: `03_eval_v2.ipynb` — Final Evaluation

**Files:**
- Create: `fine_tune_qwen_v2/03_eval_v2.ipynb`

Chạy SAU khi training xong. Load best_mae_checkpoint → evaluate 200 test items → charts → lưu results.

- [ ] **Step 1: Cell 1 — Imports + constants**

```python
# Cell 1
import os, sys, json, torch
sys.path.insert(0, os.path.abspath(".."))

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

from utils.items_vn import load_items, DATASET_NAME
from utils.evaluator_vn import VnTester
from utils.training_utils import get_bnb_config, MAX_SEQ_LENGTH

BASE_MODEL   = "Qwen/Qwen3.5-4B-Base"
BEST_CKPT    = "outputs/qwen_v2/best_mae_checkpoint"
HUB_MODEL_ID = "SeanSunny/qwen3.5-4b-vn-pricer-v2"
RESULTS_PATH = "results/v2_results.json"
EVAL_SIZE    = 200
MAX_NEW_TOKENS = 4
```

- [ ] **Step 2: Cell 2 — Load model + adapter**

```python
# Cell 2: Load base + adapter
# BẮT BUỘC: torch_dtype=torch.bfloat16
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
tokenizer.pad_token = tokenizer.eos_token

base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=get_bnb_config(),
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
model = PeftModel.from_pretrained(base, BEST_CKPT)
model.eval()
print(f"Loaded adapter from: {BEST_CKPT}")
print(f"VRAM: {torch.cuda.memory_allocated()/1e9:.2f} GB")
```

- [ ] **Step 3: Cell 3 — Load test items**

```python
# Cell 3: Test items (seed=42 để reproducible, 200 items)
import random; random.seed(42)
all_test = load_items("test")
test_items = random.sample(all_test, min(EVAL_SIZE, len(all_test)))
print(f"Test items: {len(test_items)}")
print(f"Price range: {min(i.price for i in test_items):.0f}K – {max(i.price for i in test_items):.0f}K VND")
```

- [ ] **Step 4: Cell 4 — Define predictor**

```python
# Cell 4: Predictor function
def qwen_v2_predict(item) -> float:
    """Returns predicted price in K VND."""
    inputs = tokenizer(item.prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    prompt_len = inputs["input_ids"].shape[1]
    text = tokenizer.decode(out[0, prompt_len:], skip_special_tokens=True).strip()
    try:
        return float(text)
    except ValueError:
        return 0.0
```

- [ ] **Step 5: Cell 5 — Run evaluation + charts**

```python
# Cell 5: Evaluate + charts
tester = VnTester(
    predictor=qwen_v2_predict,
    data=test_items,
    title="Qwen3.5-4B V2 Fine-tuned",
    size=EVAL_SIZE,
    workers=1,    # sequential — 1 GPU, không parallel
)
tester.run()
# Hiển thị: error trend chart + scatter chart với MAE, RMSLE, R², MSE
```

- [ ] **Step 6: Cell 6 — Save results JSON**

```python
# Cell 6: Save results
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score
from utils.evaluator_vn import _rmsle

mae_k   = float(np.mean(tester.errors))
mse     = float(mean_squared_error(tester.truths, tester.guesses))
r2      = float(r2_score(tester.truths, tester.guesses))
rmsle   = _rmsle(tester.truths, tester.guesses)

results = {
    "model": HUB_MODEL_ID,
    "checkpoint": BEST_CKPT,
    "eval_size": EVAL_SIZE,
    "mae_k_vnd": round(mae_k, 2),
    "mae_vnd": round(mae_k * 1000, 0),
    "rmsle": round(rmsle, 4),
    "mse": round(mse, 2),
    "r2": round(r2, 4),
}
os.makedirs("results", exist_ok=True)
with open(RESULTS_PATH, "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(json.dumps(results, indent=2))
```

Expected output:
```json
{
  "model": "SeanSunny/qwen3.5-4b-vn-pricer-v2",
  "mae_k_vnd": 60.5,
  "mae_vnd": 60500.0,
  "rmsle": 0.38,
  "r2": 0.75
}
```

- [ ] **Step 7: Commit**

```bash
git add fine_tune_qwen_v2/03_eval_v2.ipynb
git commit -m "feat(qwen-v2): add 03_eval_v2.ipynb — final eval, charts, results JSON"
```

---

## Task 6: `01_zero_shot.ipynb` — Baseline (chạy sau)

**Files:**
- Create: `fine_tune_qwen_v2/01_zero_shot.ipynb`

> **Lưu ý:** Notebook này chạy sau khi có thời gian. Nó tạo baseline MAE của mô hình **chưa fine-tune** để so sánh với v2 kết quả.

- [ ] **Step 1: Viết notebook skeleton**

Cấu trúc cells tương tự `03_eval_v2.ipynb` nhưng:
- Load `Qwen/Qwen3.5-4B-Base` KHÔNG có adapter
- Predictor gọi model.generate với `max_new_tokens=10` (model chưa học format)
- Kết quả lưu vào `results/zero_shot_results.json`

```python
# Cell 1
import os, sys, json, torch, random
sys.path.insert(0, os.path.abspath(".."))

from transformers import AutoTokenizer, AutoModelForCausalLM
from utils.items_vn import load_items
from utils.evaluator_vn import VnTester
from utils.training_utils import get_bnb_config

BASE_MODEL   = "Qwen/Qwen3.5-4B-Base"
RESULTS_PATH = "results/zero_shot_results.json"
EVAL_SIZE    = 200

# Cell 2: Load base model (no adapter)
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=get_bnb_config(),
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
model.eval()

# Cell 3: Test items
random.seed(42)
all_test = load_items("test")
test_items = random.sample(all_test, min(EVAL_SIZE, len(all_test)))

# Cell 4: Predictor (zero-shot)
def zero_shot_predict(item) -> float:
    inputs = tokenizer(item.prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs, max_new_tokens=10, do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    prompt_len = inputs["input_ids"].shape[1]
    text = tokenizer.decode(out[0, prompt_len:], skip_special_tokens=True).strip()
    try:
        return float(text.split()[0])
    except (ValueError, IndexError):
        return 0.0

# Cell 5: Evaluate
tester = VnTester(zero_shot_predict, test_items, title="Qwen3.5-4B Zero-shot", size=EVAL_SIZE, workers=1)
tester.run()
```

- [ ] **Step 2: Commit skeleton**

```bash
git add fine_tune_qwen_v2/01_zero_shot.ipynb
git commit -m "feat(qwen-v2): add 01_zero_shot.ipynb skeleton — baseline eval (run separately)"
```

---

## Execution Order

```
Task 1 (items_vn.py)       → smoke test → commit
Task 2 (evaluator_vn.py)   → smoke test → commit
Task 3 (training_utils.py) → import check → commit
Task 4 (02_train_v2.ipynb) → run on GPU → ~15-18h on 3090Ti
Task 5 (03_eval_v2.ipynb)  → run after training → charts + results JSON
Task 6 (01_zero_shot.ipynb)→ run separately khi có thời gian
```

## Acceptance Criteria

| Item | Target |
|------|--------|
| `utils/` smoke tests pass | Bắt buộc |
| `02_train_v2.ipynb` chạy đến cuối không crash | Bắt buộc |
| `results/v2_results.json` tồn tại | Bắt buộc |
| MAE < 80,000 VND (beat v1) | P0 |
| MAE < 70,000 VND | P1 |
| MAE < 60,000 VND | Stretch |
| Charts vẽ được (scatter + error trend) | Bắt buộc |

---

*Created: 2026-05-19 | Branch: feature/day5-qlora-qwen | Model: Qwen3.5-4B-Base*
