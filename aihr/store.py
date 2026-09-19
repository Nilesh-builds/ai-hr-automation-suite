"""SQLite persistence layer.

Replaces the raw Google Sheets dependency with a real, queryable database.
The dashboard and evaluation harness consume data through this store.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd

from .models import Employee, NewHire, Policy


class HRStore:
    def __init__(self, db_path: str | Path = "data/db/aihr.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS employees (
                    employee_id TEXT PRIMARY KEY,
                    first_name TEXT, last_name TEXT, email TEXT,
                    status TEXT, department TEXT
                );
                CREATE TABLE IF NOT EXISTS new_hires (
                    hire_id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT,
                    email TEXT, start_date TEXT, department TEXT, onboarding_status TEXT
                );
                CREATE TABLE IF NOT EXISTS leave_requests (
                    request_id TEXT PRIMARY KEY, employee_id TEXT,
                    text TEXT, start_date TEXT, end_date TEXT,
                    duration_days REAL, leave_type TEXT,
                    confidence REAL, approved INTEGER DEFAULT 0, reason TEXT
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY, employee_id TEXT, mood TEXT,
                    sentiment_score REAL, comments TEXT,
                    urgency_level TEXT, attrition_risk TEXT, key_themes TEXT,
                    needs_follow_up INTEGER, submitted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS policies (
                    policy_id TEXT PRIMARY KEY, title TEXT, body TEXT, category TEXT
                );
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY, name TEXT, resume_text TEXT,
                    role TEXT, score REAL, verdict TEXT,
                    matched_skills TEXT, missing_skills TEXT,
                    experience_years REAL, confidence REAL
                );
                CREATE TABLE IF NOT EXISTS policy_queries (
                    query_id TEXT PRIMARY KEY, employee_id TEXT, question TEXT,
                    answer TEXT, policy_ids TEXT, grounded INTEGER,
                    confidence REAL, created_at TEXT
                );
                """
            )

    # --- employees ---
    def upsert_employee(self, emp: Employee) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO employees
                   (employee_id, first_name, last_name, email, status, department)
                   VALUES (?,?,?,?,?,?)""",
                (emp.employee_id, emp.first_name, emp.last_name,
                 emp.email, emp.status, emp.department),
            )

    def active_employees(self) -> pd.DataFrame:
        with self.connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM employees WHERE status = 'Active'", conn
            )

    def employee_count(self) -> int:
        with self.connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM employees WHERE status='Active'").fetchone()[0]

    # --- new hires / onboarding ---
    def upsert_new_hire(self, hire: NewHire) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO new_hires
                   (hire_id, first_name, last_name, email, start_date, department, onboarding_status)
                   VALUES (?,?,?,?,?,?,?)""",
                (hire.hire_id, hire.first_name, hire.last_name, hire.email,
                 hire.start_date.isoformat(), hire.department, hire.onboarding_status),
            )

    def update_hire_status(self, hire_id: str, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE new_hires SET onboarding_status=? WHERE hire_id=?", (status, hire_id)
            )

    def upcoming_hires(self) -> pd.DataFrame:
        with self.connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM new_hires WHERE onboarding_status != 'Completed' ORDER BY start_date",
                conn,
            )

    # --- leave ---
    def insert_leave_request(self, request: dict) -> str:
        import uuid

        request_id = request.get("request_id") or f"LV-{uuid.uuid4().hex[:10]}"
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO leave_requests
                   (request_id, employee_id, text, start_date, end_date,
                    duration_days, leave_type, confidence, approved, reason)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (request_id, request.get("employee_id", ""), request.get("text", ""),
                 request.get("start_date", ""), request.get("end_date", ""),
                 request.get("duration_days", 0), request.get("leave_type", ""),
                 request.get("confidence", 0.0), int(request.get("approved", False)),
                 request.get("reason", "")),
            )
        return request_id

    def leave_requests(self) -> pd.DataFrame:
        with self.connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM leave_requests ORDER BY start_date DESC", conn
            )

    # --- feedback ---
    def insert_feedback(self, fb: dict) -> str:
        import uuid

        feedback_id = fb.get("feedback_id") or f"FB-{uuid.uuid4().hex[:10]}"
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO feedback
                   (feedback_id, employee_id, mood, sentiment_score, comments,
                    urgency_level, attrition_risk, key_themes, needs_follow_up, submitted_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (feedback_id, fb.get("employee_id", ""), fb.get("mood", ""),
                 fb.get("sentiment_score", 0.0), fb.get("comments", ""),
                 fb.get("urgency_level", "low"), fb.get("attrition_risk", "low"),
                 ", ".join(fb.get("key_themes", [])), int(fb.get("needs_follow_up", False)),
                 fb.get("submitted_at", "")),
            )
        return feedback_id

    def feedback_rows(self) -> pd.DataFrame:
        with self.connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM feedback ORDER BY submitted_at DESC", conn
            )

    def sentiment_distribution(self) -> pd.Series:
        df = self.feedback_rows()
        if df.empty:
            return pd.Series(dtype=float)
        return df["sentiment_score"].round(1).value_counts().sort_index()

    # --- policies ---
    def upsert_policy(self, policy: Policy) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO policies (policy_id, title, body, category)
                   VALUES (?,?,?,?)""",
                (policy.policy_id, policy.title, policy.body, policy.category),
            )

    def list_policies(self) -> list[Policy]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM policies").fetchall()
        return [Policy(row["policy_id"], row["title"], row["body"], row["category"]) for row in rows]

    # --- candidates ---
    def insert_candidate(self, cand: dict) -> str:
        import uuid

        candidate_id = cand.get("candidate_id") or f"CA-{uuid.uuid4().hex[:10]}"
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO candidates
                   (candidate_id, name, resume_text, role, score, verdict,
                    matched_skills, missing_skills, experience_years, confidence)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (candidate_id, cand.get("name", ""), cand.get("resume_text", ""),
                 cand.get("role", ""), cand.get("score", 0.0), cand.get("verdict", ""),
                 ", ".join(cand.get("matched_skills", [])),
                 ", ".join(cand.get("missing_skills", [])),
                 cand.get("experience_years", 0.0), cand.get("confidence", 0.0)),
            )
        return candidate_id

    def candidates(self) -> pd.DataFrame:
        with self.connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM candidates ORDER BY score DESC", conn
            )

    # --- policy queries ---
    def insert_policy_query(self, pq: dict) -> str:
        import uuid

        query_id = pq.get("query_id") or f"PQ-{uuid.uuid4().hex[:10]}"
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO policy_queries
                   (query_id, employee_id, question, answer, policy_ids,
                    grounded, confidence, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (query_id, pq.get("employee_id", ""), pq.get("question", ""),
                 pq.get("answer", ""), ", ".join(pq.get("policy_ids", [])),
                 int(pq.get("grounded", False)), pq.get("confidence", 0.0),
                 pq.get("created_at", "")),
            )
        return query_id

    def policy_queries(self) -> pd.DataFrame:
        with self.connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM policy_queries ORDER BY created_at DESC", conn
            )

    # --- summary helpers ---
    def summary(self) -> dict:
        with self.connect() as conn:
            counts = {
                name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in (
                    "employees", "new_hires", "leave_requests", "feedback",
                    "policies", "candidates", "policy_queries",
                )
            }
        return counts