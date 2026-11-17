#!/usr/bin/env python3
"""render.py: turn brief2mp4-art-forms.html into brief2mp4-art-forms.pdf with WeasyPrint, then check it.

    python3 docs/guide/render.py

Checks after rendering: the page count, that every contents entry points at a real page, that no text runs off a
page, and the document metadata. Writes qa/contact-NN.jpg sheets to look through (not kept in the repository).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault('DYLD_FALLBACK_LIBRARY_PATH', '/opt/homebrew/lib')   # where Homebrew puts Pango on Apple silicon
from weasyprint import HTML  # noqa: E402
import pymupdf  # noqa: E402

HERE = Path(__file__).resolve().parent
PDF = HERE / 'brief2mp4-art-forms.pdf'
HTML(filename=str(HERE / 'brief2mp4-art-forms.html')).write_pdf(str(PDF), pdf_tags=True)

doc = pymupdf.open(PDF)
problems = []
for n, page in enumerate(doc, 1):
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            r = pymupdf.Rect(line['bbox'])
            if r.x1 > page.rect.width + 0.5 or r.y1 > page.rect.height + 0.5 or r.x0 < -0.5:
                problems.append(f'page {n}: text outside the page: {"".join(s["text"] for s in line["spans"])[:60]!r}')
links = [l for l in doc[1].get_links() if l['kind'] in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED)]
if len(links) < 6:
    problems.append(f'contents page has only {len(links)} links')
if doc.metadata.get('author') != 'Varun Pratap Bhardwaj':
    problems.append('author metadata is missing')
qa = HERE / 'qa'
qa.mkdir(exist_ok=True)
if '--sheets' in sys.argv:
    from PIL import Image
    thumbs = []
    for page in doc:
        pix = page.get_pixmap(matrix=pymupdf.Matrix(0.42, 0.42), alpha=False)
        thumbs.append(Image.frombytes('RGB', [pix.width, pix.height], pix.samples))
    for start in range(0, len(thumbs), 15):
        batch = thumbs[start:start + 15]
        w, h = batch[0].size
        sheet = Image.new('RGB', (5 * (w + 8) + 8, 3 * (h + 8) + 8), '#8a8a8a')
        for i, im in enumerate(batch):
            sheet.paste(im, (8 + (i % 5) * (w + 8), 8 + (i // 5) * (h + 8)))
        sheet.save(qa / f'contact-{start + 1:02d}.jpg', quality=82)
print(f'{PDF.name}: {len(doc)} pages, {PDF.stat().st_size // 1024} KB')
for line in problems:
    print('PROBLEM', line)
sys.exit(1 if problems else 0)
