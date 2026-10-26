import json
import logging
import re
import time
import uuid
from datetime import datetime
from typing import TypedDict

import httpx

from logging_config import PROMPT_LOGGER_NAME, session_log_extra

logger = logging.getLogger(__name__)
prompt_logger = logging.getLogger(PROMPT_LOGGER_NAME)

SYSTEM_PROMPT: str = """You are a plain, direct assistant. You receive zero or more earlier entries from the same journaling session, then one current entry. Treat the earlier entries as background only and respond to the current entry.

Classify the current entry:
- "venting": the person needs to be heard, not analyzed.
- "clarity": the person is unsure what they feel and wants help naming it.
- "heard": the person knows what they feel and just needed to say it.

Reply in one or two sentences. No advice, no questions, no therapy language.

You MUST respond ONLY with valid JSON matching this exact schema with no extra text, markdown, or code fences:
{
  "mode": "venting" | "clarity" | "heard",
  "reflection": "string"
}"""

TITLE_PROMPT: str = """Generate a short, meaningful title (maximum 6 words) for a journaling session based on these journal entries. The title should capture the main theme or feeling of the session.

Respond only with the title text — no quotes, no explanations, no punctuation beyond what's in the title itself."""

ANALYSIS_TEMPERATURE: float = 0.4
TITLE_TEMPERATURE: float = 0.3

# Roughly 4 characters per token. Reserved for the system prompt and reply.
CHARS_PER_TOKEN: int = 4
PROMPT_TOKEN_RESERVE: int = 1000


class AnalysisResult(TypedDict):
    reflection: str
    detected_mode: str | None
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    request_id: str
    created_at: int


def _normalize_mode(mode: str | None) -> str | None:
    """Map model output onto the three modes we accept, or None if it made one up."""
    if not mode:
        return None
    m: str = str(mode).strip().lower().replace(" ", "").replace("-", "")
    if m == "venting":
        return "venting"
    if m == "clarity":
        return "clarity"
    if m in ("heard", "heared", "hear", "hearing"):
        return "heard"
    return None


def _extract_json_object(content: str) -> str:
    """Strip code fences and surrounding prose, leaving the JSON object."""
    content = content.strip()
    content = re.sub(r"```(?:json)?\s*|\s*```", "", content).strip()
    if content.startswith("{") and content.endswith("}"):
        return content
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        return match.group(0)
    return content


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


def _fit_text(text: str, num_ctx: int) -> str:
    """Keep the start and end of over-long text so a long entry is not silently cut off."""
    limit: int = _max_chars(num_ctx)
    if len(text) <= limit:
        return text
    head_length: int = limit * 2 // 3
    tail_length: int = limit - head_length
    logger.warning(
        "Input truncated from %d to %d characters to fit the model context (%d tokens)",
        len(text),
        limit,
        num_ctx,
    )
    return text[:head_length] + "\n\n[...]\n\n" + text[-tail_length:]


def _build_user_content(message: str, context: list[str]) -> str:
    """Put earlier exchanges before the current one without asking for a reply to them."""
    if not context:
        return message

    entries: str = "\n\n".join(
        f"Earlier entry {index}:\n{transcript}"
        for index, transcript in enumerate(context, start=1)
    )
    return (
        "Earlier entries from this session, oldest first. "
        "Use them only as context; respond to the current entry.\n\n"
        f"{entries}\n\n---\n\n"
        "Current entry:\n"
        f"{message}"
    )


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
        reflection="",
        detected_mode=None,
        model_used=model,
        prompt_tokens=0,
        completion_tokens=0,
        request_id="",
        created_at=int(time.time()),
    )


async def analyze(
        message: str,
        context: list[str],
        http_client: httpx.AsyncClient,
        base_url: str,
        model: str,
        num_ctx: int,
        session_id: uuid.UUID,
) -> AnalysisResult:
    extra: dict[str, str] = session_log_extra(session_id)
    try:
        data = await _chat(
            http_client=http_client,
            base_url=base_url,
            model=model,
            num_ctx=num_ctx,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _fit_text(_build_user_content(message, context), num_ctx),
                },
            ],
            temperature=ANALYSIS_TEMPERATURE,
            force_json=True,
            purpose="analysis",
            session_id=session_id,
        )

        content: str = data["message"]["content"]
        logger.debug("Raw analysis content: %s", content, extra=extra)
        content = _extract_json_object(content)

        reflection: str = ""
        mode: str | None = None
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                reflection = parsed.get("reflection", "") or ""
                mode = _normalize_mode(parsed.get("mode"))
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning("Failed to parse LLM reflection JSON: %s", exc, extra=extra)
            try:
                reflection_match = re.search(
                    r'"reflection"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', content
                )
                if reflection_match:
                    reflection = reflection_match.group(1).encode("utf-8").decode("unicode_escape")
                mode_match = re.search(r'"mode"\s*:\s*"([^"]+)"', content, re.IGNORECASE)
                if mode_match:
                    mode = _normalize_mode(mode_match.group(1))
            except Exception:
                pass

        if not reflection.strip():
            logger.warning("Ollama returned an empty reflection for model %r", model, extra=extra)

        return AnalysisResult(
            reflection=reflection,
            detected_mode=mode,
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
