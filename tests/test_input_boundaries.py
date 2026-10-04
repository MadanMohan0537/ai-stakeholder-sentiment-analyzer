"""Reject ambiguous dates and lossy CSV imports before calculations or storage."""

from datetime import date

import pytest

from common import iso_date, parse_csv


@pytest.mark.parametrize("value", ["2026-1-5", date(2026, 10, 5)])
def test_dates_require_literal_calendar_format(value):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        iso_date(value)


def test_valid_leap_day_and_quoted_csv_remain_supported():
    assert iso_date("2028-02-29") == date(2028, 2, 29)
    assert parse_csv('\ufeffid,note\nA,"Hello, team"', {"id", "note"}) == [
        {"id": "A", "note": "Hello, team"}
    ]


@pytest.mark.parametrize("text", ["id,id\nA,B", "id,\nA,B", 'id,note\nA,"unterminated'])
def test_ambiguous_or_malformed_csv_is_not_silently_accepted(text):
    with pytest.raises(ValueError):
        parse_csv(text, {"id"})


def test_csv_size_limit_counts_utf8_bytes():
    with pytest.raises(ValueError, match="1 MB"):
        parse_csv("id,note\nA," + "é" * 500_000, {"id", "note"})
