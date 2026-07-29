"""arXiv API client for fetching recent papers."""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from src.fetcher.http_utils import fetch

ARXIV_API = "http://export.arxiv.org/api/query"
CATEGORIES = ["cs.CV", "cs.AI", "cs.CL", "cs.LG", "cs.MM"]

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract clean arxiv ID from full URL, e.g. '2401.12345' from 'http://arxiv.org/abs/2401.12345v1'."""
    raw = entry_id.split("/abs/")[-1]
    # Remove version suffix
    if "v" in raw:
        raw = raw.rsplit("v", 1)[0]
    return raw


def fetch_recent_papers(days: int = 7, max_results: int = 500) -> list[dict]:
    """Fetch papers from arXiv submitted in the last N days across target categories."""
    papers = []
    seen_ids = set()

    for cat in CATEGORIES:
        query = f"cat:{cat}"
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        resp = fetch(ARXIV_API, params=params)
        root = ET.fromstring(resp.text)

        cutoff = datetime.utcnow() - timedelta(days=days)

        for entry in root.findall("atom:entry", ATOM_NS):
            published_str = entry.find("atom:published", ATOM_NS).text
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00")).replace(tzinfo=None)
            if published < cutoff:
                continue

            arxiv_id = _extract_arxiv_id(entry.find("atom:id", ATOM_NS).text)
            if arxiv_id in seen_ids:
                continue
            seen_ids.add(arxiv_id)

            authors = [a.find("atom:name", ATOM_NS).text
                       for a in entry.findall("atom:author", ATOM_NS)]

            primary_cat_el = entry.find("arxiv:primary_category", ATOM_NS)
            primary_cat = primary_cat_el.attrib.get("term", "") if primary_cat_el is not None else ""

            summary = entry.find("atom:summary", ATOM_NS).text or ""

            papers.append({
                "arxiv_id": arxiv_id,
                "title": " ".join(entry.find("atom:title", ATOM_NS).text.split()),
                "abstract": " ".join(summary.split()),
                "authors": authors,
                "published": published.isoformat(),
                "primary_category": primary_cat,
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                "source": "arxiv",
            })

    print(f"[arxiv] Fetched {len(papers)} papers from last {days} days")
    return papers
