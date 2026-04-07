"""Pydantic models for Tiki scraped products."""

from pydantic import BaseModel


class TikiProduct(BaseModel):
    """San pham da scrape tu Tiki, day du thong tin."""

    product_id: int
    title: str
    brand: str
    price: int  # VND
    features: str  # description + specifications gop lai
    url: str
    category: str  # breadcrumb path: "Laptop > Linh kien > RAM"
    category_id: int
