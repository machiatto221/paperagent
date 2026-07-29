"""Keyword-based filtering using whitelist/blacklist from config."""

import re
import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "keywords.yaml")


def _load_config() -> dict:
    with open(os.path.abspath(CONFIG_PATH), "r") as f:
        return yaml.safe_load(f)


def _text_contains(text: str, keyword: str) -> bool:
    return bool(re.search(re.escape(keyword.lower()), text))


def _parse_whitelist(raw: list) -> list[dict]:
    """Normalize whitelist entries to {keyword, weight} dicts."""
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append({"keyword": item["keyword"], "weight": item.get("weight", 1)})
        else:
            result.append({"keyword": item, "weight": 1})
    return result


def keyword_filter(papers: list[dict]) -> list[dict]:
    """Keep papers matching whitelist keywords, reject those matching blacklist.

    Also stores the best matching keyword weight on each paper for scoring.
    """
    config = _load_config()
    whitelist = _parse_whitelist(config.get("whitelist", []))
    blacklist = config.get("blacklist", [])

    passed = []
    for p in papers:
        # HF featured papers bypass keyword filter
        if p.get("hf_featured"):
            p["topic_weight"] = 5
            passed.append(p)
            continue

        text = f"{p.get('title', '')} {p.get('abstract', '')}".lower()

        # Blacklist check
        blocked = False
        for bl in blacklist:
            if _text_contains(text, bl):
                blocked = True
                break
        if blocked:
            continue

        # Whitelist: find best (highest weight) match
        best_weight = 0
        for entry in whitelist:
            if _text_contains(text, entry["keyword"]):
                best_weight = max(best_weight, entry["weight"])

        if best_weight > 0:
            p["topic_weight"] = best_weight
            passed.append(p)

    print(f"[keyword] {len(papers)} -> {len(passed)} papers after keyword filtering")
    return passed
