import logging
import re
import time
import uuid
from datetime import datetime
from typing import TypedDict

import httpx

from logging_config import PROMPT_LOGGER_NAME, session_log_extra
from services.context_window import CachedMessage

logger = logging.getLogger(__name__)
prompt_logger = logging.getLogger(PROMPT_LOGGER_NAME)

SYSTEM_PROMPT: str = """You are a friendly, warm, and lightly humorous conversation partner, especially when it comes to the user's occupation and interests.

Be direct and conversational. Keep your responses concise.

Rather than summarizing or restating what the user just said, respond with your own thoughts or ask a specific, natural follow-up question to keep the conversation going. Ask at least one specific question when it naturally fits, rather than leaving the user without something to respond to.

Avoid generic reflective openers like "It sounds like...", "Sounds like you're...", or "You seem...". Don't mirror the user's phrasing.

Stay non-judgmental and encouraging, but speak as if you're continuing a conversation, not giving a therapy summary."""

TITLE_PROMPT: str = """Generate a short, meaningful title (maximum 6 words) for a journaling session based on these journal entries. The title should capture the main theme or feeling of the session.

Respond only with the title text — no quotes, no explanations, no punctuation beyond what's in the title itself."""

ANALYSIS_TEMPERATURE: float = 0.3
TITLE_TEMPERATURE: float = 0.3

# Roughly 4 characters per token. Reserved for the reply.
CHARS_PER_TOKEN: int = 4
PROMPT_TOKEN_RESERVE: int = 1000


class AnalysisResult(TypedDict):
    content: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    request_id: str
    created_at: int


def _parse_created_at(raw: str | None) -> int:
    """Ollama returns an ISO-8601 timestamp; our DB stores a unix timestamp."""
    if not raw:
        return int(time.time())
    try:
        return int(datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp())
    except (ValueError, AttributeError):
        return int(time.time())


def _max_chars(num_ctx: int) -> int:
    return (num_ctx - PROMPT_TOKEN_RESERVE) * CHARS_PER_TOKEN


def _fit_text(
        text: str,
        num_ctx: int,
        max_chars: int | None = None,
) -> str:
    """Keep the start and end of over-long text so a long entry is not silently cut off.

    ``max_chars`` lets a caller reserve part of the budget (for the system
    prompt) without changing how the text itself is shortened.
    """
    limit: int = _max_chars(num_ctx) if max_chars is None else max_chars
    limit = max(1, limit)
    if len(text) <= limit:
        return text

    marker: str = "\n\n[...]\n\n"
    if limit <= len(marker):
        return text[:limit]

    # Leave room for the marker so the result actually fits ``limit``.
    body_length: int = limit - len(marker)
    head_length: int = body_length * 2 // 3
    tail_length: int = body_length - head_length
    tail: str = text[-tail_length:] if tail_length else ""
    logger.warning(
        "Input truncated from %d to %d characters to fit the model context (%d tokens)",
        len(text),
        limit,
        num_ctx,
    )
    return text[:head_length] + marker + tail


def _build_messages(
        system_prompt: str | None,
        history: list[CachedMessage],
        message: str,
        num_ctx: int,
) -> list[dict[str, str]]:
    """Compose the chat payload: system prompt, role-tagged history, new message.

    The current message is fitted first because it must never be lost. History
    is then prepended newest first for as long as the character budget allows,
    which keeps the most recent context and drops the oldest messages.
    """
    limit: int = _max_chars(num_ctx)

    messages: list[dict[str, str]] = []
    system_length: int = 0
    if system_prompt and system_prompt.strip():
        system_length = len(system_prompt)
        messages.append({"role": "system", "content": system_prompt})

    # The current message must survive, and the system prompt is fixed, so
    # history only gets whatever remains after both.
    current_budget: int = max(1, limit - system_length)
    current: str = _fit_text(message, num_ctx, max_chars=current_budget)

    remaining: int = max(0, current_budget - len(current))
    history_messages: list[dict[str, str]] = []
    for cached in reversed(history):
        if len(cached.content) > remaining:
            # History is chronological, and we walk it newest first. Stopping
            # here keeps a contiguous suffix; skipping this message to fit an
            # older one would leave a hole in the conversation.
            break
        history_messages.append(
            {"role": cached.role.value, "content": cached.content}
        )
        remaining -= len(cached.content)

    dropped: int = len(history) - len(history_messages)
    if dropped:
        logger.warning(
            "Dropped the %d oldest historical message(s) that did not fit "
            "the model context (%d tokens)",
            dropped,
            num_ctx,
        )

    history_messages.reverse()
    messages.extend(history_messages)
    messages.append({"role": "user", "content": current})
    return messages


def _log_messages(messages: list[dict[str, str]], session_id: uuid.UUID) -> None:
    """Write the exact text sent to the model into the session's log file.

    Uses ``prompt_logger``, whose level is pinned to DEBUG by
    ``configure_logging``, so the dump is always recorded even when LOG_LEVEL
    is INFO. The console handler is restricted to INFO, so it stays off the
    terminal. ``session_id`` routes the lines to that session's directory.
    """
    extra: dict[str, str] = session_log_extra(session_id)
    for index, message in enumerate(messages, start=1):
        prompt_logger.debug(
            "--- message %d/%d role=%s chars=%d ---\n%s\n--- end message %d ---",
            index,
            len(messages),
            message["role"],
            len(message["content"]),
            message["content"],
            index,
            extra=extra,
        )


async def _chat(
        http_client: httpx.AsyncClient,
        base_url: str,
        model: str,
        num_ctx: int,
        messages: list[dict[str, str]],
        temperature: float,
        force_json: bool,
        purpose: str,
        session_id: uuid.UUID,
        num_predict: int | None = None,
) -> dict:
    """Call Ollama's native /api/chat, which (unlike /v1) honours num_ctx."""
    options: dict[str, float | int] = {
        "num_ctx": num_ctx,
        "temperature": temperature,
    }
    if num_predict is not None:
        options["num_predict"] = num_predict

    body: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options,
    }
    if force_json:
        body["format"] = "json"

    extra: dict[str, str] = session_log_extra(session_id)
    total_chars: int = sum(len(message["content"]) for message in messages)
    logger.info(
        "Ollama request purpose=%s model=%s num_ctx=%d temperature=%s json=%s "
        "messages=%d chars=%d (~%d tokens)",
        purpose,
        model,
        num_ctx,
        temperature,
        force_json,
        len(messages),
        total_chars,
        total_chars // CHARS_PER_TOKEN,
        extra=extra,
    )
    _log_messages(messages, session_id)

    response = await http_client.post(f"{base_url}/api/chat", json=body)
    response.raise_for_status()
    data: dict = response.json()

    logger.info(
        "Ollama response purpose=%s model=%s prompt_tokens=%s completion_tokens=%s",
        purpose,
        data.get("model", model),
        data.get("prompt_eval_count", 0),
        data.get("eval_count", 0),
        extra=extra,
    )
    return data


def _empty_result(model: str) -> AnalysisResult:
    return AnalysisResult(
        content="",
        model_used=model,
        prompt_tokens=0,
        completion_tokens=0,
        request_id="",
        created_at=int(time.time()),
    )


async def analyze(
        message: str,
        context: list[CachedMessage],
        http_client: httpx.AsyncClient,
        base_url: str,
        model: str,
        num_ctx: int,
        session_id: uuid.UUID,
        system_prompt: str | None = None,
) -> AnalysisResult:
    extra: dict[str, str] = session_log_extra(session_id)
    try:
        messages: list[dict[str, str]] = _build_messages(
            system_prompt=system_prompt,
            history=context,
            message=message,
            num_ctx=num_ctx,
        )

        data = await _chat(
            http_client=http_client,
            base_url=base_url,
            model=model,
            num_ctx=num_ctx,
            messages=messages,
            temperature=ANALYSIS_TEMPERATURE,
            force_json=False,
            purpose="analysis",
            session_id=session_id,
        )

        content: str = data["message"]["content"].strip()
        logger.debug("Raw analysis content: %s", content, extra=extra)

        if not content:
            logger.warning("Ollama returned an empty reply for model %r", model, extra=extra)

        return AnalysisResult(
            content=content,
            model_used=data.get("model", model),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            request_id="",
            created_at=_parse_created_at(data.get("created_at")),
        )
    except httpx.TimeoutException:
        logger.warning(
            "Ollama analysis timed out. Local inference may be slower than "
            "OLLAMA_TIMEOUT_SECONDS; raise it if this keeps happening.",
            extra=extra,
        )
        return _empty_result(model)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Ollama analysis HTTP error: %s %s",
            exc.response.status_code,
            exc.response.text[:200],
            extra=extra,
        )
        return _empty_result(model)
    except Exception as exc:
        logger.warning("Ollama analysis failed: %s", exc, extra=extra)
        return _empty_result(model)


async def generate_title(
        transcripts: list[str],
        http_client: httpx.AsyncClient,
        base_url: str,
        model: str,
        num_ctx: int,
        session_id: uuid.UUID,
) -> str:
    extra: dict[str, str] = session_log_extra(session_id)
    try:
        combined: str = _fit_text("\n\n".join(transcripts), num_ctx)
        data = await _chat(
            http_client=http_client,
            base_url=base_url,
            model=model,
            num_ctx=num_ctx,
            messages=[
                {"role": "system", "content": TITLE_PROMPT},
                {"role": "user", "content": f"Journal entries:\n\n{combined}"},
            ],
            temperature=TITLE_TEMPERATURE,
            force_json=False,
            purpose="title",
            session_id=session_id,
        )

        content: str = data["message"]["content"].strip()
        content = re.sub(r"```(?:json)?\s*|\s*```", "", content).strip()
        lines: list[str] = [line.strip() for line in content.splitlines() if line.strip()]
        title: str = lines[0] if lines else content
        title = re.sub(r'^["\']|["\']$', "", title)
        title = re.sub(r"^[\-*•]+\s*", "", title)
        return title.strip()[:80]
    except httpx.TimeoutException:
        logger.warning(
            "Ollama title generation timed out. Local inference may be slower than "
            "OLLAMA_TIMEOUT_SECONDS; raise it if this keeps happening.",
            extra=extra,
        )
        return ""
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Ollama title generation HTTP error: %s %s",
            exc.response.status_code,
            exc.response.text[:200],
            extra=extra,
        )
        return ""
    except Exception as exc:
        logger.warning("Ollama title generation failed: %s", exc, extra=extra)
        return ""
