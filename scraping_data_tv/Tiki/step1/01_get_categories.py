"""
Step 2: Lay danh sach categories tu Tiki.
Goi API listing voi nhieu category IDs da biet, dem so san pham moi category.
Muc tieu: Xac dinh 15-20 categories tot nhat de cao ~60K+ san pham.
"""

import json
from pathlib import Path
from curl_cffi import requests as curl_requests
import time

DATA_DIR = Path(__file__).parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://tiki.vn",
}

# Cac category IDs chinh cua Tiki (lay tu sitemap va cac repos tham khao)
# Format: (category_id, ten_category)
KNOWN_CATEGORIES = [
    # Dien tu
    (1789, "Dien thoai - May tinh bang"),
    (1846, "Laptop - Thiet bi IT"),
    (1815, "May anh - Quay phim"),
    (4221, "Dien tu - Dien lanh"),
    (1882, "Phu kien - Thiet bi so"),
    (8594, "O to - Xe may - Xe dap"),

    # Gia dung
    (1883, "Nha cua - Doi song"),
    (4384, "Dien gia dung"),
    (15078, "Suc khoe - Lam dep"),
    (8322, "Do choi - Me va be"),
    (11312, "Thiet bi so - Phu kien so"),

    # Thoi trang (da co 41K tu Kaggle, nhung van lay them)
    (931, "Thoi trang nam"),
    (915, "Thoi trang nu"),
    (4371, "Giay - Dep nam"),
    (4378, "Giay - Dep nu"),
    (6000, "Tui - Vi nam"),
    (6018, "Tui - Vi nu"),

    # Khac
    (8168, "The thao - Da ngoai"),
    (17166, "Cross Border - Hang quoc te"),
    (1520, "Bach hoa online"),
    (2549, "Lam vuon - Thu cung"),
    (1801, "May doc sach"),
    (8594, "Phu kien xe"),
    (27498, "Nha sach Tiki"),
]


def get_category_info(session, category_id: int, category_name: str) -> dict:
    """Goi listing API de lay so luong san pham va sample data."""
    url = "https://tiki.vn/api/v2/products"
    params = {
        "category": category_id,
        "limit": 5,
        "page": 1,
        "include": "advertisement",
        "aggregations": 2,
    }

    try:
        resp = session.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return {
                "id": category_id,
                "name": category_name,
                "status": resp.status_code,
                "total": 0,
            }

        data = resp.json()
        paging = data.get("paging", {})
        items = data.get("data", [])

        # Lay price range tu sample
        prices = [item.get("price", 0) for item in items if item.get("price", 0) > 0]
        sample_names = [item.get("name", "")[:60] for item in items[:3]]

        return {
            "id": category_id,
            "name": category_name,
            "status": 200,
            "total": paging.get("total", 0),
            "total_text": paging.get("total_text", ""),
            "last_page": paging.get("last_page", 0),
            "price_min": min(prices) if prices else 0,
            "price_max": max(prices) if prices else 0,
            "samples": sample_names,
        }
    except Exception as e:
        return {
            "id": category_id,
            "name": category_name,
            "status": "error",
            "total": 0,
            "error": str(e),
        }


def main():
    session = curl_requests.Session(impersonate="chrome")
    session.headers.update(BASE_HEADERS)

    results = []
    seen_ids = set()

    print(f"Scanning {len(KNOWN_CATEGORIES)} categories...\n")
    print(f"{'ID':>8} | {'Total':>8} | {'Category':<40} | {'Price range'}")
    print("-" * 90)

    for cat_id, cat_name in KNOWN_CATEGORIES:
        if cat_id in seen_ids:
            continue
        seen_ids.add(cat_id)

        info = get_category_info(session, cat_id, cat_name)
        results.append(info)

        total = info.get("total", 0)
        p_min = info.get("price_min", 0)
        p_max = info.get("price_max", 0)
        status = info.get("status", "?")

        if status == 200:
            print(f"{cat_id:>8} | {total:>8} | {cat_name:<40} | {p_min:>12,} - {p_max:>12,} VND")
        else:
            print(f"{cat_id:>8} | {'FAIL':>8} | {cat_name:<40} | status={status}")

        time.sleep(0.5)

    # Sort by total descending
    results.sort(key=lambda x: x.get("total", 0), reverse=True)

    # Summary
    total_products = sum(r.get("total", 0) for r in results if r.get("status") == 200)
    ok_categories = sum(1 for r in results if r.get("status") == 200 and r.get("total", 0) > 0)

    print(f"\n{'=' * 90}")
    print(f"Tong: {ok_categories} categories hoat dong, ~{total_products:,} san pham (cap o 2000/category)")
    print(f"Luu y: 'total' bi cap o 2000, so thuc te co the nhieu hon.")
    print(f"\nTop 10 categories:")
    for r in results[:10]:
        if r.get("status") == 200:
            print(f"  {r['id']:>8} | {r['total']:>6} | {r['name']}")

    # Save
    out_file = DATA_DIR / "categories_scan.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_file}")

    session.close()


if __name__ == "__main__":
    main()
