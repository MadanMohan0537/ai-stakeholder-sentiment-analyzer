import asyncio
import json

import httpx
import pytest
from pydantic import BaseModel
from gradio.state_holder import SessionState

import ai
import api_settings as settings
import app
from test_api_settings import project_calls


class Reply(BaseModel):
    answer: str


@pytest.mark.parametrize(
    "base",
    [
        "https://api.openai.com/v1",
        "https://openrouter.ai/api/v1",
        "https://api.groq.com/openai/v1",
        "http://127.0.0.1:1234/v1",
    ],
)
@pytest.mark.parametrize("json_mode", [True, False])
def test_custom_request_uses_configured_endpoint_and_portable_payload(
    monkeypatch, base, json_mode
):
    def post(url, **kwargs):
        assert url == base + "/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer custom-placeholder"
        payload = kwargs["json"]
        assert payload["model"] == "provider/model"
        assert ("response_format" in payload) == json_mode
        assert not {"thinking", "temperature", "max_tokens"} & payload.keys()
        assert kwargs["trust_env"] == (not settings.is_loopback(base))
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
    config = settings.apply_settings(
        "custom-placeholder", "provider/model", True, base_url=base, json_mode=json_mode
    )[0]
    with settings.session_settings(config):
        assert (
            ai.generate(
                Reply, "Answer", "Data", "Custom API (OpenAI-compatible)"
            ).answer
            == "ok"
        )


@pytest.mark.parametrize(
    "base",
    [
        "http://api.example.com/v1",
        "https://secret:password@example.com/v1",
        "https://example.com/v1?api_key=secret",
        "https://example.com/v1#secret",
        "https://example.com/chat/completions",
        "https://example.com/models",
        "https://example.com:bad/v1",
        "",
    ],
)
def test_bad_endpoints_are_rejected_without_exposing_credentials(base):
    with pytest.raises(ValueError) as error:
        settings.apply_settings("placeholder", "model", True, base_url=base)
    assert "secret" not in str(error.value) and "password" not in str(error.value)


def test_switching_endpoint_requires_a_new_key():
    previous = settings.apply_settings("first-placeholder", "model", True)[0]
    with pytest.raises(ValueError, match="Re-enter"):
        settings.apply_settings(
            "", "model", True, existing=previous, base_url="https://api.openai.com/v1"
        )
    new = settings.apply_settings(
        "second-placeholder",
        "model",
        True,
        existing=previous,
        base_url="https://api.openai.com/v1",
    )[0]
    assert new.api_key == "second-placeholder"


def test_deepseek_mode_never_sends_keys_to_another_provider(monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda *a, **kw: pytest.fail("No request expected")
    )
    config = settings.APISettings(
        "placeholder", "model", True, "https://api.openai.com/v1"
    )
    with (
        settings.session_settings(config),
        pytest.raises(ai.AIError, match="Custom API"),
    ):
        ai.generate(Reply, "Answer", "Data", "DeepSeek (opt-in)")


def test_generic_environment_configuration(monkeypatch):
    monkeypatch.setenv("ALLOW_PAID_API", "true")
    monkeypatch.setenv("AI_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("AI_API_KEY", "environment-placeholder")
    monkeypatch.setenv("AI_MODEL", "example-model")
    monkeypatch.setenv("AI_JSON_MODE", "false")

    def post(url, **kwargs):
        assert url == "https://example.com/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer environment-placeholder"
        assert kwargs["json"]["model"] == "example-model"
        assert "response_format" not in kwargs["json"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"answer":"ok"}'}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    assert (
        ai.generate(Reply, "Answer", "Data", "Custom API (OpenAI-compatible)").answer
        == "ok"
    )
    assert (
        settings.apply_settings(
            "", "model", False, True, base_url="https://example.com/v1"
        )[0].api_key
        == "environment-placeholder"
    )


def test_local_compatible_server_can_run_without_an_api_key(monkeypatch):
    config = settings.apply_settings(
        "", "local-model", True, base_url="http://localhost:1234/v1"
    )[0]

    def post(url, **kwargs):
        assert kwargs["headers"] == {} and not kwargs["trust_env"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"answer":"ok"}'}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    with settings.session_settings(config):
        assert (
            ai.generate(
                Reply, "Answer", "Data", "Custom API (OpenAI-compatible)"
            ).answer
            == "ok"
        )


def test_missing_models_endpoint_does_not_claim_generation_is_broken(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **kw: httpx.Response(404, request=httpx.Request("GET", url)),
    )
    status = settings.check_connection(
        settings.APISettings("placeholder", "model", True, "https://example.com/v1")
    )
    assert "generation may still work" in status


def test_custom_mode_still_requires_valid_structured_output(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kw: httpx.Response(
            200,
            json={"choices": [{"message": {"content": "plain prose"}}]},
            request=httpx.Request("POST", url),
        ),
    )
    with (
        settings.session_settings(settings.APISettings("placeholder", "model", True)),
        pytest.raises(ai.AIError, match="invalid structured"),
    ):
        ai.generate(Reply, "Answer", "Data", "Custom API (OpenAI-compatible)")


def test_custom_provider_flows_through_all_gradio_actions(monkeypatch):
    demo = app.build_app()
    state = SessionState(demo)
    functions = {fn.fn.__name__: i for i, fn in demo.fns.items()}
    content = []
    seen = []

    def post(url, **kwargs):
        assert url == "https://example.com/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer browser-custom-placeholder"
        assert (
            kwargs["json"]["model"] == "custom-model"
            and "thinking" not in kwargs["json"]
        )
        seen.append(url)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content[0]}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)

    async def exercise():
        await demo.process_api(
            functions["apply_settings"],
            [
                "browser-custom-placeholder",
                "custom-model",
                True,
                False,
                None,
                "https://example.com/v1",
                False,
            ],
            state=state,
        )
        for name, inputs, reply in project_calls():
            content[:] = [reply]
            inputs = [
                "Custom API (OpenAI-compatible)"
                if item == "DeepSeek (opt-in)"
                else item
                for item in inputs
            ]
            result = await demo.process_api(
                functions[name], [*inputs, None], state=state
            )
            assert "browser-custom-placeholder" not in json.dumps(
                result["data"], default=str
            )

    asyncio.run(exercise())
    assert seen
