---
name: score-papers
description: "Run Stages 1+2: fetch papers then score abstracts with Claude Haiku."
user_invocable: true
---

Run the full Stage 1 + Stage 2 pipeline. Execute:

```bash
cd ~/Documents/workspace/multimodal-paper-agent && conda run -n multimodal python src/main.py score
```

This runs Stage 1 (fetch + local filter) followed by Stage 2 (abstract scoring with Haiku).
Outputs the Top 30 papers ranked by abstract relevance, novelty, and impact scores.

Token cost: Low (Haiku model, abstract-only input, ~200 tokens per paper).
