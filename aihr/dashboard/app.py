"""HR analytics dashboard — Streamlit app.

Run locally:  streamlit run aihr/dashboard/app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ..config import load_env
from ..eval.runner import run_all, write_report
from ..store import HRStore

load_env()

st.set_page_config(page_title="AIHR Analytics", page_icon="💼", layout="wide")


@st.cache_resource
def get_store() -> HRStore:
    store = HRStore()
    if store.employee_count() == 0:
        from ..seed import seed

        seed()
    return store


@st.cache_data(ttl=300)
def load_data():
    store = get_store()
    return {
        "summary": store.summary(),
        "feedback": store.feedback_rows(),
        "leave": store.leave_requests(),
        "candidates": store.candidates(),
        "hires": store.upcoming_hires(),
        "queries": store.policy_queries(),
    }


@st.cache_data(ttl=300)
def load_eval_report():
    report_path = ROOT / "data" / "reports" / "eval_report.json"
    if report_path.exists():
        return json.loads(report_path.read_text())
    return None


data = load_data()
eval_report = load_eval_report()

st.markdown("## 💼 AI HR Automation Suite — Analytics")

store = get_store()

tab_overview, tab_sentiment, tab_leave, tab_resume, tab_policy, tab_eval = st.tabs(
    ["Overview", "7 Sentiment", "Leave", "Resume", "Policy QA", "7 Eval"]
)

with tab_overview:
    summary = data["summary"]
    cols = st.columns(6)
    metrics = [
        ("Employees", summary.get("employees", 0), "👥"),
        ("Upcoming Hires", summary.get("new_hires", 0), "📈"),
        ("Leave Requests", summary.get("leave_requests", 0), "🗓️"),
        ("Feedback Rows", summary.get("feedback", 0), "💭"),
        ("Candidates", summary.get("candidates", 0), "📄"),
        ("Policy Queries", summary.get("policy_queries", 0), "❓"),
    ]
    for col, (label, value, icon) in zip(cols, metrics):
        col.metric(f"{icon} {label}", value)

    st.subheader("Sentiment Trend (last 6 weeks)")
    fb = data["feedback"].copy()
    if not fb.empty and "submitted_at" in fb:
        fb["week"] = pd.to_datetime(fb["submitted_at"]).dt.to_period("W").astype(str)
        weekly = fb.groupby("week")["sentiment_score"].mean().reset_index()
        fig = px.line(weekly, x="week", y="sentiment_score", markers=True)
        st.plotly_chart(fig, use_container_width=True)

with tab_sentiment:
    fb = data["feedback"].copy()
    if fb.empty:
        st.info("No feedback data yet.")
    else:
        cols = st.columns(3)
        cols[0].metric("Avg Sentiment", f"{fb['sentiment_score'].mean():.2f}")
        cols[1].metric("High Urgency", int((fb["urgency_level"] == "high").sum()))
        cols[2].metric("Attrition Risk", int((fb["attrition_risk"] == "high").sum()))

        st.subheader("Sentiment Score by Employee")
        fig = px.histogram(fb, x="sentiment_score", nbins=12)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Key Themes distribution")
        themes = fb["key_themes"].dropna().str.split(", ").explode().value_counts()
        fig = px.bar(x=themes.index, y=themes.values, labels={"x": "theme", "y": "count"})
        st.plotly_chart(fig, use_container_width=True)

with tab_leave:
    lv = data["leave"].copy()
    if lv.empty:
        st.info("No leave requests yet.")
    else:
        cols = st.columns(3)
        cols[0].metric("Requests", len(lv))
        cols[1].metric("Avg Duration (days)", f"{lv['duration_days'].mean():.1f}")
        cols[2].metric("Approved", int(lv["approved"].sum()))

        st.subheader("Leave by type")
        fig = px.pie(lv, names="leave_type", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Recent requests")
        st.dataframe(lv[["employee_id", "start_date", "end_date", "duration_days",
                         "leave_type", "approved", "reason"]].sort_values(
            "start_date", ascending=False, ignore_index=True), use_container_width=True)

with tab_resume:
    cand = data["candidates"].copy()
    if cand.empty:
        st.info("No candidates screened yet.")
    else:
        st.subheader("Candidate scores")
        fig = px.bar(cand.sort_values("score"), x="name", y="score",
                     color="verdict")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(cand[["candidate_id", "name", "role", "score", "verdict",
                           "matched_skills", "missing_skills", "experience_years"]],
                     use_container_width=True)

with tab_policy:
    qs = data["queries"].copy()
    if qs.empty:
        st.info("No policy queries yet.")
    else:
        cols = st.columns(2)
        cols[0].metric("Grounded", int(qs["grounded"].sum()))
        cols[1].metric("Avg Confidence", f"{qs['confidence'].mean():.2f}")
        st.dataframe(qs[["employee_id", "question", "policy_ids", "grounded",
                         "confidence", "created_at"]], use_container_width=True)

with tab_eval:
    if eval_report is None:
        st.info("No eval report yet. Run `python -m aihr.eval.runner` first.")
    else:
        st.subheader(f"Evaluation Report — mode: {eval_report['mode']}")
        targets = eval_report.get("targets", {})

        def target_metrics(name: str) -> list[tuple[str, str]]:
            cfg = {
                "leave_parsing": [("date_accuracy", "Date Acc"),
                                  ("duration_accuracy", "Duration Acc"),
                                  ("type_accuracy", "Type Acc")],
                "sentiment": [("sentiment_accuracy", "Sentiment Acc"),
                              ("urgency_accuracy", "Urgency Acc"),
                              ("attrition_accuracy", "Attrition Acc")],
                "resume_screening": [("verdict_accuracy", "Verdict Acc"),
                                     ("score_mae", "Score MAE")],
                "policy_qa": [("grounded_accuracy", "Grounded Acc"),
                              ("retrieval_accuracy", "Retrieval Acc")],
                "chat_intent": [("intent_accuracy", "Intent Acc")],
            }
            return cfg.get(name, [])

        names = list(targets.keys())
        if not names:
            st.info("No evaluation targets found.")
        else:
            shown = st.columns(min(len(names), 5))
            for col, name in zip(shown, names):
                payload = targets[name]
                lines = "\n".join(
                    f"{label}: {payload.get(metric, '-')}"
                    for metric, label in target_metrics(name)
                )
                col.caption(f"**{name.replace('_', ' ').title()}**\n\n{lines}")

        for name, payload in targets.items():
            st.divider()
            st.subheader(name.replace("_", " ").title())
            st.json(payload)

    if st.button("Re-run evaluation"):
        report = run_all()
        write_report(report)
        st.cache_data.clear()
        st.success("Evaluation re-run. Refresh to see updated report.")