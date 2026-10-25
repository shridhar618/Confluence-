import json
import urllib.error

import pytest

from app.services import ai_service
from app.services.ollama_service import OllamaServiceError, generate_json, generate_text


class _FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _fake_urlopen(payload, seen_requests=None):
    def opener(request, timeout=None):
        if seen_requests is not None:
            seen_requests.append((request, timeout))
        return _FakeHTTPResponse(payload)

    return opener


def test_generate_text_success(monkeypatch):
    seen_requests = []
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.local:11434/")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma3:4b")
    monkeypatch.setattr(
        "app.services.ollama_service.urllib.request.urlopen",
        _fake_urlopen({"response": "  hello from ollama  ", "done": True}, seen_requests),
    )

    result = generate_text("Say hello")

    assert result == "hello from ollama"
    request, timeout = seen_requests[0]
    assert request.full_url == "http://ollama.local:11434/api/generate"
    assert timeout == 60
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["model"] == "gemma3:4b"
    assert payload["prompt"] == "Say hello"
    assert payload["stream"] is False


def test_generate_json_success(monkeypatch):
    monkeypatch.setattr(
        "app.services.ollama_service.urllib.request.urlopen",
        _fake_urlopen({"response": '  {"ok": true, "value": 3}  ', "done": True}),
    )

    result = generate_json("Return JSON")

    assert result == {"ok": True, "value": 3}


def test_http_failure_raises_controlled_error(monkeypatch):
    def failing_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url,
            500,
            "server error",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("app.services.ollama_service.urllib.request.urlopen", failing_urlopen)

    with pytest.raises(OllamaServiceError, match="Ollama HTTP error 500"):
        generate_text("hello")


def test_malformed_json_failure(monkeypatch):
    monkeypatch.setattr(
        "app.services.ollama_service.urllib.request.urlopen",
        _fake_urlopen({"response": "not json", "done": True}),
    )

    with pytest.raises(OllamaServiceError, match="malformed JSON"):
        generate_json("Return JSON")


def test_ai_service_uses_ollama_provider(monkeypatch):
    seen_prompts = []
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setattr(
        "app.services.ai_service.generate_ollama_text",
        lambda prompt: seen_prompts.append(prompt) or "ollama provider response",
    )

    result = ai_service.get_ai_response([{"role": "user", "content": "hello"}])

    assert result == "ollama provider response"
    assert "User: hello" in seen_prompts[0]


def test_ai_service_ollama_failure_triggers_mock_fallback(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setattr(
        "app.services.ai_service.generate_ollama_text",
        lambda prompt: (_ for _ in ()).throw(OllamaServiceError("ollama down")),
    )
    monkeypatch.setattr(
        "app.services.ai_service._mock_response",
        lambda messages: "mock fallback response",
    )

    result = ai_service.get_ai_response([{"role": "user", "content": "hello"}])

    assert result == "mock fallback response"
