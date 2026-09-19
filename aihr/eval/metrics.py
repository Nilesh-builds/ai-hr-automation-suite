"""Scoring functions used across evaluation targets."""

from __future__ import annotations

from collections import Counter
from typing import Sequence


def accuracy(gold: Sequence[str], pred: Sequence[str]) -> float:
    n = len(gold) or 1
    hits = sum(1 for g, p in zip(gold, pred) if g == p)
    return round(hits / n, 4)


def classification_report(gold: Sequence[str], pred: Sequence[str]) -> dict:
    gold = list(gold)
    pred = list(pred)
    classes = sorted(set(gold) | set(pred))
    report: dict[str, dict] = {}
    for cls in classes:
        tp = sum(1 for g, p in zip(gold, pred) if p == cls and g == cls)
        fp = sum(1 for g, p in zip(gold, pred) if p == cls and g != cls)
        fn = sum(1 for g, p in zip(gold, pred) if g == cls and p != cls)
        precision = round(tp / (tp + fp), 4) if tp + fp else 0.0
        recall = round(tp / (tp + fn), 4) if tp + fn else 0.0
        f1 = round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0
        report[cls] = {"precision": precision, "recall": recall, "f1": f1}
    return report


def macro_f1(report: dict) -> float:
    if not report:
        return 0.0
    return round(sum(m["f1"] for m in report.values()) / len(report), 4)


def extraction_exact(gold_dates: Sequence[str], pred_dates: Sequence[str],
                     gold_durations: Sequence[int] | None = None,
                     pred_durations: Sequence[int] | None = None) -> dict:
    """Exact-match on dates plus optional duration match."""
    date_hits = sum(1 for g, p in zip(gold_dates, pred_dates) if str(g) == str(p))
    date_acc = round(date_hits / (len(gold_dates) or 1), 4)
    result = {"date_accuracy": date_acc, "n": len(gold_dates)}
    if gold_durations is not None and pred_durations is not None:
        dur_hits = sum(1 for g, p in zip(gold_durations, pred_durations) if int(g) == int(p))
        result["duration_accuracy"] = round(dur_hits / (len(gold_durations) or 1), 4)
    return result


def mean_absolute_error(gold: Sequence[float], pred: Sequence[float]) -> float:
    if not gold or not pred:
        return 0.0
    diffs = [abs(g - p) for g, p in zip(gold, pred)]
    return round(sum(diffs) / len(diffs), 4)


def rate(gold: Sequence[bool], pred: Sequence[bool]) -> float:
    if not gold:
        return 0.0
    hits = sum(1 for g, p in zip(gold, pred) if bool(g) == bool(p))
    return round(hits / len(gold), 4)