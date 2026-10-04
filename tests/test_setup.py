"""Regression checks for free setup, model readiness, and safe local requests."""

import json
import subprocess

import httpx
import pytest

import ai
import local_ai_check as check
import run


@pytest.fixture(autouse=True)
def clean_configuration(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setenv("OLLAMA_CONTEXT", "16384")
    monkeypatch.setenv("ALLOW_PAID_API", "false")


def models(monkeypatch, names):
    def get(url, **kwargs):
        assert url == "http://127.0.0.1:11434/api/tags"
        assert kwargs["trust_env"] is False
        assert kwargs["follow_redirects"] is False
        return httpx.Response(
            200,
            json={"models": [{"name": n} for n in names]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", get)


def test_readiness_is_metadata_only(monkeypatch):
    models(monkeypatch, ["qwen3:4b"])
    monkeypatch.setattr(
        check,
        "generate",
        lambda *a, **kw: pytest.fail("Readiness must not generate text"),
    )
    result = check.check_local_ai()
    assert result["ready"] and not result["inference_tested"]


def test_missing_model_has_actionable_setup_command(monkeypatch):
    models(monkeypatch, [])
    result = check.check_local_ai()
    assert not result["ready"]
    assert "ollama pull qwen3:4b" in result["message"]


def test_default_tag_matches_latest(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3")
    models(monkeypatch, ["qwen3:latest"])
    assert check.check_local_ai()["ready"]


def test_service_failure_keeps_offline_mode_available(monkeypatch):
    def fail(*a, **kw):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx, "get", fail)
    result = check.check_local_ai()
    assert not result["ready"]
    assert "Offline demo mode still works" in result["message"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("OLLAMA_BASE_URL", "https://ollama.com"),
        ("OLLAMA_BASE_URL", "http://secret:password@localhost:11434"),
        ("OLLAMA_MODEL", "qwen3-cloud"),
        ("OLLAMA_CONTEXT", "not-a-number"),
    ],
)
def test_invalid_setup_never_makes_a_request(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **kw: pytest.fail("Invalid setup must not contact any service"),
    )
    result = check.check_local_ai()
    assert not result["ready"]
    assert "secret" not in result["message"] and "password" not in result["message"]


def test_smoke_test_uses_only_local_provider_even_when_paid_is_enabled(monkeypatch):
    models(monkeypatch, ["qwen3:4b"])
    monkeypatch.setenv("ALLOW_PAID_API", "true")
    seen = []

    def generate(schema, instruction, source, provider):
        seen.append((provider, source))
        return schema(status="ready")

    monkeypatch.setattr(check, "generate", generate)
    result = check.check_local_ai(True)
    assert seen == [("Ollama (local)", "Status: ready")]
    assert result["ready"] and result["inference_tested"]


def test_malformed_metadata_has_nonzero_cli_exit(monkeypatch, capsys):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **kw: httpx.Response(
            200, json=[], request=httpx.Request("GET", url)
        ),
    )
    assert check.main([]) == 1
    result = json.loads(capsys.readouterr().out)
    assert not result["ready"] and "unexpected model list" in result["message"]


def test_incomplete_inference_is_rejected_even_if_json_is_valid(monkeypatch):
    def post(url, **kwargs):
        assert kwargs["trust_env"] is False
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "length",
                "message": {"content": '{"status":"ready"}'},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(ai.AIError, match="stopped before completing"):
        ai.generate(
            check.SmokeReply, "Return a status", "Status: ready", "Ollama (local)"
        )


def fake_environment(tmp_path, monkeypatch, returncode=0):
    python = run.environment_python(tmp_path)
    python.parent.mkdir(parents=True)
    python.touch()
    (tmp_path / ".env.example").write_text("ALLOW_PAID_API=false\n")
    calls = []

    def command(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, returncode if len(calls) == 1 else 0)

    monkeypatch.setattr(subprocess, "run", command)
    return python, calls


def test_launcher_preserves_settings_and_does_not_reinstall_ready_dependencies(
    tmp_path, monkeypatch
):
    python, calls = fake_environment(tmp_path, monkeypatch)
    content = "PORT=9999\nDEEPSEEK_API_KEY=local-test-placeholder\n"
    (tmp_path / ".env").write_text(content)
    assert run.prepare(tmp_path) == python
    assert (tmp_path / ".env").read_text() == content
    assert len(calls) == 1  # Dependency check only, no pip or model request.


def test_launcher_installs_missing_dependencies_in_its_own_folder(
    tmp_path, monkeypatch
):
    python, calls = fake_environment(tmp_path, monkeypatch, 1)
    assert run.prepare(tmp_path) == python
    assert calls[1][0][:4] == [str(python), "-m", "pip", "install"]
    assert calls[1][1]["cwd"] == tmp_path
    assert (tmp_path / ".env").read_text() == "ALLOW_PAID_API=false\n"


def test_failed_install_does_not_write_new_settings(tmp_path, monkeypatch):
    python, calls = fake_environment(tmp_path, monkeypatch, 1)
    original = subprocess.run

    def fail_install(args, **kwargs):
        if "pip" in args:
            raise subprocess.CalledProcessError(1, args)
        return original(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fail_install)
    with pytest.raises(subprocess.CalledProcessError):
        run.prepare(tmp_path)
    assert not (tmp_path / ".env").exists()
