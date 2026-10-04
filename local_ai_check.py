"""Check local Ollama availability; optionally test one synthetic structured response."""

from __future__ import annotations

import argparse
import json
from typing import Literal

import httpx
from pydantic import BaseModel

from ai import AIError, PROVIDERS, generate, local_settings


class SmokeReply(BaseModel):
    status: Literal["ready"]


def _tag(name: str) -> str:
    return name if ":" in name.rsplit("/", 1)[-1] else name + ":latest"


def check_local_ai(generate_sample: bool = False) -> dict:
    result = {"ready": False, "inference_tested": False}
    try:
        base, model, context = local_settings()
        result.update(model=model, context_tokens=context)
        response = httpx.get(
            base + "/api/tags", timeout=5, follow_redirects=False, trust_env=False
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("models"), list):
            raise AIError(
                "Ollama returned an unexpected model list. Check that the configured port runs Ollama."
            )
        names = {
            _tag(name)
            for item in data["models"]
            if isinstance(item, dict)
            for name in [item.get("name") or item.get("model")]
            if isinstance(name, str)
        }
        if _tag(model) not in names:
            result["message"] = (
                f"Ollama is running, but the configured model is missing. Run: ollama pull {model}"
            )
            return result
        if generate_sample:
            generate(
                SmokeReply,
                'Return {"status":"ready"} from the supplied status. Do not add other fields.',
                "Status: ready",
                PROVIDERS[1],
            )
            result.update(
                ready=True,
                inference_tested=True,
                message="Local AI generated a valid sample response. This checks connectivity and structured output, not project-specific accuracy.",
            )
        else:
            result.update(
                ready=True,
                message="Ollama is reachable and the configured model is installed. Use Test local AI to verify generation. Memory use and output quality are not checked yet.",
            )
    except AIError as exc:
        result["message"] = str(exc)
    except httpx.TimeoutException:
        result["message"] = (
            "Ollama did not respond within 5 seconds. Check the service and try again."
        )
    except httpx.HTTPStatusError as exc:
        result["message"] = (
            f"Ollama returned HTTP {exc.response.status_code}. Check OLLAMA_BASE_URL and the local service."
        )
    except httpx.RequestError:
        result["message"] = (
            "Cannot reach Ollama. Open the Ollama app or run ollama serve, then check again. Offline demo mode still works."
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        result["message"] = (
            "The local service returned invalid JSON. Check that OLLAMA_BASE_URL points to Ollama."
        )
    return result


def status_text(generate_sample: bool = False) -> str:
    result = check_local_ai(generate_sample)
    prefix = "PASS" if result["ready"] else "SETUP NEEDED"
    return f"{prefix}: {result['message']}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Run a tiny local inference test; never calls DeepSeek.",
    )
    args = parser.parse_args(argv)
    result = check_local_ai(args.generate)
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
