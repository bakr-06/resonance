import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from config import settings
from db.database import engine
from logging_config import configure_logging
from routes import session_router
from services.ai_analysis import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

configure_logging(settings.log_level)


async def _check_ollama_model(
        http_client: httpx.AsyncClient,
        base_url: str,
        model: str,
) -> None:
    """Log a clear warning if Ollama is unreachable or the model is not pulled."""
    try:
        response = await http_client.get(f"{base_url}/api/tags", timeout=5.0)
        response.raise_for_status()
        installed_models: list[str] = [
            m["name"] for m in response.json().get("models", [])
        ]
    except Exception as exc:
        logger.warning(
            "Ollama is not reachable at %s (%s). Analysis will degrade gracefully "
            "until it is running.",
            base_url,
            exc,
        )
        return

    if model in installed_models or f"{model}:latest" in installed_models:
        return

    logger.warning(
        "Ollama model %r is not installed. Available models: %s. "
        "Run `ollama pull %s` or set OLLAMA_MODEL to one of the above.",
        model,
        installed_models,
        model,
    )


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    async_client = httpx.AsyncClient(timeout=settings.ollama_timeout_seconds)
    fastapi_app.state.http_client = async_client
    fastapi_app.state.ollama_base_url = settings.ollama_base_url
    fastapi_app.state.ollama_model = settings.ollama_model
    fastapi_app.state.ollama_num_ctx = settings.ollama_num_ctx
    fastapi_app.state.analysis_system_prompt = SYSTEM_PROMPT
    await _check_ollama_model(async_client, settings.ollama_base_url, settings.ollama_model)
    yield
    await async_client.aclose()
    await engine.dispose()


app: FastAPI = FastAPI(lifespan=lifespan)

app.include_router(session_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello Resonance"}
