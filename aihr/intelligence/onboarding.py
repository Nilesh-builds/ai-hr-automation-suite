"""Onboarding task scheduler.

Pure logic: given a hire's start date, compute which onboarding tasks are due
on or before today. Mirrors the employee-onboarding n8n workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

WELCOME_EMAIL_LEAD_DAYS = 14
IT_SETUP_LEAD_DAYS = 7
DAY1_CHECKLIST_LEAD_DAYS = 1


@dataclass(frozen=True)
class OnboardingTask:
    task_id: str
    name: str
    due_before_start_days: int
    owner: str


ONBOARDING_TASKS = (
    OnboardingTask("welcome-email", "Send welcome email", WELCOME_EMAIL_LEAD_DAYS, "HR"),
    OnboardingTask("it-setup", "Request IT setup (laptop, accounts)", IT_SETUP_LEAD_DAYS, "IT"),
    OnboardingTask("day1-checklist", "Prepare day-1 checklist", DAY1_CHECKLIST_LEAD_DAYS, "People Ops"),
)


def tasks_due(start_date: date, today: date | None = None) -> list[OnboardingTask]:
    """Tasks whose due window has opened and close at or after today."""
    today = today or date.today()
    days_until = (start_date - today).days
    due = []
    for task in ONBOARDING_TASKS:
        if days_until <= task.due_before_start_days:
            due.append(task)
    return due


def onboarding_progress(start_date: date, completed_ids: set[str],
                        today: date | None = None) -> dict:
    tasks = tasks_due(start_date, today)
    done = [t for t in tasks if t.task_id in completed_ids]
    pending = [t for t in tasks if t.task_id not in completed_ids]
    total = len(tasks)
    return {
        "total": total,
        "completed": len(done),
        "pending": len(pending),
        "progress": round(len(done) / total, 2) if total else 1.0,
        "pending_tasks": [t.name for t in pending],
    }