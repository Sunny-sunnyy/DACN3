from pydantic import BaseModel, Field
from agents import Agent

# Hướng dẫn cho agent: tổng hợp kết quả tìm kiếm thành báo cáo chi tiết, dài 5-10 trang
INSTRUCTIONS = (
    "You are a senior researcher tasked with writing a cohesive report for a research query. "
    "You will be provided with the original query, and some initial research done by a research assistant.\n"
    "You should first come up with an outline for the report that describes the structure and "
    "flow of the report. Then, generate the report and return that as your final output.\n"
    "The final output should be in markdown format, and it should be lengthy and detailed. Aim "
    "for 5-10 pages of content, at least 1000 words."
)


# Cấu trúc dữ liệu của báo cáo nghiên cứu
class ReportData(BaseModel):
    short_summary: str = Field(description="A short 2-3 sentence summary of the findings.")  # Tóm tắt ngắn 2-3 câu
    
    markdown_report: str = Field(description="The final report")  # Báo cáo chi tiết dạng Markdown
    
    follow_up_questions: list[str] = Field(description="Suggested topics to research further")  # Câu hỏi gợi ý nghiên cứu sâu hơn


# Agent viết báo cáo: nhận kết quả tìm kiếm -> viết báo cáo dài, chi tiết (dạng ReportData)
writer_agent = Agent(
    name="WriterAgent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    output_type=ReportData,  # Output có cấu trúc theo class ReportData
)