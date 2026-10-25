import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma3:4b"
DEFAULT_TIMEOUT_SECONDS = 60


class OllamaServiceError(Exception):
    pass


def generate_text(prompt: str) -> str:
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise OllamaServiceError("Prompt is required")

    payload = _post_generate({"prompt": normalized_prompt})
    text = _extract_response_text(payload)
    if not text:
        raise OllamaServiceError("Ollama returned an empty response")
    return text


def generate_json(prompt: str) -> dict[str, Any]:
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise OllamaServiceError("Prompt is required")

    payload = _post_generate({"prompt": normalized_prompt, "format": "json"})
    text = _extract_response_text(payload)
    try:
        parsed = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        logger.warning("Ollama JSON parsing failed: %s", exc)
        raise OllamaServiceError("Ollama returned malformed JSON") from exc

    if not isinstance(parsed, dict):
        raise OllamaServiceError("Ollama did not return a JSON object")
    return parsed


def _post_generate(extra_payload: dict[str, Any]) -> dict[str, Any]:
    base_url = _base_url()
    model = _model_name()
    url = f"{base_url}/api/generate"
    payload = {
        "model": model,
        "stream": False,
        **extra_payload,
    }

    logger.info("Ollama request using model '%s'", model)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            raw_body = response.read().decode("utf-8")
    except TimeoutError as exc:
        raise OllamaServiceError("Ollama request timed out") from exc
    except urllib.error.HTTPError as exc:
        raise OllamaServiceError(f"Ollama HTTP error {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise OllamaServiceError(f"Ollama request failed: {exc.reason}") from exc
    except Exception as exc:  # noqa: BLE001
        raise OllamaServiceError("Ollama request failed") from exc

    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise OllamaServiceError("Ollama returned malformed response JSON") from exc
    if not isinstance(parsed, dict):
        raise OllamaServiceError("Ollama returned an unexpected response shape")
    return parsed


def _extract_response_text(payload: dict[str, Any]) -> str:
    text = payload.get("response")
    if text is None:
        raise OllamaServiceError("Ollama response missing 'response' text")
    return str(text).strip()


def _base_url() -> str:
    return (os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")


def _model_name() -> str:
    return (os.getenv("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL).strip() or DEFAULT_OLLAMA_MODEL
