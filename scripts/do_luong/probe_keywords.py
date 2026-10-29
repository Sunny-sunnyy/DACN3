"""Từ khoá nào nằm trong vùng dữ liệu huấn luyện? Tra 20 hàng xóm gần nhất trong ChromaDB (800k sản phẩm train)
cho mỗi từ khoá: nhóm hàng, giá trung vị, khoảng cách. Chỉ chạy local, không gọi API.
Chạy từ segment4/: uv run python ../scripts/do_luong/probe_keywords.py
"""
import statistics
from collections import Counter

import chromadb
from sentence_transformers import SentenceTransformer

KEYWORDS = [
    "laptop", "gaming laptop", "wireless headphones", "noise cancelling headphones", "wireless earbuds",
    "bluetooth speaker", "soundbar", "gaming monitor", "mechanical keyboard", "gaming mouse", "webcam",
    "external ssd", "wifi router", "smartwatch", "tablet", "smart tv", "action camera", "dash cam",
    "air fryer", "coffee maker", "robot vacuum", "microwave", "blender",
    "acoustic guitar", "electric guitar", "guitar pedal", "digital piano", "studio headphones", "microphone",
    "cordless drill", "power bank", "phone case", "car jump starter", "lego set", "drone", "printer",
]

collection = chromadb.PersistentClient(path="products_vectorstore").get_or_create_collection("products")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

print(f"{'tu khoa':28s} {'dist':>5s} {'gia tv':>7s} {'p25-p75':>13s} {'>=900':>5s}  nhom hang (top 20)  | vi du gan nhat")
for kw in KEYWORDS:
    vec = model.encode([kw]).astype(float).tolist()
    r = collection.query(query_embeddings=vec, n_results=20)
    metas, docs, dists = r["metadatas"][0], r["documents"][0], r["distances"][0]
    prices = sorted(m["price"] for m in metas)
    cats = Counter(m["category"] for m in metas).most_common(2)
    q = statistics.quantiles(prices, n=4)
    title = docs[0].split("\n")[0].replace("Title:", "").strip()[:45]
    print(f"{kw:28s} {statistics.mean(dists):5.2f} ${statistics.median(prices):6.0f} ${q[0]:5.0f}-{q[2]:5.0f} "
          f"{sum(p >= 900 for p in prices):5d}  {', '.join(f'{c}:{n}' for c, n in cats):34s} | {title}")
