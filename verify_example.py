"""Run a real local AI check using only this project's synthetic example.

This command never selects DeepSeek or writes application records. A passing
sample is an integration check, not a model-quality benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path
import time

from local_ai_check import check_local_ai

ROOT = Path(__file__).resolve().parent


def verify():
    from domain import read_feedback, analyze, validate_analysis

    rows = read_feedback((ROOT / "examples/feedback.csv").read_text())
    result = analyze(rows, "Ollama (local)")
    validate_analysis(result, rows)
    assert len(result.findings) == len(rows), (
        "Every sample message must have exactly one finding."
    )
    urgent = [row["id"] for row in rows if "today" in row["message"].lower()]
    assert all(f.urgency == "high" for f in result.findings if f.source_id in urgent), (
        "Explicit same-day urgency was not recognized."
    )
    return {
        "messages": len(rows),
        "findings": len(result.findings),
        "exact_source_quotes": True,
    }


def main() -> int:
    started = time.monotonic()
    readiness = check_local_ai()
    result = {
        "passed": False,
        "model": readiness.get("model"),
        "context_tokens": readiness.get("context_tokens"),
    }
    if not readiness["ready"]:
        result["error"] = readiness["message"]
    else:
        try:
            result["checks"] = verify()
            result["passed"] = True
        except (AssertionError, ValueError) as exc:
            result["error"] = str(exc)
    result["elapsed_seconds"] = round(time.monotonic() - started, 2)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
