#!/usr/bin/env python3
"""Generate a professional PDF from the technical specification markdown."""

import markdown
from weasyprint import HTML
from pathlib import Path

MD_FILE = Path(__file__).parent / "technical_specification.md"
PDF_FILE = Path(__file__).parent / "AI_Sale_Technical_Specification.pdf"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

@page {
    size: A4;
    margin: 25mm 20mm 25mm 20mm;
    @bottom-center {
        content: "Страница " counter(page) " из " counter(pages);
        font-size: 9px;
        color: #999;
        font-family: 'Inter', sans-serif;
    }
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #2d2d2d;
}

h1 {
    font-size: 22pt;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 4px;
    border-bottom: 3px solid #E63329;
    padding-bottom: 10px;
}

h2 {
    font-size: 15pt;
    font-weight: 700;
    color: #E63329;
    margin-top: 28px;
    margin-bottom: 12px;
    padding-bottom: 6px;
    border-bottom: 1px solid #eee;
    page-break-after: avoid;
}

h3 {
    font-size: 12pt;
    font-weight: 600;
    color: #3D3D3D;
    margin-top: 18px;
    margin-bottom: 8px;
    page-break-after: avoid;
}

p {
    margin-bottom: 8px;
    text-align: justify;
}

strong {
    font-weight: 600;
    color: #1a1a1a;
}

hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 20px 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 16px 0;
    font-size: 10pt;
    page-break-inside: avoid;
}

thead tr {
    background-color: #3D3D3D;
    color: white;
}

th {
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
    font-size: 9.5pt;
}

td {
    padding: 7px 10px;
    border-bottom: 1px solid #e5e5e5;
    vertical-align: top;
}

tbody tr:nth-child(even) {
    background-color: #f8f8f8;
}

tbody tr:hover {
    background-color: #f0f0f0;
}

ul, ol {
    margin: 8px 0;
    padding-left: 24px;
}

li {
    margin-bottom: 4px;
}

code {
    font-family: 'Menlo', 'Consolas', monospace;
    background-color: #f4f4f4;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 9.5pt;
}

pre {
    background-color: #f4f4f4;
    padding: 12px;
    border-radius: 6px;
    font-size: 9pt;
    overflow-x: auto;
    border-left: 3px solid #E63329;
}

blockquote {
    border-left: 3px solid #E63329;
    padding-left: 16px;
    margin-left: 0;
    color: #555;
    font-style: italic;
}

/* Checkbox styling */
li input[type="checkbox"] {
    margin-right: 6px;
}

em {
    color: #777;
}
"""

def main():
    md_text = MD_FILE.read_text(encoding="utf-8")

    md_text = md_text.replace("- [ ]", "- ☐")

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "smarty"],
    )

    full_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML(string=full_html).write_pdf(str(PDF_FILE))
    print(f"PDF saved: {PDF_FILE}")
    print(f"Size: {PDF_FILE.stat().st_size / 1024:.0f} KB")

if __name__ == "__main__":
    main()
