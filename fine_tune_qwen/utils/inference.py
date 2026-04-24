"""Inference utilities for Qwen fine-tuned models (Phase 1+)."""
import re
import torch
from tqdm.auto import tqdm


def predict_one(model, tokenizer, prompt: str, max_new_tokens: int) -> int:
    """Generate price prediction (in thousands VND) for a single prompt."""
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = tokenizer.decode(
        outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True
    )
    match = re.search(r"\d+", generated)
    return int(match.group()) if match else 0


def predict_batch(model, tokenizer, prompts: list[str], max_new_tokens: int) -> list[int]:
    """Predict for a list of prompts, returns list of ints (thousands VND)."""
    results = []
    for prompt in tqdm(prompts, desc="Predicting"):
        results.append(predict_one(model, tokenizer, prompt, max_new_tokens))
    return results
