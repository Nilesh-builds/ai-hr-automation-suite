"""Configuration and LLM client.

Everything is optional: the rule-based baselines and the evaluation harness
run with no API keys at all. The LLM layer is only used when OPENAI_API_KEY
is present.
"""

from __future__ import annotations

import json
import os
import re


def load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def llm_available() -> bool:
    return bool(get("OPENAI_API_KEY"))


def llm_model() -> str:
    return get("OPENAI_MODEL", "gpt-4")


def llm_client():
    from openai import OpenAI

    return OpenAI(api_key=get("OPENAI_API_KEY"))


def extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object out of an LLM response."""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("no JSON object found in LLM response")
    return json.loads(match.group(0))


def validated_str(value, category: str, default: str) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned not in category:
        return default
    return cleaned


def clamp_float(value, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return lo