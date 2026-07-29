"""Stage 3: Full-text deep reading."""

from src.llm.client import call_llm
from src.reader.pdf_extractor import download_pdf, extract_text
from src.db.history import update_status

SYSTEM_PROMPT = """You are a senior multimodal AI researcher conducting a thorough paper review.

Evaluate the paper on these dimensions:
1. methodology (0-10): Is the method well-designed, theoretically sound, and clearly explained?
2. experiments (0-10): Are experiments comprehensive? Are baselines fair? Are ablations sufficient?
3. reproducibility (0-10): Can this work be reproduced? Is code available? Are details sufficient?
4. significance (0-10): How significant is the contribution to multimodal AI / LLM research?

Return a JSON object with keys: methodology, experiments, reproducibility, significance, total (sum), summary (2-3 sentence summary in Chinese), innovation (key innovation point in Chinese), recommendation (推荐/关注/一般)."""


def deep_read_paper(paper: dict, model: str = "sonnet") -> dict:
    """Download PDF, extract text, and deep-read."""
    pdf_url = paper.get("pdf_url", "")
    arxiv_id = paper["arxiv_id"]

    pdf_path = download_pdf(pdf_url, arxiv_id)
    if not pdf_path:
        paper["deep_read"] = {"error": "PDF download failed"}
        return paper

    full_text = extract_text(pdf_path)
    if not full_text:
        paper["deep_read"] = {"error": "Text extraction failed"}
        return paper

    user_content = f"Title: {paper['title']}\n\nAuthors: {', '.join(paper.get('authors', []))}\n\nFull Text:\n{full_text}"

    try:
        result = call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_content=user_content,
            model=model,
            max_tokens=2048,
        )
        paper["deep_read"] = result
        paper["deep_total"] = result.get("total", 0)
        update_status(arxiv_id, "read", result.get("total", 0))
    except Exception as e:
        print(f"[deep] Failed to read {arxiv_id}: {e}")
        paper["deep_read"] = {"error": str(e)}
        paper["deep_total"] = 0

    return paper


def deep_read_papers(papers: list[dict], top_n: int = 10, model: str = "sonnet") -> list[dict]:
    """Deep-read all papers and return top N."""
    print(f"[deep] Deep reading {len(papers)} papers with {model}...")

    read = []
    for i, p in enumerate(papers):
        read.append(deep_read_paper(p, model=model))
        print(f"[deep] Progress: {i+1}/{len(papers)} - {p['arxiv_id']}")

    read.sort(key=lambda x: x.get("deep_total", 0), reverse=True)
    top = read[:top_n]

    print(f"[deep] Top {len(top)} selected")
    return top
