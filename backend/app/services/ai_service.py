"""
Modular AI service layer.
Supports OpenAI (GPT) and Google Gemini.
Falls back to a mock response if no API key is set (demo mode).
Also powers the local question bank, review queue, and dataset history.
"""

import csv
import io
import json
import logging
import os
import re
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .gemini_service import (
    GeminiServiceError,
    generate_json_response as generate_gemini_json_response,
    generate_text_response,
)
from .ollama_service import (
    OllamaServiceError,
    generate_json as generate_ollama_json,
    generate_text as generate_ollama_text,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are SecureAI, an enterprise assistant. "
    "Be helpful, professional, and concise. "
    "Never refuse reasonable workplace questions."
)

BASE_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
QUESTION_BANK_PATH = BASE_DATA_DIR / "mock_question_bank.json"
QUESTION_HISTORY_PATH = BASE_DATA_DIR / "mock_question_bank_history.json"
UNANSWERED_QUEUE_PATH = BASE_DATA_DIR / "unanswered_questions.json"

DEFAULT_ALLOWED_ROLES = ["admin", "hr", "intern"]
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "here", "how", "i",
    "in", "is", "me", "my", "of", "our", "the", "to", "what", "when", "with",
    "work", "you",
}
_FOLLOW_UP_PREFIXES = (
    "and ",
    "also ",
    "what about",
    "how about",
    "tell me more",
    "more on",
    "more about",
    "can you explain",
    "can you elaborate",
)
_FOLLOW_UP_TOKENS = {
    "and", "also", "that", "this", "it", "they", "them", "those", "these",
    "he", "she", "more", "too", "same", "continue",
}
_ML_MATCH_THRESHOLD = 0.28
_HEURISTIC_MATCH_THRESHOLD = 6


def get_ai_response(messages: list[dict]) -> str:
    """
    Dispatch to the configured AI provider.
    `messages` is a list of {role, content} dicts (OpenAI format).
    """
    provider = os.getenv("AI_PROVIDER", "gemini").lower()

    if provider == "openai":
        return _openai_response(messages)
    if provider == "gemini":
        return _gemini_response(messages)
    if provider == "ollama":
        return _ollama_response(messages)
    return _mock_response(messages)


def get_ai_json_response(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 900,
) -> dict[str, Any]:
    provider = os.getenv("AI_PROVIDER", "gemini").lower()

    if provider == "gemini":
        return generate_gemini_json_response(
            prompt,
            system_prompt=system_prompt or SYSTEM_PROMPT,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
    if provider == "ollama":
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt.strip()}\n\n{prompt.strip()}"
        return generate_ollama_json(full_prompt)

    raise ValueError(f"Structured AI provider is not configured: {provider}")


def list_mock_questions(role: str | None = None) -> list[dict]:
    question_bank = _filter_by_role(_load_question_bank(), role)
    return [serialize_question(item) for item in question_bank]


def search_mock_questions(query: str, role: str | None = None, limit: int = 25) -> list[dict]:
    query_text = " ".join(str(query or "").strip().lower().split())
    if not query_text:
        return list_mock_questions(role)[:limit]

    ranked = []
    for item in _filter_by_role(_load_question_bank(), role):
        score = _score_question_search(item, query_text)
        if score <= 0:
            continue
        ranked.append((score, item))

    ranked.sort(key=lambda pair: (-pair[0], pair[1]["question"].lower()))
    return [serialize_question(item) for _, item in ranked[:max(1, limit)]]


def get_question(question_id: str) -> dict | None:
    for item in _load_question_bank():
        if item["id"] == question_id:
            return dict(item)
    return None


def add_mock_question(
    question: str,
    answer: str,
    category: str = "General",
    keywords: list[str] | None = None,
    allowed_roles: list[str] | None = None,
    actor: str | None = None,
) -> dict:
    normalized_question = question.strip()
    normalized_answer = answer.strip()
    normalized_category = category.strip() or "General"
    normalized_keywords = _normalize_keywords(keywords or _extract_keywords(normalized_question))
    normalized_roles = _normalize_roles(allowed_roles)

    if not normalized_question:
        raise ValueError("Question is required")
    if not normalized_answer:
        raise ValueError("Answer is required")

    question_bank = _read_question_bank()
    entry = {
        "id": _build_unique_id(normalized_question, question_bank),
        "category": normalized_category,
        "question": normalized_question,
        "keywords": normalized_keywords,
        "allowed_roles": normalized_roles,
        "answer": normalized_answer,
    }
    question_bank.append(entry)
    _write_question_bank(question_bank)
    _append_history("create", entry["id"], actor=actor, after=entry)
    _clear_caches()
    return serialize_question(entry)


def update_mock_question(
    question_id: str,
    *,
    question: str,
    answer: str,
    category: str,
    keywords: list[str] | None = None,
    allowed_roles: list[str] | None = None,
    actor: str | None = None,
) -> dict:
    question_bank = _read_question_bank()
    for index, item in enumerate(question_bank):
        if item.get("id") != question_id:
            continue

        before = _normalize_question_record(item)
        updated = {
            "id": before["id"],
            "category": category.strip() or "General",
            "question": question.strip(),
            "keywords": _normalize_keywords(keywords or _extract_keywords(question)),
            "allowed_roles": _normalize_roles(allowed_roles),
            "answer": answer.strip(),
        }
        if not updated["question"]:
            raise ValueError("Question is required")
        if not updated["answer"]:
            raise ValueError("Answer is required")

        question_bank[index] = updated
        _write_question_bank(question_bank)
        _append_history("update", question_id, actor=actor, before=before, after=updated)
        _clear_caches()
        return serialize_question(updated, include_answer=True)

    raise ValueError("Question not found")


def delete_mock_question(question_id: str, actor: str | None = None) -> None:
    question_bank = _read_question_bank()
    new_bank = []
    removed = None
    for item in question_bank:
        if item.get("id") == question_id:
            removed = _normalize_question_record(item)
            continue
        new_bank.append(item)

    if removed is None:
        raise ValueError("Question not found")

    _write_question_bank(new_bank)
    _append_history("delete", question_id, actor=actor, before=removed)
    _clear_caches()


def import_mock_questions(entries: list[dict], actor: str | None = None) -> dict:
    if not isinstance(entries, list) or not entries:
        raise ValueError("Import payload must be a non-empty list")

    question_bank = _read_question_bank()
    existing_questions = {str(item.get("question", "")).strip().lower() for item in question_bank}
    imported = []
    skipped_duplicates = []
    for raw in entries:
        if not isinstance(raw, dict):
            raise ValueError("Each imported question must be an object")

        question = str(raw.get("question", "")).strip()
        answer = str(raw.get("answer", "")).strip()
        category = str(raw.get("category", "General")).strip() or "General"
        keywords = raw.get("keywords", [])
        allowed_roles = raw.get("allowed_roles", DEFAULT_ALLOWED_ROLES)
        if not question or not answer:
            raise ValueError("Each imported question must include question and answer")
        normalized_question_key = question.lower()
        if normalized_question_key in existing_questions:
            skipped_duplicates.append(question)
            continue

        entry = {
            "id": _build_unique_id(question, question_bank),
            "category": category,
            "question": question,
            "keywords": _normalize_keywords(keywords or _extract_keywords(question)),
            "allowed_roles": _normalize_roles(allowed_roles),
            "answer": answer,
        }
        question_bank.append(entry)
        existing_questions.add(normalized_question_key)
        imported.append(entry)
        _append_history("import", entry["id"], actor=actor, after=entry)

    _write_question_bank(question_bank)
    _clear_caches()
    return {
        "count": len(imported),
        "skipped_duplicates": skipped_duplicates,
        "questions": [serialize_question(item) for item in imported],
    }


def extract_questions_from_uploaded_file(filename: str, file_bytes: bytes) -> tuple[list[dict], dict]:
    normalized_name = (filename or "").strip().lower()
    if not normalized_name:
        raise ValueError("Uploaded file must have a filename")

    if normalized_name.endswith(".json"):
        questions = _extract_questions_from_json_bytes(file_bytes)
        return questions, {"source_type": "json", "detected_count": len(questions)}

    if normalized_name.endswith(".pdf"):
        questions, metadata = _extract_questions_from_pdf_bytes(file_bytes)
        return questions, metadata

    raise ValueError("Unsupported file type. Upload a .json or .pdf file")


def export_mock_questions_csv(role: str | None = None) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "category", "question", "keywords", "allowed_roles", "answer"])
    writer.writeheader()
    for item in _filter_by_role(_load_question_bank(), role):
        writer.writerow({
            "id": item["id"],
            "category": item["category"],
            "question": item["question"],
            "keywords": ", ".join(item["keywords"]),
            "allowed_roles": ", ".join(item["allowed_roles"]),
            "answer": item["answer"],
        })
    return buffer.getvalue()


def list_question_history(limit: int = 100) -> list[dict]:
    history = _read_json_array(QUESTION_HISTORY_PATH)
    history.reverse()
    return history[:limit]


def list_unanswered_questions(status: str | None = None) -> list[dict]:
    unresolved = _read_json_array(UNANSWERED_QUEUE_PATH)
    if status:
        unresolved = [item for item in unresolved if item.get("status") == status]
    unresolved.sort(key=lambda item: item.get("last_seen_at", ""), reverse=True)
    return unresolved


def capture_unanswered_question(query: str, role: str, username: str) -> dict:
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Query is required")

    queue = _read_json_array(UNANSWERED_QUEUE_PATH)
    now = datetime.now(UTC).isoformat()
    for item in queue:
        if item.get("query", "").strip().lower() == normalized_query.lower():
            item["count"] = int(item.get("count", 1)) + 1
            item["last_seen_at"] = now
            item["latest_role"] = role
            item["latest_username"] = username
            _write_json_array(UNANSWERED_QUEUE_PATH, queue)
            return item

    entry = {
        "id": _build_queue_id(normalized_query),
        "query": normalized_query,
        "count": 1,
        "status": "open",
        "created_at": now,
        "last_seen_at": now,
        "latest_role": role,
        "latest_username": username,
        "resolution_note": "",
    }
    queue.append(entry)
    _write_json_array(UNANSWERED_QUEUE_PATH, queue)
    return entry


def resolve_unanswered_question(queue_id: str, status: str, resolution_note: str = "") -> dict:
    valid_statuses = {"open", "resolved", "ignored"}
    if status not in valid_statuses:
        raise ValueError("Invalid queue status")

    queue = _read_json_array(UNANSWERED_QUEUE_PATH)
    for item in queue:
        if item.get("id") == queue_id:
            item["status"] = status
            item["resolution_note"] = resolution_note.strip()
            item["resolved_at"] = datetime.now(UTC).isoformat() if status != "open" else None
            _write_json_array(UNANSWERED_QUEUE_PATH, queue)
            return item
    raise ValueError("Queue item not found")


def find_question_match_for_query(query: str, role: str | None = None) -> dict | None:
    return _match_question(query, role)


def infer_question_category(query: str) -> str | None:
    matched = _match_question(query, role=None)
    return matched["category"] if matched else None


def resolve_contextual_query(messages: list[dict]) -> str:
    candidates = _build_contextual_query_candidates(messages)
    return candidates[0] if candidates else ""


def get_suggested_questions(query: str, role: str | None = None, limit: int = 4) -> list[dict]:
    candidates = _filter_by_role(_load_question_bank(), role)
    if not candidates:
        return []

    matched = _match_question(query, role)
    suggestions = []
    seen = set()

    if matched:
        for item in candidates:
            if item["id"] == matched["id"]:
                continue
            if item["category"] == matched["category"] or set(item["keywords"]) & set(matched["keywords"]):
                suggestions.append(serialize_question(item))
                seen.add(item["id"])
                if len(suggestions) >= limit:
                    return suggestions

    for item in candidates:
        if item["id"] in seen:
            continue
        suggestions.append(serialize_question(item))
        if len(suggestions) >= limit:
            break
    return suggestions


def get_question_bank_analytics(logs: list[dict], feedback_rows: list[dict]) -> dict:
    questions = _load_question_bank()
    question_map = {item["question"].lower(): item for item in questions}
    counts = {}
    blocked_by_role = {}

    for log in logs:
        query_text = str(log.get("query", "")).strip().lower()
        if query_text in question_map:
            item = question_map[query_text]
            counts[item["question"]] = counts.get(item["question"], 0) + 1

        role = log.get("role", "unknown")
        if log.get("status") == "blocked":
            blocked_by_role[role] = blocked_by_role.get(role, 0) + 1

    top_questions = sorted(
        [{"question": question, "count": count} for question, count in counts.items()],
        key=lambda item: (-item["count"], item["question"].lower()),
    )[:5]

    unhelpful_counts = {}
    for row in feedback_rows:
        if row.get("value") != "unhelpful":
            continue
        query_text = str(row.get("query", "")).strip()
        if not query_text:
            continue
        unhelpful_counts[query_text] = unhelpful_counts.get(query_text, 0) + 1

    low_quality = sorted(
        [{"query": query, "count": count} for query, count in unhelpful_counts.items()],
        key=lambda item: (-item["count"], item["query"].lower()),
    )[:5]

    unanswered = list_unanswered_questions()
    open_unanswered = [item for item in unanswered if item.get("status") == "open"]

    return {
        "question_bank_total": len(questions),
        "top_questions": top_questions,
        "blocked_by_role": blocked_by_role,
        "unanswered_count": len(open_unanswered),
        "open_unanswered": open_unanswered[:5],
        "low_quality_responses": low_quality,
    }


def serialize_question(item: dict, *, include_answer: bool = False) -> dict:
    result = {
        "id": item["id"],
        "category": item["category"],
        "question": item["question"],
        "keywords": item["keywords"],
        "allowed_roles": item["allowed_roles"],
    }
    if include_answer:
        result["answer"] = item["answer"]
    return result


def _openai_response(messages: list[dict]) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        return _mock_response(messages)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=full_messages,
            max_tokens=800,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("OpenAI error: %s", exc)
        return _fallback_error(str(exc))


def _gemini_response(messages: list[dict]) -> str:
    try:
        return generate_text_response(
            messages,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=800,
        )
    except GeminiServiceError as exc:
        logger.error("Gemini error; using mock fallback: %s", exc)
        return _mock_response(messages)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected Gemini error: %s", exc)
        return _fallback_error(str(exc))


def _ollama_response(messages: list[dict]) -> str:
    try:
        return generate_ollama_text(_messages_to_prompt(messages))
    except OllamaServiceError as exc:
        logger.error("Ollama error; using mock fallback: %s", exc)
        return _mock_response(messages)
    except Exception as exc:
        logger.error("Unexpected Ollama error: %s", exc)
        return _fallback_error(str(exc))


def _messages_to_prompt(messages: list[dict]) -> str:
    lines = [SYSTEM_PROMPT, ""]
    for message in messages:
        role = str(message.get("role", "user")).strip().lower()
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        if role == "assistant":
            lines.append(f"Assistant: {content}")
        else:
            lines.append(f"User: {content}")
    lines.append("Assistant:")
    return "\n".join(lines).strip()


def _mock_response(messages: list[dict]) -> str:
    for candidate in _build_contextual_query_candidates(messages):
        matched_entry = _match_question(candidate)
        if matched_entry:
            return matched_entry["answer"]

    return (
        "I'm SecureAI running in demo mode (no API key configured). "
        "I could not find a strong dataset match for that question yet, so I logged it for admin review. "
        "Please configure an AI provider in .env for full open-ended responses."
    )


def _fallback_error(err: str) -> str:
    return (
        "I encountered an issue connecting to the AI provider. "
        "Please check your API key configuration. "
        f"Technical detail: {err[:120]}"
    )


@lru_cache(maxsize=1)
def _load_question_bank() -> list[dict]:
    _ensure_data_files()
    return [_normalize_question_record(item) for item in _read_question_bank()]


@lru_cache(maxsize=1)
def _get_question_bank_index() -> dict | None:
    question_bank = _load_question_bank()
    if not question_bank:
        return None

    documents = [_build_training_text(item) for item in question_bank]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    matrix = vectorizer.fit_transform(documents)
    return {
        "questions": question_bank,
        "vectorizer": vectorizer,
        "matrix": matrix,
    }


def _read_question_bank() -> list[dict]:
    _ensure_data_files()
    with QUESTION_BANK_PATH.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)
    if not isinstance(data, list):
        raise ValueError("Mock question bank must be a list")
    return data


def _write_question_bank(question_bank: list[dict]) -> None:
    _ensure_data_files()
    with QUESTION_BANK_PATH.open("w", encoding="utf-8") as file_obj:
        json.dump(question_bank, file_obj, indent=2)
        file_obj.write("\n")


def _extract_questions_from_json_bytes(file_bytes: bytes) -> list[dict]:
    try:
        payload = json.loads(file_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("JSON file must be UTF-8 encoded") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("JSON file is not valid JSON") from exc

    if isinstance(payload, list):
        entries = payload
    elif isinstance(payload, dict) and isinstance(payload.get("questions"), list):
        entries = payload["questions"]
    else:
        raise ValueError("JSON file must contain an array or an object with a 'questions' array")

    if not entries:
        raise ValueError("JSON file does not contain any questions")
    return entries


def _extract_questions_from_pdf_bytes(file_bytes: bytes) -> tuple[list[dict], dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF import requires the 'pypdf' package to be installed") from exc

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError("Unable to read the uploaded PDF") from exc

    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)

    extracted_text = "\n\n".join(pages).strip()
    if not extracted_text:
        raise ValueError("Could not extract readable text from the PDF")

    json_match = _extract_json_blob(extracted_text)
    if json_match is not None:
        return _extract_questions_from_json_bytes(json_match.encode("utf-8")), {
            "source_type": "pdf",
            "parse_mode": "embedded_json",
            "page_count": len(reader.pages),
        }

    parsed = _parse_structured_pdf_text(extracted_text)
    if not parsed:
        raise ValueError(
            "Could not detect question records in the PDF. Use labeled fields like 'Question:' and 'Answer:' or embed JSON."
        )

    return parsed, {
        "source_type": "pdf",
        "parse_mode": "labeled_text",
        "page_count": len(reader.pages),
        "detected_count": len(parsed),
    }


def _extract_json_blob(text: str) -> str | None:
    start_positions = [index for index in (text.find("["), text.find("{")) if index != -1]
    if not start_positions:
        return None

    decoder = json.JSONDecoder()
    for start in sorted(start_positions):
        try:
            payload, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list) or (isinstance(payload, dict) and isinstance(payload.get("questions"), list)):
            return text[start:start + end]
    return None


def _parse_structured_pdf_text(text: str) -> list[dict]:
    normalized_text = text.replace("\r\n", "\n")
    blocks = [block.strip() for block in re.split(r"\n\s*\n", normalized_text) if block.strip()]
    questions = []
    current_block = []

    for block in blocks:
        if re.search(r"(?im)^(question|q)\s*:", block) and current_block:
            parsed = _parse_question_block("\n\n".join(current_block))
            if parsed:
                questions.append(parsed)
            current_block = [block]
            continue
        current_block.append(block)

    if current_block:
        parsed = _parse_question_block("\n\n".join(current_block))
        if parsed:
            questions.append(parsed)

    return questions


def _parse_question_block(block: str) -> dict | None:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return None

    fields: dict[str, Any] = {}
    active_key = None
    label_map = {
        "question": "question",
        "q": "question",
        "answer": "answer",
        "a": "answer",
        "category": "category",
        "keywords": "keywords",
        "keyword": "keywords",
        "allowed roles": "allowed_roles",
        "roles": "allowed_roles",
        "role": "allowed_roles",
    }

    for line in lines:
        match = re.match(r"^(Question|Q|Answer|A|Category|Keywords?|Allowed Roles?|Roles?)\s*:\s*(.*)$", line, re.IGNORECASE)
        if match:
            active_key = label_map[match.group(1).strip().lower()]
            value = match.group(2).strip()
            if active_key in {"keywords", "allowed_roles"}:
                fields[active_key] = _split_inline_list(value)
            else:
                fields[active_key] = value
            continue

        if active_key == "answer":
            fields["answer"] = f"{fields.get('answer', '')}\n{line}".strip()
        elif active_key == "question":
            fields["question"] = f"{fields.get('question', '')} {line}".strip()
        elif active_key in {"keywords", "allowed_roles"}:
            fields[active_key] = fields.get(active_key, []) + _split_inline_list(line)

    if not fields.get("question") or not fields.get("answer"):
        return None

    return {
        "question": fields["question"],
        "answer": fields["answer"],
        "category": fields.get("category", "General"),
        "keywords": fields.get("keywords", []),
        "allowed_roles": fields.get("allowed_roles", DEFAULT_ALLOWED_ROLES),
    }


def _split_inline_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,;/]", value) if item.strip()]


def _match_question(query: str, role: str | None = None) -> dict | None:
    query_text = (query or "").strip().lower()
    if not query_text:
        return None

    ml_match = _match_question_with_ml(query_text, role)
    if ml_match:
        return ml_match

    return _match_question_with_heuristics(query_text, role)


def _score_question_search(item: dict, query_text: str) -> int:
    query_tokens = set(_extract_keywords(query_text))
    if not query_tokens and not query_text:
        return 0

    question_text = item["question"].lower()
    category_text = item["category"].lower()
    answer_text = item["answer"].lower()
    aliases = item.get("aliases", [])
    score = 0

    if query_text == question_text:
        score += 100
    elif query_text in question_text:
        score += 40

    if query_text == category_text:
        score += 30
    elif query_text in category_text:
        score += 12

    for keyword in item["keywords"]:
        keyword_text = keyword.lower()
        if query_text == keyword_text:
            score += 50
        elif _keyword_in_text(keyword_text, query_text) or _keyword_in_text(query_text, keyword_text):
            score += 20

    for alias in aliases:
        alias_text = alias.lower()
        if query_text == alias_text:
            score += 35
        elif query_text in alias_text or alias_text in query_text:
            score += 18

    question_tokens = set(_extract_keywords(question_text))
    keyword_tokens = set()
    for keyword in item["keywords"]:
        keyword_tokens.update(_extract_keywords(keyword))
    category_tokens = set(_extract_keywords(category_text))
    alias_tokens = set()
    for alias in aliases:
        alias_tokens.update(_extract_keywords(alias))
    answer_tokens = set(_extract_keywords(answer_text))

    score += len(query_tokens & question_tokens) * 8
    score += len(query_tokens & keyword_tokens) * 10
    score += len(query_tokens & category_tokens) * 6
    score += len(query_tokens & alias_tokens) * 6
    score += min(3, len(query_tokens & answer_tokens)) * 2

    return score


def _build_contextual_query_candidates(messages: list[dict]) -> list[str]:
    current_user_message = ""
    previous_user_message = ""
    recent_assistant_message = ""

    for message in reversed(messages):
        role = message.get("role")
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        if role == "user" and not current_user_message:
            current_user_message = content
            continue
        if role == "assistant" and not recent_assistant_message:
            recent_assistant_message = content
            continue
        if role == "user" and not previous_user_message:
            previous_user_message = content
            break

    if not current_user_message:
        return []

    candidates = [current_user_message.lower()]
    if not previous_user_message or not _looks_like_follow_up(current_user_message):
        return candidates

    combined_user_context = f"{previous_user_message} {current_user_message}".strip().lower()
    candidates.append(combined_user_context)

    if recent_assistant_message:
        candidates.append(f"{previous_user_message} {recent_assistant_message} {current_user_message}".strip().lower())

    return candidates


def _looks_like_follow_up(query: str) -> bool:
    normalized_query = " ".join((query or "").strip().lower().split())
    if not normalized_query:
        return False

    if normalized_query.startswith(_FOLLOW_UP_PREFIXES):
        return True

    tokens = _tokenize(normalized_query)
    if len(tokens) <= 5 and any(token in _FOLLOW_UP_TOKENS for token in tokens):
        return True

    return False


def _match_question_with_ml(query_text: str, role: str | None = None) -> dict | None:
    index = _get_question_bank_index()
    if not index:
        return None

    filtered_questions = _filter_by_role(index["questions"], role)
    if not filtered_questions:
        return None

    query_vector = index["vectorizer"].transform([query_text])
    similarities = cosine_similarity(query_vector, index["matrix"]).ravel()
    ranked_indices = np.argsort(similarities)[::-1]

    allowed_ids = {item["id"] for item in filtered_questions}

    for index_value in ranked_indices:
        item = index["questions"][int(index_value)]
        if item["id"] not in allowed_ids:
            continue

        score = float(similarities[int(index_value)])
        if score >= _ML_MATCH_THRESHOLD:
            return item

    return None


def _match_question_with_heuristics(query_text: str, role: str | None = None) -> dict | None:
    query_tokens = set(_extract_keywords(query_text))
    best_match = None
    best_score = 0

    for item in _filter_by_role(_load_question_bank(), role):
        score = 0
        question_text = item["question"].lower()

        if query_text == question_text:
            score += 100
        elif question_text in query_text or query_text in question_text:
            score += 30

        for alias in item.get("aliases", []):
            if query_text == alias:
                score += 60
            elif alias in query_text or query_text in alias:
                score += 24

        for keyword in item["keywords"]:
            keyword_text = keyword.lower()
            if keyword_text and _keyword_in_text(keyword_text, query_text):
                score += 10

        question_tokens = set(_extract_keywords(question_text))
        alias_tokens = set()
        for alias in item.get("aliases", []):
            alias_tokens.update(_extract_keywords(alias))
        answer_tokens = set(_extract_keywords(item["answer"]))
        score += len(query_tokens & question_tokens) * 2
        score += len(query_tokens & alias_tokens) * 2
        score += min(3, len(query_tokens & answer_tokens))

        if score > best_score:
            best_score = score
            best_match = item

    return best_match if best_score >= _HEURISTIC_MATCH_THRESHOLD else None


def _filter_by_role(question_bank: list[dict], role: str | None) -> list[dict]:
    if not role:
        return question_bank
    return [item for item in question_bank if role in item["allowed_roles"]]


def _normalize_question_record(item: dict) -> dict:
    return {
        "id": str(item["id"]),
        "category": str(item.get("category", "General")).strip() or "General",
        "question": str(item["question"]).strip(),
        "aliases": _normalize_aliases(item.get("aliases", [])),
        "keywords": _normalize_keywords(item.get("keywords", [])),
        "allowed_roles": _normalize_roles(item.get("allowed_roles", DEFAULT_ALLOWED_ROLES)),
        "answer": str(item["answer"]).strip(),
    }


def _append_history(action: str, question_id: str, *, actor: str | None, before: dict | None = None, after: dict | None = None) -> None:
    history = _read_json_array(QUESTION_HISTORY_PATH)
    history.append({
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "question_id": question_id,
        "actor": actor or "system",
        "before": before,
        "after": after,
    })
    _write_json_array(QUESTION_HISTORY_PATH, history)


def _ensure_data_files() -> None:
    BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for path in (QUESTION_HISTORY_PATH, UNANSWERED_QUEUE_PATH):
        if not path.exists():
            _write_json_array(path, [])


def _read_json_array(path: Path) -> list[dict]:
    _ensure_data_files()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)
    return data if isinstance(data, list) else []


def _write_json_array(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        json.dump(values, file_obj, indent=2)
        file_obj.write("\n")


def _clear_caches() -> None:
    _load_question_bank.cache_clear()
    _get_question_bank_index.cache_clear()


def _build_unique_id(question: str, question_bank: list[dict]) -> str:
    existing_ids = {str(item.get("id", "")).strip() for item in question_bank}
    slug = "-".join(_tokenize(question)) or "question"
    candidate = slug
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


def _build_queue_id(query: str) -> str:
    return f"{'-'.join(_tokenize(query))[:40] or 'question'}-{int(datetime.now(UTC).timestamp())}"


def _normalize_keywords(keywords: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for keyword in keywords:
        value = str(keyword).strip().lower()
        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)
    return cleaned


def _normalize_aliases(aliases: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for alias in aliases:
        value = " ".join(str(alias).strip().lower().split())
        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)
    return cleaned


def _normalize_roles(roles: list[str] | None) -> list[str]:
    normalized = []
    seen = set()
    raw_roles = roles or DEFAULT_ALLOWED_ROLES
    for role in raw_roles:
        value = str(role).strip().lower()
        if value in {"admin", "hr", "intern"} and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized or DEFAULT_ALLOWED_ROLES.copy()


def _build_training_text(item: dict) -> str:
    alias_text = " ".join(item.get("aliases", []))
    keyword_text = " ".join(item["keywords"])
    answer_tokens = " ".join(_extract_keywords(item["answer"]))[:300]
    return f"{item['category']} {item['question']} {alias_text} {alias_text} {keyword_text} {keyword_text} {answer_tokens}"


def _keyword_in_text(keyword: str, text: str) -> bool:
    keyword_tokens = _tokenize(keyword)
    text_tokens = _tokenize(text)
    if not keyword_tokens or not text_tokens:
        return False

    if len(keyword_tokens) == 1:
        return keyword_tokens[0] in set(text_tokens)

    window_size = len(keyword_tokens)
    for index in range(len(text_tokens) - window_size + 1):
        if text_tokens[index:index + window_size] == keyword_tokens:
            return True
    return False


def _extract_keywords(question: str) -> list[str]:
    return [token for token in _tokenize(question) if token not in _STOP_WORDS]


def _tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN_PATTERN.findall(text.lower()) if token]
