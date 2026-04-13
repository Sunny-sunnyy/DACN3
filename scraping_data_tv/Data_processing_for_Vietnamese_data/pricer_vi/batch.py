"""Day 2: Batch processing via Groq Batch API.

LLM only generates Mo ta + Thong so. Title/category/brand come from original data.
"""

import os
import json
import pickle
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv
from tqdm.auto import tqdm

from pricer_vi.preprocessor import SYSTEM_PROMPT, build_summary

load_dotenv(override=True)
groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-20b"
BATCHES_FOLDER = "batches_vi_v2"
OUTPUT_FOLDER = "output_vi_v2"
state = Path("batches_vi.pkl")


class Batch:
    BATCH_SIZE = 1_000

    batches = []

    def __init__(self, items, start, end):
        self.items = items
        self.start = start
        self.end = end
        self.filename = f"{start}_{end}.jsonl"
        self.file_id = None
        self.batch_id = None
        self.output_file_id = None
        self.done = False
        self.batches_dir = Path(BATCHES_FOLDER)
        self.output_dir = Path(OUTPUT_FOLDER)
        self.batches_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def make_jsonl(self, item):
        body = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": item.full},
            ],
            "reasoning_effort": "low",
        }
        line = {
            "custom_id": str(item.id),
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body,
        }
        return json.dumps(line, ensure_ascii=False)

    def make_file(self):
        batch_file = self.batches_dir / self.filename
        with batch_file.open("w", encoding="utf-8") as f:
            for item in self.items[self.start:self.end]:
                f.write(self.make_jsonl(item))
                f.write("\n")

    def send_file(self):
        batch_file = self.batches_dir / self.filename
        with batch_file.open("rb") as f:
            response = groq.files.create(file=f, purpose="batch")
        self.file_id = response.id

    def submit_batch(self):
        response = groq.batches.create(
            completion_window="24h",
            endpoint="/v1/chat/completions",
            input_file_id=self.file_id,
        )
        self.batch_id = response.id

    def is_ready(self):
        response = groq.batches.retrieve(self.batch_id)
        status = response.status
        if status == "completed":
            self.output_file_id = response.output_file_id
        return status == "completed"

    def fetch_output(self):
        output_file = str(self.output_dir / self.filename)
        response = groq.files.content(self.output_file_id)
        response.write_to_file(output_file)

    def apply_output(self):
        output_file = str(self.output_dir / self.filename)
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                json_line = json.loads(line)
                id = int(json_line["custom_id"])
                llm_text = json_line["response"]["body"]["choices"][0]["message"]["content"]
                self.items[id].summary = build_summary(self.items[id], llm_text)
        self.done = True

    @classmethod
    def create(cls, items):
        cls.batches = []
        for start in range(0, len(items), cls.BATCH_SIZE):
            end = min(start + cls.BATCH_SIZE, len(items))
            batch = Batch(items, start, end)
            cls.batches.append(batch)
        print(f"Created {len(cls.batches)} batches")

    @classmethod
    def run(cls):
        for batch in tqdm(cls.batches):
            batch.make_file()
            batch.send_file()
            batch.submit_batch()
        print(f"Submitted {len(cls.batches)} batches")

    @classmethod
    def fetch(cls):
        for batch in tqdm(cls.batches):
            if not batch.done:
                if batch.is_ready():
                    batch.fetch_output()
                    batch.apply_output()
        finished = [batch for batch in cls.batches if batch.done]
        print(f"Finished {len(finished)} of {len(cls.batches)} batches")

    @classmethod
    def save(cls):
        items = cls.batches[0].items
        for batch in cls.batches:
            batch.items = None
        with state.open("wb") as f:
            pickle.dump(cls.batches, f)
        for batch in cls.batches:
            batch.items = items
        print(f"Saved {len(cls.batches)} batches")

    @classmethod
    def load(cls, items):
        with state.open("rb") as f:
            cls.batches = pickle.load(f)
        for batch in cls.batches:
            batch.items = items
        print(f"Loaded {len(cls.batches)} batches")
