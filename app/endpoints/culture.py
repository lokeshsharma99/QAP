"""
Culture Endpoint
================

CRUD REST API for the ``agno_cultural_knowledge`` table.

Endpoints
---------
GET    /culture              — list all entries (optionally filter by category or agent)
GET    /culture/{id}         — get single entry
POST   /culture              — create entry (manual seed / UI-created)
DELETE /culture/{id}         — delete entry
GET    /culture/categories   — distinct category values for filter chips
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agno.db.schemas.culture import CulturalKnowledge

from app.settings import agent_db
from db import get_culture_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Culture"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CultureEntryOut(BaseModel):
    id: str | None = None
    name: str
    summary: str | None = None
    content: str | None = None
    categories: list[str] = []
    notes: list[str] = []
    agent_id: str | None = None
    team_id: str | None = None
    created_at: int | None = None
    updated_at: int | None = None


class CultureCreateRequest(BaseModel):
    name: str
    summary: str | None = None
    content: str
    categories: list[str] = []
    notes: list[str] = []


def _to_out(k: CulturalKnowledge) -> CultureEntryOut:
    return CultureEntryOut(
        id=str(k.id) if k.id else None,
        name=k.name or "",
        summary=k.summary,
        content=k.content,
        categories=k.categories or [],
        notes=k.notes or [],
        agent_id=k.agent_id,
        team_id=k.team_id,
        created_at=k.created_at,
        updated_at=k.updated_at,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/culture/categories")
async def get_culture_categories() -> dict:
    """Return distinct category strings across all cultural knowledge entries."""
    try:
        cm = get_culture_manager()
        cm.initialize()
        all_k = cm.get_all_knowledge()
        cats: set[str] = set()
        for k in all_k:
            for c in (k.categories or []):
                cats.add(c)
        return {"data": sorted(cats)}
    except Exception as exc:
        logger.exception("Failed to fetch culture categories")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/culture")
async def list_culture(
    category: Optional[str] = None,
    agent_id: Optional[str] = None,
    q: Optional[str] = None,
) -> dict:
    """List all cultural knowledge. Optionally filter by category, agent_id, or free-text."""
    try:
        cm = get_culture_manager()
        cm.initialize()
        all_k = cm.get_all_knowledge()

        if category:
            all_k = [k for k in all_k if category in (k.categories or [])]
        if agent_id:
            all_k = [k for k in all_k if k.agent_id == agent_id]
        if q:
            ql = q.lower()
            all_k = [
                k for k in all_k
                if ql in (k.name or "").lower()
                or ql in (k.summary or "").lower()
                or ql in (k.content or "").lower()
                or any(ql in c.lower() for c in (k.categories or []))
            ]

        return {"data": [_to_out(k).model_dump() for k in all_k], "total": len(all_k)}
    except Exception as exc:
        logger.exception("Failed to list culture")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/culture/{entry_id}")
async def get_culture_entry(entry_id: str) -> dict:
    """Fetch a single cultural knowledge entry by ID."""
    try:
        cm = get_culture_manager()
        cm.initialize()
        all_k = cm.get_all_knowledge()
        for k in all_k:
            if str(k.id) == entry_id:
                return {"data": _to_out(k).model_dump()}
        raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get culture entry")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/culture", status_code=201)
async def create_culture_entry(body: CultureCreateRequest) -> dict:
    """Manually create a cultural knowledge entry (UI seed / manual principle)."""
    try:
        cm = get_culture_manager()
        cm.initialize()
        entry = CulturalKnowledge(
            name=body.name,
            summary=body.summary,
            content=body.content,
            categories=body.categories,
            notes=body.notes,
        )
        cm.add_cultural_knowledge(entry)
        return {"message": "Created", "name": body.name}
    except Exception as exc:
        logger.exception("Failed to create culture entry")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/culture/{entry_id}", status_code=200)
async def delete_culture_entry(entry_id: str) -> dict:
    """Delete a cultural knowledge entry by ID."""
    try:
        cm = get_culture_manager()
        cm.initialize()
        cm.delete_knowledge(entry_id)
        return {"message": "Deleted"}
    except Exception as exc:
        logger.exception("Failed to delete culture entry")
        raise HTTPException(status_code=500, detail=str(exc))
