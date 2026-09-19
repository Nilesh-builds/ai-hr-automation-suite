"""Static checks for the repository used by CI and local dev.

- n8n workflow JSON exports must be valid, importable JSON with expected shape.
- No real credentials must be committed: only placeholder values allowed.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "workflows"

PLACEHOLDER_PATTERNS = [
    re.compile(r"your-[a-z-]+-credential-id"),
    re.compile(r"^your-[a-z-]+$", re.IGNORECASE),
    re.compile(r"your_google_sheet_id", re.IGNORECASE),
    re.compile(r"yours@example\.com", re.IGNORECASE),
]

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xoxb-[a-zA-Z0-9-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
]


def _is_placeholder(value: str) -> bool:
    return any(p.search(value) for p in PLACEHOLDER_PATTERNS)


def validate_workflow_json(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "nodes" in data and isinstance(data["nodes"], list), (
        f"{path.name}: missing 'nodes'"
    )
    assert "connections" in data, f"{path.name}: missing 'connections'"
    for node in data["nodes"]:
        assert "name" in node and "type" in node, f"{path.name}: node missing name/type"
    assert len(data["nodes"]) >= 2, f"{path.name}: implausibly small workflow"


def check_credentials(all_text: str) -> list[str]:
    problems = []
    for pattern in SECRET_PATTERNS:
        match = pattern.search(all_text)
        if match:
            problems.append(f"possible committed secret matched {pattern.pattern!r}")
    for line_no, line in enumerate(all_text.splitlines(), start=1):
        if re.search(r"(api[_-]?key|token|secret|password)\s*[:=]\s*[\"']?[A-Za-z0-9_-]{8,}",
                     line, re.IGNORECASE) and not _is_placeholder(line):
            problems.append(f"line {line_no}: plausible credential assignment")
    return problems


def run() -> int:
    problems: list[str] = []
    json_count = 0

    if WORKFLOW_DIR.exists():
        for path in sorted(WORKFLOW_DIR.glob("*.json")):
            json_count += 1
            try:
                validate_workflow_json(path)
            except (json.JSONDecodeError, AssertionError) as exc:
                problems.append(f"{path.name}: {exc}")

    for path in sorted(ROOT.rglob("*")):
        if "node_modules" in path.parts or ".git" in path.parts:
            continue
        if not path.is_file():
            continue
        if path.suffix in (".md", ".toml", ".txt", ".yaml", ".yml", ".gitignore"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        problems.extend(check_credentials(text))

    if problems:
        joined = "\n".join(f"  - {p}" for p in problems)
        print(f"FAILED static checks ({len(problems)})\n{joined}")
        return 1

    print(f"OK: {json_count} workflow JSON validated, no secrets or stray credentials found")
    return 0


if __name__ == "__main__":
    sys.exit(run())