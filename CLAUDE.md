# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multimodal Paper Agent — 自动化追踪、筛选、精读前沿多模态 AI 论文的四阶段漏斗流水线。

**核心设计原则**：分阶段过滤，尽可能在本地零 Token 阶段淘汰低质量论文，只对高潜力论文消耗 LLM API。

## Architecture

```
Stage 1 (zero tokens)     Stage 2 (low tokens)    Stage 3 (high tokens)    Stage 4
arXiv/HF → dedup →        abstracts →              PDFs →                   Top 10 →
keyword filter →           Haiku scoring →          Sonnet deep read →       Markdown
S2 enrich → local score    Top 30                   Top 10                   report
```

### Data Sources (src/fetcher/)
- `arxiv_client.py` — arXiv API (cs.CV/AI/CL/LG), last 7 days
- `semantic_scholar.py` — S2 API batch enrichment (authors, affiliations, citations)
- `hf_daily_papers.py` — HuggingFace Daily Papers (auto-bypasses keyword filter)
- `http_utils.py` — shared HTTP: UA rotation, per-domain rate limits, exponential backoff

### Filters (src/filter/)
- `dedup.py` — SQLite dedup by arXiv ID (data/history.db)
- `keyword_filter.py` — whitelist/blacklist from config/keywords.yaml
- `quality_scorer.py` — institution/venue/open-source local scoring

### Readers (src/reader/)
- `abstract_reader.py` — Stage 2, Haiku, scores relevance/novelty/impact
- `fulltext_reader.py` — Stage 3, Sonnet, scores methodology/experiments/reproducibility/significance
- `pdf_extractor.py` — PyMuPDF text extraction, truncated to ~15k chars

### LLM (src/llm/client.py)
- Anthropic SDK only. Haiku for abstracts, Sonnet for full-text.
- **All calls enforce no-CoT**: system prompt appends strict JSON-only instruction
- `temperature=0` always

## Commands

```bash
# Activate environment
conda activate multimodal

# Install project dependencies
pip install -r requirements.txt

# Run pipeline stages
python src/main.py fetch       # Stage 1 only (zero tokens)
python src/main.py score       # Stage 1 + 2
python src/main.py deep-read   # Stage 1 + 2 + 3
python src/main.py report      # Full pipeline + report generation
```

## Configuration

| File | Purpose |
|------|---------|
| `config/keywords.yaml` | Keyword whitelist/blacklist for filtering |
| `config/institutions.yaml` | Tier1/Tier2 institutions + known authors with weights |
| `config/conferences.yaml` | Top venues for acceptance matching |
| `.env` | API keys: `ANTHROPIC_API_KEY`, `S2_API_KEY` (optional) |

## Critical Rules

1. **Never call Google Scholar** — use arXiv API, Semantic Scholar API, HF Daily Papers only
2. **Dedup before any LLM call** — check history.db first, reject duplicates silently
3. **No CoT in API calls** — all LLM prompts must enforce raw JSON output
4. **Rate limiting** — arXiv ≥3s, S2 ≥1s (with key) / ≥3s (without), exponential backoff on 429
5. **Report language** — Chinese-English mixed: terms in English, analysis in Chinese
