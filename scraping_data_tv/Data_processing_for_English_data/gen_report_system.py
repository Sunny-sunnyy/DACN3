"""Generate report_system.html from report_system.md with gradient glassmorphism theme."""
import re
from pathlib import Path
import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension

MD_PATH = Path(__file__).parent / "report_system.md"
HTML_PATH = Path(__file__).parent / "report_system.html"

md_text = MD_PATH.read_text(encoding="utf-8")

md = markdown.Markdown(
    extensions=[
        FencedCodeExtension(),
        TableExtension(),
        TocExtension(toc_depth="2-3", title=""),
        "md_in_html",
        "attr_list",
    ]
)

body_html = md.convert(md_text)
toc_html = md.toc

# Parse toc items to build sidebar nav
toc_items = re.findall(r'<li><a href="(#[^"]+)">([^<]+)</a>', toc_html)

MAIN_PREFIXES = ("#phan-", "#hanh-trinh", "#chi-tiet", "#tong-ket")

nav_links = ""
for href, title in toc_items:
    is_main = any(href.startswith(p) for p in MAIN_PREFIXES)
    css = "nav-main" if is_main else "nav-sub"
    nav_links += f'<a href="{href}" class="{css}" data-target="{href[1:]}">{title}</a>\n'

TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Báo cáo: AI Price Intelligence System — The Price Is Right</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/bash.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/json.min.js"></script>
<style>
  :root {
    --bg-primary: #0d0b1e;
    --bg-secondary: #13102a;
    --bg-card: rgba(255,255,255,0.04);
    --border-glass: rgba(168,85,247,0.18);
    --purple: #a855f7;
    --cyan: #22d3ee;
    --pink: #ec4899;
    --green: #10b981;
    --yellow: #f59e0b;
    --text-primary: #e2e8f0;
    --text-muted: #94a3b8;
    --sidebar-width: 280px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  html { scroll-behavior: smooth; }

  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* ── Progress Bar ── */
  #progress-bar {
    position: fixed;
    top: 0; left: 0;
    height: 3px;
    width: 0%;
    background: linear-gradient(90deg, var(--purple), var(--cyan), var(--pink));
    z-index: 1000;
    transition: width 0.1s ease;
    box-shadow: 0 0 8px var(--purple);
  }

  /* ── Sidebar ── */
  #sidebar {
    position: fixed;
    top: 0; left: 0;
    width: var(--sidebar-width);
    height: 100vh;
    overflow-y: auto;
    background: rgba(13,11,30,0.95);
    border-right: 1px solid var(--border-glass);
    backdrop-filter: blur(16px);
    z-index: 100;
    padding: 24px 0 40px;
    scrollbar-width: thin;
    scrollbar-color: var(--purple) transparent;
  }

  #sidebar::-webkit-scrollbar { width: 4px; }
  #sidebar::-webkit-scrollbar-thumb { background: var(--purple); border-radius: 2px; }

  .sidebar-header {
    padding: 0 20px 20px;
    border-bottom: 1px solid var(--border-glass);
    margin-bottom: 16px;
  }

  .sidebar-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    background: linear-gradient(135deg, var(--purple), var(--cyan));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .sidebar-subtitle {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  #sidebar a {
    display: block;
    text-decoration: none;
    color: var(--text-muted);
    font-size: 13px;
    line-height: 1.4;
    padding: 6px 20px;
    border-left: 2px solid transparent;
    transition: all 0.2s ease;
    word-break: break-word;
  }

  #sidebar a.nav-sub {
    padding-left: 32px;
    font-size: 12px;
  }

  #sidebar a:hover {
    color: var(--cyan);
    border-left-color: var(--cyan);
    background: rgba(34,211,238,0.05);
  }

  #sidebar a.active {
    color: var(--purple);
    border-left-color: var(--purple);
    background: rgba(168,85,247,0.08);
    font-weight: 600;
  }

  /* ── Main Content ── */
  #main {
    margin-left: var(--sidebar-width);
    padding: 48px 56px 80px;
    max-width: calc(var(--sidebar-width) + 900px);
  }

  /* ── Hero Header ── */
  .hero {
    background: linear-gradient(135deg, rgba(168,85,247,0.12) 0%, rgba(34,211,238,0.08) 50%, rgba(236,72,153,0.06) 100%);
    border: 1px solid var(--border-glass);
    border-radius: 16px;
    padding: 40px 48px;
    margin-bottom: 48px;
    position: relative;
    overflow: hidden;
  }

  .hero::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(168,85,247,0.08) 0%, transparent 70%);
    pointer-events: none;
  }

  .hero h1 {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #fff 0%, var(--purple) 50%, var(--cyan) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.25;
    margin-bottom: 20px;
  }

  .hero blockquote {
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
  }

  .hero blockquote p {
    color: var(--text-muted);
    font-size: 14px;
    line-height: 1.7;
    margin-bottom: 6px;
  }

  .hero blockquote strong {
    color: var(--cyan);
  }

  .meta-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 20px;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
  }

  .badge-purple { background: rgba(168,85,247,0.15); color: var(--purple); border: 1px solid rgba(168,85,247,0.3); }
  .badge-cyan   { background: rgba(34,211,238,0.12); color: var(--cyan);   border: 1px solid rgba(34,211,238,0.25); }
  .badge-pink   { background: rgba(236,72,153,0.12); color: var(--pink);   border: 1px solid rgba(236,72,153,0.25); }
  .badge-green  { background: rgba(16,185,129,0.12); color: var(--green);  border: 1px solid rgba(16,185,129,0.25); }

  /* ── Section headings ── */
  #content h2 {
    font-size: 1.5rem;
    font-weight: 700;
    color: #fff;
    margin: 56px 0 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-glass);
    position: relative;
  }

  #content h2::before {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    width: 60px;
    height: 2px;
    background: linear-gradient(90deg, var(--purple), var(--cyan));
  }

  #content h3 {
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--cyan);
    margin: 32px 0 14px;
  }

  #content h4 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--purple);
    margin: 24px 0 10px;
  }

  /* ── Paragraphs ── */
  #content p {
    color: #cbd5e1;
    font-size: 15px;
    line-height: 1.8;
    margin-bottom: 14px;
  }

  #content strong {
    color: #f1f5f9;
    font-weight: 600;
  }

  #content em { color: var(--cyan); font-style: italic; }

  /* ── Code blocks ── */
  #content pre {
    background: #0d1117 !important;
    border: 1px solid rgba(168,85,247,0.2);
    border-radius: 10px;
    margin: 20px 0;
    overflow-x: auto;
    position: relative;
  }

  #content pre code {
    font-family: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.65;
    padding: 20px 20px !important;
    display: block;
  }

  .copy-btn {
    position: absolute;
    top: 10px;
    right: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
    border-radius: 5px;
    border: 1px solid rgba(168,85,247,0.35);
    background: rgba(168,85,247,0.12);
    color: var(--purple);
    cursor: pointer;
    transition: all 0.2s;
    z-index: 5;
  }

  .copy-btn:hover { background: rgba(168,85,247,0.25); color: #fff; }
  .copy-btn.copied { color: var(--green); border-color: var(--green); background: rgba(16,185,129,0.1); }

  /* ── Inline code ── */
  #content code {
    background: rgba(168,85,247,0.12);
    color: var(--cyan);
    border: 1px solid rgba(168,85,247,0.2);
    border-radius: 4px;
    padding: 1px 6px;
    font-family: 'Fira Code', monospace;
    font-size: 13px;
  }

  #content pre code {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    font-size: 13px;
  }

  /* ── Tables ── */
  #content table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 14px;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--border-glass);
  }

  #content thead tr {
    background: linear-gradient(135deg, rgba(168,85,247,0.2), rgba(34,211,238,0.12));
  }

  #content th {
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    color: #fff;
    font-size: 13px;
    letter-spacing: 0.02em;
    border-bottom: 1px solid var(--border-glass);
  }

  #content td {
    padding: 10px 16px;
    color: #cbd5e1;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    vertical-align: top;
  }

  #content tbody tr:hover td {
    background: rgba(168,85,247,0.05);
  }

  #content tbody tr:last-child td { border-bottom: none; }

  /* ── Blockquote ── */
  #content blockquote {
    border-left: 3px solid var(--purple);
    background: rgba(168,85,247,0.06);
    border-radius: 0 8px 8px 0;
    padding: 16px 20px;
    margin: 20px 0;
  }

  #content blockquote p { color: #c4b5fd; margin: 0; font-style: italic; }
  #content blockquote strong { color: var(--cyan); }

  /* ── Lists ── */
  #content ul, #content ol {
    padding-left: 24px;
    margin: 12px 0;
  }

  #content li {
    color: #cbd5e1;
    font-size: 15px;
    line-height: 1.75;
    margin-bottom: 4px;
  }

  #content li::marker { color: var(--purple); }

  /* ── HR ── */
  #content hr {
    border: none;
    border-top: 1px solid var(--border-glass);
    margin: 40px 0;
  }

  /* ── ASCII diagrams ── */
  .ascii-diagram {
    background: rgba(13,17,23,0.8);
    border: 1px solid var(--border-glass);
    border-radius: 10px;
    padding: 20px;
    overflow-x: auto;
    font-family: 'Fira Code', 'Cascadia Mono', monospace;
    font-size: 12.5px;
    line-height: 1.5;
    color: #7dd3fc;
    margin: 20px 0;
  }

  /* ── Back to top ── */
  #back-to-top {
    position: fixed;
    bottom: 32px;
    right: 32px;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--purple), var(--cyan));
    color: #fff;
    border: none;
    cursor: pointer;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 20px rgba(168,85,247,0.4);
    opacity: 0;
    transform: translateY(20px);
    transition: all 0.3s ease;
    z-index: 200;
  }

  #back-to-top.visible { opacity: 1; transform: translateY(0); }
  #back-to-top:hover { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(168,85,247,0.6); }

  /* ── Day cards ── */
  .day-card {
    background: var(--bg-card);
    border: 1px solid var(--border-glass);
    border-radius: 12px;
    padding: 24px 28px;
    margin: 16px 0;
    backdrop-filter: blur(8px);
    transition: border-color 0.2s ease;
  }
  .day-card:hover { border-color: rgba(168,85,247,0.4); }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 8px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg-primary); }
  ::-webkit-scrollbar-thumb { background: rgba(168,85,247,0.35); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--purple); }

  /* ── Responsive ── */
  @media (max-width: 900px) {
    #sidebar { display: none; }
    #main { margin-left: 0; padding: 24px 20px 60px; }
  }
</style>
</head>
<body>

<div id="progress-bar"></div>

<!-- Sidebar -->
<nav id="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-title">The Price Is Right</div>
    <div class="sidebar-subtitle">AI Price Intelligence — Week 8</div>
  </div>
  {NAV_LINKS}
</nav>

<!-- Main content -->
<main id="main">
  <!-- Hero header -->
  <div class="hero">
    <h1>Báo cáo: Xây dựng Hệ thống AI Price Intelligence — "The Price Is Right"</h1>
    <blockquote>
      <p><strong>Mục đích:</strong> Tài liệu chi tiết về quá trình xây dựng toàn bộ hệ thống production, từ việc triển khai mô hình đã fine-tune lên cloud cho đến hai ứng dụng hoàn chỉnh.</p>
      <p><strong>Phạm vi:</strong> Week 8 (Day 1–5) — từ Specialist Agent đầu tiên đến Multi-Source Deal Finder hoàn chỉnh</p>
    </blockquote>
    <div class="meta-badges">
      <span class="badge badge-purple">📅 2026-05-11</span>
      <span class="badge badge-cyan">📂 segment4/</span>
      <span class="badge badge-pink">🤖 price_is_right.py</span>
      <span class="badge badge-green">🔍 search_key.py</span>
    </div>
  </div>

  <div id="content">
    {BODY_HTML}
  </div>
</main>

<!-- Back to top -->
<button id="back-to-top" title="Back to top">↑</button>

<script>
// ── Highlight.js ──
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('pre code').forEach(block => {
    // Detect language
    const text = block.textContent;
    if (!block.className) {
      if (text.includes('def ') || text.includes('import ') || text.includes('class ')) {
        block.classList.add('language-python');
      } else if (text.match(/^(cd |uv run|modal |git )/m)) {
        block.classList.add('language-bash');
      } else if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
        block.classList.add('language-json');
      } else if (text.includes('│') || text.includes('├') || text.includes('└') || text.includes('┌') || text.includes('▼')) {
        // ASCII diagram — skip highlight, apply special styling
        block.closest('pre').classList.add('ascii-pre');
        return;
      }
    }
    hljs.highlightElement(block);
  });

  // Style ASCII diagrams
  document.querySelectorAll('pre.ascii-pre').forEach(pre => {
    pre.style.background = 'rgba(13,17,23,0.8)';
    pre.style.borderColor = 'rgba(34,211,238,0.2)';
    pre.querySelector('code').style.color = '#7dd3fc';
    pre.querySelector('code').style.fontFamily = "'Fira Code', monospace";
    pre.querySelector('code').style.fontSize = '12.5px';
  });

  // ── Copy buttons ──
  document.querySelectorAll('pre').forEach(pre => {
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = 'Copy';
    btn.addEventListener('click', () => {
      const code = pre.querySelector('code');
      navigator.clipboard.writeText(code.innerText).then(() => {
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1800);
      });
    });
    pre.style.position = 'relative';
    pre.appendChild(btn);
  });

  // ── Active nav on scroll ──
  const navLinks = document.querySelectorAll('#sidebar a[data-target]');
  const headings = document.querySelectorAll('#content h2, #content h3');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        navLinks.forEach(a => {
          a.classList.toggle('active', a.dataset.target === id);
        });
      }
    });
  }, { rootMargin: '-10% 0px -80% 0px', threshold: 0 });

  headings.forEach(h => { if (h.id) observer.observe(h); });

  // ── Scroll progress bar ──
  const progressBar = document.getElementById('progress-bar');
  const backTop = document.getElementById('back-to-top');

  window.addEventListener('scroll', () => {
    const scrollTop = window.scrollY;
    const docHeight = document.body.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    progressBar.style.width = progress + '%';
    backTop.classList.toggle('visible', scrollTop > 400);
  });

  backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  // ── Smooth scroll for nav links ──
  document.querySelectorAll('#sidebar a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const target = document.getElementById(a.dataset.target);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
});
</script>
</body>
</html>
"""

final_html = TEMPLATE.replace("{NAV_LINKS}", nav_links).replace("{BODY_HTML}", body_html)

# Remove the duplicate H1 from converted body (we have it in hero)
final_html = re.sub(
    r'<h1[^>]*>Báo cáo: Xây dựng Hệ thống AI Price Intelligence.*?</h1>\s*',
    '',
    final_html,
    count=1,
    flags=re.DOTALL
)

# Remove the opening blockquote that was in the .md header (already in hero)
final_html = re.sub(
    r'<blockquote>\s*<p><strong>Mục đích:</strong>.*?</blockquote>\s*',
    '',
    final_html,
    count=1,
    flags=re.DOTALL
)

HTML_PATH.write_text(final_html, encoding="utf-8")
print(f"Generated: {HTML_PATH}")
print(f"Size: {HTML_PATH.stat().st_size / 1024:.1f} KB")
