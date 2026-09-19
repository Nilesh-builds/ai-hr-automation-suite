"""Evaluation runner.

Walks every available labeled dataset, runs the chosen intelligence layer
(rule-based baseline or LLM), scores predictions, and writes a JSON report
under data/reports.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .. import config
from ..intelligence import leave as leave_mod
from ..intelligence import policy as policy_mod
from ..intelligence import resume as resume_mod
from ..intelligence import sentiment as sentiment_mod
from ..intelligence import whatsapp as whatsapp_mod
from . import datasets
from .metrics import (accuracy, classification_report, extraction_exact,
                      macro_f1, mean_absolute_error, rate)

REPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "reports"


def eval_leave(df) -> dict:
    preds = [leave_mod.parse_leave_rule_based(str(row["text"])) for _, row in df.iterrows()]
    gold_acc = extraction_exact(
        df["gold_start_date"].tolist(),
        [p["start_date"] for p in preds],
        df["gold_duration_days"].tolist(),
        [p["duration_days"] for p in preds],
    )
    type_acc = accuracy(df["gold_type"].tolist(), [p["leave_type"] for p in preds])
    return {
        "n": len(df),
        "extraction": gold_acc,
        "type_accuracy": type_acc,
    }


def eval_sentiment(df) -> dict:
    preds = [sentiment_mod.score_feedback_rule_based(
        str(row["mood"]), str(row["comments"])) for _, row in df.iterrows()]

    def bucket(score: float) -> str:
        return "negative" if score < -0.2 else "positive" if score > 0.2 else "neutral"

    gold_sent = df["gold_sentiment"].tolist()
    pred_sent = [bucket(p["sentiment_score"]) for p in preds]
    report = classification_report(gold_sent, pred_sent)
    return {
        "n": len(df),
        "sentiment_accuracy": accuracy(gold_sent, pred_sent),
        "sentiment_macro_f1": macro_f1(report),
        "sentiment_report": report,
        "urgency_accuracy": accuracy(
            df["gold_urgency"].tolist(), [p["urgency_level"] for p in preds]),
        "attrition_accuracy": accuracy(
            df["gold_attrition_risk"].tolist(), [p["attrition_risk"] for p in preds]),
    }


def eval_resume(df) -> dict:
    preds = []
    for _, row in df.iterrows():
        skills = [s.strip() for s in str(row["gold_required_skills"]).split(";")]
        preds.append(resume_mod.screen_resume_rule_based(
            str(row["resume_text"]), str(row["role"]), skills,
            float(row["gold_min_experience"]) if str(row["gold_min_experience"]) else 0.0,
        ))
    score_mae = mean_absolute_error(df["gold_score"].tolist(), [p["score"] for p in preds])
    verdict_acc = accuracy(df["gold_verdict"].tolist(), [p["verdict"] for p in preds])
    recall = sum(len(p["matched_skills"]) for p in preds) / max(
        1, sum(len(str(row["gold_required_skills"]).split(";")) for _, row in df.iterrows()))
    return {
        "n": len(df),
        "score_mae": score_mae,
        "verdict_accuracy": verdict_acc,
        "skill_recall": round(recall, 4),
    }


def eval_policy(df_policies, df_questions) -> dict:
    policies = []
    for _, row in df_policies.iterrows():
        from ..models import Policy

        policies.append(Policy(
            policy_id=str(row["policy_id"]),
            title=str(row["title"]),
            body=str(row["body"]),
            category=str(row["category"]),
        ))
    preds = [policy_mod.answer_policy_rule_based(str(row["question"]), policies)
             for _, row in df_questions.iterrows()]
    grounded_acc = rate(
        df_questions["gold_grounded"].astype(bool).tolist(),
        [p["grounded"] for p in preds],
    )
    gold_ids = df_questions["gold_policy_id"].tolist()
    pred_ids = [p["policy_ids"][0] if p["policy_ids"] else "none" for p in preds]
    retrieval_acc = accuracy(gold_ids, pred_ids)
    return {
        "n": len(df_questions),
        "grounded_accuracy": grounded_acc,
        "retrieval_accuracy": retrieval_acc,
    }


def eval_chat(df) -> dict:
    preds = [whatsapp_mod.route_intent_rule_based(str(row["message"])).intent
             for _, row in df.iterrows()]
    report = classification_report(df["gold_intent"].tolist(), preds)
    return {
        "n": len(df),
        "intent_accuracy": accuracy(df["gold_intent"].tolist(), preds),
        "intent_macro_f1": macro_f1(report),
        "intent_report": report,
    }


def run_all() -> dict:
    report: dict = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "rule_baseline" if not config.llm_available() else "llm",
        "targets": {},
    }
    available = datasets.require_available()
    if "leave_requests" in available:
        report["targets"]["leave_parsing"] = eval_leave(datasets.leave_requests())
    if "employee_feedback" in available:
        report["targets"]["sentiment"] = eval_sentiment(datasets.feedback())
    if "resumes" in available:
        report["targets"]["resume_screening"] = eval_resume(datasets.resumes())
    if "policies" in available and "policy_questions" in available:
        report["targets"]["policy_qa"] = eval_policy(
            datasets.policies(), datasets.policy_questions())
    if "chat_messages" in available:
        report["targets"]["chat_intent"] = eval_chat(datasets.chat_messages())
    return report


def write_report(report: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "eval_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AIHR evaluation harness")
    parser.add_argument("--print", action="store_true", help="print report to stdout")
    args = parser.parse_args()

    report = run_all()
    path = write_report(report)
    if args.print:
        print(json.dumps(report, indent=2))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())