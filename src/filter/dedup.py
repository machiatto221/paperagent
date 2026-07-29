"""Deduplication filter using SQLite history database."""

from src.db.history import is_seen, batch_filter_new, insert_paper


def deduplicate(papers: list[dict]) -> list[dict]:
    """Remove papers already in the history database. Insert new ones as 'pending'."""
    if not papers:
        return []

    arxiv_ids = [p["arxiv_id"] for p in papers]
    new_ids = set(batch_filter_new(arxiv_ids))

    new_papers = []
    for p in papers:
        if p["arxiv_id"] in new_ids:
            insert_paper(
                arxiv_id=p["arxiv_id"],
                doi=p.get("doi", ""),
                title=p.get("title", ""),
                status="pending",
            )
            new_papers.append(p)

    print(f"[dedup] {len(papers)} total -> {len(new_papers)} new (filtered {len(papers) - len(new_papers)} duplicates)")
    return new_papers
