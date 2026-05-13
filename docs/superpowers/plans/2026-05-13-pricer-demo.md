# Pricer Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tạo `segment4/pricer_demo.py` — Gradio app cho phép nhập mô tả sản phẩm, chọn model (DNN / Llama / GPT+RAG / Ensemble), nhận về giá ước lượng; Ensemble mode hiển thị thêm breakdown từng model.

**Architecture:** Pre-load `EnsembleAgent(collection)` một lần khi khởi động — bên trong nó đã tạo sẵn `NeuralNetworkAgent`, `SpecialistAgent`, `FrontierAgent`, và `Preprocessor`. Single-model modes dùng trực tiếp các sub-agent đó với raw text (không qua preprocessor). Ensemble mode chạy preprocessor rồi gọi từng sub-agent riêng lẻ để lấy breakdown.

**Tech Stack:** Gradio, ChromaDB, các agent có sẵn trong `price_agents/` — không thêm dependency mới, không sửa file cũ.

**Constraint cứng:** Chỉ tạo `segment4/pricer_demo.py`. Không được sửa bất kỳ file nào khác.

**Chạy:** `cd segment4 && uv run pricer_demo.py` (phải ở thư mục `segment4/` vì các agent dùng relative path cho `deep_neural_network.pth` và `products_vectorstore/`).

---

## File Structure

| File | Action | Mô tả |
|------|--------|-------|
| `segment4/pricer_demo.py` | **Create** | Toàn bộ app: ChromaDB init, agent loading, Gradio UI, handler |

Không tạo thêm file nào khác.

---

## Thiết kế chi tiết `pricer_demo.py`

### Cách tái dùng agents mà không sửa code cũ

`EnsembleAgent(collection)` khởi tạo nội bộ 4 objects:
- `self.neural_network = NeuralNetworkAgent()` — PyTorch DNN
- `self.specialist = SpecialistAgent()` — Modal Llama
- `self.frontier = FrontierAgent(collection)` — GPT-5.1 + ChromaDB RAG
- `self.preprocessor = Preprocessor()` — LiteLLM text rewrite

Ta chỉ cần tạo một `EnsembleAgent`, rồi trỏ trực tiếp vào các attribute đó:

| Model được chọn | Cách gọi | Input |
|----------------|----------|-------|
| DNN | `ensemble.neural_network.price(description)` | raw text |
| Llama 3.2 (Modal) | `ensemble.specialist.price(description)` | raw text |
| GPT-5.1 + RAG | `ensemble.frontier.price(description)` | raw text |
| Ensemble | preprocess → gọi 3 agent riêng → tính weighted avg | preprocessed text |

### Ensemble breakdown logic (chỉ trong pricer_demo.py)

```python
rewrite = self.ensemble.preprocessor.preprocess(description)
dnn_price   = self.ensemble.neural_network.price(rewrite)
llama_price = self.ensemble.specialist.price(rewrite)
gpt_price   = self.ensemble.frontier.price(rewrite)
combined    = gpt_price * 0.8 + llama_price * 0.1 + dnn_price * 0.1
```

### UI layout

```
[Title]
[Product description — gr.Textbox, lines=4]
[Model — gr.Dropdown: DNN | Llama 3.2 (Modal) | GPT-5.1 + RAG | Ensemble]
[Estimate button — primary]
[Estimated Price — gr.Textbox, read-only]
[Breakdown table — gr.Dataframe, visible=False by default, chỉ hiện khi Ensemble]
```

### Handler outputs

Handler `estimate(description, model_choice)` trả về tuple `(price_str, dataframe_update)`:
- `price_str`: chuỗi `"$xxx.xx"`
- `dataframe_update`: `gr.update(visible=False, value=[])` cho single models; `gr.update(visible=True, value=[...rows...])` cho Ensemble

---

## Task 1: Tạo skeleton App + ChromaDB init

**Files:**
- Create: `segment4/pricer_demo.py`

- [ ] **Step 1: Tạo file với skeleton App**

```python
"""
Pricer Demo - Price Estimator with model selection

Usage: cd segment4 && uv run pricer_demo.py
"""

import logging
import os

import chromadb
import gradio as gr
from dotenv import load_dotenv

from price_agents.ensemble_agent import EnsembleAgent

DB = "products_vectorstore"


def init_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)


class App:
    def __init__(self):
        load_dotenv(override=True)
        init_logging()
        logging.info("[PricerDemo] Initializing...")
        client = chromadb.PersistentClient(path=DB)
        collection = client.get_or_create_collection("products")
        logging.info(f"[PricerDemo] ChromaDB ready: {collection.count()} products")
        self.ensemble = EnsembleAgent(collection)
        logging.info("[PricerDemo] All agents ready")

    def run(self):
        pass  # UI được thêm ở Task 2


if __name__ == "__main__":
    App().run()
```

- [ ] **Step 2: Kiểm tra import và init không lỗi**

```bash
cd /home/hieu0606sunny/price2026wsl/tech2ai/segment4
uv run python -c "from pricer_demo import App; print('import OK')"
```

Expected: in ra `import OK`, không có traceback.

Nếu lỗi `ModuleNotFoundError`: kiểm tra lại đang ở thư mục `segment4/` và `uv sync` đã chạy.

- [ ] **Step 3: Commit skeleton**

```bash
cd /home/hieu0606sunny/price2026wsl/tech2ai
git add segment4/pricer_demo.py
git commit -m "feat: add pricer_demo.py skeleton with ChromaDB + EnsembleAgent init"
```

---

## Task 2: Implement estimate handler

**Files:**
- Modify: `segment4/pricer_demo.py` (thêm method `estimate`)

- [ ] **Step 1: Thêm method `estimate` vào class App**

Thêm method này vào class `App`, thay thế `pass` trong phần body:

```python
    MODELS = ["DNN", "Llama 3.2 (Modal)", "GPT-5.1 + RAG", "Ensemble"]

    def estimate(self, description: str, model_choice: str):
        """Run the selected model and return (price_str, dataframe_update)."""
        description = description.strip()
        if not description:
            return "Please enter a product description.", gr.update(visible=False, value=[])

        if model_choice == "DNN":
            price = self.ensemble.neural_network.price(description)
            return f"${price:.2f}", gr.update(visible=False, value=[])

        if model_choice == "Llama 3.2 (Modal)":
            price = self.ensemble.specialist.price(description)
            return f"${price:.2f}", gr.update(visible=False, value=[])

        if model_choice == "GPT-5.1 + RAG":
            price = self.ensemble.frontier.price(description)
            return f"${price:.2f}", gr.update(visible=False, value=[])

        # Ensemble: preprocess + breakdown
        rewrite = self.ensemble.preprocessor.preprocess(description)
        dnn_price   = self.ensemble.neural_network.price(rewrite)
        llama_price = self.ensemble.specialist.price(rewrite)
        gpt_price   = self.ensemble.frontier.price(rewrite)
        combined    = gpt_price * 0.8 + llama_price * 0.1 + dnn_price * 0.1
        rows = [
            ["DNN",              f"${dnn_price:.2f}",   "10%"],
            ["Llama 3.2 (Modal)", f"${llama_price:.2f}", "10%"],
            ["GPT-5.1 + RAG",   f"${gpt_price:.2f}",   "80%"],
            ["Ensemble (combined)", f"${combined:.2f}", "—"],
        ]
        return f"${combined:.2f}", gr.update(visible=True, value=rows)
```

- [ ] **Step 2: Test handler logic thủ công (không cần modal/openai thật)**

```bash
cd /home/hieu0606sunny/price2026wsl/tech2ai/segment4
uv run python -c "
from pricer_demo import App
app = App()
price, df_update = app.estimate('', 'DNN')
assert 'Please enter' in price, f'Expected error message, got: {price}'
print('Empty input check: OK')
print('estimate method: OK')
"
```

Expected: in ra `Empty input check: OK` và `estimate method: OK`.

- [ ] **Step 3: Commit handler**

```bash
cd /home/hieu0606sunny/price2026wsl/tech2ai
git add segment4/pricer_demo.py
git commit -m "feat: add estimate handler with 4 model modes and ensemble breakdown"
```

---

## Task 3: Build Gradio UI và launch

**Files:**
- Modify: `segment4/pricer_demo.py` (thay `pass` trong `run()` bằng Gradio UI hoàn chỉnh)

- [ ] **Step 1: Thay thế method `run()` bằng Gradio UI hoàn chỉnh**

```python
    def run(self):
        with gr.Blocks(title="AI Price Estimator", theme=gr.themes.Soft()) as ui:

            gr.Markdown("# AI Price Estimator\nNhập mô tả sản phẩm và chọn model để ước lượng giá.")

            with gr.Row():
                with gr.Column(scale=2):
                    description_input = gr.Textbox(
                        label="Product Description",
                        placeholder="e.g., Apple iPhone 17 Pro Max 256GB",
                        lines=4,
                    )
                    model_dropdown = gr.Dropdown(
                        choices=self.MODELS,
                        value="Ensemble",
                        label="Model",
                    )
                    estimate_btn = gr.Button("Estimate Price", variant="primary")

                with gr.Column(scale=1):
                    price_output = gr.Textbox(
                        label="Estimated Price",
                        interactive=False,
                        value="",
                    )
                    breakdown_table = gr.Dataframe(
                        headers=["Model", "Predicted Price", "Weight"],
                        label="Ensemble Breakdown",
                        visible=False,
                        interactive=False,
                    )

            estimate_btn.click(
                fn=self.estimate,
                inputs=[description_input, model_dropdown],
                outputs=[price_output, breakdown_table],
            )

        ui.launch(share=False, inbrowser=True)
```

- [ ] **Step 2: Chạy thử app — kiểm tra UI load được**

```bash
cd /home/hieu0606sunny/price2026wsl/tech2ai/segment4
uv run pricer_demo.py
```

Expected:
- App khởi động, in log `[PricerDemo] All agents ready`
- Browser mở `http://127.0.0.1:7860` (hoặc port kế tiếp nếu 7860 đã dùng)
- Thấy textbox, dropdown, button
- Chọn "DNN", nhập `"wireless headphones"`, click Estimate → thấy giá (không thấy breakdown table)
- Chọn "Ensemble", nhập `"wireless headphones"`, click Estimate → thấy giá + breakdown table với 4 dòng

- [ ] **Step 3: Commit hoàn chỉnh**

```bash
cd /home/hieu0606sunny/price2026wsl/tech2ai
git add segment4/pricer_demo.py docs/superpowers/plans/2026-05-13-pricer-demo.md
git commit -m "feat: complete pricer_demo.py with Gradio UI, 4 models, ensemble breakdown"
```

---

## Self-Review

**Spec coverage:**
- [x] Ô nhập mô tả sản phẩm — `gr.Textbox description_input`
- [x] Chọn model: DNN, Llama 3.2, GPT-5.1+RAG, Ensemble — `gr.Dropdown`
- [x] Single models dùng raw text (không preprocessor)
- [x] Ensemble dùng preprocessor + hiển thị breakdown
- [x] Không sửa file cũ — chỉ tạo `pricer_demo.py`
- [x] Pre-load tất cả agent khi khởi động (Option 2)
- [x] Tái dùng sub-agents của EnsembleAgent cho single-model modes (không load trùng)

**Placeholder scan:** Không có TBD/TODO nào trong các code blocks.

**Type consistency:**
- `estimate(description: str, model_choice: str) -> tuple[str, gr.update]` — nhất quán giữa handler và Gradio outputs binding.
- `self.ensemble.neural_network`, `self.ensemble.specialist`, `self.ensemble.frontier`, `self.ensemble.preprocessor` — đúng với attribute names trong `ensemble_agent.py` (line 19-22).
- `self.MODELS` được khai báo ở Task 2 và dùng trong `gr.Dropdown(choices=self.MODELS)` ở Task 3 — nhất quán.
