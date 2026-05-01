"""
Profile API
===========

GET  /profile  — return current user's profile
PUT  /profile  — update profile fields (name, username, email)

Profiles are stored in PostgreSQL (agno_user_profiles table).
Falls back to in-memory for resilience when DB is unavailable.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.tenancy import get_user_id
from db.url import db_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])

# ---------------------------------------------------------------------------
# PostgreSQL helpers
# ---------------------------------------------------------------------------

def _ensure_table() -> None:
    """Create agno_user_profiles table if it doesn't exist."""
    try:
        import psycopg
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS agno_user_profiles (
                        user_id   TEXT PRIMARY KEY,
                        name      TEXT NOT NULL DEFAULT '',
                        username  TEXT NOT NULL DEFAULT '',
                        email     TEXT NOT NULL DEFAULT '',
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
            conn.commit()
    except Exception as e:
        logger.warning("Could not create agno_user_profiles table: %s", e)


def _get_profile_db(user_id: str) -> dict | None:
    try:
        import psycopg
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, name, username, email FROM agno_user_profiles WHERE user_id = %s",
                    (user_id,)
                )
                row = cur.fetchone()
                if row:
                    return {"user_id": row[0], "name": row[1], "username": row[2], "email": row[3]}
    except Exception as e:
        logger.warning("DB read error (profile): %s", e)
    return None


def _upsert_profile_db(user_id: str, name: str, username: str, email: str) -> bool:
    try:
        import psycopg
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agno_user_profiles (user_id, name, username, email, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET name = EXCLUDED.name,
                        username = EXCLUDED.username,
                        email = EXCLUDED.email,
                        updated_at = NOW()
                """, (user_id, name, username, email))
            conn.commit()
        return True
    except Exception as e:
        logger.warning("DB write error (profile): %s", e)
        return False


# Ensure table exists at import time (non-fatal)
try:
    _ensure_table()
except Exception:
    pass

# ---------------------------------------------------------------------------
# In-memory fallback store
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
    row = _get_profile_db(user_id)
    if row:
        return row
    return _profiles.get(user_id, _default_profile(user_id))


@router.put("")
async def update_profile(
    body: ProfileUpdate,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Update profile fields. Only provided (non-None) fields are changed."""
    user_id = get_user_id(authorization)
    # Start from DB or fallback
    profile = _get_profile_db(user_id) or _profiles.get(user_id, _default_profile(user_id))
    if body.name is not None:
        profile["name"] = body.name
    if body.username is not None:
        profile["username"] = body.username
    if body.email is not None:
        profile["email"] = body.email
    # Persist to DB; fall back to in-memory
    ok = _upsert_profile_db(user_id, profile["name"], profile["username"], profile["email"])
    if not ok:
        _profiles[user_id] = profile
    logger.info("Profile updated for user_id=%s (db=%s)", user_id, ok)
    return profile

