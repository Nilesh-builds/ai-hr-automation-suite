# Architecture

This section describes the structure of the AI HR Automation Suite after the
Python-first rebuild.

## High-level layout

```
workflows/        n8n workflow exports (kept as importable reference)
├── ai-policy-qa-bot.json
├── ai-resume-screener-ranker.json
├── employee-onboarding-automation.json
├── employee-sentiment-feedback-analyzer.json
├── leave-management-system.json
└── whatsapp-hr-chatbot.json

aihr/             Python package — the core engine
├── config.py        LLM/credential configuration (optional; works keyless)
├── models.py        canonical dataclasses for all entities
├── store.py         SQLite persistence layer + query helpers
├── seed.py          synthetic demo-data generator
├── intelligence/    rule-based baselines with optional LLM upgrade paths
│   ├── leave.py         leave-request parsing
│   ├── sentiment.py     employee feedback scoring
│   ├── resume.py        resume screener/ranker
│   ├── policy.py        grounded policy Q&A (retrieval)
│   ├── onboarding.py    onboarding task scheduler (pure logic)
│   └── whatsapp.py      chatbot intent routing
├── eval/           evaluation harness — the evidence layer
│   ├── datasets.py  labeled dataset loaders (CSV)
│   ├── metrics.py   accuracy, macro-F1, extraction/MAE helpers
│   └── runner.py    end-to-end evaluation -> data/reports/eval_report.json
└── dashboard/      Streamlit HR analytics dashboard

data/
├── labeled/         versioned labeled datasets (leave, sentiment, resumes,
│                    policies, policy Q&A, chat intents)
├── db/              generated SQLite files (gitignored)
└── reports/         generated evaluation reports (gitignored)

scripts/
└── static_checks.py CI static validation (workflow JSON + credential hygiene)

tests/             pytest suite
```

## Design decisions

### Python-first, n8n as reference
The original repo was six n8n workflow JSON exports. Workflows are powerful
glue but hard to test and impossible to benchmark. Core logic now lives in
`aihr/intelligence/` as deterministic rule-based baselines. Each module also
implements an LLM upgrade path used automatically when an API key is present in
the environment. The n8n exports are retained under `workflows/` so the suite
can still be run end-to-end inside n8n.

### Evaluation is not optional
Every AI-facing component has a labeled dataset under `data/labeled/` and a
scoring function in the harness:

| Target                 | Dataset            | Metrics                                   |
| :--------------------- | :----------------- | :---------------------------------------- |
| Leave request parsing  | leave_requests     | date/duration accuracy, type accuracy     |
| Employee sentiment     | employee_feedback  | sentiment accuracy, macro-F1, urgency, attrition |
| Resume screening       | resumes            | verdict accuracy, score MAE, skill recall |
| Policy Q&A             | policies + policy_questions | retrieval accuracy, grounded accuracy |
| Chat intent routing    | chat_messages      | intent accuracy, macro-F1                 |

The baseline numbers are intentionally honest: a couple of hard examples remain
that the rule baselines miss, which is exactly what the LLM layer improves on.
Run the harness with `python -m aihr.eval.runner`.

### Retrieval-grounded policy answers
Policy Q&A never lets the model improvise. The retrieval step (`retrieve_policies`)
scores policies by term overlap and the answer is built from the retrieved
passage. The LLM path is groundedness-checked: `grounded` is only true if the
cited policy id exists in the corpus. This prevents silent hallucination.

### Validation and fallbacks
LLM JSON outputs are parsed defensively with fallbacks, so a malformed or
rate-limited response degrades to a safe default instead of crashing a run.
See `config.extract_json`, `config.validated_str`, and each module's `*_llm`
function.

### Persistence
`HRStore` (SQLite) replaces Google Sheets as the system of record for new work:
employees, hires, leave requests, feedback, candidates, policies, and policy
queries all get normalized tables. `aihr/seed.py` populates a realistic demo
dataset.

### Credential hygiene
Secrets never ship in the repo. `.env.example` documents environment
variables; `scripts/static_checks.py` (run in CI) validates every workflow JSON
and scans the tree for accidentally committed keys.

## Data flow

```
labeled CSV data ──┐
                  ├──> intelligence (baseline or LLM) ──> eval metrics ──> report JSON
n8n workflow ────►┘                                     └───────────────> dashboard
raw events ──> HRStore (SQLite) ──> analytics queries ──> Streamlit tabs
```

## CI

GitHub Actions pipeline (`.github/workflows/ci.yml`):

1. Static checks: workflow JSON validity + credential scan.
2. `pytest` — the full unit suite runs keyless.
3. Rule-baseline evaluation — regenerates `data/reports/eval_report.json`.