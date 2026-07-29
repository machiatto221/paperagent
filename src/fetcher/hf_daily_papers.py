"""Hugging Face Daily Papers scraper."""

from bs4 import BeautifulSoup
from src.fetcher.http_utils import fetch

HF_PAPERS_URL = "https://huggingface.co/papers"


def fetch_hf_daily_papers() -> list[dict]:
    """Scrape Hugging Face Daily Papers page for recent papers."""
    papers = []
    try:
        resp = fetch(HF_PAPERS_URL)
        soup = BeautifulSoup(resp.text, "html.parser")

        # HF papers page lists papers with links to arxiv
        for article in soup.find_all("article"):
            link = article.find("a", href=True)
            if not link:
                continue
            href = link.get("href", "")
            # Links are like /papers/2401.12345
            if not href.startswith("/papers/"):
                continue
            arxiv_id = href.replace("/papers/", "").strip()
            if not arxiv_id:
                continue

            title_el = article.find("h3") or article.find("h4") or link
            title = title_el.get_text(strip=True) if title_el else ""

            papers.append({
                "arxiv_id": arxiv_id,
                "title": title,
                "abstract": "",
                "authors": [],
                "published": "",
                "primary_category": "",
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                "source": "hf_daily",
                "hf_featured": True,
            })

    except Exception as e:
        print(f"[hf] Failed to fetch daily papers: {e}")

    print(f"[hf] Fetched {len(papers)} papers from HuggingFace Daily")
    return papers
