# Import các framework và agents cần thiết
from agents import Runner, trace, gen_trace_id  # Runner để chạy agents, trace để debug
from search_agent import search_agent  # Agent tìm kiếm web
from planner_agent import planner_agent, WebSearchItem, WebSearchPlan  # Agent lập kế hoạch
from writer_agent import writer_agent, ReportData  # Agent viết báo cáo
from email_agent import email_agent  # Agent gửi email
import asyncio  # Chạy các tác vụ bất đồng bộ song song

# Class quản lý toàn bộ quy trình nghiên cứu (orchestrator)
class ResearchManager:

    # Hàm chính điều phối toàn bộ workflow: lập kế hoạch -> tìm kiếm -> viết báo cáo -> gửi email
    async def run(self, query: str):
        """ Run the deep research process, yielding the status updates and the final report"""
        trace_id = gen_trace_id()  # Tạo ID để theo dõi luồng thực thi
        with trace("Research trace", trace_id=trace_id):  # Bật trace để debug trên OpenAI Platform
            print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
            yield f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}"
            print("Starting research...")
            # Bước 1: Lập kế hoạch tìm kiếm (tạo danh sách từ khóa)
            search_plan = await self.plan_searches(query)
            yield "Searches planned, starting to search..."     
            # Bước 2: Thực hiện tìm kiếm song song
            search_results = await self.perform_searches(search_plan)
            yield "Searches complete, writing report..."
            # Bước 3: Viết báo cáo từ kết quả tìm kiếm
            report = await self.write_report(query, search_results)
            yield "Report written, sending email..."
            # Bước 4: Gửi email báo cáo
            await self.send_email(report)
            yield "Email sent, research complete"
            # Trả về báo cáo cuối cùng
            yield report.markdown_report
        

    # Bước 1: Lập kế hoạch - chuyển câu hỏi thành danh sách từ khóa tìm kiếm
    async def plan_searches(self, query: str) -> WebSearchPlan:
        """ Plan the searches to perform for the query """
        print("Planning searches...")
        # Gọi planner_agent để tạo kế hoạch tìm kiếm
        result = await Runner.run(
            planner_agent,
            f"Query: {query}",
        )
        print(f"Will perform {len(result.final_output.searches)} searches")
        return result.final_output_as(WebSearchPlan)  # Trả về danh sách các tìm kiếm

    # Bước 2: Thực hiện các tìm kiếm song song (concurrent) để tăng tốc
    async def perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
        """ Perform the searches to perform for the query """
        print("Searching...")
        num_completed = 0
        # Tạo các task tìm kiếm chạy đồng thời (async)
        tasks = [asyncio.create_task(self.search(item)) for item in search_plan.searches]
        results = []
        # Thu thập kết quả khi các task hoàn thành (không theo thứ tự)
        for task in asyncio.as_completed(tasks):
            result = await task
            if result is not None:  # Chỉ lưu kết quả thành công
                results.append(result)
            num_completed += 1
            print(f"Searching... {num_completed}/{len(tasks)} completed")
        print("Finished searching")
        return results  # Trả về danh sách các kết quả tìm kiếm

    # Hàm phụ: thực hiện 1 lần tìm kiếm web với search_agent
    async def search(self, item: WebSearchItem) -> str | None:
        """ Perform a search for the query """
        input = f"Search term: {item.query}\nReason for searching: {item.reason}"
        try:
            # Gọi search_agent để tìm kiếm và tóm tắt
            result = await Runner.run(
                search_agent,
                input,
            )
            return str(result.final_output)  # Trả về tóm tắt kết quả
        except Exception:
            return None  # Nếu lỗi, trả về None (không crash cả hệ thống)

    # Bước 3: Viết báo cáo từ các kết quả tìm kiếm
    async def write_report(self, query: str, search_results: list[str]) -> ReportData:
        """ Write the report for the query """
        print("Thinking about report...")
        # Ghép câu hỏi gốc và các tóm tắt tìm kiếm làm input
        input = f"Original query: {query}\nSummarized search results: {search_results}"
        # Gọi writer_agent để viết báo cáo chi tiết
        result = await Runner.run(
            writer_agent,
            input,
        )

        print("Finished writing report")
        return result.final_output_as(ReportData)  # Trả về đối tượng ReportData
    
    # Bước 4: Gửi email báo cáo qua email_agent
    async def send_email(self, report: ReportData) -> None:
        print("Writing email...")
        # Gọi email_agent để chuyển báo cáo thành HTML và gửi email
        result = await Runner.run(
            email_agent,
            report.markdown_report,  # Truyền báo cáo markdown vào
        )
        print("Email sent")
        return report