"""Semantic Scholar API client for enriching paper metadata."""

from src.fetcher.http_utils import fetch

S2_API = "https://api.semanticscholar.org/graph/v1"

FIELDS = "paperId,externalIds,title,abstract,authors,authors.affiliations,citationCount,influentialCitationCount,venue,year,openAccessPdf,url"
AUTHOR_FIELDS = "authorId,name,affiliations,hIndex,paperCount,citationCount"


def search_papers(query: str, limit: int = 100, year: str = "2025-") -> list[dict]:
    """Search papers via Semantic Scholar."""
    params = {"query": query, "limit": limit, "fields": FIELDS, "year": year}
    resp = fetch(f"{S2_API}/paper/search", params=params)
    data = resp.json()
    return data.get("data", [])


def get_paper_by_arxiv_id(arxiv_id: str) -> dict | None:
    """Fetch paper details by arXiv ID."""
    try:
        resp = fetch(f"{S2_API}/paper/ARXIV:{arxiv_id}", params={"fields": FIELDS})
        return resp.json()
    except Exception:
        return None


def batch_get_papers(arxiv_ids: list[str]) -> list[dict]:
    """Batch fetch paper details for a list of arXiv IDs.

    S2 batch endpoint: POST /paper/batch with {"ids": ["ARXIV:xxx", ...]}
    """
    if not arxiv_ids:
        return []

    results = []
    # S2 batch limit is 500 per request
    for i in range(0, len(arxiv_ids), 500):
        batch = arxiv_ids[i:i + 500]
        ids = [f"ARXIV:{aid}" for aid in batch]
        try:
            from src.fetcher.http_utils import _session, _wait_for_rate_limit, USER_AGENTS
            import random

            _wait_for_rate_limit("api.semanticscholar.org")
            headers = {"User-Agent": random.choice(USER_AGENTS)}

            import os
            s2_key = os.getenv("S2_API_KEY")
            if s2_key:
                headers["x-api-key"] = s2_key

            resp = _session.post(
                f"{S2_API}/paper/batch",
                json={"ids": ids},
                params={"fields": FIELDS},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            batch_results = resp.json()
            results.extend([r for r in batch_results if r is not None])
        except Exception as e:
            print(f"[s2] Batch request failed: {e}")

    print(f"[s2] Enriched {len(results)}/{len(arxiv_ids)} papers")
    return results


def enrich_papers(papers: list[dict]) -> list[dict]:
    """Enrich arXiv papers with Semantic Scholar metadata (authors, affiliations, citations)."""
    arxiv_ids = [p["arxiv_id"] for p in papers]
    s2_data = batch_get_papers(arxiv_ids)

    s2_map = {}
    for s2p in s2_data:
        ext = s2p.get("externalIds", {})
        aid = ext.get("ArXiv")
        if aid:
            s2_map[aid] = s2p

    for paper in papers:
        s2p = s2_map.get(paper["arxiv_id"])
        if not s2p:
            paper["s2_enriched"] = False
            paper["citation_count"] = 0
            paper["influential_citations"] = 0
            paper["affiliations"] = []
            paper["venue"] = ""
            continue

        paper["s2_enriched"] = True
        paper["citation_count"] = s2p.get("citationCount", 0) or 0
        paper["influential_citations"] = s2p.get("influentialCitationCount", 0) or 0
        paper["venue"] = s2p.get("venue", "") or ""

        affiliations = set()
        for author in s2p.get("authors", []):
            for aff in (author.get("affiliations") or []):
                if aff:
                    affiliations.add(aff)
        paper["affiliations"] = list(affiliations)

        oa = s2p.get("openAccessPdf")
        if oa and oa.get("url"):
            paper["pdf_url"] = oa["url"]

    return papers
