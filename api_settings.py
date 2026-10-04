"""Session-scoped API credentials; never persisted or placed in process globals."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import functools
import inspect
import os
import re
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class APISettings:
    api_key: str = field(default="", repr=False)
    model: str = "deepseek-flash"
    allow_paid: bool = False
    base_url: str = "https://api.deepseek.com"
    json_mode: bool = True


_active: ContextVar[APISettings | None] = ContextVar("deepseek_settings", default=None)


def current_settings() -> APISettings | None:
    return _active.get()


@contextmanager
def session_settings(settings: APISettings):
    if not isinstance(settings, APISettings):
        raise ValueError("Apply API settings before using an API provider.")
    token = _active.set(settings)
    try:
        yield
    finally:
        _active.reset(token)


def validate_base_url(value):
    base = (value or "").strip().rstrip("/")
    try:
        parsed = urlparse(base)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        valid = (
            parsed.hostname
            and (parsed.scheme == "https" or (parsed.scheme == "http" and local))
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
            and (parsed.port is None or 1 <= parsed.port <= 65535)
            and not any(ch.isspace() for ch in base)
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(
            "Use an HTTPS API base URL without credentials or query parameters. HTTP is allowed only for loopback servers."
        )
    if parsed.path.endswith(("/chat/completions", "/models")):
        raise ValueError(
            "Enter the API base URL, such as https://api.openai.com/v1, without /chat/completions or /models."
        )
    return base


def is_loopback(base):
    return urlparse(base).hostname in {"localhost", "127.0.0.1", "::1"}


def apply_settings(
    key,
    model,
    allow_paid,
    use_env=False,
    existing=None,
    base_url="https://api.deepseek.com",
    json_mode=True,
):
    base = validate_base_url(base_url)
    if (
        existing
        and existing.api_key
        and existing.base_url != base
        and not key
        and not use_env
    ):
        raise ValueError(
            "The endpoint changed. Re-enter the key for this endpoint before applying settings."
        )
    retained_key = existing.api_key if isinstance(existing, APISettings) else ""
    key = (
        os.getenv(
            "DEEPSEEK_API_KEY"
            if urlparse(base).hostname == "api.deepseek.com"
            else "AI_API_KEY",
            "",
        )
        if use_env
        else key or retained_key
    ).strip()
    model = (model or "").strip()
    if not key and not is_loopback(base):
        raise ValueError("Enter your API key, or configure the selected .env key.")
    if key and (len(key) > 512 or not re.fullmatch(r"[!-~]+", key)):
        raise ValueError(
            "The API key must contain printable ASCII characters without spaces."
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}", model):
        raise ValueError("Enter a valid model ID.")
    settings = APISettings(key, model, bool(allow_paid), base, bool(json_mode))
    message = "API settings applied for this session. The key field was cleared. "
    message += (
        "Select the matching API mode and run a project action when ready; usage may be billed."
        if settings.allow_paid
        else "Generation remains disabled until you opt in and apply settings again."
    )
    return settings, "", message


def clear_settings():
    return (
        APISettings(),
        "",
        False,
        False,
        "Session API key cleared. API generation is disabled.",
    )


def check_connection(settings: APISettings):
    if not isinstance(settings, APISettings) or (
        not settings.api_key and not is_loopback(settings.base_url)
    ):
        raise ValueError("Apply an API key before checking the connection.")
    base = validate_base_url(settings.base_url)
    try:
        response = httpx.get(
            base + "/models",
            headers={"Authorization": "Bearer " + settings.api_key}
            if settings.api_key
            else {},
            timeout=15,
            follow_redirects=False,
            trust_env=not is_loopback(base),
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            return "The provider returned an unexpected model list. No generation was requested."
        available = {
            item.get("id")
            for item in data["data"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if settings.model not in available:
            return "The key was accepted, but the configured model was not listed. Check the model name. No generation was requested."
        return "Connection checked: the key was accepted and the model is listed. No generation was requested; this does not verify your balance or output quality."
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code in {404, 405}:
            return "This provider does not expose a model-list endpoint. Check its documentation; generation may still work."
        if code in {401, 403}:
            return "The provider rejected this key. Check your key and account permissions."
        return f"The provider returned HTTP {code}. Check your account and retry."
    except httpx.TimeoutException:
        return "The provider did not respond in time. Try checking again."
    except httpx.RequestError:
        return "Cannot reach the provider. Check your internet connection."
    except (ValueError, TypeError):
        return (
            "The provider returned invalid model metadata. No generation was requested."
        )


def with_api_settings(fn):
    """Supply Gradio's last State input only for the duration of this callback."""

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if "api_settings" in kwargs:
            settings = kwargs.pop("api_settings")
        else:
            *args, settings = args
        with session_settings(settings):
            return fn(*args, **kwargs)

    signature = inspect.signature(fn)
    wrapped.__signature__ = signature.replace(
        parameters=[
            *signature.parameters.values(),
            inspect.Parameter("api_settings", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ]
    )
    return wrapped
