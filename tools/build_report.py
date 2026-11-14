"""Build the report PDF from its Markdown source.

    python tools/build_report.py

Markdown (06_rapport/sources/report.md) → HTML (pandoc) → PDF (headless Chromium, via Playwright).
"""

import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "06_rapport" / "sources"
HTML = SOURCES / "report.html"
PDF = ROOT / "06_rapport" / "final_report.pdf"
CHROMIUM = next((str(c) for c in sorted(Path("/opt/pw-browsers").glob("chromium*/chrome-linux*/chrome"))), None)

subprocess.run(["pandoc", str(SOURCES / "report.md"), "-f", "markdown+raw_html", "-t", "html5", "-s",
                "--metadata", "title=VIGIE — Integrated Project report (Group BI 5)", "--css", "report.css",
                "-o", str(HTML)], check=True, cwd=SOURCES)
# pandoc adds a visible title block; the cover page plays that role.
html = HTML.read_text(encoding="utf-8")
html = html.replace('<header id="title-block-header">', '<header id="title-block-header" style="display:none">')
HTML.write_text(html, encoding="utf-8")

footer = ('<div style="width:100%;font-size:7.5pt;color:#6B7280;padding:0 17mm;display:flex;justify-content:space-between;'
          'font-family:DejaVu Sans,sans-serif"><span>VIGIE · Group BI 5 · Integrated Project 2026</span>'
          '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()
    page = browser.new_page()
    page.goto(HTML.as_uri(), wait_until="networkidle")
    page.pdf(path=str(PDF), format="A4", print_background=True, display_header_footer=True,
             header_template="<span></span>", footer_template=footer,
             margin={"top": "18mm", "bottom": "20mm", "left": "17mm", "right": "17mm"})
    browser.close()
print("written:", PDF.relative_to(ROOT))
