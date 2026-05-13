"""
Pricer Demo - Price Estimator with model selection.

Usage: cd segment4 && uv run pricer_demo.py
"""

import logging

import chromadb
import gradio as gr
from dotenv import load_dotenv

from price_agents.ensemble_agent import EnsembleAgent

DB = "products_vectorstore"


class App:

    MODELS = ["DNN", "Llama 3.2 (Modal)", "GPT-5.1 + RAG", "Ensemble"]

    def __init__(self):
        load_dotenv(override=True)
        logging.basicConfig(level=logging.INFO)
        logging.info("[PricerDemo] Initializing...")
        client = chromadb.PersistentClient(path=DB)
        collection = client.get_or_create_collection("products")
        logging.info(f"[PricerDemo] ChromaDB ready: {collection.count()} products")
        self.ensemble = EnsembleAgent(collection)
        logging.info("[PricerDemo] All agents ready")

    def estimate(self, description: str, model_choice: str):
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

        # Ensemble: preprocess text, then get individual predictions for breakdown
        rewrite = self.ensemble.preprocessor.preprocess(description)
        dnn_price   = self.ensemble.neural_network.price(rewrite)
        llama_price = self.ensemble.specialist.price(rewrite)
        gpt_price   = self.ensemble.frontier.price(rewrite)
        combined    = gpt_price * 0.8 + llama_price * 0.1 + dnn_price * 0.1
        rows = [
            ["DNN",                 f"${dnn_price:.2f}",   "10%"],
            ["Llama 3.2 (Modal)",   f"${llama_price:.2f}", "10%"],
            ["GPT-5.1 + RAG",       f"${gpt_price:.2f}",   "80%"],
            ["Ensemble (combined)", f"${combined:.2f}",    "—"],
        ]
        return f"${combined:.2f}", gr.update(visible=True, value=rows)

    def run(self):
        with gr.Blocks(title="AI Price Estimator", theme=gr.themes.Soft()) as ui:

            gr.Markdown("# AI Price Estimator\nNhập mô tả sản phẩm, chọn model, nhận giá ước lượng.")

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


if __name__ == "__main__":
    App().run()
