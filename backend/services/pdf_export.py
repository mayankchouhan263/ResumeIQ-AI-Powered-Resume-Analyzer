"""HTML -> PDF export.

Two engines, tried in this order (set PDF_ENGINE=playwright|weasyprint to force one):

  1. WeasyPrint             - light on memory (fits a 512 MB server). Needs Pango on Linux
                              (apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0)
                              and the MSYS2/GTK libraries on Windows.
  2. Playwright + Chromium  - best fidelity, but a headless browser needs several hundred MB of
                              RAM, so it is only a fallback (and is not installed on the server):
                                  pip install playwright
                                  playwright install chromium
"""
import asyncio
import io
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:                                    # PyPDF2 is already in requirements.txt
    from PyPDF2 import PdfReader, PdfWriter

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_INSTALLED = True
    WEASYPRINT_ERROR = ''
except Exception as _exc:      # ImportError (not installed) *and* OSError (GTK/Pango DLLs missing on Windows)
    WEASYPRINT_INSTALLED = False
    WEASYPRINT_ERROR = str(_exc)

logger = logging.getLogger('ats_resume_scorer')

PDF_ENGINE = os.getenv('PDF_ENGINE', 'auto').strip().lower()


# -- merging ------------------------------------------------------------------
def _merge_pdfs(pdf_parts: List[bytes]) -> bytes:
    if len(pdf_parts) == 1:
        return pdf_parts[0]
    writer = PdfWriter()
    for part in pdf_parts:
        for page in PdfReader(io.BytesIO(part)).pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# -- engine 1: Playwright / Chromium -----------------------------------------
def _playwright_render_sync(html_docs: List[str]) -> List[bytes]:
    from playwright.sync_api import sync_playwright

    parts: List[bytes] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for html in html_docs:
                page = browser.new_page()
                page.set_content(html, wait_until='load')
                parts.append(page.pdf(
                    format='A4',
                    print_background=True,          # keep the coloured score bars / badges
                    margin={'top': '12mm', 'bottom': '12mm', 'left': '10mm', 'right': '10mm'},
                ))
                page.close()
        finally:
            browser.close()
    return parts


def _run_off_event_loop(fn, *args):
    """Playwright's sync API refuses to run inside a running asyncio loop (FastAPI's), and on
    Windows uvicorn's loop can't spawn subprocesses. A plain worker thread has neither problem."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return fn(*args)                    # no loop in this thread: just run it
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(fn, *args).result()


def _render_with_playwright(html_docs: List[str]) -> bytes:
    return _merge_pdfs(_run_off_event_loop(_playwright_render_sync, html_docs))


# -- engine 2: WeasyPrint -----------------------------------------------------
def _render_with_weasyprint(html_docs: List[str]) -> bytes:
    if not WEASYPRINT_INSTALLED:
        raise RuntimeError(f'WeasyPrint is unavailable: {WEASYPRINT_ERROR}')
    documents = [HTML(string=h).render() for h in html_docs]
    first_doc = documents[0]
    for other in documents[1:]:
        first_doc.pages.extend(other.pages)
    return first_doc.write_pdf()


# -- public API ---------------------------------------------------------------
def generate_combined_pdf(html_docs: Dict[str, str]) -> bytes:
    docs = list(html_docs.values())
    if not docs:
        raise ValueError('No HTML documents to render.')

    engines = {
        'playwright':  [('playwright', _render_with_playwright)],
        'weasyprint':  [('weasyprint', _render_with_weasyprint)],
    }.get(PDF_ENGINE, [('weasyprint', _render_with_weasyprint),
                       ('playwright', _render_with_playwright)])

    errors: List[str] = []
    for name, render in engines:
        try:
            pdf = render(docs)
            logger.info(f'PDF generated with {name}')
            return pdf
        except Exception as exc:
            logger.warning(f'PDF engine {name} failed: {exc}')
            errors.append(f'{name}: {str(exc).splitlines()[0] if str(exc) else type(exc).__name__}')

    raise RuntimeError(
        'No PDF engine worked. On a server install Pango (libpango-1.0-0, libpangoft2-1.0-0, libharfbuzz-subset0) '
        'for WeasyPrint; on Windows run "pip install playwright" then "playwright install chromium" and restart. '
        'Details - ' + ' | '.join(errors)
    )
