from pathlib import Path

import pandas as pd

from aihr.eval import datasets
from aihr.eval.metrics import accuracy, classification_report, extraction_exact, macro_f1


def test_datasets_loadable():
    assert (datasets.LABELED_DIR / "leave_requests.csv").exists()
    df = datasets.leave_requests()
    assert len(df) >= 10
    assert {"text", "gold_start_date", "gold_type"} <= set(df.columns)


def test_accuracy_basic():
    assert accuracy(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert accuracy(["a", "b"], ["a", "a"]) == 0.5


def test_classification_report_and_macro_f1():
    report = classification_report(["a", "b", "b"], ["a", "a", "b"])
    assert "a" in report and "b" in report
    f1 = macro_f1(report)
    assert 0.0 <= f1 <= 1.0


def test_extraction_exact():
    result = extraction_exact(
        ["2026-08-12", "2026-08-13"],
        ["2026-08-12", "2026-08-20"],
        [2, 3],
        [2, 5],
    )
    assert result["date_accuracy"] == 0.5
    assert result["duration_accuracy"] == 0.5


def test_unrelated_csv_columns_present():
    fb = datasets.feedback()
    assert "gold_sentiment" in fb.columns
    assert "gold_urgency" in fb.columns