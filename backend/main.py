"""FastAPI placeholder. Investigation API is wired enough for local demo use."""

from __future__ import annotations

from fastapi import FastAPI

from backend.api.incidents import router as incidents_router
from backend.api.investigations import router as investigations_router
from backend.logging_setup import configure_logging

configure_logging()
app = FastAPI(title="SONIQ", version="0.1.0")
app.include_router(incidents_router)
app.include_router(investigations_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
