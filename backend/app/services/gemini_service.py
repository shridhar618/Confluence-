import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
]


class GeminiServiceError(Exception):
    pass


def gemini_is_configured() -> bool:
    api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"')
    return bool(api_key and not api_key.startswith("your-"))


def generate_text(prompt: str) -> str:
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise GeminiServiceError("Prompt is required")
    return _generate_text_with_system_prompt(
        normalized_prompt,
        system_prompt=None,
        temperature=0.7,
        max_output_tokens=800,
    )


def generate_json(prompt: str) -> dict[str, Any]:
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise GeminiServiceError("Prompt is required")

    payload = _generate_json_with_system_prompt(
        normalized_prompt,
        system_prompt=None,
        temperature=0.2,
        max_output_tokens=900,
    )
    if not isinstance(payload, dict):
        raise GeminiServiceError("Gemini did not return a JSON object")
    return payload


def generate_text_response(
    messages: list[dict],
    *,
    system_prompt: str,
    model_name: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 800,
) -> str:
    prompt = _messages_to_prompt(messages)
    return _generate_text_with_system_prompt(
        prompt,
        system_prompt=system_prompt,
        model_name=model_name,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def generate_json_response(
    prompt: str,
    *,
    system_prompt: str,
    model_name: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 900,
) -> dict[str, Any]:
    payload = _generate_json_with_system_prompt(
        prompt,
        system_prompt=system_prompt,
        model_name=model_name,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    if not isinstance(payload, dict):
        raise GeminiServiceError("Gemini did not return a JSON object")
    return payload


def _generate_text_with_system_prompt(
    prompt: str,
    *,
    system_prompt: str | None,
    model_name: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 800,
) -> str:
    if not gemini_is_configured():
        raise GeminiServiceError("Gemini API key is not configured")

    genai = _load_genai_module()
    api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"')
    genai.configure(api_key=api_key)

    last_error = None
    for candidate_model in _candidate_models(model_name):
        try:
            logger.info("Gemini text request using model '%s'", candidate_model)
            model = genai.GenerativeModel(
                model_name=candidate_model,
                system_instruction=system_prompt,
            )
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                },
            )
            text = _extract_text(response)
            if not text:
                raise GeminiServiceError("Gemini returned an empty response")
            return text
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Gemini text model '%s' failed: %s", candidate_model, exc)

    raise GeminiServiceError(str(last_error or "Gemini text generation failed"))


def _generate_json_with_system_prompt(
    prompt: str,
    *,
    system_prompt: str | None,
    model_name: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 900,
) -> dict[str, Any]:
    if not gemini_is_configured():
        raise GeminiServiceError("Gemini API key is not configured")

    genai = _load_genai_module()
    api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"')
    genai.configure(api_key=api_key)

    last_error = None
    for candidate_model in _candidate_models(model_name):
        try:
            logger.info("Gemini JSON request using model '%s'", candidate_model)
            model = genai.GenerativeModel(
                model_name=candidate_model,
                system_instruction=system_prompt,
            )
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_output_tokens,
                        "response_mime_type": "application/json",
                    },
                )
                return _parse_json_response(response)
            except GeminiServiceError as exc:
                logger.warning(
                    "Gemini JSON-mode parsing failed for model '%s'; retrying as plain text: %s",
                    candidate_model,
                    exc,
                )
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_output_tokens,
                    },
                )
                return _parse_json_response(response)
        except GeminiServiceError as exc:
            last_error = exc
            logger.warning("Gemini JSON parsing failed for model '%s': %s", candidate_model, exc)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Gemini JSON model '%s' failed: %s", candidate_model, exc)

    raise GeminiServiceError(str(last_error or "Gemini JSON generation failed"))


def _load_genai_module():
    try:
        import google.generativeai as genai
    except Exception as exc:  # noqa: BLE001
        raise GeminiServiceError("google-generativeai is not installed") from exc
    return genai


def _candidate_models(model_name: str | None) -> list[str]:
    configured_model = (model_name or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip()
    raw_candidates = [configured_model, *DEFAULT_FALLBACK_MODELS]

    candidates = []
    seen = set()
    for raw in raw_candidates:
        normalized = raw.removeprefix("models/").strip()
        if normalized and normalized not in seen:
            candidates.append(normalized)
            seen.add(normalized)
    return candidates


def _extract_text(response: Any) -> str:
    direct_text = getattr(response, "text", None)
    if direct_text:
        return str(direct_text).strip()

    candidates = getattr(response, "candidates", None) or []
    parts = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            text = getattr(part, "text", None)
            if text:
                parts.append(str(text))

    extracted = "\n".join(parts).strip()
    if extracted:
        return extracted
    raise GeminiServiceError("Gemini returned no extractable text")


def _extract_text_from_candidates(response: Any) -> str:
    candidates = getattr(response, "candidates", None) or []
    parts = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            text = getattr(part, "text", None)
            if text:
                parts.append(str(text))

    extracted = "\n".join(parts).strip()
    if extracted:
        return extracted
    raise GeminiServiceError("Gemini returned no extractable candidate text")


def _parse_json_response(response: Any) -> dict[str, Any]:
    errors = []
    seen = set()

    for extractor in (
        lambda: getattr(response, "text", None),
        lambda: _extract_text_from_candidates(response),
        lambda: _extract_text(response),
    ):
        try:
            raw_text = extractor()
        except GeminiServiceError as exc:
            errors.append(str(exc))
            continue

        normalized = str(raw_text or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)

        try:
            return _parse_json_payload(normalized)
        except GeminiServiceError as exc:
            errors.append(str(exc))
            continue

    raise GeminiServiceError(errors[-1] if errors else "Gemini JSON generation failed")


def _parse_json_payload(text: str) -> dict[str, Any]:
    cleaned = str(text or "").strip()
    if not cleaned:
        raise GeminiServiceError("Gemini returned empty JSON text")

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Gemini JSON parse failed on first attempt")

    fenced = cleaned
    if fenced.startswith("```"):
        fenced = fenced.strip("`")
        if fenced.lower().startswith("json\n"):
            fenced = fenced[5:]
        fenced = fenced.strip()
        try:
            return json.loads(fenced)
        except json.JSONDecodeError:
            logger.warning("Gemini fenced JSON parse failed")

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            logger.warning("Gemini JSON block extraction failed")
            raise GeminiServiceError("Gemini returned malformed JSON") from exc

    raise GeminiServiceError("Gemini returned malformed JSON")


def _messages_to_prompt(messages: list[dict]) -> str:
    prompt_lines = []
    last_user_message = ""
    for message in messages:
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        if role == "assistant":
            prompt_lines.append(f"Assistant: {content}")
        elif role == "user":
            prompt_lines.append(f"User: {content}")
            last_user_message = content

    if not last_user_message:
        raise GeminiServiceError("No user message provided to Gemini")

    return "\n".join(prompt_lines)
