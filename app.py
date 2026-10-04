import json
import os
from pathlib import Path

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
import gradio as gr
import pandas as pd
import plotly.express as px

from api_settings import with_api_settings
from common import csv_text, export_text, read_upload, save_report
from domain import Analysis, analyze, read_feedback, records, summary, validate_analysis
from ui import CSS, hero, history_panel, launch, metrics, provider_picker, safe

SAMPLE = (Path(__file__).parent / "examples/feedback.csv").read_text()


def plots(result, rows):
    df = pd.DataFrame(records(result, rows))
    trend = df.groupby(["date", "sentiment"]).size().reset_index(name="messages")
    fig = px.bar(
        trend,
        x="date",
        y="messages",
        color="sentiment",
        barmode="stack",
        title="Feedback over time · message counts",
        color_discrete_map={
            "positive": "#0d9488",
            "negative": "#dc4c64",
            "mixed": "#ca8a04",
            "neutral": "#64748b",
            "unclear": "#8b5cf6",
        },
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=330)
    topics = pd.DataFrame(
        [
            {"topic": topic, "sentiment": f.sentiment}
            for f in result.findings
            for topic in f.topics
        ]
    )
    grouped = topics.groupby(["topic", "sentiment"]).size().reset_index(name="mentions")
    topic_fig = px.bar(
        grouped,
        x="topic",
        y="mentions",
        color="sentiment",
        title="Topics raised · one message can mention multiple topics",
        color_discrete_map={
            "positive": "#0d9488",
            "negative": "#dc4c64",
            "mixed": "#ca8a04",
            "neutral": "#64748b",
            "unclear": "#8b5cf6",
        },
    )
    topic_fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=330)
    return df, fig, topic_fig


@safe
def run(text, provider):
    rows = read_feedback(text)
    result = analyze(rows, provider)
    df, trend, topics = plots(result, rows)
    return (
        metrics(
            {
                "Messages": len(rows),
                "Concern / mixed": sum(
                    f.sentiment in {"negative", "mixed"} for f in result.findings
                ),
                "High urgency": sum(f.urgency == "high" for f in result.findings),
                "Unclear": sum(f.sentiment == "unclear" for f in result.findings),
            }
        ),
        summary(result),
        df,
        trend,
        topics,
        result.model_dump_json(indent=2),
        {"rows": rows, "provider": provider},
    )


@safe
def save(raw, context):
    if not context:
        raise ValueError("Analyze feedback first.")
    result = Analysis.model_validate_json(raw)
    validate_analysis(result, context["rows"])
    payload = {**context, "analysis": result.model_dump()}
    save_report(
        "sentiment",
        "Feedback report · " + str(len(context["rows"])) + " messages",
        payload,
    )
    return "Saved reviewed labels locally.", [
        export_text(json.dumps(payload, indent=2), ".json"),
        export_text(csv_text(records(result, context["rows"])), ".csv"),
        export_text(summary(result)),
    ]


def build_app():
    with gr.Blocks(
        title="Signal · Stakeholder Sentiment",
        theme=gr.themes.Soft(primary_hue="violet", font=["Arial", "sans-serif"]),
        css=CSS,
        analytics_enabled=False,
    ) as app:
        hero(
            "Signal",
            "Understand the concerns behind project feedback. Keep the source text visible and give every interpretation a chance to be reviewed.",
        )
        with gr.Tab("Feedback workspace"):
            with gr.Row():
                with gr.Column(scale=2):
                    text = gr.Textbox(
                        label="Feedback CSV",
                        lines=10,
                        placeholder="id,date,stakeholder,message",
                    )
                    with gr.Row():
                        example = gr.Button("Load sample feedback")
                        file = gr.File(label="Import CSV", file_types=[".csv"])
                with gr.Column(scale=1):
                    provider, credentials = provider_picker()
                    gr.Markdown(
                        "Analyze up to 100 messages per batch. Use feedback you are authorized to process. Local mode keeps it on your computer; selecting DeepSeek sends it to that provider."
                    )
            go = gr.Button("Analyze stakeholder feedback", variant="primary")
            stats = gr.HTML()
            note = gr.Markdown()
            with gr.Row():
                trend = gr.Plot(label="Sentiment trends")
                topics = gr.Plot(label="Topic breakdown")
            table = gr.Dataframe(
                label="Findings and exact source evidence", interactive=False, wrap=True
            )
            context = gr.State({})
            with gr.Accordion("Review and correct classifications", open=False):
                raw = gr.Code(
                    label="Editable analysis JSON", language="json", interactive=True
                )
                gr.Markdown(
                    "Change labels and follow-up suggestions here. Preserve source IDs and exact evidence quotes. Exports use your reviewed version."
                )
            save_btn = gr.Button("Save reviewed analysis and export")
            saved = gr.Markdown()
            files = gr.Files(label="JSON, CSV, and Markdown")
            example.click(lambda: SAMPLE, outputs=text)
            file.change(safe(read_upload), inputs=file, outputs=text)
            go.click(
                with_api_settings(run),
                inputs=[text, provider, credentials],
                outputs=[stats, note, table, trend, topics, raw, context],
            )
            save_btn.click(save, inputs=[raw, context], outputs=[saved, files])
        history_panel("sentiment")
    return app


if __name__ == "__main__":
    launch(build_app())
