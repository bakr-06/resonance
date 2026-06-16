from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from openrouter import OpenRouter

from config import settings
from db.database import engine
from routes.create_entry import router as create_entry_router


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    async_client = httpx.AsyncClient(timeout=10.0)
    fastapi_app.state.http_client = async_client
    fastapi_app.state.openrouter_client = OpenRouter(
        api_key=settings.openrouter_api_key,
        async_client=async_client,
    )
    yield
    await async_client.aclose()
    await engine.dispose()


app: FastAPI = FastAPI(lifespan=lifespan)

app.include_router(create_entry_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}
