"""Labeled evaluation datasets.

Datasets live as CSV files under data/labeled so they can be versioned,
inspected, and extended without touching code.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import load_env

ROOT = Path(__file__).resolve().parents[2]
LABELED_DIR = ROOT / "data" / "labeled"

load_env()


def _load(name: str) -> pd.DataFrame:
    path = LABELED_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"missing labeled dataset: {path}")
    return pd.read_csv(path)


def leave_requests() -> pd.DataFrame:
    return _load("leave_requests")


def feedback() -> pd.DataFrame:
    return _load("employee_feedback")


def resumes() -> pd.DataFrame:
    return _load("resumes")


def policies() -> pd.DataFrame:
    return _load("policies")


def policy_questions() -> pd.DataFrame:
    return _load("policy_questions")


def chat_messages() -> pd.DataFrame:
    return _load("chat_messages")


def require_available() -> list[str]:
    available = []
    for name in ("leave_requests", "employee_feedback", "resumes",
                 "policies", "policy_questions", "chat_messages"):
        if (LABELED_DIR / f"{name}.csv").exists():
            available.append(name)
    return available