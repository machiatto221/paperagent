---
name: deep-read
description: "Run Stages 1-3: fetch, score abstracts, then deep-read full papers with Claude Sonnet."
user_invocable: true
---

Run the full Stage 1 + 2 + 3 pipeline. Execute:

```bash
cd ~/Documents/workspace/multimodal-paper-agent && conda run -n multimodal python src/main.py deep-read
```

This runs all three stages: fetch + filter, abstract scoring (Haiku), and full-text deep reading (Sonnet).
Downloads PDFs for the Top 30 and performs multi-dimensional evaluation.

Token cost: High (Sonnet model, full paper text input for up to 30 papers).
