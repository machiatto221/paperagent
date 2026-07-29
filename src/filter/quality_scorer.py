"""Local quality scorer based on institution, author, venue, and open-source signals."""

import re
import yaml
import os

CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config"))


def _load_yaml(name: str) -> dict:
    with open(os.path.join(CONFIG_DIR, name), "r") as f:
        return yaml.safe_load(f)


def _institution_score(paper: dict, inst_config: dict) -> float:
    """Score based on author affiliations matching known institutions."""
    affiliations = paper.get("affiliations", [])
    author_names = [a if isinstance(a, str) else a.get("name", "") for a in paper.get("authors", [])]
    text = " ".join(affiliations + author_names).lower()

    score = 0.0
    for tier_key in ["tier1", "tier2"]:
        tier = inst_config.get(tier_key, {})
        weight = tier.get("weight", 0)
        for name in tier.get("names", []):
            if name.lower() in text:
                score = max(score, weight)
                break

    # Known authors bonus
    known = inst_config.get("known_authors", {})
    kw = known.get("weight", 0)
    for name in known.get("names", []):
        if name.lower() in text:
            score += kw
            break

    return score


def _venue_score(paper: dict, conf_config: dict) -> float:
    """Score based on venue / conference acceptance."""
    venue = (paper.get("venue", "") or "").lower()
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    combined = f"{venue} {title} {abstract}"

    top_venues = conf_config.get("top_venues", {})
    weight = top_venues.get("weight", 0)
    for v in top_venues.get("names", []):
        if v.lower() in combined:
            return weight
    return 0.0


def _open_source_score(paper: dict) -> float:
    """Bonus for papers with GitHub or HuggingFace links."""
    text = f"{paper.get('abstract', '')} {paper.get('title', '')}"
    score = 0.0
    if "github.com" in text.lower():
        score += 5.0
    if "huggingface.co" in text.lower() or "hf.co" in text.lower():
        score += 5.0
    if paper.get("hf_featured"):
        score += 8.0
    return score


def _citation_score(paper: dict) -> float:
    """Score from citation metrics (limited for new papers)."""
    citations = paper.get("citation_count", 0) or 0
    influential = paper.get("influential_citations", 0) or 0
    return min(citations * 0.1 + influential * 2.0, 10.0)


def score_papers(papers: list[dict]) -> list[dict]:
    """Score and rank papers using local heuristics. No LLM calls."""
    inst_config = _load_yaml("institutions.yaml")
    conf_config = _load_yaml("conferences.yaml")

    for p in papers:
        inst = _institution_score(p, inst_config)
        venue = _venue_score(p, conf_config)
        oss = _open_source_score(p)
        cit = _citation_score(p)
        topic = float(p.get("topic_weight", 0))
        p["quality_score"] = inst + venue + oss + cit + topic
        p["score_breakdown"] = {
            "institution": inst,
            "venue": venue,
            "open_source": oss,
            "citation": cit,
            "topic": topic,
        }

    papers.sort(key=lambda x: x["quality_score"], reverse=True)
    print(f"[scorer] Scored {len(papers)} papers, top score: {papers[0]['quality_score']:.1f}" if papers else "[scorer] No papers to score")
    return papers
