import types

import pytest

from app.services import ai_service
from app.services.gemini_service import (
    GeminiServiceError,
    _generate_json_with_system_prompt,
    _parse_json_response,
    _parse_json_payload,
    generate_json,
    generate_text,
)


class _FakeResponse:
    def __init__(self, text=None, parts=None):
        self.text = text
        if parts is None:
            self.candidates = []
        else:
            self.candidates = [
                types.SimpleNamespace(
                    content=types.SimpleNamespace(
                        parts=[types.SimpleNamespace(text=part) for part in parts]
                    )
                )
            ]


class _FakeModel:
    def __init__(self, model_name, system_instruction=None, fail_models=None, response=None):
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.fail_models = fail_models or set()
        self.response = response or _FakeResponse(text="ok")

    def generate_content(self, prompt, generation_config=None):
        if self.model_name in self.fail_models:
            raise RuntimeError(f"boom:{self.model_name}")
        return self.response


class _FakeGenAI:
    def __init__(self, fail_models=None, response=None):
        self.fail_models = fail_models or set()
        self.response = response
        self.configured_key = None

    def configure(self, api_key):
        self.configured_key = api_key

    def GenerativeModel(self, model_name, system_instruction=None):
        return _FakeModel(
            model_name,
            system_instruction=system_instruction,
            fail_models=self.fail_models,
            response=self.response,
        )


def test_generate_text_returns_string(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "broken-model")
    fake_genai = _FakeGenAI(
        fail_models={"broken-model"},
        response=_FakeResponse(text="  hello from gemini  "),
    )
    monkeypatch.setattr("app.services.gemini_service._load_genai_module", lambda: fake_genai)

    result = generate_text("Say hello")

    assert result == "hello from gemini"
    assert fake_genai.configured_key == "test-key"


def test_generate_json_returns_dict(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    fake_genai = _FakeGenAI(response=_FakeResponse(text='{"ok": true, "value": 3}'))
    monkeypatch.setattr("app.services.gemini_service._load_genai_module", lambda: fake_genai)

    result = generate_json("Return JSON")

    assert result == {"ok": True, "value": 3}


def test_malformed_json_is_handled():
    assert _parse_json_payload('```json\n{"a":1}\n```') == {"a": 1}
    assert _parse_json_payload('prefix {"a": 2} suffix') == {"a": 2}
    with pytest.raises(GeminiServiceError):
        _parse_json_payload("not json at all")


def test_json_response_uses_candidate_parts_when_direct_text_is_truncated():
    response = _FakeResponse(
        text='{"reason":"truncated"',
        parts=[
            '{"reason":"Operational risk","severity":"medium","impact":"risk","affected_assignment_ids":[1],"suggestion":"Review workload","draft_details":"Manager note","summary":"Assignment risk detected"}'
        ],
    )

    result = _parse_json_response(response)

    assert result["reason"] == "Operational risk"
    assert result["affected_assignment_ids"] == [1]


def test_generate_json_retries_plain_text_when_json_mode_response_is_unusable(monkeypatch):
    class SwitchingModel:
        def __init__(self, model_name, system_instruction=None):
            self.model_name = model_name
            self.system_instruction = system_instruction

        def generate_content(self, prompt, generation_config=None):
            if generation_config and generation_config.get("response_mime_type") == "application/json":
                return _FakeResponse(text='{"reason":"truncated"')
            return _FakeResponse(
                text='{"reason":"Operational risk","severity":"medium","impact":"risk","affected_assignment_ids":[1],"suggestion":"Review workload","draft_details":"Manager note","summary":"Assignment risk detected"}'
            )

    class SwitchingGenAI:
        def configure(self, api_key):
            self.api_key = api_key

        def GenerativeModel(self, model_name, system_instruction=None):
            return SwitchingModel(model_name, system_instruction=system_instruction)

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.gemini_service._load_genai_module", lambda: SwitchingGenAI())

    result = _generate_json_with_system_prompt(
        "Return JSON",
        system_prompt="Be concise",
    )

    assert result["reason"] == "Operational risk"
    assert result["severity"] == "medium"


def test_ai_service_gemini_failure_triggers_mock_fallback(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setattr(
        "app.services.ai_service.generate_text_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(GeminiServiceError("gemini down")),
    )
    monkeypatch.setattr(
        "app.services.ai_service._mock_response",
        lambda messages: "mock fallback response",
    )

    result = ai_service.get_ai_response([{"role": "user", "content": "hello"}])

    assert result == "mock fallback response"
