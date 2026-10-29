"""Sinh báo cáo HTML nền sáng từ một file Markdown (dùng cho report_system3 trở đi).

Chạy trong thư mục này:
    uv run python gen_report_html.py report_system3.md report_system3.html

File .md là nguồn duy nhất — sửa .md rồi sinh lại, không sửa tay .html. Các dòng đặc biệt ở đầu .md (lấy ra làm phần
đầu trang, không lặp trong thân bài):
    # <tiêu đề>
    > **Mục đích:** …   /   > **Phạm vi:** …
    **Nhãn:** a · b · c
    **Thẻ giá:** <tên sản phẩm> | <giá bán> | <giá ước> | <chênh lệch> | <chú thích>
Nhãn bằng chứng trong thân bài ([đã đo], [có trong code], [suy luận], [đề xuất]) được tô màu theo loại.
Giao diện cũ (nền tối) vẫn sinh bằng gen_report_system.py.
"""
import html
import re
import sys
from pathlib import Path

import markdown

MD_PATH = Path(sys.argv[1])
HTML_PATH = Path(sys.argv[2])
md_text = MD_PATH.read_text(encoding="utf-8")


def line_value(pattern: str) -> str:
    m = re.search(pattern, md_text, flags=re.MULTILINE)
    return m.group(1).strip() if m else ""


title = line_value(r"^# (.+)$")
purpose = line_value(r"^> \*\*Mục đích:\*\*\s*(.+)$")
scope = line_value(r"^> \*\*Phạm vi:\*\*\s*(.+)$")
labels = [x.strip() for x in line_value(r"^\*\*Nhãn:\*\*\s*(.+)$").split("·") if x.strip()]
tag_parts = [x.strip() for x in line_value(r"^\*\*Thẻ giá:\*\*\s*(.+)$").split("|")]

# Bỏ các dòng đầu trang khỏi phần thân trước khi chuyển Markdown
body_md = md_text
body_md = re.sub(r"^# .+\n", "", body_md, count=1, flags=re.MULTILINE)
body_md = re.sub(r"^> \*\*(Mục đích|Phạm vi):\*\*.*\n", "", body_md, flags=re.MULTILINE)
body_md = re.sub(r"^\*\*(Nhãn|Thẻ giá):\*\*.*\n", "", body_md, flags=re.MULTILINE)

md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "attr_list", "md_in_html"],
                       extension_configs={"toc": {"toc_depth": "2-3"}})
body = md.convert(body_md)

# Nhãn bằng chứng ⇒ chip màu (thông tin: mức chắc chắn của từng ý)
EVIDENCE = {"đã đo": "ev-measured", "đã kiểm": "ev-measured", "có trong code": "ev-code",
            "suy luận": "ev-inferred", "đề xuất": "ev-proposed"}


def chip(m: re.Match) -> str:
    text = m.group(1)
    key = next((k for k in EVIDENCE if text.startswith(k)), None)
    return f'<span class="ev {EVIDENCE[key]}">{text}</span>' if key else m.group(0)


body = re.sub(r"(?:<strong>)?\[((?:đã đo|đã kiểm|có trong code|suy luận|đề xuất)[^\]<]*)\](?:</strong>)?", chip, body)
# Ô "Tự kiểm" có khung riêng
body = re.sub(r"<blockquote>\s*<p><strong>Tự kiểm:</strong>", '<blockquote class="quiz"><p><strong>Tự kiểm</strong>', body)
# Bảng cuộn ngang được trên màn hình hẹp, không làm cả trang cuộn ngang
body = re.sub(r"<table>", '<div class="table-wrap"><table>', body).replace("</table>", "</table></div>")


def toc_html(tokens, level=0) -> str:
    if not tokens:
        return ""
    items = []
    for t in tokens:
        name = html.escape(re.sub(r"<[^>]+>", "", t["name"]))
        items.append(f'<li><a href="#{t["id"]}" data-id="{t["id"]}">{name}</a>{toc_html(t["children"], level + 1)}</li>')
    return f'<ol class="toc-l{level}">' + "".join(items) + "</ol>"


toc = toc_html(md.toc_tokens)

hero_tag = ""
if len(tag_parts) >= 4:
    product, sale, estimate, diff = (html.escape(x) for x in tag_parts[:4])
    note = html.escape(tag_parts[4]) if len(tag_parts) > 4 else ""
    hero_tag = f"""
      <figure class="price-tag" aria-label="Ví dụ một deal: giá bán, giá AI ước lượng và phần chênh lệch">
        <div class="tag-hole" aria-hidden="true"></div>
        <figcaption class="tag-product">{product}</figcaption>
        <div class="tag-row"><span>Giá bán</span><span class="tag-sale">${sale}</span></div>
        <div class="tag-row"><span>AI ước giá trị</span><span class="tag-estimate">${estimate}</span></div>
        <div class="tag-diff"><span>Chênh lệch</span><strong>+${diff}</strong></div>
        <p class="tag-note">{note}</p>
      </figure>"""

chips = "".join(f"<li>{html.escape(x)}</li>" for x in labels)

page = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=JetBrains+Mono:wght@400;600&display=swap&subset=vietnamese" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<style>
  :root {{
    --paper: #F5F7FA;
    --surface: #FFFFFF;
    --ink: #172033;
    --muted: #566176;
    --rule: #DCE1EA;
    --blue: #1D4ED8;
    --blue-soft: #E8EEFD;
    --tag: #FFD43B;
    --red: #B42318;
    --sans: "Be Vietnam Pro", system-ui, sans-serif;
    --serif: "Source Serif 4", Georgia, serif;
    --mono: "JetBrains Mono", ui-monospace, monospace;
    --measure: 72ch;
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-padding-top: 24px; }}
  body {{ margin: 0; background: var(--paper); color: var(--ink); font: 400 17px/1.7 var(--serif);
         -webkit-font-smoothing: antialiased; }}
  a {{ color: var(--blue); text-underline-offset: 3px; }}
  a:focus-visible, button:focus-visible, summary:focus-visible {{ outline: 3px solid var(--blue); outline-offset: 2px; border-radius: 4px; }}

  .layout {{ display: grid; grid-template-columns: 290px minmax(0, 1fr); max-width: 1320px; margin: 0 auto; }}

  /* Mục lục */
  .toc {{ position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 28px 18px 40px 24px;
         border-right: 1px solid var(--rule); font: 400 14px/1.45 var(--sans); }}
  .toc-title {{ font-weight: 700; font-size: 15px; margin: 0 0 4px; }}
  .toc-sub {{ color: var(--muted); font-size: 13px; margin: 0 0 20px; }}
  .toc ol {{ list-style: none; margin: 0; padding: 0; }}
  .toc .toc-l1 {{ margin: 2px 0 8px 12px; }}
  .toc a {{ display: block; padding: 5px 10px; border-radius: 6px; color: var(--muted); text-decoration: none; }}
  .toc .toc-l0 > li > a {{ color: var(--ink); font-weight: 600; margin-top: 6px; }}
  .toc a:hover {{ background: var(--blue-soft); color: var(--ink); }}
  .toc a.active {{ background: var(--blue-soft); color: var(--blue); font-weight: 600; }}
  .toc-mobile {{ display: none; }}

  main {{ padding: 48px 56px 96px; min-width: 0; }}

  /* Phần đầu trang */
  .hero {{ display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 48px; align-items: center;
          padding-bottom: 40px; margin-bottom: 40px; border-bottom: 1px solid var(--rule); }}
  .hero h1 {{ font: 800 clamp(30px, 3.6vw, 44px)/1.15 var(--sans); letter-spacing: -0.02em; margin: 0 0 20px; }}
  .hero .lede {{ font-size: 18px; margin: 0 0 10px; max-width: 62ch; }}
  .hero .lede strong {{ font-family: var(--sans); font-weight: 600; }}
  .hero .scope {{ color: var(--muted); font-size: 16px; margin: 0 0 20px; max-width: 62ch; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; margin: 0; }}
  .chips li {{ font: 500 13px/1 var(--sans); padding: 7px 11px; border: 1px solid var(--rule); border-radius: 999px;
              background: var(--surface); color: var(--muted); }}

  /* Thẻ giá — điểm nhấn duy nhất của trang */
  .price-tag {{ position: relative; margin: 0; background: var(--tag); color: var(--ink); padding: 34px 24px 20px;
               border-radius: 6px 22px 6px 6px; box-shadow: 0 14px 30px -18px rgba(23, 32, 51, 0.55);
               transform: rotate(-2deg); font-family: var(--sans); }}
  .tag-hole {{ position: absolute; top: 14px; right: 18px; width: 14px; height: 14px; border-radius: 50%;
              background: var(--paper); box-shadow: inset 0 1px 2px rgba(0,0,0,.25); }}
  .tag-product {{ font-weight: 600; font-size: 15px; line-height: 1.35; margin-bottom: 16px; padding-right: 20px; }}
  .tag-row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; font-size: 14px; margin: 6px 0; }}
  .tag-sale {{ font-weight: 700; font-size: 20px; text-decoration: line-through; text-decoration-color: var(--red);
              text-decoration-thickness: 2px; }}
  .tag-estimate {{ font-weight: 800; font-size: 26px; }}
  .tag-diff {{ display: flex; justify-content: space-between; align-items: baseline; margin-top: 14px; padding-top: 12px;
              border-top: 2px dashed rgba(23, 32, 51, 0.35); font-size: 14px; }}
  .tag-diff strong {{ font-size: 30px; font-weight: 800; color: var(--red); letter-spacing: -0.01em; }}
  .tag-note {{ margin: 12px 0 0; font-size: 12.5px; line-height: 1.4; color: #3D3A2A; }}

  /* Thân bài */
  .content > * {{ max-width: var(--measure); }}
  .content > .table-wrap, .content > pre {{ max-width: 100%; }}
  .content h2 {{ font: 700 28px/1.25 var(--sans); letter-spacing: -0.015em; margin: 72px 0 18px; padding-top: 8px; }}
  .content h2:first-child {{ margin-top: 0; }}
  .content h3 {{ font: 600 20px/1.35 var(--sans); margin: 40px 0 12px; }}
  .content p {{ margin: 0 0 16px; }}
  .content strong {{ font-weight: 600; }}
  .content ul, .content ol {{ padding-left: 1.4em; margin: 0 0 18px; }}
  .content li {{ margin-bottom: 6px; }}
  .content li::marker {{ color: var(--blue); }}
  .content hr {{ border: 0; height: 1px; background: var(--rule); margin: 56px 0; max-width: 100%; }}
  .content code {{ font: 400 0.84em/1.4 var(--mono); background: #EDF0F5; padding: 2px 6px; border-radius: 4px; }}
  /* đường dẫn dài trong code giữa câu được ngắt dòng, không đẩy trang rộng ra trên điện thoại */
  .content :not(pre) > code {{ overflow-wrap: anywhere; }}
  .content pre {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; padding: 18px 20px;
                 overflow-x: auto; margin: 0 0 22px; }}
  .content pre code {{ background: none; padding: 0; font-size: 13.5px; line-height: 1.6; }}
  .hljs {{ background: transparent; padding: 0; }}

  .table-wrap {{ overflow-x: auto; margin: 0 0 24px; border: 1px solid var(--rule); border-radius: 8px; background: var(--surface); }}
  table {{ border-collapse: collapse; width: 100%; font: 400 14.5px/1.5 var(--sans); }}
  th {{ text-align: left; font-weight: 600; background: #F0F3F8; color: var(--ink); padding: 11px 14px; border-bottom: 1px solid var(--rule); }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #EBEEF3; vertical-align: top; }}
  tr:last-child td {{ border-bottom: 0; }}
  td strong {{ font-weight: 650; }}

  blockquote {{ margin: 0 0 20px; padding: 14px 18px; border-left: 3px solid var(--rule); color: var(--muted); }}
  blockquote p:last-child {{ margin-bottom: 0; }}
  blockquote.quiz {{ background: var(--blue-soft); border-left: 4px solid var(--blue); border-radius: 0 8px 8px 0; color: var(--ink);
                    font-style: italic; margin-top: 28px; }}
  blockquote.quiz strong {{ font: 700 13px/1 var(--sans); font-style: normal; color: var(--blue); display: block; margin-bottom: 8px; }}

  .ev {{ display: inline-block; font: 600 12px/1.6 var(--sans); padding: 0 7px; border-radius: 4px; white-space: nowrap; vertical-align: 1px; }}
  .ev-measured {{ background: #E3F3E8; color: #17603A; }}
  .ev-code {{ background: #ECEEF2; color: #3F4859; }}
  .ev-inferred {{ background: #FFF1D1; color: #7A4E00; }}
  .ev-proposed {{ background: #E8EEFD; color: #1D4ED8; }}

  .progress {{ position: fixed; top: 0; left: 0; height: 3px; width: 0; background: var(--blue); z-index: 10; }}

  @media (max-width: 1080px) {{
    .layout {{ grid-template-columns: minmax(0, 1fr); }}
    .toc {{ display: none; }}
    .toc-mobile {{ display: block; margin: 0 0 32px; border: 1px solid var(--rule); border-radius: 8px; background: var(--surface);
                  font: 400 15px/1.5 var(--sans); }}
    .toc-mobile summary {{ cursor: pointer; padding: 12px 16px; font-weight: 600; }}
    .toc-mobile ol {{ list-style: none; padding: 0 16px 12px; margin: 0; }}
    .toc-mobile .toc-l1 {{ padding: 0 0 4px 14px; }}
    .toc-mobile a {{ display: block; padding: 4px 0; text-decoration: none; }}
    main {{ padding: 32px 16px 72px; }}
    .hero {{ grid-template-columns: minmax(0, 1fr); gap: 32px; }}
    .price-tag {{ max-width: 320px; }}
  }}
  @media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior: auto; }} .price-tag {{ transform: none; }} }}
  @media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior: smooth; }} }}
  @media print {{
    body {{ background: #fff; font-size: 11.5pt; }}
    .toc, .toc-mobile, .progress {{ display: none; }}
    .layout {{ display: block; }}
    main {{ padding: 0; }}
    .price-tag {{ transform: none; box-shadow: none; border: 1px solid #999; }}
    .content h2 {{ break-before: page; margin-top: 0; }}
    .table-wrap, pre, blockquote {{ break-inside: avoid; }}
    a {{ color: inherit; text-decoration: none; }}
  }}
</style>
</head>
<body>
<div class="progress" aria-hidden="true"></div>
<div class="layout">
  <nav class="toc" aria-label="Mục lục">
    <p class="toc-title">The Price Is Right</p>
    <p class="toc-sub">Báo cáo hệ thống — DACN3</p>
    {toc}
  </nav>
  <main>
    <header class="hero">
      <div>
        <h1>{html.escape(title)}</h1>
        <p class="lede"><strong>Mục đích.</strong> {html.escape(purpose)}</p>
        <p class="scope"><strong>Phạm vi.</strong> {html.escape(scope)}</p>
        <ul class="chips" aria-label="Thông tin báo cáo">{chips}</ul>
      </div>{hero_tag}
    </header>
    <details class="toc-mobile"><summary>Mục lục</summary>{toc}</details>
    <article class="content">
{body}
    </article>
  </main>
</div>
<script>
  hljs.highlightAll();
  // Tô mục lục theo phần đang đọc + thanh tiến độ đọc (phản hồi thao tác cuộn của người đọc)
  const links = [...document.querySelectorAll('.toc a[data-id]')];
  const byId = Object.fromEntries(links.map(a => [a.dataset.id, a]));
  const heads = [...document.querySelectorAll('.content h2[id], .content h3[id]')];
  const bar = document.querySelector('.progress');
  function onScroll() {{
    let current = heads[0];
    for (const h of heads) {{ if (h.getBoundingClientRect().top < 120) current = h; else break; }}
    links.forEach(a => a.classList.remove('active'));
    if (current && byId[current.id]) {{
      byId[current.id].classList.add('active');
      byId[current.id].scrollIntoView({{ block: 'nearest' }});
    }}
    const max = document.documentElement.scrollHeight - innerHeight;
    bar.style.width = (max > 0 ? scrollY / max * 100 : 0) + '%';
  }}
  addEventListener('scroll', onScroll, {{ passive: true }});
  onScroll();
</script>
</body>
</html>
"""

HTML_PATH.write_text(page, encoding="utf-8")
print(f"Generated: {HTML_PATH} ({HTML_PATH.stat().st_size / 1024:.1f} KB)")
