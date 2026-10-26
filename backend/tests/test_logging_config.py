"""Tests for per-session log file routing.

Run from ``backend/`` with ``python -m pytest -q``.
"""

import logging
import uuid
from pathlib import Path

from logging_config import (
    APP_LOG_NAME,
    PROMPT_LOGGER_NAME,
    SESSION_LOG_NAME,
    SessionFileHandler,
    configure_logging,
    session_log_extra,
)

SESSION_A: uuid.UUID = uuid.UUID(int=1)
SESSION_B: uuid.UUID = uuid.UUID(int=2)


def make_logger(log_dir: Path, max_open: int = 32) -> logging.Logger:
    """A standalone logger, so the root logger and other tests are untouched."""
    logger: logging.Logger = logging.Logger("tests.logging_config", level=logging.DEBUG)
    handler: SessionFileHandler = SessionFileHandler(log_dir, max_open=max_open)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_record_with_session_id_goes_to_that_sessions_directory(tmp_path: Path) -> None:
    """The directory is created on first write; no setup step is needed."""
    log_dir: Path = tmp_path / "logs"
    logger: logging.Logger = make_logger(log_dir)

    logger.info("Ollama request purpose=analysis", extra=session_log_extra(SESSION_A))

    session_log: Path = log_dir / str(SESSION_A) / SESSION_LOG_NAME
    assert session_log.is_file()
    assert "purpose=analysis" in read(session_log)


def test_record_without_session_id_goes_to_app_log(tmp_path: Path) -> None:
    """Startup and non-session warnings must not be lost or misfiled."""
    log_dir: Path = tmp_path / "logs"
    logger: logging.Logger = make_logger(log_dir)

    logger.warning("Ollama is not reachable")

    app_log: Path = log_dir / APP_LOG_NAME
    assert app_log.is_file()
    assert "not reachable" in read(app_log)


def test_two_sessions_do_not_share_a_file(tmp_path: Path) -> None:
    """Each session's log is its own file, not a shared sink."""
    log_dir: Path = tmp_path / "logs"
    logger: logging.Logger = make_logger(log_dir)

    logger.info("entry from A", extra=session_log_extra(SESSION_A))
    logger.info("entry from B", extra=session_log_extra(SESSION_B))

    log_a: str = read(log_dir / str(SESSION_A) / SESSION_LOG_NAME)
    log_b: str = read(log_dir / str(SESSION_B) / SESSION_LOG_NAME)

    assert "entry from A" in log_a
    assert "entry from B" not in log_a
    assert "entry from B" in log_b
    assert "entry from A" not in log_b


def test_evicted_file_handle_is_reopened_without_losing_lines(tmp_path: Path) -> None:
    """Closing the least recently used handle must not drop earlier writes.

    This also guards the truncate-once rule: a reopened file is appended to,
    not wiped.
    """
    log_dir: Path = tmp_path / "logs"
    logger: logging.Logger = make_logger(log_dir, max_open=1)

    logger.info("first entry for A", extra=session_log_extra(SESSION_A))
    logger.info("only entry for B", extra=session_log_extra(SESSION_B))
    logger.info("second entry for A", extra=session_log_extra(SESSION_A))

    log_a: Path = log_dir / str(SESSION_A) / SESSION_LOG_NAME
    log_b: Path = log_dir / str(SESSION_B) / SESSION_LOG_NAME

    assert "first entry for A" in read(log_a)
    assert "second entry for A" in read(log_a)
    assert "only entry for B" in read(log_b)


def test_session_log_extra_uses_the_uuid_string() -> None:
    """The handler keys directories on ``str(uuid)``; keep both sides in sync."""
    assert session_log_extra(SESSION_A) == {"session_id": str(SESSION_A)}


def test_a_new_run_truncates_the_previous_file(tmp_path: Path) -> None:
    """A second process writing the same session starts from an empty file."""
    log_dir: Path = tmp_path / "logs"
    first_run: logging.Logger = make_logger(log_dir)
    first_run.info("line from the previous run", extra=session_log_extra(SESSION_A))

    second_run: logging.Logger = make_logger(log_dir)
    second_run.info("line from the new run", extra=session_log_extra(SESSION_A))

    text: str = read(log_dir / str(SESSION_A) / SESSION_LOG_NAME)

    assert "line from the new run" in text
    assert "line from the previous run" not in text


def test_prompt_dump_reaches_the_file_even_at_info_level(tmp_path: Path) -> None:
    """LOG_LEVEL=INFO must not hide the prompt text; that file is the point.

    The prompt logger's level is pinned to DEBUG, so the record is created
    regardless of the root level, and the file handler writes it while the
    console handler (INFO) drops it.
    """
    root: logging.Logger = logging.getLogger()
    saved_handlers: list[logging.Handler] = list(root.handlers)
    saved_root_level: int = root.level
    prompt_logger: logging.Logger = logging.getLogger(PROMPT_LOGGER_NAME)
    saved_prompt_level: int = prompt_logger.level

    try:
        for handler in saved_handlers:
            root.removeHandler(handler)
        configure_logging("INFO", tmp_path / "logs")

        assert prompt_logger.level == logging.DEBUG

        prompt_logger.debug(
            "--- message 2/2 role=user chars=13 ---\nCurrent entry:\nI feel guilty.",
            extra=session_log_extra(SESSION_A),
        )

        session_log: Path = tmp_path / "logs" / str(SESSION_A) / SESSION_LOG_NAME
        assert "I feel guilty." in read(session_log)
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()
        for handler in saved_handlers:
            root.addHandler(handler)
        root.setLevel(saved_root_level)
        prompt_logger.setLevel(saved_prompt_level)
