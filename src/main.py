"""Multimodal Paper Agent — CLI entry point for the four-stage pipeline."""

import argparse
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


def stage1_fetch() -> list[dict]:
    """Stage 1: Fetch + local filter (zero tokens).

    Automatically adjusts search range based on time since last search.
    First run covers from 2026-01-01 to now.
    """
    from datetime import datetime
    from src.fetcher.arxiv_client import fetch_recent_papers
    from src.fetcher.hf_daily_papers import fetch_hf_daily_papers
    from src.fetcher.semantic_scholar import enrich_papers
    from src.filter.dedup import deduplicate
    from src.filter.keyword_filter import keyword_filter
    from src.filter.quality_scorer import score_papers
    from src.db.history import get_last_search_time, record_search

    print("=" * 60)
    print("STAGE 1: Fetch + Local Filter (zero LLM tokens)")
    print("=" * 60)

    # Calculate search range from last search time
    last_search = get_last_search_time()
    now = datetime.utcnow()
    gap_days = (now - last_search).days

    if gap_days <= 0:
        gap_days = 1

    # Determine fetch parameters based on gap
    # Normal: 7 days, max_results=500, top_n=30
    # Gap > 7 days: expand proportionally
    if gap_days <= 7:
        days = 7
        max_results = 500
        top_n_abstract = 30
        top_n_deep = 10
    elif gap_days <= 14:
        days = gap_days + 1  # slight overlap for safety
        max_results = 800
        top_n_abstract = 50
        top_n_deep = 15
    elif gap_days <= 30:
        days = gap_days + 2
        max_results = 1500
        top_n_abstract = 80
        top_n_deep = 20
    else:
        days = gap_days + 3
        max_results = 2000
        top_n_abstract = 100
        top_n_deep = 30

    print(f"[schedule] Last search: {last_search.strftime('%Y-%m-%d %H:%M')}")
    print(f"[schedule] Gap: {gap_days} days -> fetching last {days} days, max_results={max_results}")

    # 1. Fetch from sources
    arxiv_papers = fetch_recent_papers(days=days, max_results=max_results)
    hf_papers = fetch_hf_daily_papers()

    # Merge and dedup by arxiv_id
    all_papers = {}
    for p in arxiv_papers:
        all_papers[p["arxiv_id"]] = p
    for p in hf_papers:
        aid = p["arxiv_id"]
        if aid in all_papers:
            all_papers[aid]["hf_featured"] = True
        else:
            all_papers[aid] = p

    merged = list(all_papers.values())
    print(f"[merge] {len(merged)} unique papers from all sources")

    # 2. Dedup against history
    new_papers = deduplicate(merged)

    # 3. Keyword filter
    filtered = keyword_filter(new_papers)

    # 4. Enrich with Semantic Scholar
    enriched = enrich_papers(filtered)

    # 5. Quality score
    scored = score_papers(enriched)

    # Record this search
    record_search(days_searched=days, papers_found=len(scored))

    # Attach dynamic top_n for downstream stages
    for p in scored:
        p["_top_n_abstract"] = top_n_abstract
        p["_top_n_deep"] = top_n_deep

    print(f"\nStage 1 complete: {len(scored)} candidate papers")
    if gap_days > 7:
        print(f"[schedule] Expanded mode: abstract top {top_n_abstract}, deep-read top {top_n_deep}")
    return scored


def stage2_score(papers: list[dict], model: str = "haiku") -> list[dict]:
    """Stage 2: Abstract reading with LLM (low tokens)."""
    from src.reader.abstract_reader import score_abstracts

    top_n = papers[0].get("_top_n_abstract", 30) if papers else 30

    print("\n" + "=" * 60)
    print(f"STAGE 2: Abstract Scoring ({model}, low token cost)")
    print("=" * 60)

    top = score_abstracts(papers, top_n=top_n, model=model)
    print(f"\nStage 2 complete: Top {len(top)} papers selected")
    return top


def stage3_deep_read(papers: list[dict], model: str = "sonnet") -> list[dict]:
    """Stage 3: Full-text deep reading with LLM (high tokens)."""
    from src.reader.fulltext_reader import deep_read_papers

    top_n = papers[0].get("_top_n_deep", 10) if papers else 10

    print("\n" + "=" * 60)
    print(f"STAGE 3: Deep Reading ({model}, high token cost)")
    print("=" * 60)

    top = deep_read_papers(papers, top_n=top_n, model=model)
    print(f"\nStage 3 complete: Top {len(top)} papers reviewed")
    return top


def stage4_report(papers: list[dict]) -> str:
    """Stage 4: Generate recommendation report."""
    from src.report.generator import generate_report

    print("\n" + "=" * 60)
    print("STAGE 4: Report Generation")
    print("=" * 60)

    filepath = generate_report(papers)
    print(f"\nStage 4 complete: Report saved to {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Multimodal Paper Agent")
    parser.add_argument("command", choices=["fetch", "score", "deep-read", "report", "run"],
                        help="Pipeline stage to run")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--llm", choices=["claude", "qwen"], default="qwen",
                        help="LLM provider: claude (Haiku+Sonnet) or qwen (qwen-max)")
    args = parser.parse_args()

    # Map provider to model names for each stage
    if args.llm == "qwen":
        abstract_model = "qwen"
        deep_model = "qwen"
        print(f"[config] LLM provider: Qwen (qwen-max via DashScope)")
    else:
        abstract_model = "haiku"
        deep_model = "sonnet"
        print(f"[config] LLM provider: Claude (Haiku + Sonnet)")

    if args.command == "fetch":
        papers = stage1_fetch()
        print(f"\nResult: {len(papers)} papers ready for scoring")

    elif args.command == "score":
        papers = stage1_fetch()
        top30 = stage2_score(papers, model=abstract_model)
        for i, p in enumerate(top30[:10], 1):
            score = p.get("abstract_total", 0)
            print(f"  {i}. [{score}] {p['title'][:80]}")

    elif args.command == "deep-read":
        papers = stage1_fetch()
        top30 = stage2_score(papers, model=abstract_model)
        top10 = stage3_deep_read(top30, model=deep_model)
        for i, p in enumerate(top10, 1):
            score = p.get("deep_total", 0)
            print(f"  {i}. [{score}] {p['title'][:80]}")

    elif args.command == "report" or args.command == "run":
        papers = stage1_fetch()
        top30 = stage2_score(papers, model=abstract_model)
        top10 = stage3_deep_read(top30, model=deep_model)
        filepath = stage4_report(top10)
        print(f"\n{'='*60}")
        print(f"DONE! Report: {filepath}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
