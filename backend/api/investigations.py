from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.deps import engine
from rca.engine import render_report

router = APIRouter()


@router.get("/investigations/{investigation_id}")
async def get_investigation(investigation_id: str) -> dict:
    investigation = engine.investigations.get(investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="investigation not found")
    return investigation.model_dump(mode="json")


@router.get("/investigations/{investigation_id}/evidence")
async def get_evidence(investigation_id: str) -> list[dict]:
    investigation = engine.investigations.get(investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="investigation not found")
    return [e.model_dump(mode="json") for e in investigation.evidence]


@router.get("/investigations/{investigation_id}/hypotheses")
async def get_hypotheses(investigation_id: str) -> list[dict]:
    investigation = engine.investigations.get(investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="investigation not found")
    return [h.model_dump(mode="json") for h in investigation.hypotheses]


@router.get("/investigations/{investigation_id}/report")
async def get_report(investigation_id: str) -> dict:
    investigation = engine.investigations.get(investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="investigation not found")
    return {"text": render_report(investigation), "rca": investigation.rca.model_dump(mode="json") if investigation.rca else None}


@router.post("/investigations/{investigation_id}/approve")
async def approve(investigation_id: str, payload: dict | None = None) -> dict:
    try:
        investigation = engine.approve(investigation_id, (payload or {}).get("action"))
    except KeyError:
        raise HTTPException(status_code=404, detail="investigation not found") from None
    return investigation.model_dump(mode="json")


@router.post("/investigations/{investigation_id}/verify")
async def verify(investigation_id: str, payload: dict | None = None) -> dict:
    try:
        investigation = engine.verify(investigation_id, (payload or {}).get("metrics_after"))
    except KeyError:
        raise HTTPException(status_code=404, detail="investigation not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return investigation.model_dump(mode="json")
