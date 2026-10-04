"""Session-scoped DeepSeek credentials; never persisted or placed in process globals."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import functools
import inspect
import os
import re

import httpx


@dataclass(frozen=True)
class APISettings:
    api_key: str = field(default="", repr=False)
    model: str = "deepseek-flash"
    allow_paid: bool = False


_active: ContextVar[APISettings | None] = ContextVar("deepseek_settings", default=None)


def current_settings() -> APISettings | None:
    return _active.get()


@contextmanager
def session_settings(settings: APISettings):
    if not isinstance(settings, APISettings):
        raise ValueError("Apply API settings before using DeepSeek.")
    token = _active.set(settings)
    try:
        yield
    finally:
        _active.reset(token)


def apply_settings(key, model, allow_paid, use_env=False, existing=None):
    retained_key = existing.api_key if isinstance(existing, APISettings) else ""
    key = (
        os.getenv("DEEPSEEK_API_KEY", "") if use_env else key or retained_key
    ).strip()
    model = (model or "").strip()
    if not key:
        raise ValueError(
            "Enter your DeepSeek API key, or configure the selected .env key."
        )
    if len(key) > 512 or not re.fullmatch(r"[!-~]+", key):
        raise ValueError(
            "The API key must contain printable ASCII characters without spaces."
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}", model):
        raise ValueError("Enter a valid DeepSeek model name.")
    settings = APISettings(key, model, bool(allow_paid))
    message = "API settings applied for this session. The key field was cleared. "
    message += (
        "Select DeepSeek and run a project action when ready; usage may be billed."
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
        "Session API key cleared. DeepSeek generation is disabled.",
    )


def check_connection(settings: APISettings):
    if not isinstance(settings, APISettings) or not settings.api_key:
        raise ValueError("Apply an API key before checking the connection.")
    try:
        response = httpx.get(
            "https://api.deepseek.com/models",
            headers={"Authorization": "Bearer " + settings.api_key},
            timeout=15,
            follow_redirects=False,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            return "DeepSeek returned an unexpected model list. No generation was requested."
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
        if code in {401, 403}:
            return "DeepSeek rejected this key. Check your key and account permissions."
        return f"DeepSeek returned HTTP {code}. Check your account and retry."
    except httpx.TimeoutException:
        return "DeepSeek did not respond in time. Try checking again."
    except httpx.RequestError:
        return "Cannot reach DeepSeek. Check your internet connection."
    except (ValueError, TypeError):
        return "DeepSeek returned invalid model metadata. No generation was requested."


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
