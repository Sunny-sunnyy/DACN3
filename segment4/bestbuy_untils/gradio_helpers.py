"""
Gradio Helpers - Utility functions for Gradio UI components.

Contains:
- QueueHandler: Custom logging handler for real-time log display
- setup_logging: Configure logging to use queue
- html_for_logs: Convert log messages to styled HTML
- opportunities_to_table: Format opportunities for Gradio Dataframe
- format_questions_html: Format clarification questions as HTML

These helpers are used by bestbuy4.py and can be reused by other Gradio apps.
"""

import logging
import queue
from typing import List

from log_utils import reformat
from price_agents.deals import Opportunity
from bestbuy_untils.clarification_agent import ClarificationQuestion


# ============================================================================
# LOGGING HANDLER
# ============================================================================

class QueueHandler(logging.Handler):
    """
    Custom logging handler that puts logs into a queue for Gradio.
    
    This allows real-time display of logs in Gradio UI by polling the queue.
    
    Args:
        log_queue: Queue to put log messages into
    """
    
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        """Put formatted log record into queue."""
        self.log_queue.put(self.format(record))


def setup_logging(log_queue: queue.Queue) -> None:
    """
    Setup logging to capture all logs into queue.
    
    Configures root logger to use QueueHandler for real-time log streaming.
    
    Args:
        log_queue: Queue to put log messages into
    """
    handler = QueueHandler(log_queue)
    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    
    # Add handler to root logger
    logger = logging.getLogger()
    # Remove existing QueueHandlers to avoid duplicates
    for h in logger.handlers[:]:
        if isinstance(h, QueueHandler):
            logger.removeHandler(h)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ============================================================================
# HTML FORMATTERS
# ============================================================================

def html_for_logs(log_data: List[str], max_logs: int = 25) -> str:
    """
    Convert log data to styled HTML for display in Gradio.
    
    Args:
        log_data: List of log messages
        max_logs: Maximum number of recent logs to display (default: 25)
        
    Returns:
        HTML string with styled log container
    """
    # Keep last N logs
    recent_logs = log_data[-max_logs:]
    # Format each log with color using log_utils
    formatted = [reformat(log) for log in recent_logs]
    output = '<br>'.join(formatted)
    return f"""
    <div style="height: 400px; overflow-y: auto; border: 1px solid #444; 
                background-color: #1a1a2e; padding: 10px; font-family: monospace; 
                font-size: 12px; border-radius: 8px;">
    {output}
    </div>
    """


def format_questions_html(questions: List[ClarificationQuestion]) -> str:
    """
    Format clarification questions as styled HTML.
    
    Args:
        questions: List of ClarificationQuestion objects
        
    Returns:
        HTML string with styled question cards
    """
    html = ""
    for i, q in enumerate(questions, 1):
        options_html = ", ".join(q.options)
        html += f"""
        <div style="margin-bottom: 15px; padding: 10px; background: #2a2a4a; border-radius: 8px;">
            <strong style="color: #87CEEB;">Q{i}: {q.question}</strong>
            <br><span style="color: #888; font-size: 0.9em;">Options: {options_html}</span>
        </div>
        """
    return f"""
    <div style="background: #1a1a2e; padding: 15px; border-radius: 10px; border: 1px solid #444;">
        <h4 style="color: #87CEEB; margin-top: 0;">🤖 Clarification Questions</h4>
        {html}
        <p style="color: #888; font-size: 0.85em;">
            💡 Answer these questions below, or click "Skip" to search directly.
        </p>
    </div>
    """


# ============================================================================
# TABLE FORMATTERS
# ============================================================================

def opportunities_to_html(opportunities: List[Opportunity]) -> str:
    """Convert opportunities to an HTML table with clickable URLs."""
    if not opportunities:
        return '<p style="color: #888;">No deals found.</p>'

    header = """
    <table style="width:100%; border-collapse:collapse; font-size:14px; color:#e0e0e0;">
    <thead>
    <tr style="background:#2a2a4a; text-align:left;">
        <th style="padding:8px; border-bottom:1px solid #444;">Product</th>
        <th style="padding:8px; border-bottom:1px solid #444;">Sale $</th>
        <th style="padding:8px; border-bottom:1px solid #444;">Estimate $</th>
        <th style="padding:8px; border-bottom:1px solid #444;">Discount $</th>
        <th style="padding:8px; border-bottom:1px solid #444;">Discount %</th>
        <th style="padding:8px; border-bottom:1px solid #444;">URL</th>
    </tr>
    </thead>
    <tbody>
    """

    rows_html = ""
    for opp in opportunities:
        discount_pct = (opp.discount / opp.estimate * 100) if opp.estimate > 0 else 0

        if opp.discount > 200:
            status = "HOT"
        elif opp.discount > 100:
            status = "Good"
        elif opp.discount > 0:
            status = "OK"
        else:
            status = "Overpriced"

        url = opp.deal.url
        link = f'<a href="{url}" target="_blank" style="color:#87CEEB;">Link</a>'
        desc = opp.deal.product_description[:80].replace("<", "&lt;") + "..."

        rows_html += f"""
        <tr style="border-bottom:1px solid #333;">
            <td style="padding:8px;">{desc}</td>
            <td style="padding:8px;">${opp.deal.price:.2f}</td>
            <td style="padding:8px;">${opp.estimate:.2f}</td>
            <td style="padding:8px;">${opp.discount:.2f}</td>
            <td style="padding:8px;">{discount_pct:.1f}% {status}</td>
            <td style="padding:8px;">{link}</td>
        </tr>
        """

    return header + rows_html + "</tbody></table>"
