"""
Lay sub-categories tu cac category lon de vuot qua gioi han 2000 san pham/category.
Tiki tra ve filters trong listing API, bao gom sub-category IDs.
"""

import json
import time
from pathlib import Path
from curl_cffi import requests as curl_requests

DATA_DIR = Path(__file__).parent / "data" / "raw"

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://tiki.vn",
}

# Categories chinh co 2000+ san pham (tu 01_get_categories.py)
PARENT_CATEGORIES = [
    (1846, "Laptop - Thiet bi IT"),
    (1815, "May anh - Quay phim"),
    (4221, "Dien tu - Dien lanh"),
    (1882, "Phu kien - Thiet bi so"),
    (8594, "O to - Xe may - Xe dap"),
    (1883, "Nha cua - Doi song"),
    (4384, "Dien gia dung"),
    (15078, "Suc khoe - Lam dep"),
    (8322, "Do choi - Me va be"),
    (931, "Thoi trang nam"),
    (915, "Thoi trang nu"),
    (6000, "Tui - Vi nam"),
    (1520, "Bach hoa online"),
    (2549, "Lam vuon - Thu cung"),
    (27498, "Nha sach Tiki"),
]


def get_subcategories(session, parent_id: int) -> list[dict]:
    """Lay sub-categories tu filters cua listing API."""
    url = "https://tiki.vn/api/v2/products"
    params = {
        "category": parent_id,
        "limit": 1,
        "page": 1,
        "aggregations": 2,  # aggregations=2 tra ve filters chi tiet hon
    }

    resp = session.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        return []

    data = resp.json()
    filters = data.get("filters", [])

    # Tim filter co type="category"
    for f in filters:
        if f.get("query_name") == "category":
            values = f.get("values", [])
            return [
                {
                    "id": v.get("query_value"),
                    "name": v.get("display_value", ""),
                    "count": v.get("count", 0),
                }
                for v in values
                if v.get("query_value")
            ]

    return []


def main():
    session = curl_requests.Session(impersonate="chrome")
    session.headers.update(BASE_HEADERS)

    all_subcats = {}
    total_estimated = 0

    for parent_id, parent_name in PARENT_CATEGORIES:
        subcats = get_subcategories(session, parent_id)
        all_subcats[parent_id] = {
            "name": parent_name,
            "subcategories": subcats,
        }

        parent_total = sum(s.get("count", 0) for s in subcats)
        total_estimated += parent_total

        print(f"\n[{parent_id}] {parent_name} — {len(subcats)} sub-categories, ~{parent_total:,} san pham")
        for s in subcats[:8]:
            print(f"    {s['id']:>8} | {s['count']:>6} | {s['name']}")
        if len(subcats) > 8:
            print(f"    ... va {len(subcats) - 8} sub-categories nua")

        time.sleep(0.5)

    # Summary
    all_sub_list = []
    for pid, pdata in all_subcats.items():
        for s in pdata["subcategories"]:
            all_sub_list.append({
                "parent_id": pid,
                "parent_name": pdata["name"],
                "id": s["id"],
                "name": s["name"],
                "count": s["count"],
            })

    all_sub_list.sort(key=lambda x: x["count"], reverse=True)

    print(f"\n{'=' * 80}")
    print(f"Tong: {len(all_sub_list)} sub-categories, uoc tinh ~{total_estimated:,} san pham")
    print(f"\nTop 20 sub-categories (nhieu san pham nhat):")
    for s in all_sub_list[:20]:
        print(f"  {s['id']:>8} | {s['count']:>6} | {s['parent_name']} > {s['name']}")

    # Loc sub-categories co >= 100 san pham
    usable = [s for s in all_sub_list if s["count"] >= 100]
    usable_total = sum(s["count"] for s in usable)
    print(f"\nSub-categories co >= 100 san pham: {len(usable)}, tong ~{usable_total:,}")

    # Save
    out_file = DATA_DIR / "subcategories_scan.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_subcats, f, ensure_ascii=False, indent=2)

    out_file2 = DATA_DIR / "subcategories_flat.json"
    with open(out_file2, "w", encoding="utf-8") as f:
        json.dump(all_sub_list, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {out_file} va {out_file2}")
    session.close()


if __name__ == "__main__":
    main()
