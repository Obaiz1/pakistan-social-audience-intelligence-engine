"""OPTIONAL: an LLM rewrites a recommendation card in plain language, with every number locked to the card's evidence.

Adapted from Repo A (pakistani-social-media-content-detective, src/recommendations/llm_wording.py @957e3b6f).
- Off by default. Enabled only locally when NVIDIA_API_KEY is set AND AUDIENCEIQ_ENABLE_LLM=1 (never on the public demo).
- Only the card's already-computed, aggregated text is sent (no comment text, no personal data).
- If the rewrite contains any number that is not in the card, it is rejected and the deterministic text is kept.
- Provider: NVIDIA API Catalog (OpenAI-compatible). Model from NVIDIA_MODEL; default is the model Project 1 used.
"""

import os
import re

URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
_NUM = re.compile(r"[-+]?\d+(?:[.,]\d+)?")

PROMPT = ("Rewrite this marketing recommendation for a Pakistani clothing brand's marketing manager in 2–3 short, "
          "plain-English sentences. Keep it cautious (it is evidence to test, not a guarantee). Use ONLY numbers that "
          "appear in the card; do not invent, round differently, or add numbers.\n\nCARD:\n{card}\n\nRewrite:")


def card_text(card: dict) -> str:
    return (f"Title: {card['title']}\nWhat: {card['what_to_do']}\nWhy: {card['why_it_matters']}\n"
            f"Evidence n: {card['sample_size']}\nStrength: {card['evidence_strength']}\nTest: {card['test_plan']}")


def numbers_in(text: str) -> set[float]:
    """Numeric values in the text ("06" == "6"; thousands separators removed; sign kept)."""
    return {float(m.replace(",", "")) for m in _NUM.findall(text.replace("−", "-").replace("–", " "))}


def number_lock_ok(rewrite: str, card: dict) -> bool:
    allowed = numbers_in(card_text(card))
    allowed |= {abs(x) for x in allowed}
    return numbers_in(rewrite) <= allowed


def rewrite(card: dict, api_key: str | None = None, model: str | None = None, timeout: int = 60, post=None) -> dict:
    """Returns {text, used_llm, model, reason}. Falls back to the deterministic text on any error or lock failure."""
    template = f"{card['what_to_do']} {card['why_it_matters']}"
    key = api_key if api_key is not None else os.environ.get("NVIDIA_API_KEY", "")
    model = model or os.environ.get("NVIDIA_MODEL") or DEFAULT_MODEL
    if not key:
        return {"text": template, "used_llm": False, "model": None, "reason": "no API key configured"}
    if post is None:
        import requests

        post = requests.post
    try:
        r = post(URL, timeout=timeout, headers={"Authorization": f"Bearer {key}"}, json={
            "model": model, "temperature": 0.2, "max_tokens": 600,
            "messages": [{"role": "user", "content": PROMPT.format(card=card_text(card))}]})
        r.raise_for_status()
        text = (r.json()["choices"][0]["message"].get("content") or "").strip()
    except Exception as exc:  # network, HTTP, schema: always fall back
        return {"text": template, "used_llm": False, "model": model, "reason": f"provider error: {type(exc).__name__}"}
    if not text:
        return {"text": template, "used_llm": False, "model": model, "reason": "empty response"}
    if not number_lock_ok(text, card):
        return {"text": template, "used_llm": False, "model": model, "reason": "rejected: rewrite changed or added numbers"}
    return {"text": text, "used_llm": True, "model": model, "reason": "number lock passed"}
