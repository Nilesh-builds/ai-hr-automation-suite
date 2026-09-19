"""WhatsApp HR chatbot intent routing.

Classifies an inbound message into a supported intent using keyword rules,
then picks the appropriate reply template. No API required by default.
"""

from __future__ import annotations

import re

from .. import config
from ..models import ChatMessage

_INTENT_PATTERNS: dict[str, list[str]] = {
    "leave_balance": ["leave balance", "leave-balance", "balance", "days left",
                      "days remaining", "annual days", "leave i have left",
                      "leave remaining", "how many days"],
    "policy": ["policy", "rule", "procedure", "guideline", "allowed", "is it ok"],
    "payslip": ["payslip", "salary slip", "pay stub", "payslips", "salary ticket"],
    "attendance": ["attendance", "late", "punch", "clock in", "time off",
                   "mark my attendance"],
    "hr_contact": ["contact hr", "talk to hr", "hr rep", "reach hr", "emergency",
                   "someone from hr", "connect me with", "hr person"],
}

GREETINGS = ("hi", "hello", "hey", "namaste", "good morning", "good afternoon",
             "good evening")


def greet(text: str) -> bool:
    low = text.lower().strip()
    return low in GREETINGS or low.split()[0] in GREETINGS


def route_intent_rule_based(message: str) -> ChatMessage:
    low = message.lower()
    if greet(low):
        return ChatMessage(
            intent="greeting",
            reply="Hello! I'm the HR assistant. Ask me about leave balance, policies, "
                  "or payslips — or type 'contact HR' to reach a person.",
            confidence=0.95,
        )

    scores = {
        intent: sum(1 for pattern in patterns if pattern in low)
        for intent, patterns in _INTENT_PATTERNS.items()
    }
    intent, score = max(scores.items(), key=lambda pair: pair[1])
    confidence = 0.9 if score else 0.0

    replies = {
        "leave_balance": "Please share your employee ID and I will look up your leave balance.",
        "policy": "Sure — tell me which policy you'd like to know about and I'll pull it up.",
        "payslip": "I can help with payslips. Please share your employee ID and the month you need.",
        "attendance": "I can check attendance records. Please share your employee ID.",
        "hr_contact": "An HR representative will reach out to you shortly. For urgent matters call the HR desk.",
    }
    if not score:
        return ChatMessage(
            intent="unknown",
            reply="I'm not sure about that. Try asking about leave, policies, or payslips, "
                  "or type 'contact HR'.",
            confidence=confidence,
        )
    return ChatMessage(intent=intent, reply=replies[intent], confidence=confidence)


def route_intent(message: str) -> ChatMessage:
    if config.llm_available():
        return route_intent_llm(message)
    return route_intent_rule_based(message)


def route_intent_llm(message: str) -> ChatMessage:
    """LLM fallback kept deliberately thin; rule routing is the default."""
    return route_intent_rule_based(message)