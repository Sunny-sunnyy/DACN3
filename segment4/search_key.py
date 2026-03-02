"""
Multi-Source Deal Finder - Gradio Web App (search_key.py)

Pattern follows: price_is_right.py
This file contains ONLY Gradio UI and event handlers.
Business logic is in: MultiSourceFramework + MultiSourcePlanningAgent

Search on BOTH BestBuy AND Amazon simultaneously.

Supports 2 flows:
1. Clarification Flow: User answers 3 questions -> Refined query -> Better deals
2. Skip Flow: User skips questions -> Search with original keyword

Author: Refactored from bestbuy4.py
Date: 2026-02-07
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
    format_questions_html
)

load_dotenv(override=True)


class App:
    """
    Gradio App for Multi-Source Deal Finder.
    Pattern follows price_is_right.py App class.
    """

    def __init__(self):
        self.framework = None
        self.current_questions = None
        self.current_keyword = ""
        self.current_max_urls = 10

    def get_framework(self):
        """Lazy initialization of framework."""
        if not self.framework:
            self.framework = MultiSourceFramework()
        return self.framework

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def generate_questions_handler(self, keyword: str):
        """Handle keyword input and generate clarification questions."""
        if not keyword or len(keyword.strip()) < 2:
            return (
                "",
                "Please enter a keyword (at least 2 characters)",
                gr.update(visible=False),
            )

        self.current_keyword = keyword.strip()
        logging.info(f"Generating questions for: {self.current_keyword}")

        response = self.get_framework().generate_questions(self.current_keyword)
        self.current_questions = response

        questions_html = format_questions_html(response.questions)

        return (
            questions_html,
            f"Category: {response.product_category} | Answer the questions below or skip.",
            gr.update(visible=True),
        )

    def submit_answers_handler(self, a1: str, a2: str, a3: str, max_urls: int, log_data: List[str]):
        """Handle submit answers and run clarification flow."""
        if not self.current_questions:
            yield [], "Please generate questions first!", "", html_for_logs(["Error"])
            return

        self.current_max_urls = int(max_urls) if max_urls else 10
        answers = [a1.strip(), a2.strip(), a3.strip()]

        refined = self.get_framework().planner.build_refined_query(
            self.current_keyword,
            self.current_questions.questions,
            answers
        )
        search_query = refined.query
        comparison = f"Original: \"{self.current_keyword}\" -> Refined: \"{search_query}\""

        yield from self._run_pipeline(search_query, comparison, log_data)

    def skip_handler(self, max_urls: int, log_data: List[str]):
        """Handle skip button - search with original keyword."""
        if not self.current_keyword:
            yield [], "Please enter a keyword first!", "", html_for_logs(["Error"])
            return

        self.current_max_urls = int(max_urls) if max_urls else 10
        comparison = f"Skip mode - searching with: \"{self.current_keyword}\""

        yield from self._run_pipeline(self.current_keyword, comparison, log_data)

    def _run_pipeline(self, query: str, comparison: str, initial_log: List[str]):
        """Generator that runs pipeline and yields updates for Gradio."""
        log_q = queue.Queue()
        result_q = queue.Queue()
        setup_logging(log_q)

        log_data = initial_log.copy() if initial_log else []
        log_data.append(f"Starting MULTI-SOURCE search: {query}")
        log_data.append("Sources: BestBuy + Amazon")

        def worker():
            opps = self.get_framework().run(query, self.current_max_urls)
            table = opportunities_to_table(opps)
            status = f"Found {len(opps)} deals!" if opps else "No deals found."
            result_q.put((table, status))

        thread = threading.Thread(target=worker)
        thread.start()

        final_result = None
        while thread.is_alive() or not log_q.empty() or final_result is None:
            # Drain log queue
            while True:
                try:
                    log_data.append(log_q.get_nowait())
                except queue.Empty:
                    break

            # Check for result
            try:
                final_result = result_q.get_nowait()
            except queue.Empty:
                pass

            if final_result:
                yield final_result[0], final_result[1], comparison, html_for_logs(log_data)
            else:
                yield [], "Processing...", comparison, html_for_logs(log_data)

            time.sleep(0.1)

        if final_result:
            log_data.append("Pipeline completed!")
            yield final_result[0], final_result[1], comparison, html_for_logs(log_data)

    def push_notification_handler(self, index: int) -> str:
        """Send push notification for selected deal."""
        idx = int(index)
        return self.get_framework().send_notification(idx)

    # =========================================================================
    # GRADIO UI
    # =========================================================================

    def run(self):
        """Build and launch Gradio app."""
        with gr.Blocks(
            title="Multi-Source Deal Finder",
            theme=gr.themes.Soft(),
            fill_width=True,
        ) as ui:

            log_state = gr.State([])

            # Header
            gr.Markdown("""
            # Multi-Source Deal Finder
            Search on **BOTH** BestBuy AND Amazon simultaneously!
            **Flow:** Enter Keyword -> Answer Questions (or Skip) -> Search -> Estimate Prices
            """)

            # Step 1: Keyword Input
            with gr.Group():
                gr.Markdown("### Step 1: Enter Product Keyword")
                with gr.Row():
                    keyword_input = gr.Textbox(
                        label="What are you looking for?",
                        placeholder="e.g., laptop, Smart TV, headphones",
                        scale=3
                    )
                    max_urls_input = gr.Number(
                        label="Max URLs (per source)",
                        value=10, minimum=5, maximum=20, precision=0, scale=1
                    )
                    generate_btn = gr.Button("Generate Questions", variant="primary", scale=1)

            status_text = gr.Textbox(
                label="Status",
                interactive=False,
                value="Enter a keyword and click 'Generate Questions'"
            )

            # Step 2: Questions
            questions_html = gr.HTML(
                value='<div style="padding: 20px; text-align: center; color: #888;">Questions will appear here...</div>'
            )

            # Step 3: Answers
            with gr.Group(visible=False) as answers_section:
                gr.Markdown("### Step 2: Answer the Questions")
                with gr.Row():
                    answer1 = gr.Textbox(label="Answer 1", placeholder="Your answer to Q1...")
                    answer2 = gr.Textbox(label="Answer 2", placeholder="Your answer to Q2...")
                    answer3 = gr.Textbox(label="Answer 3", placeholder="Your answer to Q3...")
                with gr.Row():
                    submit_btn = gr.Button("Submit & Search", variant="primary", scale=2)
                    skip_btn = gr.Button("Skip, Search Now", variant="secondary", scale=1)

            # Query Comparison
            query_comparison = gr.Textbox(
                label="Query Comparison",
                interactive=False,
                placeholder="Original vs Refined query..."
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
                    value=0, minimum=0, precision=0, scale=1
                )
                push_btn = gr.Button("Send Push Notification", variant="secondary", scale=1)
            push_status = gr.Textbox(label="Notification Status", interactive=False)

            # Footer
            gr.Markdown("""
            ---
            **Legend:** 🔥 > $200 | ✅ > $100 | 👍 > $0 | ❌ Overpriced
            """)

            # Event Bindings
            generate_btn.click(
                fn=self.generate_questions_handler,
                inputs=[keyword_input],
                outputs=[questions_html, status_text, answers_section],
            )
            submit_btn.click(
                fn=self.submit_answers_handler,
                inputs=[answer1, answer2, answer3, max_urls_input, log_state],
                outputs=[results_table, status_text, query_comparison, logs_html],
            )
            skip_btn.click(
                fn=self.skip_handler,
                inputs=[max_urls_input, log_state],
                outputs=[results_table, status_text, query_comparison, logs_html],
            )
            push_btn.click(
                fn=self.push_notification_handler,
                inputs=[deal_index],
                outputs=[push_status],
            )

        ui.launch(share=False, inbrowser=True)


if __name__ == "__main__":
    print("=" * 60)
    print("Multi-Source Deal Finder - Starting...")
    print("Sources: BestBuy + Amazon")
    print("=" * 60)
    App().run()
