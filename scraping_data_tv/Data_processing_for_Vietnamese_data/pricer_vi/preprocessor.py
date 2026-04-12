"""Day 2: LLM Preprocessor — Single-item rewrite via litellm.

LLM only generates Mo ta + Thong so. Title/category/brand come from original data.
"""

from litellm import completion
from pricer_vi.items import Item

DEFAULT_MODEL_NAME = "groq/openai/gpt-oss-20b"
DEFAULT_REASONING_EFFORT = "low"

SYSTEM_PROMPT = """Tạo mô tả ngắn gọn cho một sản phẩm. Chỉ trả lời đúng 2 dòng theo định dạng sau. Không bao gồm mã sản phẩm.
Mô tả: 1 câu mô tả sản phẩm
Thông số: 1 câu về tính năng nổi bật"""


def build_summary(item: Item, llm_response: str) -> str:
    """Combine original title/category/brand with LLM-generated description/details."""
    brand = item.brand if item.brand else "Không rõ"
    return (
        f"Tiêu đề: {item.title}\n"
        f"Danh mục: {item.category}\n"
        f"Thương hiệu: {brand}\n"
        f"{llm_response}"
    )


class Preprocessor:
    def __init__(self, model_name=DEFAULT_MODEL_NAME, reasoning_effort=DEFAULT_REASONING_EFFORT):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0
        self.model_name = model_name
        self.reasoning_effort = reasoning_effort

    def messages_for(self, text: str) -> list[dict]:
        return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]

    def preprocess(self, item: Item) -> str:
        """Send item.full to LLM, return full summary with original metadata."""
        messages = self.messages_for(item.full)
        response = completion(
            messages=messages, model=self.model_name, reasoning_effort=self.reasoning_effort
        )
        self.total_input_tokens += response.usage.prompt_tokens
        self.total_output_tokens += response.usage.completion_tokens
        self.total_cost += response._hidden_params["response_cost"]
        llm_text = response.choices[0].message.content
        return build_summary(item, llm_text)
