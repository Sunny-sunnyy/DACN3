from pricer.items import Item

import json
import re
import html
import unicodedata

from bs4 import BeautifulSoup
from nltk.corpus import stopwords

MIN_CHARS = 600
MIN_PRICE = 0.5
MAX_PRICE = 999.49
MAX_TEXT_EACH = 3000
MAX_TEXT_TOTAL = 4000

REMOVALS = [
    "Part Number",
    "Best Sellers Rank",
    "Batteries Included?",
    "Batteries Required?",
    "Item model number",
]

# Load NLTK stopwords once at module level
#STOP_WORDS = set(stopwords.words("english"))

# Marketing spam phrases to remove (case-insensitive)
MARKETING_PHRASES = [
    r"click add to cart",
    r"add to cart now",
    r"buy now",
    r"order now",
    r"limited time offer",
    r"100% satisfaction guarantee",
    r"satisfaction guaranteed",
    r"money back guarantee",
    r"risk free",
    r"act now",
    r"best seller",
    r"free shipping",
    r"as seen on tv",
    r"scroll up and click",
    r"don't miss out",
    r"hurry up",
    r"what are you waiting for",
    r"makes a great gift",
    r"perfect gift",
    r"gift idea",
]

MARKETING_PATTERN = re.compile(
    "|".join(MARKETING_PHRASES), flags=re.IGNORECASE
)

# Regex patterns (compiled once)
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\S+@\S+\.\S+")
PRODUCT_CODE_PATTERN = re.compile(r"\b(?=[A-Z0-9]{7,}\b)(?=.*[A-Z])(?=.*\d)[A-Z0-9]+\b")
UPC_EAN_PATTERN = re.compile(r"\b\d{8,14}\b")
REPEATED_PUNCT_PATTERN = re.compile(r"([!?.]){2,}")
EMPTY_BRACKETS_PATTERN = re.compile(r"\(\s*\)|\[\s*\]|\{\s*\}")
MULTI_SPACE_PATTERN = re.compile(r"\s{2,}")
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "\U00002600-\U000026FF"  # misc symbols (★, ♥, ☀, etc.)
    "\U00002700-\U000027BF"  # dingbats
    "\U00002B50-\U00002B55"  # stars
    "\U000023CF-\U000023FA"  # misc technical
    "\U0000200D"             # zero width joiner
    "\U0000FE0F"             # variation selector
    "]+",
    flags=re.UNICODE,
)
# Misc symbols: arrows, bullets, checkmarks, etc.
MISC_SYMBOLS_PATTERN = re.compile(r"[►▶▷◀◁◆◇○●■□▪▫✓✔✗✘✦✧★☆♦♠♣♥♡→←↑↓«»†‡§¶©®™±×÷≤≥≠≈∞∑∏√∫]")


def strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    soup = BeautifulSoup(text, "html.parser")
    clean = soup.get_text(separator=" ")
    return html.unescape(clean)


def normalize_unicode(text: str) -> str:
    """Normalize unicode to NFKD form and remove non-ASCII control chars."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cc")


def remove_emojis_and_symbols(text: str) -> str:
    """Strip emojis, icons, and miscellaneous symbols."""
    text = EMOJI_PATTERN.sub("", text)
    text = MISC_SYMBOLS_PATTERN.sub("", text)
    return text


def remove_urls_and_emails(text: str) -> str:
    """Strip URLs and email addresses."""
    text = URL_PATTERN.sub("", text)
    text = EMAIL_PATTERN.sub("", text)
    return text


def remove_marketing_spam(text: str) -> str:
    """Remove common marketing filler phrases."""
    return MARKETING_PATTERN.sub("", text)


def remove_codes(text: str) -> str:
    """Remove product codes (7+ alphanum) and UPC/EAN barcodes (8-14 digits)."""
    text = PRODUCT_CODE_PATTERN.sub("", text)
    text = UPC_EAN_PATTERN.sub("", text)
    return text


def collapse_punctuation(text: str) -> str:
    """Collapse repeated punctuation marks (!!!, ...) into a single one."""
    text = REPEATED_PUNCT_PATTERN.sub(r"\1", text)
    text = EMPTY_BRACKETS_PATTERN.sub("", text)
    return text


# def remove_stopwords(text: str) -> str:
#     """Remove English stopwords while preserving word order."""
#     words = text.split()
#     return " ".join(w for w in words if w not in STOP_WORDS)


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces and strip."""
    return MULTI_SPACE_PATTERN.sub(" ", text).strip()


def clean_text(text: str) -> str:
    """Full cleaning pipeline for a single text field."""
    text = strip_html(text)
    text = normalize_unicode(text)
    text = remove_emojis_and_symbols(text)
    text = remove_urls_and_emails(text)
    text = remove_marketing_spam(text)
    text = remove_codes(text)
    text = collapse_punctuation(text)
    text = text.lower()
    #text = remove_stopwords(text)
    text = normalize_whitespace(text)
    return text


def simplify(text_list) -> str:
    """Return a cleaned, simplified string, limited to MAX_TEXT_EACH characters."""
    raw = (
        str(text_list)
        .replace("\n", " ")
        .replace("\r", "")
        .replace("\t", "")
    )
    return clean_text(raw)[:MAX_TEXT_EACH]


def scrub(title, description, features, details) -> str:
    """Return a fully cleansed product string."""
    for remove in REMOVALS:
        details.pop(remove, None)

    result = clean_text(title) + "\n"
    if description:
        result += simplify(description) + "\n"
    if features:
        result += simplify(features) + "\n"
    if details:
        details_str = json.dumps(details)
        result += clean_text(details_str) + "\n"
    return result.strip()[:MAX_TEXT_TOTAL]


def get_weight(details):
    """Parse item weight from details dict. Returns weight in pounds."""
    weight_str = details.get("Item Weight")
    if weight_str:
        parts = weight_str.split(" ")
        amount = float(parts[0])
        unit = parts[1].lower()
        if unit == "pounds":
            return amount
        elif unit == "ounces":
            return amount / 16
        elif unit == "grams":
            return amount / 453.592
        elif unit == "milligrams":
            return amount / 453592
        elif unit == "kilograms":
            return amount / 0.453592
        elif unit == "hundredths" and parts[2].lower() == "pounds":
            return amount / 100
    return 0


def parse(datapoint, category):
    """Parse a raw datapoint into an Item. Returns None if invalid."""
    try:
        price = float(datapoint["price"])
    except ValueError:
        return None
    if MIN_PRICE <= price <= MAX_PRICE:
        title = datapoint["title"]
        description = datapoint["description"]
        features = datapoint["features"]
        details = json.loads(datapoint["details"])
        weight = get_weight(details)
        full = scrub(title, description, features, details)
        if len(full) >= MIN_CHARS:
            return Item(
                title=title,
                category=category,
                price=price,
                full=full,
                weight=weight,
            )
