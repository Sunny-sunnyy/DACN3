from pydantic import BaseModel, Field
from agents import Agent

# Số lượng tìm kiếm web sẽ thực hiện cho mỗi câu hỏi
HOW_MANY_SEARCHES = 5

# Hướng dẫn cho agent: nhận câu hỏi -> đề xuất N từ khóa tìm kiếm phù hợp
INSTRUCTIONS = f"You are a helpful research assistant. Given a query, come up with a set of web searches \
to perform to best answer the query. Output {HOW_MANY_SEARCHES} terms to query for."


# Cấu trúc dữ liệu cho 1 lần tìm kiếm web
class WebSearchItem(BaseModel):
    reason: str = Field(description="Your reasoning for why this search is important to the query.")  # Lý do tại sao cần tìm
    query: str = Field(description="The search term to use for the web search.")  # Từ khóa tìm kiếm


# Cấu trúc dữ liệu chứa danh sách các tìm kiếm cần thực hiện
class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem] = Field(description="A list of web searches to perform to best answer the query.")
    
# Agent lập kế hoạch: nhận câu hỏi -> trả về danh sách các từ khóa cần tìm (dạng WebSearchPlan)
planner_agent = Agent(
    name="PlannerAgent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    output_type=WebSearchPlan,  # Output có cấu trúc theo class WebSearchPlan
)