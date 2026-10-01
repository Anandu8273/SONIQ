from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.deps import engine

router = APIRouter()


@router.post("/incidents")
async def create_incident(payload: dict) -> dict:
    incident = engine.create_incident(**payload)
    return incident.model_dump(mode="json")


@router.get("/incidents")
async def list_incidents() -> list[dict]:
    return [i.model_dump(mode="json") for i in engine.incidents.values()]


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str) -> dict:
    incident = engine.incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident.model_dump(mode="json")


@router.post("/incidents/{incident_id}/investigate")
async def start_investigation(incident_id: str) -> dict:
    incident = engine.incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    investigation = await engine.investigate(incident)
    return investigation.model_dump(mode="json")
