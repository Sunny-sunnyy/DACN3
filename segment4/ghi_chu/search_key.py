"""
=============================================================================
SEARCH_KEY.PY - GRADIO WEB APP CHO MULTI-SOURCE DEAL FINDER
=============================================================================
File: search_key.py

MỤC ĐÍCH:
- Đây là file chứa GIAO DIỆN GRADIO (UI only)
- Không chứa business logic - chỉ gọi xuống MultiSourceFramework
- Pattern theo: price_is_right.py

KIẾN TRÚC (Theo Single Responsibility Principle):
    search_key.py (UI) 
        → MultiSourceFramework (orchestrator)
            → MultiSourcePlanningAgent (pipeline logic)

FLOW NGƯỜI DÙNG:
1. Nhập keyword (VD: "laptop")
2. Click "Generate Questions" → Hiện 3 câu hỏi
3. Trả lời hoặc Skip → Chạy pipeline
4. Xem kết quả → Gửi notification nếu muốn

2 LUỒNG XỬ LÝ:
- Clarification Flow: User trả lời câu hỏi → Query được refined → Kết quả tốt hơn
- Skip Flow: User bỏ qua câu hỏi → Search với keyword gốc

Author: Refactored from bestbuy4.py
Date: 2026-02-07
=============================================================================
"""

import logging
import queue
import threading
import time
from typing import List

import gradio as gr
from dotenv import load_dotenv

# Import framework (orchestrator) - chứa business logic
from multi_source_framework import MultiSourceFramework

# Import helper functions cho Gradio
from bestbuy_untils.gradio_helpers import (
    QueueHandler,        # Handler để capture logs vào queue
    setup_logging,       # Setup logging cho pipeline
    html_for_logs,       # Convert logs → HTML hiển thị đẹp
    opportunities_to_table,   # Convert opportunities → Dataframe rows
    format_questions_html     # Convert questions → HTML đẹp
)

# Load biến môi trường (.env file)
load_dotenv(override=True)


# =============================================================================
# APP CLASS - CHỨA TOÀN BỘ UI VÀ EVENT HANDLERS
# =============================================================================

class App:
    """
    Gradio App class cho Multi-Source Deal Finder.
    
    Pattern theo price_is_right.py:
    - App class chứa state và event handlers
    - run() method để build và launch Gradio UI
    - Lazy initialization cho framework

    Attributes:
        framework: MultiSourceFramework instance (lazy init)
        current_questions: Câu hỏi hiện tại từ ClarificationAgent
        current_keyword: Keyword người dùng nhập
        current_max_urls: Số lượng URLs tối đa mỗi nguồn
    """

    def __init__(self):
        """Khởi tạo app với các state variables."""
        self.framework = None            # Framework sẽ init khi cần (lazy)
        self.current_questions = None    # Lưu câu hỏi để dùng khi submit answers
        self.current_keyword = ""        # Keyword gốc người dùng nhập
        self.current_max_urls = 10       # Default 10 URLs mỗi nguồn

    def get_framework(self):
        """
        Lazy initialization của framework.
        
        Tại sao lazy init?
        - Framework init mất ~3-5s (ChromaDB, agents)
        - Chỉ init khi thực sự cần (user click button)
        - Tránh slow startup
        
        Returns:
            MultiSourceFramework instance
        """
        if not self.framework:
            self.framework = MultiSourceFramework()
        return self.framework

    # =========================================================================
    # EVENT HANDLERS - XỬ LÝ CÁC SỰ KIỆN TỪ UI
    # =========================================================================

    def generate_questions_handler(self, keyword: str):
        """
        Xử lý khi user click "Generate Questions".
        
        Flow:
        1. Kiểm tra keyword hợp lệ (>= 2 ký tự)
        2. Gọi ClarificationAgent sinh 3 câu hỏi
        3. Lưu câu hỏi vào state
        4. Trả về HTML hiển thị câu hỏi
        
        Args:
            keyword: Từ khóa người dùng nhập
            
        Returns:
            Tuple (questions_html, status_text, answers_section_visible)
        """
        # Validate keyword
        if not keyword or len(keyword.strip()) < 2:
            return (
                "",
                "Hãy nhập keyword (ít nhất 2 ký tự)",
                gr.update(visible=False),  # Ẩn phần trả lời
            )

        # Lưu keyword vào state
        self.current_keyword = keyword.strip()
        logging.info(f"Đang tạo câu hỏi cho: {self.current_keyword}")

        # Gọi ClarificationAgent thông qua framework
        response = self.get_framework().generate_questions(self.current_keyword)
        self.current_questions = response  # Lưu để dùng khi submit

        # Convert questions → HTML đẹp
        questions_html = format_questions_html(response.questions)

        return (
            questions_html,                                    # Hiển thị câu hỏi
            f"Danh mục: {response.product_category} | Trả lời câu hỏi hoặc bấm Skip.",
            gr.update(visible=True),                          # Hiện phần trả lời
        )

    def submit_answers_handler(self, a1: str, a2: str, a3: str, max_urls: int, log_data: List[str]):
        """
        Xử lý khi user click "Submit & Search".
        
        Flow - CLARIFICATION FLOW:
        1. Kiểm tra đã có câu hỏi chưa
        2. Gọi ClarificationAgent.build_refined_query() để tạo query tốt hơn
        3. Chạy pipeline với refined query
        4. Yield updates liên tục cho Gradio (streaming)
        
        Args:
            a1, a2, a3: 3 câu trả lời của user
            max_urls: Số URLs tối đa mỗi nguồn
            log_data: Log data hiện tại (Gradio state)
            
        Yields:
            Tuple (results_table, status, query_comparison, logs_html)
        """
        # Validate: Phải generate questions trước
        if not self.current_questions:
            yield [], "Hãy tạo câu hỏi trước!", "", html_for_logs(["Error"])
            return

        self.current_max_urls = int(max_urls) if max_urls else 10
        answers = [a1.strip(), a2.strip(), a3.strip()]

        # Tạo refined query từ câu trả lời
        # VD: "laptop" + ["gaming", "under $1000", "15 inch"] 
        #     → "gaming laptops 15 inch under $1000"
        refined = self.get_framework().planner.build_refined_query(
            self.current_keyword,
            self.current_questions.questions,
            answers
        )
        search_query = refined.query
        comparison = f"Gốc: \"{self.current_keyword}\" → Refined: \"{search_query}\""

        # Chạy pipeline và yield updates
        yield from self._run_pipeline(search_query, comparison, log_data)

    def skip_handler(self, max_urls: int, log_data: List[str]):
        """
        Xử lý khi user click "Skip, Search Now".
        
        Flow - SKIP FLOW:
        1. Kiểm tra đã nhập keyword chưa
        2. Chạy pipeline với keyword gốc (không refined)
        3. Yield updates liên tục cho Gradio
        
        Args:
            max_urls: Số URLs tối đa mỗi nguồn
            log_data: Log data hiện tại
            
        Yields:
            Tuple (results_table, status, query_comparison, logs_html)
        """
        # Validate: Phải nhập keyword trước
        if not self.current_keyword:
            yield [], "Hãy nhập keyword trước!", "", html_for_logs(["Error"])
            return

        self.current_max_urls = int(max_urls) if max_urls else 10
        comparison = f"Chế độ Skip - tìm với: \"{self.current_keyword}\""

        # Chạy pipeline với keyword gốc
        yield from self._run_pipeline(self.current_keyword, comparison, log_data)

    def _run_pipeline(self, query: str, comparison: str, initial_log: List[str]):
        """
        Generator chạy pipeline và yield updates cho Gradio.
        
        ĐÂY LÀ HÀM QUAN TRỌNG NHẤT!
        
        Tại sao dùng Generator?
        - Gradio cần nhận updates liên tục để hiển thị real-time
        - yield từng bước để UI cập nhật mượt
        - Không block UI trong khi pipeline chạy
        
        Flow:
        1. Setup logging với queue (capture logs)
        2. Tạo worker thread chạy pipeline (background)
        3. Loop: drain log queue + check result + yield updates
        4. Kết thúc khi có result
        
        Threading Pattern:
            Main thread (Gradio) ←─ yield updates
                ↓
            Worker thread (Pipeline) → result_queue
                ↓
            Logging → log_queue → drain by main thread
        
        Args:
            query: Search query (gốc hoặc refined)
            comparison: Text so sánh query gốc vs refined
            initial_log: Log data ban đầu
            
        Yields:
            Tuple (results_table, status, comparison, logs_html)
        """
        # Setup 2 queues:
        # - log_q: Nhận logs từ pipeline (logging module)
        # - result_q: Nhận kết quả cuối cùng từ worker
        log_q = queue.Queue()
        result_q = queue.Queue()
        setup_logging(log_q)  # Redirect logging → log_q

        # Copy log data ban đầu
        log_data = initial_log.copy() if initial_log else []
        log_data.append(f"Bắt đầu MULTI-SOURCE search: {query}")
        log_data.append("Nguồn: BestBuy + Amazon")

        # Worker function - chạy trong background thread
        def worker():
            # Gọi framework.run() - chứa pipeline 6 bước
            opps = self.get_framework().run(query, self.current_max_urls)
            # Convert opportunities → table rows
            table = opportunities_to_table(opps)
            status = f"Tìm thấy {len(opps)} deals!" if opps else "Không tìm thấy deals."
            result_q.put((table, status))  # Đẩy result vào queue

        # Start worker thread
        thread = threading.Thread(target=worker)
        thread.start()

        # Main loop: Yield updates cho Gradio
        final_result = None
        while thread.is_alive() or not log_q.empty() or final_result is None:
            # Drain log queue - lấy hết logs mới
            while True:
                try:
                    log_data.append(log_q.get_nowait())
                except queue.Empty:
                    break

            # Check result queue
            try:
                final_result = result_q.get_nowait()
            except queue.Empty:
                pass

            # Yield update cho Gradio
            if final_result:
                yield final_result[0], final_result[1], comparison, html_for_logs(log_data)
            else:
                yield [], "Đang xử lý...", comparison, html_for_logs(log_data)

            # Small delay để không loop quá nhanh
            time.sleep(0.1)

        # Final yield
        if final_result:
            log_data.append("Pipeline hoàn tất!")
            yield final_result[0], final_result[1], comparison, html_for_logs(log_data)

    def push_notification_handler(self, index: int) -> str:
        """
        Gửi push notification cho deal được chọn.
        
        Args:
            index: Index của deal trong danh sách (0 = best deal)
            
        Returns:
            Status message
        """
        idx = int(index)
        return self.get_framework().send_notification(idx)

    # =========================================================================
    # GRADIO UI - ĐỊNH NGHĨA GIAO DIỆN
    # =========================================================================

    def run(self):
        """
        Build và launch Gradio app.
        
        Layout gồm các phần:
        1. Header - Tiêu đề và mô tả
        2. Step 1 - Nhập keyword + nút Generate Questions
        3. Step 2 - Hiển thị câu hỏi + ô trả lời
        4. Results - Bảng kết quả + logs
        5. Notification - Nút gửi push notification
        6. Footer - Chú thích
        
        Event Bindings:
        - generate_btn.click → generate_questions_handler
        - submit_btn.click → submit_answers_handler
        - skip_btn.click → skip_handler
        - push_btn.click → push_notification_handler
        """
        with gr.Blocks(
            title="Multi-Source Deal Finder",
            theme=gr.themes.Soft(),     # Theme sáng, dễ đọc
            fill_width=True,            # Full width
        ) as ui:

            # State để lưu log data giữa các lần yield
            log_state = gr.State([])

            # ===================== HEADER =====================
            gr.Markdown("""
            # 🔍 Multi-Source Deal Finder
            Tìm kiếm deals trên **CẢ** BestBuy VÀ Amazon cùng lúc!
            
            **Flow:** Nhập Keyword → Trả lời câu hỏi (hoặc Skip) → Tìm kiếm → Ước lượng giá
            """)

            # ===================== STEP 1: KEYWORD INPUT =====================
            with gr.Group():
                gr.Markdown("### 📝 Bước 1: Nhập từ khóa sản phẩm")
                with gr.Row():
                    # Ô nhập keyword
                    keyword_input = gr.Textbox(
                        label="Bạn muốn tìm gì?",
                        placeholder="VD: laptop, Smart TV, tai nghe",
                        scale=3  # Chiếm 3 phần
                    )
                    # Số URLs tối đa
                    max_urls_input = gr.Number(
                        label="Max URLs (mỗi nguồn)",
                        value=10, minimum=5, maximum=20, precision=0, scale=1
                    )
                    # Nút tạo câu hỏi
                    generate_btn = gr.Button("Tạo câu hỏi", variant="primary", scale=1)

            # Status text
            status_text = gr.Textbox(
                label="Trạng thái",
                interactive=False,
                value="Nhập keyword và click 'Tạo câu hỏi'"
            )

            # ===================== STEP 2: QUESTIONS =====================
            # HTML hiển thị câu hỏi
            questions_html = gr.HTML(
                value='<div style="padding: 20px; text-align: center; color: #888;">Câu hỏi sẽ xuất hiện ở đây...</div>'
            )

            # Phần trả lời câu hỏi (ẩn ban đầu)
            with gr.Group(visible=False) as answers_section:
                gr.Markdown("### 💬 Bước 2: Trả lời các câu hỏi")
                with gr.Row():
                    answer1 = gr.Textbox(label="Câu trả lời 1", placeholder="Trả lời câu hỏi 1...")
                    answer2 = gr.Textbox(label="Câu trả lời 2", placeholder="Trả lời câu hỏi 2...")
                    answer3 = gr.Textbox(label="Câu trả lời 3", placeholder="Trả lời câu hỏi 3...")
                with gr.Row():
                    submit_btn = gr.Button("Gửi & Tìm kiếm", variant="primary", scale=2)
                    skip_btn = gr.Button("Bỏ qua, Tìm ngay", variant="secondary", scale=1)

            # ===================== QUERY COMPARISON =====================
            query_comparison = gr.Textbox(
                label="So sánh Query",
                interactive=False,
                placeholder="Query gốc vs refined..."
            )

            # ===================== RESULTS =====================
            with gr.Row():
                # Bảng kết quả
                with gr.Column(scale=3):
                    gr.Markdown("### 📊 Kết quả Deals")
                    results_table = gr.Dataframe(
                        headers=["Sản phẩm", "Giá $", "Ước lượng $", "Discount $", "Discount %", "URL"],
                        wrap=True,
                        column_widths=[4, 1, 1, 1, 1, 2],
                        max_height=350,
                    )
                # Logs panel
                with gr.Column(scale=2):
                    gr.Markdown("### 📋 Pipeline Logs")
                    logs_html = gr.HTML(
                        value='<div style="height: 400px; background-color: #1a1a2e; padding: 10px; color: #87CEEB;">Sẵn sàng...</div>'
                    )

            # ===================== PUSH NOTIFICATION =====================
            with gr.Row():
                deal_index = gr.Number(
                    label="Deal # để notify (0 = tốt nhất)",
                    value=0, minimum=0, precision=0, scale=1
                )
                push_btn = gr.Button("Gửi Push Notification", variant="secondary", scale=1)
            push_status = gr.Textbox(label="Trạng thái Notification", interactive=False)

            # ===================== FOOTER =====================
            gr.Markdown("""
            ---
            **Chú thích:** 🔥 > $200 | ✅ > $100 | 👍 > $0 | ❌ Overpriced
            """)

            # ===================== EVENT BINDINGS =====================
            # Kết nối buttons với handlers
            
            generate_btn.click(
                fn=self.generate_questions_handler,   # Handler function
                inputs=[keyword_input],               # Input components
                outputs=[questions_html, status_text, answers_section],  # Output components
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

        # Launch app
        ui.launch(share=False, inbrowser=True)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Multi-Source Deal Finder - Đang khởi động...")
    print("Nguồn: BestBuy + Amazon")
    print("=" * 60)
    App().run()
