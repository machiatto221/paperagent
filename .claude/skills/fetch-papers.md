---
name: fetch-papers
description: "Run Stage 1 pipeline: fetch papers from arXiv/HF, deduplicate, keyword filter, and quality score."
user_invocable: true
---

Run the Stage 1 paper fetching pipeline. Execute:

```bash
cd ~/Documents/workspace/multimodal-paper-agent && conda run -n multimodal python src/main.py fetch
```

This will:
1. Fetch recent papers from arXiv (cs.CV, cs.AI, cs.CL, cs.LG) and HuggingFace Daily Papers
2. Deduplicate against `data/history.db`
3. Filter by keyword whitelist/blacklist (`config/keywords.yaml`)
4. Enrich with Semantic Scholar metadata (authors, affiliations, citations)
5. Score locally by institution/venue/open-source signals

Zero LLM token consumption. Output: list of scored candidate papers.
