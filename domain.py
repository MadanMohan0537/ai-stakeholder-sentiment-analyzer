"""Evidence-linked topic and sentiment analysis; no hidden-state or employee scoring."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from ai import generate
from common import iso_date, parse_csv

TOPICS = {
    "timeline": ["deadline", "delay", "launch", "date", "schedule", "late", "ready"],
    "budget": ["budget", "cost", "invoice", "spend", "price"],
    "scope": ["scope", "requirement", "feature", "change"],
    "quality": ["quality", "bug", "design", "test", "accessibility", "broken"],
    "communication": ["update", "response", "communication", "reply", "clarify"],
}


class Finding(BaseModel):
    source_id: str
    sentiment: Literal["positive", "negative", "mixed", "neutral", "unclear"]
    topics: list[
        Literal["timeline", "budget", "scope", "quality", "communication", "general"]
    ] = Field(min_length=1)
    urgency: Literal["low", "medium", "high"]
    concern: str = Field(max_length=1200)
    evidence: str = Field(min_length=1, max_length=3000)
    suggested_follow_up: str = Field(max_length=1000)


class Analysis(BaseModel):
    findings: list[Finding] = Field(max_length=100)


def read_feedback(text: str) -> list[dict]:
    rows = parse_csv(text, {"id", "date", "stakeholder", "message"})
    if len(rows) > 100:
        raise ValueError("Analyze at most 100 messages at a time.")
    if len({r["id"] for r in rows}) != len(rows) or any(
        not r["id"].strip() for r in rows
    ):
        raise ValueError("Every feedback row needs a unique, nonempty ID.")
    for row in rows:
        iso_date(row["date"])
        if not row["message"].strip() or len(row["message"]) > 3000:
            raise ValueError("Each message must contain 1-3,000 characters.")
        if not row["stakeholder"].strip():
            raise ValueError("Every message needs a stakeholder label.")
    return rows


def validate_analysis(analysis: Analysis, rows: list[dict]):
    source = {r["id"]: r for r in rows}
    ids = [f.source_id for f in analysis.findings]
    if len(set(ids)) != len(ids) or set(ids) != set(source):
        raise ValueError(
            "Analysis must contain exactly one finding for every source row."
        )
    for f in analysis.findings:
        if f.evidence not in source[f.source_id]["message"]:
            raise ValueError(
                f"{f.source_id} contains an evidence quote absent from the source. Review the result."
            )


def analyze(rows: list[dict], provider: str) -> Analysis:
    if provider != "Offline demo":
        result = generate(
            Analysis,
            "Analyze expressed project feedback, not personality or unspoken emotions. "
            "Return exactly one finding per source ID. Consider conversation context, topic, explicit urgency, "
            "negation, and mixed opinions. Use unclear for ambiguity. Evidence must be an exact nonempty substring "
            "of that row's message. Follow-ups are suggestions for review, never sent messages.",
            json.dumps(rows),
            provider,
        )
    else:
        findings = []
        for row in rows:
            text = row["message"].lower()
            positive = bool(
                re.search(
                    r"\b(great|happy|pleased|excellent|good|approved|love|thanks|confident)\b",
                    text,
                )
            )
            negative = bool(
                re.search(
                    r"\b(worried|concern|concerned|unhappy|late|delay|delayed|blocked|broken|overrun|unclear|unacceptable)\b",
                    text,
                )
            )
            if re.search(r"\bnot (happy|good|ready|confident|approved)\b", text):
                negative, positive = True, False
            if re.search(r"\bnot (bad|worried|concerned)\b", text):
                positive, negative = True, False
            sentiment = (
                "mixed"
                if positive and negative
                else ("positive" if positive else "negative" if negative else "neutral")
            )
            if re.search(r"\b(sure,? whatever|yeah right|fine,? i guess)\b", text):
                sentiment = "unclear"
            topics = [
                topic
                for topic, words in TOPICS.items()
                if any(
                    re.search(r"\b" + re.escape(word) + r"\b", text) for word in words
                )
            ] or ["general"]
            urgency = (
                "high"
                if re.search(
                    r"\b(urgent|immediately|today|blocked|unacceptable)\b", text
                )
                else ("medium" if negative or "?" in text else "low")
            )
            concern = (
                row["message"]
                if negative or "?" in text or sentiment == "unclear"
                else "No explicit concern detected by keyword rules."
            )
            # Concern is a compact preview; retain the complete source in
            # evidence and in the original row for review and export.
            if len(concern) > 1200:
                concern = concern[:1199] + "…"
            findings.append(
                Finding(
                    source_id=row["id"],
                    sentiment=sentiment,
                    topics=topics,
                    urgency=urgency,
                    concern=concern,
                    evidence=row["message"],
                    suggested_follow_up=(
                        "Ask the stakeholder to clarify the concern and agree an owner and next update."
                        if negative or "?" in text or sentiment == "unclear"
                        else "Acknowledge the feedback and retain it in the project record."
                    ),
                )
            )
        result = Analysis(findings=findings)
    validate_analysis(result, rows)
    return result


def records(result: Analysis, rows: list[dict]) -> list[dict]:
    sources = {r["id"]: r for r in rows}
    return [
        {**sources[f.source_id], **f.model_dump(), "topics": ", ".join(f.topics)}
        for f in result.findings
    ]


def summary(result: Analysis) -> str:
    counts = Counter(f.sentiment for f in result.findings)
    concerns = [
        f
        for f in result.findings
        if f.sentiment in {"negative", "mixed", "unclear"} or f.urgency == "high"
    ]
    text = "**Expressed feedback**\n\n" + " · ".join(
        f"{name}: {counts[name]}"
        for name in ["positive", "negative", "mixed", "neutral", "unclear"]
    )
    text += "\n\n**Items to review**\n\n"
    text += (
        "\n".join(
            f"- [{f.source_id}] {f.concern} ({f.urgency} urgency)" for f in concerns
        )
        or "No flagged items in this batch."
    )
    text += "\n\nLabels describe text in the supplied messages. They are not measurements of a person's feelings, intent, or performance."
    return text
