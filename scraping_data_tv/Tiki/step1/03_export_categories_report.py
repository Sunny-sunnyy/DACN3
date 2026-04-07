"""Export category scan results to CSV for easy viewing."""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "raw"
OUT_DIR = Path(__file__).parent.parent  # scraping_data_tv/Tiki/


def main():
    scan_file = DATA_DIR / "subcategories_scan.json"
    with open(scan_file, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for parent_id, parent_data in data.items():
        parent_name = parent_data["name"]
        subcats = parent_data["subcategories"]
        parent_total = sum(s["count"] for s in subcats)

        for sub in sorted(subcats, key=lambda x: x["count"], reverse=True):
            cap_status = "OVER_CAP" if sub["count"] > 2000 else "OK"
            rows.append({
                "parent_id": int(parent_id),
                "parent_name": parent_name,
                "parent_total": parent_total,
                "sub_id": sub["id"],
                "sub_name": sub["name"],
                "product_count": sub["count"],
                "listing_cap_status": cap_status,
                "scrape_estimate_hours": round(sub["count"] / (2.7 * 3600), 2),
            })

    # Sort: parent_total desc, then product_count desc
    rows.sort(key=lambda x: (-x["parent_total"], -x["product_count"]))

    # Write CSV
    csv_file = OUT_DIR / "tiki_categories_report.csv"
    fieldnames = [
        "parent_id", "parent_name", "parent_total",
        "sub_id", "sub_name", "product_count",
        "listing_cap_status", "scrape_estimate_hours",
    ]
    with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Print summary
    total_subs = len(rows)
    total_products = sum(r["product_count"] for r in rows)
    over_cap = [r for r in rows if r["listing_cap_status"] == "OVER_CAP"]
    unique_parents = len(data)

    print(f"Exported to {csv_file}")
    print(f"\nSummary:")
    print(f"  Parent categories: {unique_parents}")
    print(f"  Sub-categories: {total_subs}")
    print(f"  Total products: {total_products:,}")
    print(f"  Over 2000 cap: {len(over_cap)} sub-categories")
    for r in over_cap:
        print(f"    - [{r['sub_id']}] {r['sub_name']}: {r['product_count']:,} SP")

    # Print table
    print(f"\n{'Parent':<35} | {'Sub-category':<45} | {'Sub ID':>7} | {'SP':>8} | Cap?")
    print("-" * 115)
    current_parent = None
    for r in rows:
        parent_label = ""
        if r["parent_name"] != current_parent:
            current_parent = r["parent_name"]
            parent_label = f"{r['parent_name']} ({r['parent_total']:,})"
        cap = "!!" if r["listing_cap_status"] == "OVER_CAP" else ""
        print(f"{parent_label:<35} | {r['sub_name']:<45} | {r['sub_id']:>7} | {r['product_count']:>8,} | {cap}")


if __name__ == "__main__":
    main()
