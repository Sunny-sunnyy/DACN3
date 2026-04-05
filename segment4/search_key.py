"""
Multi-Source Deal Finder - Gradio Web App

Search on BOTH BestBuy AND Amazon simultaneously.
Flow: Enter Keyword -> Search -> Estimate Prices -> Results
"""

import logging
import queue
import threading
import time
from typing import List

import gradio as gr
from dotenv import load_dotenv

from multi_source_framework import MultiSourceFramework
from bestbuy_untils.gradio_helpers import (
    QueueHandler,
    setup_logging,
    html_for_logs,
    opportunities_to_table,
)

load_dotenv(override=True)


class App:
    """Gradio App for Multi-Source Deal Finder."""

    def __init__(self):
        self.framework = None
        self.current_keyword = ""
        self.current_max_urls = 10

    def get_framework(self):
        if not self.framework:
            self.framework = MultiSourceFramework()
        return self.framework

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def search_handler(self, keyword: str, max_urls: int, log_data: List[str]):
        """Handle search button click - run full pipeline."""
        if not keyword or len(keyword.strip()) < 2:
            yield [], "Please enter a keyword (at least 2 characters)", html_for_logs(["Error: keyword too short"])
            return

        self.current_keyword = keyword.strip()
        self.current_max_urls = int(max_urls) if max_urls else 10

        yield from self._run_pipeline(self.current_keyword, log_data)

    def _run_pipeline(self, query: str, initial_log: List[str]):
        """Generator that runs pipeline and yields updates for Gradio."""
        log_q = queue.Queue()
        result_q = queue.Queue()
        setup_logging(log_q)

        log_data = initial_log.copy() if initial_log else []
        log_data.append(f"Starting search: {query}")
        log_data.append("Source: BestBuy")

        def worker():
            opps = self.get_framework().run(query, self.current_max_urls)
            table = opportunities_to_table(opps)
            status = f"Found {len(opps)} deals!" if opps else "No deals found."
            result_q.put((table, status))

        thread = threading.Thread(target=worker)
        thread.start()

        final_result = None
        while thread.is_alive() or not log_q.empty() or final_result is None:
            while True:
                try:
                    log_data.append(log_q.get_nowait())
                except queue.Empty:
                    break

            try:
                final_result = result_q.get_nowait()
            except queue.Empty:
                pass

            if final_result:
                yield final_result[0], final_result[1], html_for_logs(log_data)
            else:
                yield [], "Processing...", html_for_logs(log_data)

            time.sleep(0.1)

        if final_result:
            log_data.append("Pipeline completed!")
            yield final_result[0], final_result[1], html_for_logs(log_data)

    def push_notification_handler(self, index: int) -> str:
        idx = int(index)
        return self.get_framework().send_notification(idx)

    # =========================================================================
    # GRADIO UI
    # =========================================================================

    def run(self):
        with gr.Blocks(
            title="Multi-Source Deal Finder",
            theme=gr.themes.Soft(),
            fill_width=True,
        ) as ui:

            log_state = gr.State([])

            gr.Markdown("""
            # BestBuy Deal Finder
            Search for the best deals on BestBuy!
            """)

            # Keyword Input + Search
            with gr.Group():
                gr.Markdown("### Search")
                with gr.Row():
                    keyword_input = gr.Textbox(
                        label="What are you looking for?",
                        placeholder="e.g., laptop, Smart TV, headphones",
                        scale=3,
                    )
                    max_urls_input = gr.Number(
                        label="Max URLs (per source)",
                        value=10, minimum=5, maximum=20, precision=0, scale=1,
                    )
                    search_btn = gr.Button("Search", variant="primary", scale=1)

            status_text = gr.Textbox(
                label="Status",
                interactive=False,
                value="Enter a keyword and click Search",
            )

            # Results
            with gr.Row():
                with gr.Column(scale=3):
                    gr.Markdown("### Deal Results")
                    results_table = gr.Dataframe(
                        headers=["Product", "Sale $", "Estimate $", "Discount $", "Discount %", "URL"],
                        wrap=True,
                        column_widths=[4, 1, 1, 1, 1, 2],
                        max_height=350,
                    )
                with gr.Column(scale=2):
                    gr.Markdown("### Pipeline Logs")
                    logs_html = gr.HTML(
                        value='<div style="height: 400px; background-color: #1a1a2e; padding: 10px; color: #87CEEB;">Ready...</div>'
                    )

            # Push Notification
            with gr.Row():
                deal_index = gr.Number(
                    label="Deal # to notify (0 = best)",
                    value=0, minimum=0, precision=0, scale=1,
                )
                push_btn = gr.Button("Send Push Notification", variant="secondary", scale=1)
            push_status = gr.Textbox(label="Notification Status", interactive=False)

            gr.Markdown("---\n**Legend:** HOT DEAL > $200 | Good Deal > $100 | OK > $0 | Overpriced")

            # Event Bindings
            search_btn.click(
                fn=self.search_handler,
                inputs=[keyword_input, max_urls_input, log_state],
                outputs=[results_table, status_text, logs_html],
            )
            push_btn.click(
                fn=self.push_notification_handler,
                inputs=[deal_index],
                outputs=[push_status],
            )

        ui.launch(share=False, inbrowser=True)


if __name__ == "__main__":
    print("=" * 60)
    print("BestBuy Deal Finder - Starting...")
    print("Source: BestBuy")
    print("=" * 60)
    App().run()
