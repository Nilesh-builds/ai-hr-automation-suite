"""Employee sentiment analysis.

A deterministic lexicon baseline scores free-text feedback and derives
urgency level, attrition risk, and key themes without any API. The LLM path
produces the same structured output for nuanced phrasing.
"""

from __future__ import annotations

import re

from .. import config

MOOD_SCORES = {
    "great": 1.0,
    "good": 0.5,
    "okay": 0.0,
    "stressed": -0.5,
    "struggling": -1.0,
}

POSITIVE_TERMS = {
    "happy", "love", "great", "good", "excellent", "amazing", "supportive",
    "grateful", "thank", "enjoy", "helpful", "fair", "promotion", "raise",
    "positive", "thankful", "improving", "benefits", "appreciate",
}
NEGATIVE_TERMS = {
    "overwhelmed", "burnout", "stressed", "unhappy", "awful", "toxic",
    "too much", "exhausted", "frustrated", "unfair", "underpaid", "worried",
    "struggling", "anxious", "sick of", "cant handle", "leave", "quit",
    "discriminated", "harassment", "pressure", "deadline",
}
_THEME_TERMS = {
    "workload": ("overwhelmed", "too much", "exhausted", "pressure", "deadline", "workload"),
    "management": ("manager", "boss", "micromanag", "unfair", "favoritism"),
    "pay": ("salary", "pay", "raise", "compensation", "underpaid"),
    "growth": ("promotion", "career", "growth", "learning", "training", "stuck"),
    "culture": ("toxic", "culture", "harassment", "discriminated", "respect"),
    "worklife": ("balance", "work-life", "wlb", "burnout", "vacation"),
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def score_feedback_rule_based(mood: str, comments: str) -> dict:
    """Positive/negative term counting with emphasis on negation."""
    mood_score = MOOD_SCORES.get(mood.lower(), 0.0)
    tokens = _tokenize(comments)
    connected = " ".join(tokens)

    positive_hits = sum(term in connected for term in POSITIVE_TERMS)
    negative_hits = sum(term in connected for term in NEGATIVE_TERMS)
    negation_discount = sum(1 for i in range(len(tokens) - 1)
                            if tokens[i] in ("not", "never", "no")
                            and tokens[i + 1] in POSITIVE_TERMS)

    score = mood_score + (0.15 * positive_hits) - (0.25 * negative_hits) - (0.3 * negation_discount)
    score = max(-1.0, min(1.0, round(score, 2)))

    themes = [name for name, terms in _THEME_TERMS.items()
              if any(term in connected for term in terms)]
    if not themes and negative_hits:
        themes.append("general")

    urgency = "high" if negative_hits >= 2 or score <= -0.5 else "medium" if negative_hits >= 1 else "low"
    attrition = "high" if negative_hits >= 2 or score <= -0.7 else "medium" if score <= -0.3 else "low"
    needs_follow_up = urgency in ("high", "medium")

    return {
        "sentiment_score": score,
        "key_themes": themes[:4],
        "urgency_level": urgency,
        "attrition_risk": attrition,
        "needs_follow_up": needs_follow_up,
        "confidence": 0.7 if comments.strip() else 0.5,
    }


_LLM_SYSTEM = (
    "Analyze the employee feedback and return JSON only: "
    "{\"sentimentScore\":number,-1..1,\"keyThemes\":[string],"
    "\"urgencyLevel\":\"low|medium|high\",\"attritionRisk\":\"low|medium|high\","
    "\"needsFollowUp\":bool,\"suggestedActions\":[string]}."
)


def score_feedback_llm(mood: str, comments: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=config.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=config.llm_model(),
        temperature=0.1,
        messages=[
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": f"Mood: {mood}\nComments: {comments or '(none)'}"},
        ],
    )
    raw = response.choices[0].message.content or ""
    try:
        payload = config.extract_json(raw)
        return {
            "sentiment_score": config.clamp_float(payload.get("sentimentScore"), -1.0, 1.0),
            "key_themes": [str(t) for t in (payload.get("keyThemes") or [])][:4],
            "urgency_level": config.validated_str(payload.get("urgencyLevel"), "low medium high", "low"),
            "attrition_risk": config.validated_str(payload.get("attritionRisk"), "low medium high", "low"),
            "needs_follow_up": bool(payload.get("needsFollowUp", False)),
            "confidence": 0.9,
        }
    except (ValueError, TypeError):
        return {
            "sentiment_score": 0.0, "key_themes": [],
            "urgency_level": "low", "attrition_risk": "low",
            "needs_follow_up": False, "confidence": 0.5,
        }


def score_feedback(mood: str, comments: str) -> dict:
    if config.llm_available():
        return score_feedback_llm(mood, comments)
    return score_feedback_rule_based(mood, comments)