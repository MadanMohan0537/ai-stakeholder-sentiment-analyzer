from pathlib import Path
import pytest
from domain import analyze, read_feedback, validate_analysis


def sample():
    return read_feedback(
        (Path(__file__).parents[1] / "examples/feedback.csv").read_text()
    )


def test_mixed_sentiment_retains_both_topics():
    result = analyze(sample(), "Offline demo")
    assert result.findings[0].sentiment == "mixed"
    assert set(result.findings[0].topics) == {"quality", "timeline"}
    assert result.findings[2].urgency == "high"
    assert result.findings[-1].sentiment == "unclear"


def test_evidence_must_exist_in_original_message():
    rows = sample()
    result = analyze(rows, "Offline demo")
    result.findings[0].evidence = "Fabricated quotation"
    with pytest.raises(ValueError, match="absent"):
        validate_analysis(result, rows)


def test_omitted_or_duplicate_rows_rejected():
    rows = sample()
    result = analyze(rows, "Offline demo")
    result.findings.pop()
    with pytest.raises(ValueError, match="exactly one"):
        validate_analysis(result, rows)


def test_negation():
    row = {
        "id": "a",
        "date": "2026-10-03",
        "stakeholder": "Client",
        "message": "I am not happy with the quality.",
    }
    assert analyze([row], "Offline demo").findings[0].sentiment == "negative"


def test_invalid_source_date():
    with pytest.raises(ValueError):
        read_feedback("id,date,stakeholder,message\na,yesterday,Client,Hello")
