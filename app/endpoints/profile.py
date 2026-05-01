"""
Profile API
===========

GET  /profile  — return current user's profile
PUT  /profile  — update profile fields (name, username, email)

Profiles are stored in-memory keyed by user_id extracted from the JWT.
For durable multi-user storage, replace _profiles dict with a PostgreSQL
table (e.g. agno_user_profiles) using agent_db.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.tenancy import get_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])

# ---------------------------------------------------------------------------
# In-memory store — keyed by user_id.
# ---------------------------------------------------------------------------
_profiles: dict[str, dict] = {}


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None


def _default_profile(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "name": "",
        "username": user_id,
        "email": user_id if "@" in user_id else "",
    }


@router.get("")
async def get_profile(authorization: Optional[str] = Header(default=None)) -> dict:
    """Return the current user's profile."""
    user_id = get_user_id(authorization)
    return _profiles.get(user_id, _default_profile(user_id))


@router.put("")
async def update_profile(
    body: ProfileUpdate,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Update profile fields.  Only provided (non-None) fields are changed."""
    user_id = get_user_id(authorization)
    profile = _profiles.get(user_id, _default_profile(user_id))
    if body.name is not None:
        profile["name"] = body.name
    if body.username is not None:
        profile["username"] = body.username
    if body.email is not None:
        profile["email"] = body.email
    _profiles[user_id] = profile
    logger.info("Profile updated for user_id=%s", user_id)
    return profile
