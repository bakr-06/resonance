# main.py
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from routes.create_entry import router as create_entry_router


@asynccontextmanager
async def lifespan(fast_api_app: FastAPI):
    # Startup: create the client
    fast_api_app.state.http_client = httpx.AsyncClient(
        timeout=10.0,
        base_url="http://ws.audioscrobbler.com/2.0/",
    )
    yield
    # Shutdown: close it cleanly
    await fast_api_app.state.http_client.aclose()


app = FastAPI(lifespan=lifespan)

app.include_router(create_entry_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
