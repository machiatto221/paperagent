"""PDF text extraction using PyMuPDF (fitz)."""

import os

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "pdfs"))


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def download_pdf(pdf_url: str, arxiv_id: str) -> str | None:
    """Download PDF to data/pdfs/ and return local path."""
    _ensure_dir()
    safe_name = arxiv_id.replace("/", "_") + ".pdf"
    local_path = os.path.join(DATA_DIR, safe_name)

    if os.path.exists(local_path):
        return local_path

    try:
        from src.fetcher.http_utils import fetch
        resp = fetch(pdf_url)
        with open(local_path, "wb") as f:
            f.write(resp.content)
        return local_path
    except Exception as e:
        print(f"[pdf] Failed to download {arxiv_id}: {e}")
        return None


def extract_text(pdf_path: str, max_pages: int = 20) -> str:
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        pages = min(len(doc), max_pages)
        text_parts = []
        for i in range(pages):
            page = doc[i]
            text_parts.append(page.get_text())
        doc.close()
        full_text = "\n\n".join(text_parts)
        # Truncate to ~15000 chars to stay within reasonable token limits
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n\n[... truncated ...]"
        return full_text
    except Exception as e:
        print(f"[pdf] Extraction failed for {pdf_path}: {e}")
        return ""
