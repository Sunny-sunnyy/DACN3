# Import các thành phần từ framework Agents
from agents import Agent, WebSearchTool, ModelSettings

# Hướng dẫn cho AI agent: tóm tắt kết quả tìm kiếm web thành 2-3 đoạn ngắn gọn
INSTRUCTIONS = (
    "You are a research assistant. Given a search term, you search the web for that term and "
    "produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 "
    "words. Capture the main points. Write succintly, no need to have complete sentences or good "
    "grammar. This will be consumed by someone synthesizing a report, so its vital you capture the "
    "essence and ignore any fluff. Do not include any additional commentary other than the summary itself."
)

# Tạo agent tìm kiếm: nhận từ khóa -> tìm web -> trả về tóm tắt ngắn gọn
search_agent = Agent(
    name="Search agent",  # Tên agent
    instructions=INSTRUCTIONS,  # Hướng dẫn nhiệm vụ
    tools=[WebSearchTool(search_context_size="low")],  # Tool tìm kiếm web (kích thước context nhỏ để nhanh)
    model="gpt-4o-mini",  # Model AI sử dụng
    model_settings=ModelSettings(tool_choice="required"),  # Bắt buộc phải dùng tool
)