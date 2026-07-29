"""LLM API wrapper supporting Claude (Anthropic) and Qwen (DashScope)."""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "qwen": "qwen-max",
}


def _get_provider(model: str) -> str:
    """Determine provider from model name."""
    if model in ["haiku", "sonnet"] or model.startswith("claude"):
        return "anthropic"
    elif model == "qwen" or model.startswith("qwen"):
        return "dashscope"
    return "anthropic"  # default


def _get_provider(model: str) -> str:
    """Determine provider from model name."""
    if model in ["haiku", "sonnet"] or model.startswith("claude"):
        return "anthropic"
    elif model == "qwen" or model.startswith("qwen"):
        return "dashscope"
    return "anthropic"  # default


def _call_anthropic(system_prompt: str, user_content: str, model_id: str, max_tokens: int) -> str:
    """Call Anthropic Claude API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return message.content[0].text.strip()


def _call_dashscope(system_prompt: str, user_content: str, model_id: str, max_tokens: int) -> str:
    """Call Alibaba DashScope (Qwen) API."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY not set in .env")

    import dashscope
    dashscope.api_key = api_key

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    response = dashscope.Generation.call(
        model=model_id,
        messages=messages,
        result_format="message",
        max_tokens=max_tokens,
        temperature=0,
    )

    if response.status_code != 200:
        raise RuntimeError(f"DashScope API error: {response.message}")

    return response.output.choices[0].message.content.strip()


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
    return anthropic.Anthropic(api_key=api_key)


def call_llm(
    system_prompt: str,
    user_content: str,
    model: str = "haiku",
    max_tokens: int = 4096,
) -> dict:
    """Call LLM API (Claude or Qwen) and return parsed JSON response.

    All prompts include a strict no-CoT instruction.
    The model is expected to return ONLY valid JSON.
    """
    model_id = MODELS.get(model, model)
    provider = _get_provider(model)

    no_cot_instruction = (
        "\n\nIMPORTANT: Output ONLY valid JSON. "
        "Do NOT include any explanation, reasoning, chain-of-thought, or markdown formatting. "
        "Return the raw JSON object directly."
    )

    full_system = system_prompt + no_cot_instruction

    if provider == "dashscope":
        text = _call_dashscope(full_system, user_content, model_id, max_tokens)
    else:
        text = _call_anthropic(full_system, user_content, model_id, max_tokens)

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()

    return json.loads(text)
