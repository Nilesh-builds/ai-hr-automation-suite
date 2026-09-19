"""Evaluation harness — the evidence layer for every AI-powered workflow.

Each labeled dataset compares a model output against a ground truth. The
harness works headless (rule-based baselines) and upgrades to LLM scoring
when OPENAI_API_KEY is present.
"""

from .. import config