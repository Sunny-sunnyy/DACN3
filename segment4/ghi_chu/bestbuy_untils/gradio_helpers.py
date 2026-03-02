"""
=============================================================================
GRADIO HELPERS - HÀM HỖ TRỢ CHO GIAO DIỆN GRADIO
=============================================================================
File: bestbuy_untils/gradio_helpers.py

MỤC ĐÍCH:
- Cung cấp các hàm helper cho Gradio UI trong bestbuy4.py
- Xử lý logging real-time (QueueHandler, setup_logging)
- Format dữ liệu thành HTML/Table cho hiển thị

CÁC HÀM CHÍNH:
1. QueueHandler + setup_logging: Logging real-time cho Gradio
2. html_for_logs: Format logs thành HTML với màu sắc
3. format_questions_html: Format câu hỏi thành HTML cards
4. opportunities_to_table: Format opportunities thành table data

TẠI SAO CẦN FILE NÀY?
- Tách UI logic ra khỏi business logic
- Có thể reuse ở các Gradio apps khác
- Code gọn gàng, dễ maintain
"""

import logging
import queue
from typing import List

# Import helper format log với màu
from log_utils import reformat

# Import data classes
from price_agents.deals import Opportunity
from price_agents.clarification_agent import ClarificationQuestion


# =============================================================================
# PHẦN 1: LOGGING HANDLER - HIỂN THỊ LOG REAL-TIME TRÊN GRADIO
# =============================================================================
"""
Vấn đề: Gradio UI cần hiển thị logs real-time trong khi pipeline đang chạy.
Giải pháp: Dùng queue để truyền logs từ worker thread sang main thread.

Flow:
1. Pipeline chạy trong thread riêng, gọi logging.info()
2. QueueHandler bắt log và đưa vào queue
3. Main thread poll queue và update Gradio HTML component
"""

class QueueHandler(logging.Handler):
    """
    Custom logging handler - đưa logs vào queue thay vì print ra console.
    
    Gradio sẽ poll queue này và update HTML component theo thời gian thực.
    
    Kế thừa từ logging.Handler, override phương thức emit().
    
    Attributes:
        log_queue: Queue để chứa log messages
    
    VD sử dụng:
        log_q = queue.Queue()
        handler = QueueHandler(log_q)
        logging.getLogger().addHandler(handler)
        
        # Khi gọi logging.info("Hello"), message sẽ được đưa vào log_q
    """
    
    def __init__(self, log_queue: queue.Queue):
        """
        Khởi tạo với queue.
        
        Args:
            log_queue: Queue để chứa log messages
        """
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        """
        Được gọi khi có log message mới.
        
        Override từ logging.Handler.
        Format log record và đưa vào queue.
        
        Args:
            record: Log record chứa message, level, timestamp, etc.
        """
        # self.format() sử dụng formatter đã set (nếu có)
        self.log_queue.put(self.format(record))


def setup_logging(log_queue: queue.Queue) -> None:
    """
    Cấu hình root logger để dùng QueueHandler.
    
    Được gọi trước khi chạy pipeline:
        log_q = queue.Queue()
        setup_logging(log_q)
        # Bắt đầu pipeline...
    
    Args:
        log_queue: Queue để chứa log messages
    """
    # Tạo QueueHandler
    handler = QueueHandler(log_queue)
    
    # Tạo formatter với format: [HH:MM:SS] message
    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    
    # Thêm handler vào root logger
    logger = logging.getLogger()
    
    # Xóa QueueHandler cũ (nếu có) để tránh duplicate
    for h in logger.handlers[:]:
        if isinstance(h, QueueHandler):
            logger.removeHandler(h)
    
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# =============================================================================
# PHẦN 2: HTML FORMATTERS - CHUYỂN ĐỔI DỮ LIỆU THÀNH HTML
# =============================================================================

def html_for_logs(log_data: List[str], max_logs: int = 25) -> str:
    """
    Chuyển đổi list logs thành HTML có style cho Gradio.
    
    Features:
    - Hiển thị tối đa 25 logs gần nhất (tránh quá dài)
    - Format màu sắc bằng log_utils.reformat()
    - Container có scroll và dark theme
    
    Args:
        log_data: List các log messages
        max_logs: Số logs tối đa hiển thị (default: 25)
        
    Returns:
        HTML string với container chứa logs
    
    VD output:
        <div style="height: 400px; ...">
        [10:30:15] 🔍 Searching for laptop...<br>
        [10:30:20] ✅ Found 10 results<br>
        ...
        </div>
    """
    # Chỉ lấy N logs gần nhất
    recent_logs = log_data[-max_logs:]
    
    # Format mỗi log với màu (dùng log_utils.reformat)
    # reformat() chuyển ANSI colors thành HTML colors
    formatted = [reformat(log) for log in recent_logs]
    
    # Join bằng <br> (line break trong HTML)
    output = '<br>'.join(formatted)
    
    # Wrap trong container có style
    return f"""
    <div style="height: 400px; overflow-y: auto; border: 1px solid #444; 
                background-color: #1a1a2e; padding: 10px; font-family: monospace; 
                font-size: 12px; border-radius: 8px;">
    {output}
    </div>
    """


def format_questions_html(questions: List[ClarificationQuestion]) -> str:
    """
    Format câu hỏi làm rõ thành HTML cards.
    
    Mỗi câu hỏi được hiển thị trong 1 card với:
    - Question text (màu xanh, đậm)
    - Options (màu xám, nhỏ hơn)
    
    Args:
        questions: List ClarificationQuestion (thường là 3 câu)
        
    Returns:
        HTML string với các question cards
    
    VD output:
        <div style="background: #1a1a2e; ...">
            <h4>🤖 Clarification Questions</h4>
            <div style="...">
                <strong>Q1: What brand do you prefer?</strong>
                <br><span>Options: Dell, HP, Acer, Any</span>
            </div>
            <div>Q2: ...</div>
            <div>Q3: ...</div>
            <p>💡 Answer these questions below...</p>
        </div>
    """
    html = ""
    
    # Tạo HTML cho mỗi câu hỏi
    for i, q in enumerate(questions, 1):
        # Join options bằng ", "
        options_html = ", ".join(q.options)
        
        # Card cho mỗi câu hỏi
        html += f"""
        <div style="margin-bottom: 15px; padding: 10px; background: #2a2a4a; border-radius: 8px;">
            <strong style="color: #87CEEB;">Q{i}: {q.question}</strong>
            <br><span style="color: #888; font-size: 0.9em;">Options: {options_html}</span>
        </div>
        """
    
    # Wrap tất cả trong container
    return f"""
    <div style="background: #1a1a2e; padding: 15px; border-radius: 10px; border: 1px solid #444;">
        <h4 style="color: #87CEEB; margin-top: 0;">🤖 Clarification Questions</h4>
        {html}
        <p style="color: #888; font-size: 0.85em;">
            💡 Answer these questions below, or click "Skip" to search directly.
        </p>
    </div>
    """


# =============================================================================
# PHẦN 3: TABLE FORMATTERS - CHUYỂN ĐỔI DỮ LIỆU THÀNH GRADIO TABLE
# =============================================================================

def opportunities_to_table(opportunities: List[Opportunity]) -> list:
    """
    Chuyển đổi list Opportunity thành data cho Gradio Dataframe.
    
    Mỗi row chứa:
    - Product: Mô tả ngắn (60 chars)
    - Sale $: Giá sale hiện tại
    - Estimate $: Giá trị ước tính bởi EnsembleAgent
    - Discount $: estimate - sale (số dương = deal tốt)
    - Discount %: Phần trăm discount + status icon
    - URL: Link sản phẩm
    
    Status icons:
    - 🔥: Discount > $200 (Hot deal!)
    - ✅: Discount > $100 (Good deal)
    - 👍: Discount > $0 (Positive)
    - ❌: Discount <= $0 (Overpriced)
    
    Args:
        opportunities: List Opportunity (đã sorted by discount)
        
    Returns:
        List of rows, mỗi row là list [Product, Sale, Estimate, Discount, %, URL]
    
    VD output:
        [
            ["Acer Aspire 5 Laptop 15.6 inch AMD...", "$449.99", "$599.00", "$149.01", "24.9% ✅", "https://..."],
            ["Dell Inspiron 15...", "$399.99", "$350.00", "-$49.99", "-14.3% ❌", "https://..."],
        ]
    """
    rows = []
    
    for opp in opportunities:
        # Tính discount % (tránh chia cho 0)
        discount_pct = (opp.discount / opp.estimate * 100) if opp.estimate > 0 else 0
        
        # Chọn status icon dựa vào discount amount
        if opp.discount > 200:
            status = "🔥"  # Hot deal - discount > $200
        elif opp.discount > 100:
            status = "✅"  # Good deal - discount > $100
        elif opp.discount > 0:
            status = "👍"  # Positive discount
        else:
            status = "❌"  # Overpriced - discount <= 0
        
        # Tạo row
        rows.append([
            opp.deal.product_description[:60] + "...",  # Truncate description
            f"${opp.deal.price:.2f}",                   # Sale price
            f"${opp.estimate:.2f}",                     # Estimate
            f"${opp.discount:.2f}",                     # Discount amount
            f"{discount_pct:.1f}% {status}",            # Discount % với icon
            opp.deal.url                                # URL
        ])
    
    return rows
