"""
Test cac phuong an vuot gioi han 2000 SP/query cua Tiki Listing API.

Muc tieu: Chung minh bang du lieu thuc te cach nao lay duoc nhieu SP hon 2000.
Test tren sub-category 1951 (Dung cu nha bep, ~14,478 SP).
"""

import time
from curl_cffi import requests as curl_requests

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://tiki.vn",
}

TEST_CATEGORY = 1951  # Dung cu nha bep, 14,478 SP


def create_session():
    session = curl_requests.Session(impersonate="chrome")
    session.headers.update(BASE_HEADERS)
    return session


def listing_query(session, category_id, extra_params=None):
    """Goi listing API, tra ve (total, list_of_ids, last_page)."""
    params = {
        "category": category_id,
        "limit": 40,
        "page": 1,
        "aggregations": 2,
    }
    if extra_params:
        params.update(extra_params)

    resp = session.get("https://tiki.vn/api/v2/products", params=params, timeout=15)
    if resp.status_code != 200:
        return 0, [], 0

    data = resp.json()
    paging = data.get("paging", {})
    total = paging.get("total", 0)
    last_page = paging.get("last_page", 0)
    items = data.get("data", [])
    ids = [item["id"] for item in items if "id" in item]

    return total, ids, last_page


def get_all_ids(session, category_id, extra_params=None, max_pages=50):
    """Lay tat ca IDs tu listing (toi da max_pages)."""
    all_ids = set()
    params = {
        "category": category_id,
        "limit": 40,
        "aggregations": 1,
    }
    if extra_params:
        params.update(extra_params)

    for page in range(1, max_pages + 1):
        params["page"] = page
        resp = session.get("https://tiki.vn/api/v2/products", params=params, timeout=15)
        if resp.status_code != 200:
            break

        data = resp.json()
        items = data.get("data", [])
        if not items:
            break

        for item in items:
            if "id" in item:
                all_ids.add(item["id"])

        paging = data.get("paging", {})
        if page >= paging.get("last_page", 0):
            break

        time.sleep(0.3)

    return all_ids


def test_baseline(session):
    """Test 1: Baseline — khong dung gi dac biet."""
    print("=" * 70)
    print("TEST 1: BASELINE (khong filter, khong sort)")
    print("=" * 70)

    total, ids, last_page = listing_query(session, TEST_CATEGORY)
    print(f"  Category {TEST_CATEGORY}: total={total:,}, last_page={last_page}")
    print(f"  -> Lay duoc toi da: {min(total, last_page * 40):,} SP")
    print(f"  -> Thuc te duoc: {last_page * 40} SP (50 pages x 40 = 2000 max)")
    print()
    return total


def test_sort_rotation(session):
    """Test 2: Sort Rotation — thu cac kieu sort khac nhau."""
    print("=" * 70)
    print("TEST 2: SORT ROTATION")
    print("  Y tuong: Tiki API co param 'sort'. Moi kieu sort tra ve")
    print("  2000 SP khac nhau. Merge lai -> duoc nhieu hon 2000.")
    print("=" * 70)

    sort_options = {
        "default": {},
        "top_seller": {"sort": "top_seller"},
        "price_asc": {"sort": "price,asc"},
        "price_desc": {"sort": "price,desc"},
        "newest": {"sort": "newest"},
    }

    all_ids = set()
    for sort_name, params in sort_options.items():
        total, ids, last_page = listing_query(session, TEST_CATEGORY, params)
        readable = min(total, last_page * 40)
        print(f"  sort={sort_name:15s} -> total={total:>6,}, last_page={last_page:>3}, reachable={readable:>5,}, page1_ids={len(ids)}")
        time.sleep(0.5)

        # Lay 3 pages dau de so sanh
        page_ids = set(ids)
        for p in [2, 3]:
            _, more_ids, _ = listing_query(session, TEST_CATEGORY, {**params, "page": p})
            page_ids.update(more_ids)
            time.sleep(0.3)

        before = len(all_ids)
        all_ids.update(page_ids)
        new_ids = len(all_ids) - before
        print(f"    -> 3 pages: {len(page_ids)} IDs, {new_ids} moi (chua co truoc do)")

    print(f"\n  KET QUA: Merge 5 sorts x 3 pages = {len(all_ids)} IDs duy nhat")
    print(f"  So voi baseline 2000 -> tang {len(all_ids) / 120 * 100 - 100:.0f}%")
    print()
    return all_ids


def test_price_slicing(session):
    """Test 3: Price-Range Slicing — chia query theo khoang gia."""
    print("=" * 70)
    print("TEST 3: PRICE-RANGE SLICING")
    print("  Y tuong: Them param 'price=min,max' de chia nho ket qua.")
    print("  Moi khoang gia la 1 query rieng, moi cai toi da 2000 SP.")
    print("=" * 70)

    price_ranges = [
        (0, 50000),
        (50000, 100000),
        (100000, 200000),
        (200000, 500000),
        (500000, 1000000),
        (1000000, 2000000),
        (2000000, 5000000),
        (5000000, 50000000),
    ]

    total_reachable = 0
    for p_min, p_max in price_ranges:
        params = {"price": f"{p_min},{p_max}"}
        total, ids, last_page = listing_query(session, TEST_CATEGORY, params)
        reachable = min(total, last_page * 40)
        total_reachable += reachable
        cap_flag = " !! OVER_CAP" if total > 2000 else ""
        print(f"  price={p_min:>10,}-{p_max:>10,} -> total={total:>6,}, reachable={reachable:>5,}{cap_flag}")
        time.sleep(0.5)

    print(f"\n  KET QUA: Tong reachable = {total_reachable:,} SP")
    print(f"  So voi baseline 2000 -> tang {total_reachable / 2000 * 100 - 100:.0f}%")
    print()
    return total_reachable


def test_sub_sub_categories(session):
    """Test 4: Sub-Sub-Category Drilling — lay categories con."""
    print("=" * 70)
    print("TEST 4: SUB-SUB-CATEGORY DRILLING")
    print("  Y tuong: Dung aggregations=2 de lay sub-sub-categories.")
    print("  Moi sub-sub nho hon -> co the <2000 SP.")
    print("=" * 70)

    params = {"category": TEST_CATEGORY, "limit": 1, "page": 1, "aggregations": 2}
    resp = session.get("https://tiki.vn/api/v2/products", params=params, timeout=15)
    data = resp.json()

    filters = data.get("filters", [])
    sub_subs = []
    for f in filters:
        if f.get("query_name") == "category":
            for v in f.get("values", []):
                sub_subs.append({
                    "id": v.get("query_value"),
                    "name": v.get("display_value", ""),
                    "count": v.get("count", 0),
                })

    if not sub_subs:
        print("  Khong co sub-sub-categories!")
        return 0

    total_reachable = 0
    for ss in sorted(sub_subs, key=lambda x: x["count"], reverse=True):
        reachable = min(ss["count"], 2000)
        total_reachable += reachable
        cap_flag = " !! OVER_CAP" if ss["count"] > 2000 else ""
        print(f"  [{ss['id']:>8}] {ss['name']:<40} -> {ss['count']:>6,} SP, reachable={reachable:>5,}{cap_flag}")
        time.sleep(0.3)

    print(f"\n  Tong sub-sub: {len(sub_subs)}")
    print(f"  Tong reachable = {total_reachable:,} SP")
    print(f"  So voi baseline 2000 -> tang {total_reachable / 2000 * 100 - 100:.0f}%")
    print()
    return total_reachable


def main():
    session = create_session()

    print(f"\nTEST CATEGORY: {TEST_CATEGORY} (Dung cu nha bep, ~14,478 SP)")
    print(f"Van de: Listing API chi tra ve toi da 2000 SP. Lam sao lay het?\n")

    actual_total = test_baseline(session)
    test_sort_rotation(session)
    test_price_slicing(session)
    test_sub_sub_categories(session)

    print("=" * 70)
    print("TOM TAT")
    print("=" * 70)
    print(f"  Tong SP thuc te:  {actual_total:,}")
    print(f"  Baseline (2000):  {2000:,}")
    print(f"  -> Xem ket qua tren de chon phuong an tot nhat.")

    session.close()


if __name__ == "__main__":
    main()
