"""Vẽ 04_thoi_gian_truoc_sau.svg: thời gian một lượt tìm theo bước, trước / sau đợt tối ưu (số đo 29/10/2026).

Chạy: uv run python ve_bieu_do_thoi_gian.py   (trong thư mục này)
Số lấy từ các lượt profile_pipeline.py (mốc sáng 29/10 và lượt cuối sau khi sửa) — bảng 4.2 của report_system3.md.
Màu 3 bước: bảng màu mặc định của skill dataviz, đã chạy validate_palette.js (light): đạt; ngọc lam tương phản 2,74:1 với
nền trắng ⇒ có nhãn tổng ở cuối thanh, tooltip từng đoạn và bảng số ngay dưới hình.
"""
from pathlib import Path

RUNS = [  # (từ khoá, nhãn, [bước 1, bước 3, bước 4], tổng đo được)
    ("wireless headphones", "trước", [32.8, 3.4, 33.4], 69.5),
    ("wireless headphones", "sau", [12.2, 4.9, 4.1], 21.3),
    ("air fryer", "trước", [63.7, 4.0, 39.0], 106.7),
    ("air fryer", "sau", [22.1, 4.4, 3.7], 30.2),
]
STEPS = [("Bước 1 — cào", "#2a78d6"), ("Bước 3 — chọn deal", "#eb6834"), ("Bước 4 — ước giá", "#1baf7a")]

W, X0, X1 = 880, 236, 820          # vùng vẽ: 0 s ở X0, MAX_S ở X1
MAX_S = 110
BAR_H, GAP = 24, 2                  # thanh mảnh; khe 2px (màu nền) giữa các đoạn
ROW_Y = [92, 128, 196, 232]
s2x = lambda s: X0 + s / MAX_S * (X1 - X0)
fmt = lambda v: f"{v:.1f}".replace(".", ",")

out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 312" role="img" '
       'aria-label="Thời gian một lượt tìm theo bước: wireless headphones từ 69,5 giây còn 21,3 giây; '
       'air fryer từ 106,7 giây còn 30,2 giây; phần giảm nhiều nhất là bước cào và bước ước giá" '
       'font-family="Be Vietnam Pro, system-ui, sans-serif" fill="#172033">']

# Chú giải (luôn có khi ≥ 2 nhóm màu)
lx = X0
for name, color in STEPS:
    out.append(f'<rect x="{lx}" y="18" width="12" height="12" rx="3" fill="{color}"/>')
    out.append(f'<text x="{lx + 18}" y="28" font-size="12.5" fill="#3A4357">{name}</text>')
    lx += 18 + len(name) * 7.4 + 26

# Lưới dọc nhạt + nhãn trục
for s in range(0, MAX_S + 1, 20):
    x = s2x(s)
    out.append(f'<line x1="{x:.1f}" y1="70" x2="{x:.1f}" y2="266" stroke="#EBEEF3"/>')
    out.append(f'<text x="{x:.1f}" y="286" font-size="11.5" fill="#566176" text-anchor="middle">{s} s</text>')

# Tên từ khoá (một lần mỗi nhóm) + nhãn trước / sau
out.append(f'<text x="20" y="{ROW_Y[0] - 14}" font-size="13" font-weight="600">wireless headphones</text>')
out.append(f'<text x="20" y="{ROW_Y[2] - 14}" font-size="13" font-weight="600">air fryer</text>')

for (kw, label, parts, total), y in zip(RUNS, ROW_Y):
    out.append(f'<text x="{X0 - 12}" y="{y + 16}" font-size="12.5" fill="#566176" text-anchor="end">'
               f'{"trước tối ưu" if label == "trước" else "sau tối ưu"}</text>')
    x = X0
    for i, ((name, color), v) in enumerate(zip(STEPS, parts)):
        w = s2x(v) - X0
        last = i == len(parts) - 1
        inner = w - (GAP if i > 0 else 0)
        sx = x + (GAP if i > 0 else 0)
        tip = f"<title>{kw}, {label} tối ưu — {name}: {fmt(v)} s</title>"
        if last:  # đầu dữ liệu bo 4px, gốc vuông (bám đường 0)
            r = min(4, inner / 2)
            out.append(f'<path d="M{sx:.1f},{y} h{inner - r:.1f} a{r},{r} 0 0 1 {r},{r} v{BAR_H - 2 * r} '
                       f'a{r},{r} 0 0 1 -{r},{r} h-{inner - r:.1f} z" fill="{color}">{tip}</path>')
        else:
            out.append(f'<rect x="{sx:.1f}" y="{y}" width="{inner:.1f}" height="{BAR_H}" fill="{color}">{tip}</rect>')
        x += w
    out.append(f'<text x="{x + 8:.1f}" y="{y + 17}" font-size="13" font-weight="700">{fmt(total)} s</text>')

out.append("</svg>")
Path(__file__).with_name("04_thoi_gian_truoc_sau.svg").write_text("\n".join(out) + "\n", encoding="utf-8")
print("ok")
