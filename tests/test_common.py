import json
import httpx
import pytest
from pydantic import BaseModel

import ai
from common import csv_text, history, number, parse_csv, save_report


class Output(BaseModel):
    answer: str


@pytest.fixture(autouse=True)
def local_data(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ALLOW_PAID_API", "false")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


def test_paid_provider_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda *a, **kw: pytest.fail("Network call must not happen")
    )
    with pytest.raises(ai.AIError, match="ALLOW_PAID_API"):
        ai.generate(Output, "Answer", "Data", "DeepSeek (opt-in)")


def test_local_mode_rejects_cloud_url(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.com")
    with pytest.raises(ai.AIError, match="loopback"):
        ai.generate(Output, "Answer", "Data", "Ollama (local)")


def test_ollama_contract_and_validation(monkeypatch):
    def request(url, **kwargs):
        assert url == "http://127.0.0.1:11434/api/chat"
        assert kwargs["json"]["stream"] is False
        assert kwargs["json"]["format"]["type"] == "object"
        assert "SOURCE DATA" in kwargs["json"]["messages"][1]["content"]
        return httpx.Response(
            200,
            json={"message": {"content": '{"answer":"Reviewed"}'}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", request)
    assert ai.generate(Output, "Answer", "Data", "Ollama (local)").answer == "Reviewed"


def test_invalid_provider_output_never_becomes_success(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kw: httpx.Response(
            200,
            json={"message": {"content": "not json"}},
            request=httpx.Request("POST", url),
        ),
    )
    with pytest.raises(ai.AIError, match="invalid structured"):
        ai.generate(Output, "Answer", "Data", "Ollama (local)")


def test_deepseek_contract(monkeypatch):
    monkeypatch.setenv("ALLOW_PAID_API", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "unit-test-placeholder")

    def request(url, **kwargs):
        assert url == "https://api.deepseek.com/chat/completions"
        assert kwargs["json"]["response_format"] == {"type": "json_object"}
        assert kwargs["headers"]["Authorization"] == "Bearer unit-test-placeholder"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"answer":"Reviewed"}'},
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", request)
    assert (
        ai.generate(Output, "Answer", "Data", "DeepSeek (opt-in)").answer == "Reviewed"
    )


def test_safe_csv_and_numeric_validation():
    assert "'=SUM" in csv_text([{"note": "=SUM(A1:A9)"}])
    with pytest.raises(ValueError):
        number("nan", "Hours")
    with pytest.raises(ValueError):
        parse_csv("id,name\n1,A,extra", {"id", "name"})


def test_local_report_roundtrip():
    uid = save_report("test", "A report", {"example": [1, 2]})
    result = history("test")
    assert result[0]["id"] == uid
    assert json.loads(result[0]["payload"]) == {"example": [1, 2]}
    assert history("other") == []


@pytest.mark.parametrize("value", ["20261005", "2026-W41-1", "2026-02-30", "2026-10-05T00:00:00", " 2026-10-05", None])
def test_dates_require_calendar_format(value):
    from common import iso_date

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        iso_date(value, "Due date")


def test_valid_calendar_date():
    from common import iso_date

    assert iso_date("2024-02-29").isoformat() == "2024-02-29"
