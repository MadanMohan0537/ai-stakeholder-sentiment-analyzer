"""Local persistence, input validation, and safe exports."""

from __future__ import annotations

import csv
import io
import json
import math
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def data_dir() -> Path:
    path = Path(os.getenv("APP_DATA_DIR", str(ROOT / "data")))
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connection():
    conn = sqlite3.connect(data_dir() / "workspace.sqlite3", timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def save_report(kind: str, title: str, payload: dict) -> str:
    record_id = uuid.uuid4().hex
    with connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, kind TEXT, title TEXT, created_at TEXT, payload TEXT)"
        )
        conn.execute(
            "INSERT INTO reports VALUES (?, ?, ?, ?, ?)",
            (
                record_id,
                kind,
                title,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
    return record_id


def history(kind: str) -> list[dict]:
    with connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, kind TEXT, title TEXT, created_at TEXT, payload TEXT)"
        )
        return [
            dict(r)
            for r in conn.execute(
                "SELECT id, title, created_at, payload FROM reports WHERE kind=? ORDER BY created_at DESC LIMIT 100",
                (kind,),
            )
        ]


def export_text(text: str, suffix: str = ".md") -> str:
    path = data_dir() / "exports"
    path.mkdir(exist_ok=True)
    target = path / (uuid.uuid4().hex + suffix)
    target.write_text(text, encoding="utf-8")
    return str(target)


def csv_text(rows: list[dict], fields: list[str] | None = None) -> str:
    fields = fields or (list(rows[0]) if rows else [])
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        clean = {}
        for key in fields:
            value = row.get(key, "")
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            if isinstance(value, str) and value.lstrip().startswith(
                ("=", "+", "-", "@")
            ):
                value = "'" + value
            clean[key] = value
        writer.writerow(clean)
    return out.getvalue()


def read_upload(path: str | None, max_bytes: int = 1_000_000) -> str:
    if not path:
        return ""
    file = Path(path)
    if file.stat().st_size > max_bytes:
        raise ValueError(f"File is too large; limit is {max_bytes // 1000} KB.")
    try:
        return file.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Upload a UTF-8 text or CSV file.") from exc


def parse_csv(text: str, required: set[str]) -> list[dict]:
    if len(text.encode("utf-8")) > 1_000_000:
        raise ValueError("CSV exceeds 1 MB.")
    try:
        reader = csv.DictReader(io.StringIO(text.strip().lstrip("\ufeff")), strict=True)
        fields = reader.fieldnames
        if fields and (
            len(fields) != len(set(fields))
            or any(not field.strip() for field in fields)
        ):
            raise ValueError("CSV column names must be nonempty and unique.")
        if not fields or not required.issubset(fields):
            raise ValueError("CSV requires columns: " + ", ".join(sorted(required)))
        rows = list(reader)
    except csv.Error as exc:
        raise ValueError(
            "CSV contains malformed quoting. Export it again as a standard UTF-8 CSV."
        ) from exc
    if not rows or len(rows) > 1000:
        raise ValueError("Supply between 1 and 1,000 CSV rows.")
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("CSV rows have inconsistent column counts.")
    return rows


def number(value, label: str, low=0, high=100000) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric.") from exc
    if not math.isfinite(n) or not low <= n <= high:
        raise ValueError(f"{label} must be between {low} and {high}.")
    return n


def iso_date(value: str, label="Date") -> date:
    try:
        parsed = date.fromisoformat(value)
        # All stored dates must sort chronologically as strings. Python also
        # accepts compact and ISO week dates, which do not have that property.
        if value != parsed.isoformat():
            raise ValueError("Noncanonical calendar date")
        return parsed
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD.") from exc
