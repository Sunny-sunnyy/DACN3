"""HuggingFace upload helpers (Phase 1+)."""
import os


def push_adapter(model, tokenizer, local_dir: str, hub_name: str, token: str = None):
    token = token or os.environ.get("HF_TOKEN", "")
    model.save_pretrained(local_dir)
    tokenizer.save_pretrained(local_dir)
    model.push_to_hub(hub_name, token=token)
    tokenizer.push_to_hub(hub_name, token=token)
    print(f"Pushed adapter to {hub_name}")


def push_merged(model, tokenizer, local_dir: str, hub_name: str, token: str = None):
    token = token or os.environ.get("HF_TOKEN", "")
    model.save_pretrained_merged(local_dir, tokenizer, save_method="merged_16bit")
    model.push_to_hub_merged(hub_name, tokenizer, save_method="merged_16bit", token=token)
    print(f"Pushed merged model to {hub_name}")
