import re
import unicodedata
from pricer_vi.items import Item

MIN_CHARS = 50
MIN_PRICE = 1_000
MAX_PRICE = 50_000_000
MAX_TEXT_EACH = 3_000
MAX_TEXT_TOTAL = 4_000

# Regex patterns compiled once
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002700-\U000027BF"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero width joiner
    "]+",
    flags=re.UNICODE,
)
HTML_ENTITY_PATTERN = re.compile(r"&#x[0-9a-fA-F]+;|&[a-z]+;")
SEPARATOR_PATTERN = re.compile(r"[-=]{5,}")
SKU_PATTERN = re.compile(r"\b(?=[A-Z0-9]{8,}\b)(?=.*[A-Z])(?=.*\d)[A-Z0-9]+\b")
BARCODE_PATTERN = re.compile(r"\|?\s*Barcode:\s*[^|]*\|", re.IGNORECASE)
MULTI_SPACE_PATTERN = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """9-step Vietnamese text cleaning pipeline."""
    # 1. Unicode NFC normalization (standardize Vietnamese diacritics)
    text = unicodedata.normalize("NFC", text)
    # 2. Remove HTML entities (&#x1f4e6; &amp; etc.)
    text = HTML_ENTITY_PATTERN.sub("", text)
    # 3. Remove emoji Unicode
    text = EMOJI_PATTERN.sub("", text)
    # 4. Remove separators (-----, =====)
    text = SEPARATOR_PATTERN.sub("", text)
    # 5. Remove barcode entries (Hasaki: "| Barcode: 8999999581770 |") — before SKU removal
    text = BARCODE_PATTERN.sub("", text)
    # 5b. Remove SKU/product codes (8+ chars, uppercase+digits)
    text = SKU_PATTERN.sub("", text)
    # 6. Normalize whitespace (\n, \r, \t, multi-space -> single space)
    text = MULTI_SPACE_PATTERN.sub(" ", text).strip()
    # 7. Truncate per-field
    return text[:MAX_TEXT_EACH]


def scrub(title: str, features: str) -> str:
    """Combine title + features into cleaned full text, removing title duplication."""
    title_clean = clean_text(title)
    features_clean = clean_text(features)
    # Remove title repeated at start of features
    if features_clean.lower().startswith(title_clean.lower()):
        features_clean = features_clean[len(title_clean):].strip()
    result = title_clean + "\n" + features_clean
    return result.strip()[:MAX_TEXT_TOTAL]


def parse(datapoint: dict, category: str) -> Item | None:
    """Parse a raw JSONL datapoint into an Item, or None if filtered out."""
    price = datapoint.get("price", 0)
    if not isinstance(price, (int, float)):
        return None
    price = int(price)
    if not (MIN_PRICE <= price <= MAX_PRICE):
        return None

    title = datapoint.get("title", "")
    features = datapoint.get("features", "")
    brand = datapoint.get("brand", "").strip()

    full = scrub(title, features)
    if len(full) < MIN_CHARS:
        return None

    return Item(
        title=title.strip(),
        category=category,
        price=price,
        full=full,
        brand=brand if brand else None,
    )
