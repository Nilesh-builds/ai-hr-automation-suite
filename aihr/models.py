"""Canonical data models for the HR automation suite."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Employee:
    employee_id: str
    first_name: str
    last_name: str
    email: str
    status: str = "Active"
    department: str = ""


@dataclass
class NewHire:
    hire_id: str
    first_name: str
    last_name: str
    email: str
    start_date: date
    department: str = ""
    onboarding_status: str = "Pending"


@dataclass
class LeaveBalance:
    employee_id: str
    annual_total: int = 20
    annual_used: int = 0
    sick_total: int = 8
    sick_used: int = 0
    casual_total: int = 6
    casual_used: int = 0


@dataclass
class LeaveRequest:
    request_id: str = ""
    employee_id: str = ""
    text: str = ""
    start_date: str = ""
    end_date: str = ""
    duration_days: int = 0
    leave_type: str = ""
    confidence: float = 0.0
    approved: bool = False
    reason: str = ""


@dataclass
class Feedback:
    feedback_id: str = ""
    employee_id: str = ""
    mood: str = ""
    sentiment_score: float = 0.0
    comments: str = ""
    urgency_level: str = "low"
    attrition_risk: str = "low"
    key_themes: list[str] = field(default_factory=list)
    needs_follow_up: bool = False
    submitted_at: str = ""


@dataclass
class Policy:
    policy_id: str
    title: str
    body: str
    category: str = "General"


@dataclass
class Candidate:
    candidate_id: str = ""
    name: str = ""
    resume_text: str = ""
    role: str = ""
    score: float = 0.0
    verdict: str = ""
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    experience_years: float = 0.0
    confidence: float = 0.0


@dataclass
class PolicyQuery:
    query_id: str = ""
    employee_id: str = ""
    question: str = ""
    answer: str = ""
    policy_ids: list[str] = field(default_factory=list)
    grounded: bool = False
    confidence: float = 0.0
    created_at: str = ""


@dataclass
class ChatMessage:
    intent: str = ""
    reply: str = ""
    confidence: float = 0.0