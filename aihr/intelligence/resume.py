"""AI resume screening and ranking.

The rule-based baseline scores a resume against a role's requirements by
matching skills and an extracted years-of-experience figure. The LLM path
applies the same rubric but reads prose resumes.
"""

from __future__ import annotations

import re

from .. import config

COMMON_STOP = {
    "and", "or", "the", "a", "an", "with", "in", "on", "of", "using",
    "for", "as", "to", "experience", "years", "year", "level", "strong",
    "good", "excellent", "knowledge", "skills",
}


def _skill_hits(text: str, skills: list[str]) -> list[str]:
    """Normalize hyphens/whitespace so 'scikit-learn' matches 'scikit learn'."""
    import re as _re

    normalized = _re.sub(r"[\s_-]+", " ", text.lower())
    hits = []
    for skill in skills:
        if not skill.strip():
            continue
        key = _re.sub(r"[\s_-]+", " ", skill.strip().lower())
        if key in normalized:
            hits.append(skill.strip())
    return sorted(set(hits))


def _experience_years(text: str) -> float:
    years = re.findall(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?|yr)\b", text.lower())
    if years:
        return max(float(y) for y in years)
    months = re.findall(r"(\d+)\s*(?:months?|mos?)\b", text.lower())
    return max((int(m) / 12.0 for m in months), default=0.0)


def screen_resume_rule_based(resume_text: str, role: str, required_skills: list[str],
                             min_experience: float = 0.0) -> dict:
    low = resume_text.lower()
    matched = _skill_hits(low, required_skills)
    missing = [s for s in required_skills if s.strip().lower() not in _skill_hits(low, [s])]
    experience = _experience_years(resume_text)

    skill_ratio = len(matched) / len(required_skills) if required_skills else 1.0
    has_experience = experience >= min_experience

    score = round(100 * (0.65 * skill_ratio + (0.35 if has_experience else 0.0)) , 1)
    verdict = "Strong" if score >= 80 else "Moderate" if score >= 55 else "Weak"

    return {
        "score": score,
        "verdict": verdict,
        "matched_skills": matched,
        "missing_skills": missing,
        "experience_years": experience,
        "confidence": 0.85,
    }


_LLM_SYSTEM = (
    "You are an HR resume screener. Score the candidate against the role's "
    "required skills and minimum experience. Return JSON only: "
    "{\"score\":number(0-100),\"verdict\":\"Strong|Moderate|Weak\","
    "\"matchedSkills\":[string],\"missingSkills\":[string],"
    "\"experienceYears\":number}."
)


def screen_resume_llm(resume_text: str, role: str, required_skills: list[str],
                      min_experience: float = 0.0) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=config.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=config.llm_model(),
        temperature=0.0,
        messages=[
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": (
                f"Role: {role}\nRequired skills: {', '.join(required_skills)}\n"
                f"Min experience: {min_experience} years\n\nResume:\n{resume_text}"
            )},
        ],
    )
    raw = response.choices[0].message.content or ""
    try:
        payload = config.extract_json(raw)
        score = config.clamp_float(payload.get("score"), 0.0, 100.0)
        verdict = str(payload.get("verdict", "")).strip().capitalize()
        if verdict not in ("Strong", "Moderate", "Weak"):
            verdict = "Strong" if score >= 80 else "Moderate" if score >= 55 else "Weak"
        return {
            "score": round(score, 1),
            "verdict": verdict,
            "matched_skills": [str(s) for s in (payload.get("matchedSkills") or [])],
            "missing_skills": [str(s) for s in (payload.get("missingSkills") or [])],
            "experience_years": max(0.0, float(payload.get("experienceYears", 0.0))),
            "confidence": 0.9,
        }
    except (ValueError, TypeError):
        return {
            "score": 0.0, "verdict": "Weak",
            "matched_skills": [], "missing_skills": required_skills,
            "experience_years": 0.0, "confidence": 0.5,
        }


def screen_resume(resume_text: str, role: str, required_skills: list[str],
                  min_experience: float = 0.0) -> dict:
    if config.llm_available():
        return screen_resume_llm(resume_text, role, required_skills, min_experience)
    return screen_resume_rule_based(resume_text, role, required_skills, min_experience)