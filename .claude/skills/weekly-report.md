---
name: weekly-report
description: "Run the complete 4-stage pipeline and generate a weekly paper recommendation report."
user_invocable: true
---

Run the complete pipeline and generate a Markdown report. Execute:

```bash
cd ~/Documents/workspace/multimodal-paper-agent && conda run -n multimodal python src/main.py report
```

Full pipeline: fetch → dedup → keyword filter → quality score → abstract scoring (Haiku) → deep reading (Sonnet) → Top 10 report.

The report is saved to `data/reports/report_YYYY-MM-DD.md` with:
- One-line highlights (中文)
- Recommendation reasons (中文)
- Institution info
- Innovation summary (中文)
- Multi-dimensional scores
- Open-source links (GitHub/HuggingFace)

Token cost: High (Haiku for 阶段二 + Sonnet for 阶段三).
