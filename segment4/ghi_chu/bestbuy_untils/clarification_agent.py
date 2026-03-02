"""
=============================================================================
CLARIFICATION AGENT - TẠO CÂU HỎI LÀM RÕ NHU CẦU NGƯỜI DÙNG
=============================================================================
File: bestbuy_untils/clarification_agent.py

MỤC ĐÍCH:
- Tạo 3 câu hỏi làm rõ nhu cầu khi user nhập keyword mơ hồ (VD: "laptop")
- Tạo refined query từ câu trả lời để tìm kiếm chính xác hơn
- Sử dụng GPT-5-mini với Structured Outputs (Pydantic)

VÍ DỤ SỬ DỤNG:
    agent = ClarificationAgent()
    
    # Bước 1: Tạo câu hỏi
    response = agent.generate_questions("laptop")
    # → Q1: Bạn thích hãng nào? (Dell, HP, Acer, Any)
    # → Q2: Dùng để làm gì? (Gaming, Work, Study, Any)
    # → Q3: Ngân sách bao nhiêu? (under $500, $500-$1000, over $1000, Any)
    
    # Bước 2: Tạo refined query từ câu trả lời
    refined = agent.build_refined_query("laptop", response.questions, ["Acer", "for students", "under $800"])
    # → refined.query = "Acer laptops for students under $800"

TẠI SAO DÙNG GPT-5-MINI?
- Đủ thông minh để hiểu context sản phẩm
- Chi phí thấp hơn GPT-5.1
- Structured Outputs đảm bảo output đúng format Pydantic
"""

import logging
from typing import List

from openai import OpenAI
from pydantic import BaseModel, Field


# =============================================================================
# PHẦN 1: PYDANTIC SCHEMAS (ĐỊNH NGHĨA CẤU TRÚC DỮ LIỆU)
# =============================================================================
"""
Tại sao dùng Pydantic?
- OpenAI Structured Outputs yêu cầu Pydantic BaseModel
- Đảm bảo output của GPT đúng format (không cần parse JSON thủ công)
- Validate data tự động (VD: min_length, max_length)
"""

class ClarificationQuestion(BaseModel):
    """
    Schema cho MỘT câu hỏi làm rõ.
    
    Attributes:
        question: Nội dung câu hỏi (tiếng Anh)
        options: Danh sách 4-6 lựa chọn, option cuối luôn là "Any"/"No preference"
    
    VD:
        question = "What brand do you prefer?"
        options = ["Dell", "HP", "Acer", "Lenovo", "Any"]
    """
    question: str = Field(description="The clarification question in English")
    options: List[str] = Field(
        description="4-6 options for the user to choose from. Last option should always be 'Any' or 'No preference'",
        min_length=3,  # Ít nhất 3 options
        max_length=6   # Tối đa 6 options
    )


class ClarificationResponse(BaseModel):
    """
    Schema cho response của generate_questions().
    
    Attributes:
        product_category: Loại sản phẩm được phát hiện (VD: "laptop", "TV")
        questions: Danh sách ĐÚNG 3 câu hỏi
    
    VD:
        product_category = "laptop"
        questions = [ClarificationQuestion(...), ClarificationQuestion(...), ClarificationQuestion(...)]
    """
    product_category: str = Field(
        description="Detected product category (e.g., 'laptop', 'TV', 'headphones')"
    )
    questions: List[ClarificationQuestion] = Field(
        description="Exactly 3 clarification questions to help refine the search",
        min_length=3,  # Đúng 3 câu hỏi
        max_length=3
    )


class RefinedQuery(BaseModel):
    """
    Schema cho refined query sau khi user trả lời.
    
    Attributes:
        query: Query tối ưu để tìm kiếm (VD: "Acer laptops for students under $800")
        summary: Tóm tắt ngắn về nhu cầu user
    
    VD:
        query = "Acer laptops for students under $800"
        summary = "Budget-friendly Acer laptop for student use, under $800"
    """
    query: str = Field(description="Optimized search query in English for product search")
    summary: str = Field(description="Brief summary of what the user is looking for")


# =============================================================================
# PHẦN 2: CLARIFICATION AGENT CLASS
# =============================================================================

class ClarificationAgent:
    """
    Agent tạo câu hỏi làm rõ nhu cầu và build refined query.
    
    Sử dụng GPT-5-mini với OpenAI Structured Outputs:
    - generate_questions(): Tạo 3 câu hỏi từ keyword
    - build_refined_query(): Tạo query tối ưu từ câu trả lời
    
    Attributes:
        MODEL: Model sử dụng (gpt-5-mini)
        openai: OpenAI client instance
        GENERATE_QUESTIONS_PROMPT: System prompt cho generate_questions
        BUILD_QUERY_PROMPT: System prompt cho build_refined_query
    """
    
    # Model sử dụng: GPT-5-mini (cân bằng giữa chi phí và chất lượng)
    MODEL = "gpt-5-mini"
    
    # -----------------------------------------------------------------
    # PROMPT 1: Tạo câu hỏi làm rõ
    # -----------------------------------------------------------------
    GENERATE_QUESTIONS_PROMPT = """You are a smart shopping assistant. When a user wants to search for a product, 
you need to ask 3 clarification questions to better understand their needs.

RULES:
1. Generate exactly 3 questions relevant to the product type
2. Each question should have 4-6 options
3. The last option should always be "Any" or "No preference"
4. Questions should cover different aspects like: brand, use case, budget, features, size, etc.
5. Adapt questions to the product category (laptop questions differ from skincare questions)
6. Keep questions concise and clear

EXAMPLES:
- For "laptop": Ask about brand preference, primary use (gaming/work/study), budget range
- For "TV": Ask about screen size, smart features, brand preference
- For "headphones": Ask about type (over-ear/in-ear), use case (music/gaming/calls), wireless preference
"""
    # Giải thích prompt:
    # - Rule 1-3: Đảm bảo format output đúng
    # - Rule 4: Cover nhiều khía cạnh để query đa dạng
    # - Rule 5: Adapt theo loại sản phẩm (laptop ≠ skincare ≠ TV)
    # - Rule 6: Ngắn gọn, dễ hiểu
    
    # -----------------------------------------------------------------
    # PROMPT 2: Build refined query từ câu trả lời
    # -----------------------------------------------------------------
    BUILD_QUERY_PROMPT = """Based on the user's original keyword and their answers to clarification questions,
build an optimized search query for product search on e-commerce sites.

RULES:
1. Query should be in English
2. Keep it concise - only include relevant keywords
3. If user answered "Any" or "No preference", skip that criterion
4. Include price constraint if user specified a budget (e.g., "under $800")
5. Focus on searchable terms that e-commerce sites would understand
"""
    # Giải thích prompt:
    # - Rule 2: Ngắn gọn, không dài dòng
    # - Rule 3: Bỏ qua tiêu chí "Any" (không giới hạn)
    # - Rule 4: Quan trọng! Budget là filter mạnh
    # - Rule 5: Dùng từ khóa e-commerce hiểu được
    
    def __init__(self):
        """
        Khởi tạo agent với OpenAI client.
        
        OpenAI client tự động lấy OPENAI_API_KEY từ environment variable.
        """
        self.openai = OpenAI()
        logging.info("ClarificationAgent initialized with GPT-5-mini")
    
    def generate_questions(self, keyword: str) -> ClarificationResponse:
        """
        Tạo 3 câu hỏi làm rõ từ keyword.
        
        Flow:
        1. Gọi GPT-5-mini với GENERATE_QUESTIONS_PROMPT
        2. GPT trả về JSON đúng format ClarificationResponse
        3. OpenAI SDK tự động parse thành Pydantic object
        
        Args:
            keyword: Từ khóa user nhập (VD: "laptop", "headphones")
            
        Returns:
            ClarificationResponse chứa:
            - product_category: Loại sản phẩm (VD: "laptop")
            - questions: List 3 ClarificationQuestion
        
        Raises:
            OpenAI exceptions nếu API call fail
        """
        logging.info(f"Generating clarification questions for: '{keyword}'")
        
        # Gọi OpenAI với response_format = Pydantic class
        # Structured Outputs đảm bảo output đúng format
        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.GENERATE_QUESTIONS_PROMPT},
                {"role": "user", "content": f"Product keyword: {keyword}"}
            ],
            response_format=ClarificationResponse  # Structured Output với Pydantic
        )
        
        # result.choices[0].message.parsed đã là Pydantic object
        response = result.choices[0].message.parsed
        logging.info(f"Generated {len(response.questions)} questions")
        return response
    
    def build_refined_query(
        self, 
        keyword: str, 
        questions: List[ClarificationQuestion],
        answers: List[str]
    ) -> RefinedQuery:
        """
        Build refined query từ câu trả lời của user.
        
        Flow:
        1. Format Q&A thành text cho prompt
        2. Gọi GPT-5-mini với BUILD_QUERY_PROMPT
        3. GPT tạo query tối ưu từ context
        
        VD:
            keyword = "laptop"
            questions = [Q1: Brand?, Q2: Use case?, Q3: Budget?]
            answers = ["Acer", "for students", "under $800"]
            → RefinedQuery(query="Acer laptops for students under $800")
        
        Args:
            keyword: Keyword gốc của user
            questions: List câu hỏi đã hỏi
            answers: List câu trả lời của user (cùng thứ tự với questions)
            
        Returns:
            RefinedQuery chứa:
            - query: Query tối ưu để tìm kiếm
            - summary: Tóm tắt nhu cầu
        """
        logging.info("Building refined query...")
        
        # Format Q&A thành text
        # VD: "Q1: What brand?\nA1: Acer\n\nQ2: Use case?\nA2: for students\n\n..."
        qa_text = ""
        for i, (q, a) in enumerate(zip(questions, answers), 1):
            qa_text += f"Q{i}: {q.question}\nA{i}: {a}\n\n"
        
        # Tạo user message với context
        user_message = f"""Original keyword: {keyword}

User's answers:
{qa_text}

Build an optimized search query based on these answers."""
        
        # Gọi GPT-5-mini
        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.BUILD_QUERY_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format=RefinedQuery  # Structured Output
        )
        
        refined = result.choices[0].message.parsed
        logging.info(f"Refined query: '{refined.query}'")
        return refined
