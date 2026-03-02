# Import các thư viện cần thiết
import gradio as gr  # Thư viện để tạo giao diện web
from dotenv import load_dotenv  # Load biến môi trường từ file .env
from research_manager import ResearchManager  # Class quản lý quy trình nghiên cứu

# Load các biến môi trường (API keys, config...)
load_dotenv(override=True)


# Hàm chính chạy quy trình nghiên cứu và trả về kết quả dần dần
async def run(query: str):
    """Nhận câu hỏi từ user, chạy nghiên cứu và trả về từng phần kết quả (streaming)"""
    async for chunk in ResearchManager().run(query):
        yield chunk


# Tạo giao diện web với Gradio
with gr.Blocks(theme=gr.themes.Default(primary_hue="sky")) as ui:
    gr.Markdown("# Deep Research")  # Tiêu đề
    query_textbox = gr.Textbox(label="What topic would you like to research?")  # Ô nhập câu hỏi
    run_button = gr.Button("Run", variant="primary")  # Nút chạy
    report = gr.Markdown(label="Report")  # Vùng hiển thị báo cáo
    
    # Khi click nút Run -> gọi hàm run()
    run_button.click(fn=run, inputs=query_textbox, outputs=report)
    # Khi nhấn Enter ở ô textbox -> cũng gọi hàm run()
    query_textbox.submit(fn=run, inputs=query_textbox, outputs=report)

# Khởi chạy giao diện web và tự động mở trình duyệt
ui.launch(inbrowser=True)

