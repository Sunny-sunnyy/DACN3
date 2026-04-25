"""Re-profile token lengths using the actual prompt format (summary-based) from items_prompts_tv_3."""
import json, math, random
import numpy as np
from transformers import AutoTokenizer
from datasets import load_dataset

MODEL_NAME = "Qwen/Qwen3.5-4B-Base"
DATASET    = "SeanSunny/items_prompts_tv_3"
SAMPLE     = 1000
SEED       = 42

random.seed(SEED)
np.random.seed(SEED)

print(f"Loading tokenizer {MODEL_NAME} ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print(f"Loading {DATASET} ...")
ds = load_dataset(DATASET)
train = ds["train"]
indices = random.sample(range(len(train)), SAMPLE)
sample = train.select(indices)

prompt_lens, completion_lens, full_lens = [], [], []
for item in sample:
    p_ids = tokenizer.encode(item["prompt"],    add_special_tokens=False)
    c_ids = tokenizer.encode(item["completion"], add_special_tokens=False)
    f_ids = tokenizer.encode(item["prompt"] + item["completion"], add_special_tokens=False)
    prompt_lens.append(len(p_ids))
    completion_lens.append(len(c_ids))
    full_lens.append(len(f_ids))

def pstats(arr):
    arr = np.array(arr)
    return {k: int(v) for k, v in zip(
        ["p50","p90","p95","p99","max"],
        [np.percentile(arr,p) for p in [50,90,95,99,100]]
    )} | {"mean": round(float(arr.mean()), 1)}

ps = pstats(prompt_lens)
cs = pstats(completion_lens)
fs = pstats(full_lens)

print(f"\nPrompt tokens    : {ps}")
print(f"Completion tokens: {cs}")
print(f"Full tokens      : {fs}")

recommended_seq        = math.ceil(fs["p95"] / 64) * 64
recommended_new_tokens = cs["p99"] + 1

print(f"\n==> max_seq_length  = {recommended_seq}  (p95_full={fs['p95']} rounded up to nearest 64)")
print(f"==> max_new_tokens  = {recommended_new_tokens}  (p99_completion={cs['p99']} + 1)")

results = {
    "model": MODEL_NAME, "dataset": DATASET, "sample_size": SAMPLE, "seed": SEED,
    "prompt_tokens": ps, "completion_tokens": cs, "full_tokens": fs,
    "recommended_max_seq_length": recommended_seq,
    "recommended_max_new_tokens": recommended_new_tokens,
}
out_path = "fine_tune_qwen/profile_results_v3.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\nSaved {out_path}")
