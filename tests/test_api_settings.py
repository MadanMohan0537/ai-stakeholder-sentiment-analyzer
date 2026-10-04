import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from threading import Barrier

import httpx
import pytest
from pydantic import BaseModel

import ai
import api_settings as settings
import app
import domain
from gradio.state_holder import SessionState


class Reply(BaseModel):
    answer: str


def test_apply_masks_key_and_does_not_write_files_or_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "existing-placeholder")
    key = "session-placeholder"
    config, field, status = settings.apply_settings(key, "deepseek-flash", True)
    assert config.api_key == key and config.allow_paid
    assert field == "" and key not in status and key not in repr(config)
    assert os.getenv("DEEPSEEK_API_KEY") == "existing-placeholder"
    assert not list(tmp_path.iterdir())
    cleared, field, paid, use_env, status = settings.clear_settings()
    assert not cleared.api_key and not cleared.allow_paid
    assert field == "" and not paid and not use_env and key not in status


@pytest.mark.parametrize("key", ["", "a\nb", "a b", "é", "a" * 513])
def test_invalid_keys_are_rejected_without_echo(key):
    with pytest.raises(ValueError) as error:
        settings.apply_settings(key, "deepseek-flash", True)
    if key:
        assert key not in str(error.value)


def test_env_key_is_only_used_when_explicitly_selected(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-placeholder")
    config, _, _ = settings.apply_settings("", "deepseek-flash", False, True)
    assert config.api_key == "environment-placeholder" and not config.allow_paid
    with pytest.raises(ValueError, match="Enter"):
        settings.apply_settings("", "deepseek-flash", False)


def test_session_overrides_env_and_requires_its_own_opt_in(monkeypatch):
    monkeypatch.setenv("ALLOW_PAID_API", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-placeholder")
    seen = []

    def post(url, **kwargs):
        seen.append(kwargs)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"finish_reason": "stop", "message": {"content": '{"answer":"ok"}'}}
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    with settings.session_settings(
        settings.APISettings("session-placeholder", "custom-model", True)
    ):
        assert ai.generate(Reply, "Answer", "Data", "DeepSeek (opt-in)").answer == "ok"
    assert seen[0]["headers"]["Authorization"] == "Bearer session-placeholder"
    assert seen[0]["json"]["model"] == "custom-model"
    for config in [
        settings.APISettings("session-placeholder"),
        settings.clear_settings()[0],
    ]:
        with (
            settings.session_settings(config),
            pytest.raises(ai.AIError, match="opt in"),
        ):
            ai.generate(Reply, "Answer", "Data", "DeepSeek (opt-in)")
    assert len(seen) == 1 and settings.current_settings() is None


def test_keys_do_not_cross_concurrent_requests_and_context_resets_on_failure():
    barrier = Barrier(2)

    def request(key):
        with settings.session_settings(settings.APISettings(key)):
            barrier.wait(timeout=5)
            result = settings.current_settings().api_key
        assert settings.current_settings() is None
        return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(
            executor.map(request, ["first-placeholder", "second-placeholder"])
        ) == ["first-placeholder", "second-placeholder"]
    with pytest.raises(RuntimeError):
        with settings.session_settings(settings.APISettings("failure-placeholder")):
            raise RuntimeError("Simulated workflow failure")
    assert settings.current_settings() is None


@pytest.mark.parametrize(
    "case", ["success", "missing-model", "unauthorized", "timeout", "malformed"]
)
def test_connection_check_only_fetches_metadata_and_hides_credentials(
    monkeypatch, case
):
    key = "check-placeholder"

    def get(url, **kwargs):
        assert url == "https://api.deepseek.com/models"
        assert kwargs["headers"]["Authorization"] == "Bearer " + key
        assert not kwargs["follow_redirects"]
        if case == "timeout":
            raise httpx.ReadTimeout(key)
        body = (
            {"data": [{"id": "deepseek-flash"}]} if case == "success" else {"data": []}
        )
        if case == "malformed":
            body = []
        return httpx.Response(
            401 if case == "unauthorized" else 200,
            json=body,
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", get)
    monkeypatch.setattr(
        httpx, "post", lambda *a, **kw: pytest.fail("Metadata check must not generate")
    )
    status = settings.check_connection(settings.APISettings(key))
    assert key not in status
    expected = {
        "success": "Connection checked",
        "missing-model": "not listed",
        "unauthorized": "rejected",
        "timeout": "in time",
        "malformed": "unexpected",
    }
    assert expected[case] in status


def project_calls():
    """Valid project inputs and deterministic provider replies for real event wiring."""
    name = Path(__file__).parents[1].name
    provider = "DeepSeek (opt-in)"
    if name == "ai-meeting-summarizer":
        return [
            (
                "analyze",
                ["Meeting", app.SAMPLE, provider],
                domain.MeetingReport().model_dump_json(),
            ),
            (
                "ask",
                [app.SAMPLE, "What was decided?", provider],
                '{"answer":"Review line one", "source_lines":[1]}',
            ),
        ]
    if name == "ai-project-planning-assistant":
        raw = domain.draft(app.SAMPLE, "Offline demo").model_dump_json()
        dates = ["2026-10-05", "2026-11-01", 2, 25]
        return [
            ("create", [app.SAMPLE, provider, *dates], raw),
            ("change", [raw, json.loads(raw), "Add review", 4, provider, *dates], raw),
        ]
    if name == "ai-resource-health-dashboard":
        return [
            (
                "inspect",
                [
                    (app.EXAMPLES / "tasks.csv").read_text(),
                    (app.EXAMPLES / "people.csv").read_text(),
                    "2026-10-05",
                    1,
                    provider,
                ],
                '{"summary":"Reviewed", "actions":[]}',
            )
        ]
    if name == "ai-stakeholder-sentiment-analyzer":
        raw = domain.analyze(
            domain.read_feedback(app.SAMPLE), "Offline demo"
        ).model_dump_json()
        return [("run", [app.SAMPLE, provider], raw)]
    return [
        (
            "preview",
            ["Review launch", provider],
            domain.capture("Review launch", "Offline demo").model_dump_json(),
        )
    ]


def test_browser_state_flows_to_all_ai_actions_and_is_not_returned(monkeypatch):
    demo = app.build_app()
    state = SessionState(demo)
    other_session = SessionState(demo)
    functions = {fn.fn.__name__: i for i, fn in demo.fns.items()}
    key = "browser-placeholder"
    response_content = []
    seen = []

    def post(url, **kwargs):
        seen.append(kwargs["headers"]["Authorization"])
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": response_content[0]},
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)

    async def exercise():
        applied = await demo.process_api(
            functions["apply_settings"],
            [
                key,
                "deepseek-flash",
                True,
                False,
                None,
                "https://api.deepseek.com",
                True,
            ],
            state=state,
        )
        assert applied["data"][0] is None and applied["data"][1] == ""
        assert key not in json.dumps(applied["data"])
        for name, inputs, reply in project_calls():
            response_content[:] = [reply]
            event = demo.fns[functions[name]]
            assert event.inputs[-1].stateful
            assert not other_session[event.inputs[-1]._id].api_key
            result = await demo.process_api(
                functions[name], [*inputs, None], state=state
            )
            assert key not in json.dumps(result["data"], default=str)
            data = result["data"]
            if name == "analyze":
                app.save_review(data[2], state[event.outputs[3]._id])
            elif name in {"create", "change"}:
                app.save(data[0], "2026-10-05", "2026-11-01", 2, 25)
            elif name == "inspect":
                app.save(state[event.outputs[-1]._id])
            elif name == "run":
                app.save(data[5], state[event.outputs[-1]._id])
            elif name == "preview":
                app.approve(data[0])
                app.export_all()
        cleared = await demo.process_api(functions["clear_settings"], [], state=state)
        assert key not in json.dumps(cleared["data"])
        credential_state = demo.fns[functions["check_connection"]].inputs[0]
        assert not state[credential_state._id].api_key

    asyncio.run(exercise())
    assert seen and all(header == "Bearer " + key for header in seen)
    assert settings.current_settings() is None
    assert key not in json.dumps(demo.config, default=str)
    for file in Path(os.environ["APP_DATA_DIR"]).rglob("*"):
        if file.is_file():
            assert key.encode() not in file.read_bytes()


def test_editing_settings_retains_masked_key_until_cleared():
    config, _, _ = settings.apply_settings(
        "retained-placeholder", "deepseek-flash", False
    )
    updated, field, _ = settings.apply_settings(
        "", "custom-model", True, existing=config
    )
    assert updated.api_key == config.api_key and updated.allow_paid
    assert updated.model == "custom-model" and field == ""
    with pytest.raises(ValueError, match="Enter"):
        settings.apply_settings(
            "", "custom-model", True, existing=settings.clear_settings()[0]
        )
