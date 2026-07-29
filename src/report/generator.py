"""Report generator — produces weekly Markdown recommendation report."""

import os
from datetime import datetime

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports"))


def generate_report(papers: list[dict]) -> str:
    """Generate a Markdown report for the top recommended papers."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"report_{date_str}.md"
    filepath = os.path.join(REPORTS_DIR, filename)

    lines = [
        f"# Multimodal Paper Weekly Report",
        f"",
        f"> 生成日期：{date_str}",
        f"> 推荐论文数：{len(papers)}",
        f"",
        f"---",
        f"",
    ]

    for rank, p in enumerate(papers, 1):
        dr = p.get("deep_read", {})
        ls = p.get("llm_score", {})
        sb = p.get("score_breakdown", {})

        title = p.get("title", "Untitled")
        arxiv_id = p.get("arxiv_id", "")
        authors = ", ".join(p.get("authors", [])[:5])
        if len(p.get("authors", [])) > 5:
            authors += " et al."

        affiliations = ", ".join(p.get("affiliations", [])[:3])
        recommendation = dr.get("recommendation", "关注")
        one_liner = ls.get("one_liner", "")
        summary = dr.get("summary", "")
        innovation = dr.get("innovation", "")

        deep_total = p.get("deep_total", 0)
        methodology = dr.get("methodology", "-")
        experiments = dr.get("experiments", "-")
        reproducibility = dr.get("reproducibility", "-")
        significance = dr.get("significance", "-")

        lines.extend([
            f"## {rank}. {title}",
            f"",
            f"**arXiv**: [{arxiv_id}](https://arxiv.org/abs/{arxiv_id}) | "
            f"**PDF**: [Link](https://arxiv.org/pdf/{arxiv_id}.pdf) | "
            f"**推荐等级**: {recommendation}",
            f"",
            f"**Authors**: {authors}",
            f"",
        ])

        if affiliations:
            lines.append(f"**Institutions**: {affiliations}")
            lines.append("")

        if one_liner:
            lines.append(f"**一句话亮点**: {one_liner}")
            lines.append("")

        if summary:
            lines.append(f"**摘要评述**: {summary}")
            lines.append("")

        if innovation:
            lines.append(f"**核心创新**: {innovation}")
            lines.append("")

        lines.extend([
            f"| 维度 | 得分 |",
            f"|------|------|",
            f"| 方法论 | {methodology}/10 |",
            f"| 实验充分性 | {experiments}/10 |",
            f"| 可复现性 | {reproducibility}/10 |",
            f"| 重要性 | {significance}/10 |",
            f"| **综合** | **{deep_total}/40** |",
            f"",
        ])

        # Open source links
        abstract = p.get("abstract", "")
        if "github.com" in abstract.lower():
            import re
            gh_links = re.findall(r'https?://github\.com/[\w-]+/[\w.-]+', abstract, re.IGNORECASE)
            if gh_links:
                lines.append(f"**GitHub**: {gh_links[0]}")
                lines.append("")

        lines.append("---")
        lines.append("")

    report_content = "\n".join(lines)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"[report] Generated: {filepath}")
    return filepath
