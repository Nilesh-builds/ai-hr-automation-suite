"""Leave request parsing.

Rule-based baseline extracts dates, duration, and leave type from plain-text
requests without any API. An LLM path is available for free-form phrasing.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from .. import config

LEAVE_TYPES = ("annual", "sick", "casual", "personal", "unpaid")

_DATE_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{2})[/.-](\d{2})[/.-](\d{4})"),
    re.compile(r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
               r"[\s,]*(\d{4})", re.IGNORECASE),
]

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _coerce_dates(value: str) -> list[date]:
    found: list[date] = []
    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(value):
            try:
                if pattern == _DATE_PATTERNS[0]:
                    found.append(date(int(match.group(1)), int(match.group(2)), int(match.group(3))))
                elif pattern == _DATE_PATTERNS[1]:
                    found.append(date(int(match.group(3)), int(match.group(2)), int(match.group(1))))
                else:
                    found.append(date(int(match.group(3)), _MONTHS[match.group(2).lower()], int(match.group(1))))
            except ValueError:
                continue
    return found


def _day_names(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).strftime("%A")


def _parse_day_relative(text: str) -> date | None:
    low = text.lower()
    today = date.today()
    specs = {
        "today": 0,
        "tomorrow": 1,
        "day after tomorrow": 2,
    }
    for label, offset in specs.items():
        if label in low:
            return today + timedelta(days=offset)
    if "next monday" in low:
        return today + timedelta(days=(7 - today.weekday()) % 7 or 7)
    if "next friday" in low:
        return today + timedelta(days=(4 - today.weekday()) % 7 or 7)
    return None


def _detect_type(text: str) -> str:
    low = text.lower()
    has_word = lambda *words: any(re.search(rf"\b{w}\b", low) for w in words)
    if has_word("annual leave", "annual"):
        return "annual"
    if has_word("sick leave", "medical leave", "sick", "ill", "fever", "surgery", "doctor"):
        return "sick"
    if has_word("casual leave", "casual"):
        return "casual"
    if has_word("unpaid leave", "unpaid", "without pay"):
        return "unpaid"
    if has_word("personal", "family", "marriage", "wedding", "move"):
        return "personal"
    return "annual"


def parse_leave_rule_based(text: str) -> dict:
    """Deterministic leave parser with a confidence estimate."""
    dates = list(_coerce_dates(text))
    relative = _parse_day_relative(text)
    if relative:
        dates.append(relative)
    dates = list(dict.fromkeys(dates))
    if not dates:
        return {
            "parsed": False, "start_date": "", "end_date": "",
            "duration_days": 0, "leave_type": _detect_type(text),
            "confidence": 0.0, "text": text,
        }

    start = min(dates)
    end = max(dates)
    duration = (end - start).days + 1

    days_exp = re.search(r"(\d+)\s*(?:days?|working days?)", text, re.IGNORECASE)
    if days_exp and duration == 1:
        duration = int(days_exp.group(1))
        end = start + timedelta(days=duration - 1)

    if " to " in text.lower() or " till " in text.lower() or " until " in text.lower():
        confidence = 0.95 if duration >= 1 else 0.7
    else:
        confidence = 0.8 if duration == 1 else 0.7

    return {
        "parsed": True,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "duration_days": duration,
        "leave_type": _detect_type(text),
        "confidence": round(confidence, 2),
        "text": text,
    }


_LLM_SYSTEM = (
    "Extract leave request details from the employee message. "
    "Return JSON only: {\"start_date\":\"YYYY-MM-DD\",\"end_date\":\"YYYY-MM-DD\","
    "\"duration_days\":int,\"leave_type\":\"annual|sick|casual|personal|unpaid\","
    "\"parsed\":bool}. Use the most recent plausible dates. "
    "If dates cannot be determined set parsed to false."
)


def parse_leave_llm(text: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=config.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=config.llm_model(),
        temperature=0.0,
        messages=[
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": text},
        ],
    )
    raw = response.choices[0].message.content or ""
    try:
        payload = config.extract_json(raw)
        parsed = bool(payload.get("parsed", True))
        leave_type = config.validated_str(payload.get("leave_type"), "".join(LEAVE_TYPES), "annual")
        start = str(payload.get("start_date", ""))
        end = str(payload.get("end_date", ""))
        duration = max(0, int(payload.get("duration_days", 0)))
        return {
            "parsed": parsed and bool(start),
            "start_date": start,
            "end_date": end or start,
            "duration_days": duration,
            "leave_type": leave_type,
            "confidence": 0.95 if parsed else 0.5,
            "text": text,
        }
    except (ValueError, TypeError):
        return {
            "parsed": False, "start_date": "", "end_date": "",
            "duration_days": 0, "leave_type": "annual", "confidence": 0.5,
            "text": text,
        }


def parse_leave(text: str) -> dict:
    if config.llm_available():
        return parse_leave_llm(text)
    return parse_leave_rule_based(text)