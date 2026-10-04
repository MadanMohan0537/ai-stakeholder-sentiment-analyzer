"""Small, consistent UI helpers for this standalone application."""

from __future__ import annotations

import functools
import html
import json
import os

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
import gradio as gr

from ai import PROVIDERS
from common import history

CSS = """
.gradio-container {max-width: 1180px !important; margin:auto;}
.hero {padding:26px 0 22px;border-bottom:1px solid #d8e2ea;margin-bottom:20px;}
.hero .eyebrow {font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#537080;}
.hero h1 {font-size:38px;font-weight:700;letter-spacing:-1.5px;margin:8px 0;}
.hero p {font-size:16px;max-width:740px;line-height:1.6;}
.metrics {display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin:16px 0;}
.metric {border:1px solid #b8c8d833;border-radius:12px;padding:16px;background:#8096ad0c;}
.metric b {display:block;font-size:27px;line-height:1.4;}
.metric span {font-size:12px;opacity:.75;}
footer {display:none !important;}
"""


def hero(name: str, subtitle: str):
    gr.HTML(
        f'<div class="hero"><div class="eyebrow">Project management · Local workspace</div><h1>{html.escape(name)}</h1><p>{html.escape(subtitle)}</p></div>'
    )


def metrics(values: dict):
    return (
        '<div class="metrics">'
        + "".join(
            f'<div class="metric"><b>{html.escape(str(v))}</b><span>{html.escape(k)}</span></div>'
            for k, v in values.items()
        )
        + "</div>"
    )


def provider_picker():
    picker = gr.Dropdown(PROVIDERS, value=PROVIDERS[0], label="Analysis mode")
    gr.Markdown(
        "**Offline demo** uses transparent rules and templates. **Ollama** runs a local AI model. **DeepSeek** requires explicit setup and can incur charges."
    )
    return picker


def safe(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:
            raise gr.Error(str(exc)) from exc

    return wrapped


def history_panel(kind: str):
    with gr.Tab("Saved reports"):
        gr.Markdown(
            "Reports are saved on this computer. Reload the list after saving a report."
        )
        selected = gr.Dropdown(label="Saved report", choices=[])
        refresh = gr.Button("Refresh reports")
        view = gr.JSON(label="Report contents")

        def refresh_list():
            rows = history(kind)
            return gr.update(
                choices=[
                    (r["title"] + " · " + r["created_at"][:16], r["id"]) for r in rows
                ],
                value=None,
            )

        def load_report(record_id):
            row = next((r for r in history(kind) if r["id"] == record_id), None)
            return json.loads(row["payload"]) if row else {}

        refresh.click(refresh_list, outputs=selected)
        selected.change(load_report, inputs=selected, outputs=view)


def launch(app):
    app.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=int(os.getenv("PORT", "7864")),
        share=False,
        show_error=False,
        inbrowser=False,
    )
