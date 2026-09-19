import tempfile
from pathlib import Path

from aihr.models import Employee, NewHire, Policy
from aihr.store import HRStore


def test_store_summary_empty(tmp_path: Path):
    store = HRStore(tmp_path / "test.db")
    assert store.summary()["employees"] == 0


def test_upsert_employee_and_count(tmp_path: Path):
    store = HRStore(tmp_path / "test.db")
    store.upsert_employee(Employee("E1", "A", "B", "a@x.io", "Active"))
    assert store.employee_count() == 1


def test_roundtrip_hire(tmp_path: Path):
    from datetime import date, timedelta

    store = HRStore(tmp_path / "test.db")
    hire = NewHire("H1", "A", "B", "a@x.io", date.today() + timedelta(days=5))
    store.upsert_new_hire(hire)
    df = store.upcoming_hires()
    assert len(df) == 1
    assert df.iloc[0]["hire_id"] == "H1"


def test_leave_and_feedback_insert(tmp_path: Path):
    store = HRStore(tmp_path / "test.db")
    store.insert_leave_request({"text": "annual leave 2026-10-01 to 2026-10-03",
                                "start_date": "2026-10-01", "end_date": "2026-10-03",
                                "duration_days": 3, "leave_type": "annual",
                                "confidence": 0.9})
    store.insert_feedback({"mood": "good", "comments": "all good", "sentiment_score": 0.5,
                           "urgency_level": "low", "attrition_risk": "low",
                           "key_themes": ["culture"], "needs_follow_up": False})
    assert len(store.leave_requests()) == 1
    assert len(store.feedback_rows()) == 1


def test_policy_upsert(tmp_path: Path):
    store = HRStore(tmp_path / "test.db")
    store.upsert_policy(Policy("P1", "Title", "Body", "General"))
    assert store.list_policies()[0].policy_id == "P1"