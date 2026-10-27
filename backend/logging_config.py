"""Logging setup: console summary plus one file tree per session.

Layout::

    backend/logs/app.log              # everything not tied to a session
    backend/logs/<session_id>/requests.log   # the text sent to the model

A record is routed to a session directory when it carries
``extra={"session_id": "..."}``. Use :func:`session_log_extra` so the key is
never misspelled.
"""

import logging
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import TextIO

BACKEND_DIR: Path = Path(__file__).resolve().parent
import os
DEFAULT_LOG_DIR: Path = Path(os.environ.get("RESONANCE_LOG_DIR") or (Path("/tmp") / "resonance-logs"))
APP_LOG_NAME: str = "app.log"
SESSION_LOG_NAME: str = "requests.log"
MAX_OPEN_FILES: int = 32

# The exact prompt text is written through this logger at DEBUG. Its level is
# pinned to DEBUG so the dump always reaches the session files, whatever
# LOG_LEVEL is set to; the console handler stays at INFO, so it never appears
# on the terminal.
PROMPT_LOGGER_NAME: str = "services.ai_analysis.prompt"


def session_log_extra(session_id: uuid.UUID) -> dict[str, str]:
    """Extra fields that send a log record to that session's directory."""
    return {"session_id": str(session_id)}


class SessionFileHandler(logging.Handler):
    """Write each record to a file chosen by the record's ``session_id``.

    Directories are created on first use. Every file is truncated the first
    time this process writes to it, so each run starts with a clean log rather
    than growing forever; later writes in the same run append, including after
    a handle has been evicted and reopened.

    Only the most recently used ``max_open`` files stay open, so sessions left
    open forever cannot exhaust file descriptors; closing a file loses nothing
    because every write is flushed.
    """

    def __init__(self, log_dir: Path, max_open: int = MAX_OPEN_FILES) -> None:
        super().__init__()
        self._log_dir: Path = log_dir
        self._max_open: int = max_open
        self._handles: OrderedDict[Path, TextIO] = OrderedDict()
        self._truncated: set[Path] = set()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            path: Path = self._path_for(record)
            handle: TextIO = self._handle_for(path)
            handle.write(self.format(record) + "\n")
            handle.flush()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()
        self._truncated.clear()
        super().close()

    def _path_for(self, record: logging.LogRecord) -> Path:
        session_id: object = getattr(record, "session_id", None)
        if session_id is None:
            return self._log_dir / APP_LOG_NAME
        return self._log_dir / str(session_id) / SESSION_LOG_NAME

    def _handle_for(self, path: Path) -> TextIO:
        handle: TextIO | None = self._handles.pop(path, None)
        if handle is None:
            path.parent.mkdir(parents=True, exist_ok=True)
            mode: str = "a" if path in self._truncated else "w"
            handle = path.open(mode, encoding="utf-8")
            self._truncated.add(path)

        self._handles[path] = handle
        while len(self._handles) > self._max_open:
            _, evicted = self._handles.popitem(last=False)
            evicted.close()
        return handle


def configure_logging(level: str, log_dir: Path = DEFAULT_LOG_DIR) -> None:
    """Attach console and per-session file handlers to the root logger.

    Uvicorn configures only its own ``uvicorn.*`` loggers, so without this the
    app's ``logger.info``/``logger.debug`` calls propagate to an unconfigured
    root logger and are dropped by Python's WARNING-level fallback handler.

    The console stays at INFO so the terminal keeps the one-line summaries.
    The prompt dump is pinned to DEBUG on its own logger, so it always lands in
    the session files even when ``LOG_LEVEL`` is INFO.
    """
    root: logging.Logger = logging.getLogger()
    root.setLevel(level.upper())

    logging.getLogger(PROMPT_LOGGER_NAME).setLevel(logging.DEBUG)

    if any(isinstance(handler, SessionFileHandler) for handler in root.handlers):
        return

    formatter: logging.Formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    console: logging.StreamHandler = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    files: SessionFileHandler = SessionFileHandler(log_dir)
    files.setFormatter(formatter)

    root.addHandler(console)
    root.addHandler(files)
