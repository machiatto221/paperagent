"""Stage 2: LLM-based abstract reading and scoring."""

from src.llm.client import call_llm
from src.db.history import update_status

SYSTEM_PROMPT = """You are a senior multimodal AI researcher. Your task is to evaluate paper abstracts for relevance and novelty.

Evaluate each abstract on these dimensions:
1. relevance (0-10): How relevant is this to multimodal large models, VLM, OVOD, multimodal agents, SFT, RL, self-reward, native multimodal architectures, or agentic RL?
2. novelty (0-10): How novel is the approach? Does it propose a breakthrough architecture, training method, or paradigm?
3. impact (0-10): Potential impact on the field based on the claims in the abstract.

Return a JSON object with keys: relevance, novelty, impact, total (sum of three scores), one_liner (one sentence highlight in Chinese)."""


def score_abstract(paper: dict, model: str = "haiku") -> dict:
    """Score a single paper's abstract."""
    user_content = f"Title: {paper['title']}\n\nAbstract: {paper['abstract']}"
    try:
        result = call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_content=user_content,
            model=model,
            max_tokens=512,
        )
        paper["llm_score"] = result
        paper["abstract_total"] = result.get("total", 0)
        update_status(paper["arxiv_id"], "scored", result.get("total", 0))
    except Exception as e:
        print(f"[abstract] Failed to score {paper['arxiv_id']}: {e}")
        paper["llm_score"] = {}
        paper["abstract_total"] = 0

    return paper


def score_abstracts(papers: list[dict], top_n: int = 30, model: str = "haiku") -> list[dict]:
    """Score all paper abstracts and return top N."""
    print(f"[abstract] Scoring {len(papers)} abstracts with {model}...")

    scored = []
    for i, p in enumerate(papers):
        if not p.get("abstract"):
            continue
        scored.append(score_abstract(p, model=model))
        if (i + 1) % 10 == 0:
            print(f"[abstract] Progress: {i+1}/{len(papers)}")

    scored.sort(key=lambda x: x.get("abstract_total", 0), reverse=True)
    top = scored[:top_n]

    print(f"[abstract] Top {len(top)} selected (best score: {top[0].get('abstract_total', 0) if top else 0})")
    return top
