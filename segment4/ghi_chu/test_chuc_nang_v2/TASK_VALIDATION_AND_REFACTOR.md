# 🎯 NHIỆM VỤ: INPUT VALIDATION & CODE REFACTOR

> **Ngày tạo:** 2026-02-06  
> **Target file:** `bestbuy3.py`  
> **Status:** 📋 Planning

---

## 📋 MỤC LỤC

1. [Tổng quan](#1-tổng-quan)
2. [Nhiệm vụ 1: Keyword Validation Agent](#2-nhiệm-vụ-1-keyword-validation-agent)
3. [Nhiệm vụ 2: Code Refactoring](#3-nhiệm-vụ-2-code-refactoring)
4. [Implementation Plan](#4-implementation-plan)
5. [Testing Checklist](#5-testing-checklist)

---

## 1. TỔNG QUAN

### 🎯 **Mục tiêu:**
1. **Validation Agent**: Kiểm tra keyword đầu vào của user trước khi generate questions
2. **Refactor Code**: Tách `bestbuy3.py` (1225 dòng) thành các module nhỏ hơn

### 📊 **Lý do cần làm:**

| Vấn đề | Giải pháp |
|--------|-----------|
| User nhập "dànbhèbe" → Tạo câu hỏi vô nghĩa | Validate trước, yêu cầu nhập lại |
| `bestbuy3.py` quá dài (1225 lines) | Tách thành modules |
| Khó maintain và debug | Code modular, dễ đọc |

---

## 2. NHIỆM VỤ 1: KEYWORD VALIDATION AGENT

### 📝 **Mô tả:**
Tạo agent để kiểm tra keyword có phải là product hợp lệ hay không.

### ⚙️ **Specifications:**

| Item | Value |
|------|-------|
| Model | `gpt-5-mini` |
| Behavior on invalid | Báo lỗi, yêu cầu nhập lại |
| Suggest correction? | ❌ Không |
| Apply to | `bestbuy3.py` |

### 🔄 **Flow Diagram:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KEYWORD VALIDATION FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER INPUT: "dànbhèbe"                                                      │
│       ↓                                                                      │
│  1️⃣ KeywordValidationAgent.validate(keyword)                                │
│  ├─► GPT-5-mini with Structured Output                                      │
│  ├─► Check: Is this a valid product search query?                           │
│  │                                                                           │
│  │   VALID examples:                                                         │
│  │   ├─► "laptop"                                                           │
│  │   ├─► "Smart TV"                                                         │
│  │   ├─► "iPhone 15 Pro"                                                    │
│  │   ├─► "gaming headphones"                                                │
│  │   └─► "MacBook Air M2"                                                   │
│  │                                                                           │
│  │   INVALID examples:                                                       │
│  │   ├─► "dànbhèbe"         (gibberish)                                     │
│  │   ├─► "asdfgh"           (random keys)                                   │
│  │   ├─► "12345"            (numbers only)                                  │
│  │   ├─► "hello world"      (not a product)                                 │
│  │   └─► ""                 (empty)                                         │
│  │                                                                           │
│  └─► Return ValidationResult(is_valid, error_message)                        │
│       ↓                                                                      │
│  2️⃣ Check Result:                                                           │
│  ├─► is_valid = True  → Continue to ClarificationAgent                      │
│  └─► is_valid = False → Show error, ask user to re-enter                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 📂 **New Files:**

| File | Mô tả |
|------|-------|
| `price_agents/validation_agent.py` | 🆕 KeywordValidationAgent class |
| `test_chuc_nang_v2/test_validation.ipynb` | 🆕 Notebook test validation |

### 📦 **Pydantic Schema:**

```python
class ValidationResult(BaseModel):
    """Result of keyword validation."""
    is_valid: bool = Field(description="True if keyword is a valid product search")
    error_message: str = Field(description="Error message if invalid, empty if valid")
    category: str = Field(description="Detected category if valid (e.g., 'electronics', 'appliances')")
```

### 🤖 **Agent Code:**

```python
class KeywordValidationAgent(BaseAgent):
    """
    Validates if user's keyword is a valid product search query.
    Uses GPT-5-mini to check.
    """
    
    name = "Keyword Validation Agent"
    color = BaseAgent.YELLOW
    MODEL = "gpt-5-mini"
    
    SYSTEM_PROMPT = """You validate if a user's search query is a valid product search.

VALID product queries:
- Product names: "laptop", "TV", "headphones", "camera"
- Specific products: "iPhone 15", "MacBook Air M2", "Sony WH-1000XM5"
- Product categories: "gaming laptop", "wireless earbuds", "smart home devices"
- Brand + product: "Samsung TV", "Dell monitor", "Bose speaker"

INVALID queries:
- Gibberish: "dànbhèbe", "asdfgh", "qwerty123"
- Random characters: "!!!@@@", "abc123xyz"
- Non-product searches: "hello world", "how are you", "weather today"
- Too vague: "thing", "stuff", "buy something"
- Empty or just spaces

Respond with:
- is_valid: true/false
- error_message: If invalid, explain why (e.g., "This doesn't appear to be a valid product name")
- category: If valid, detected category (e.g., "electronics", "appliances", "accessories")
"""
    
    def validate(self, keyword: str) -> ValidationResult:
        """
        Validate if keyword is a valid product search.
        
        Args:
            keyword: User's search keyword
            
        Returns:
            ValidationResult with is_valid, error_message, category
        """
        ...
```

### 📊 **Test Cases:**

| Input | Expected is_valid | Expected error_message |
|-------|-------------------|------------------------|
| `"laptop"` | ✅ True | `""` |
| `"Smart TV"` | ✅ True | `""` |
| `"iPhone 15 Pro"` | ✅ True | `""` |
| `"dànbhèbe"` | ❌ False | `"This doesn't appear to be a valid product name..."` |
| `"asdfgh"` | ❌ False | `"..."` |
| `"12345"` | ❌ False | `"..."` |
| `""` | ❌ False | `"Please enter a product keyword"` |

---

## 3. NHIỆM VỤ 2: CODE REFACTORING

### 📝 **Mô tả:**
Tách `bestbuy3.py` (1225 dòng) thành các file module nhỏ hơn.

### 📊 **Hiện trạng `bestbuy3.py`:**

```
bestbuy3.py (1225 lines)
├── Section 1: Setup & Configuration         (~20 lines)
├── Section 2: Pydantic Schemas              (~50 lines)
├── Section 3: UnifiedScrapedDeal            (~80 lines)
├── Section 4: ClarificationAgent            (~100 lines)
├── Section 5: MultiSourceScannerAgent       (~100 lines)
├── Section 6: Global Variables              (~20 lines)
├── Section 7: Agent Initialization          (~40 lines)
├── Section 8: Pipeline Functions            (~100 lines)
├── Section 9: Gradio Helpers                (~80 lines)
├── Section 10: Clarification Flow           (~100 lines)
├── Section 11: Main Search Pipeline         (~200 lines)
├── Section 12: Push Notification            (~40 lines)
├── Section 13: Gradio UI Definition         (~250 lines)
└── Section 14: Main Entry Point             (~20 lines)
```

### 🎯 **Proposed Structure:**

```
price_agents/
├── __init__.py
├── agent.py                           # BaseAgent (existing)
├── deals.py                           # Deal, DealSelection (existing)
├── ensemble_agent.py                  # EnsembleAgent (existing)
├── messaging_agent.py                 # MessagingAgent (existing)
├── bestbuy_deals.py                   # BestBuy scraping (existing)
├── bestbuy_scanner_agent.py           # BestBuy agents (existing)
├── amazon_deals.py                    # Amazon scraping (existing)
├── amazon_scanner_agent.py            # Amazon agents (existing)
│
├── 🆕 validation_agent.py             # KeywordValidationAgent
├── 🆕 clarification_agent.py          # ClarificationAgent 
├── 🆕 multi_source_scanner_agent.py   # MultiSourceScannerAgent
├── 🆕 unified_deal.py                 # UnifiedScrapedDeal class
└── 🆕 gradio_helpers.py               # Gradio helper functions

bestbuy3.py (AFTER REFACTOR: ~300-400 lines)
├── Imports from modules
├── Global variables
├── Main pipeline function
├── Gradio UI definition
└── Main entry point
```

### 📂 **New Files to Create:**

| File | Content | Lines |
|------|---------|-------|
| `price_agents/validation_agent.py` | `KeywordValidationAgent` | ~80 |
| `price_agents/clarification_agent.py` | `ClarificationAgent`, Pydantic schemas | ~120 |
| `price_agents/multi_source_scanner_agent.py` | `MultiSourceScannerAgent` | ~80 |
| `price_agents/unified_deal.py` | `UnifiedScrapedDeal` class | ~70 |
| `price_agents/gradio_helpers.py` | `html_for_logs`, `opportunities_to_table`, etc. | ~100 |

### 📊 **Before vs After:**

| Metric | Before | After |
|--------|--------|-------|
| `bestbuy3.py` lines | **1225** | **~300-400** |
| Modules | 1 monolithic file | 5+ focused modules |
| Reusability | Low | High (agents can be used elsewhere) |
| Maintainability | Hard | Easy |
| Testing | Difficult | Easy (test each module) |

---

## 4. IMPLEMENTATION PLAN

### 📅 **Thứ tự thực hiện (UPDATED):**

```
Phase 1: Refactor bestbuy3.py ← LÀM TRƯỚC
├── Step 1.1: Create clarification_agent.py
├── Step 1.2: Create unified_deal.py
├── Step 1.3: Create multi_source_scanner_agent.py
├── Step 1.4: Create gradio_helpers.py
├── Step 1.5: Refactor bestbuy3.py (import from modules)
└── Step 1.6: Test app hoạt động OK

Phase 2: Add Validation Agent ← LÀM SAU
├── Step 2.1: Create test_validation.ipynb (test trước)
├── Step 2.2: Create validation_agent.py
├── Step 2.3: Integrate vào bestbuy3.py
└── Step 2.4: Test full flow

Phase 3: Update Documentation
├── Step 3.1: Update COMPLETE_PROJECT_DOCUMENTATION.md
└── Step 3.2: Update this file with completion status
```

### ⏱️ **Estimated Time:**

| Phase | Time |
|-------|------|
| Phase 1 (Refactor) | 45 min |
| Phase 2 (Validation) | 30 min |
| Phase 3 (Docs) | 15 min |
| **Total** | **~1.5 hours** |

---

## 5. TESTING CHECKLIST

### ✅ **Phase 1: Refactored bestbuy3.py (LÀM TRƯỚC)**

- [ ] `clarification_agent.py` - imports work
- [ ] `unified_deal.py` - imports work
- [ ] `multi_source_scanner_agent.py` - imports work
- [ ] `gradio_helpers.py` - imports work
- [ ] App starts without errors
- [ ] Clarification flow works
- [ ] Search pipeline works (BestBuy + Amazon)
- [ ] Results display correctly
- [ ] Push notification works

### ✅ **Phase 2: Validation Agent (LÀM SAU)**

- [ ] Test với keyword hợp lệ: "laptop" → is_valid=True
- [ ] Test với keyword hợp lệ: "Smart TV" → is_valid=True
- [ ] Test với gibberish: "dànbhèbe" → is_valid=False
- [ ] Test với random: "asdfgh" → is_valid=False
- [ ] Test với empty: "" → is_valid=False
- [ ] Test với numbers: "12345" → is_valid=False
- [ ] Validation blocks invalid keywords in app
- [ ] Valid keywords proceed to clarification

---

## 📝 NOTES

### 💡 **Design Decisions:**

1. **Why refactor FIRST?**
   - Cần cấu trúc code sạch trước khi thêm feature mới
   - Validation agent sẽ được thêm vào file đã clean
   - Dễ test và maintain hơn

2. **Why GPT-5-mini for validation?**
   - Đây là project học tập, không cần optimize cost
   - GPT-5-mini đủ thông minh để nhận biết product vs gibberish

3. **Why no spell correction?**
   - Keep it simple (KISS principle)
   - User có thể tự sửa và nhập lại
   - Tránh suggest sai (e.g., "airpod pro" → không phải typo)

---

## 📌 BƯỚC TIẾP THEO

**Bắt đầu với Phase 1: REFACTOR**

1. Tạo `price_agents/clarification_agent.py`
2. Tạo `price_agents/unified_deal.py`
3. Tạo `price_agents/multi_source_scanner_agent.py`
4. Tạo `price_agents/gradio_helpers.py`
5. Refactor `bestbuy3.py` để import từ các modules
6. Test app hoạt động OK

**Sau khi Phase 1 xong → Phase 2: Validation Agent**

---

*Created: 2026-02-06*  
*Author: AI Assistant*  
*Status: 📋 Planning (Phase 1: Refactor → Phase 2: Validation)*

