"""
Organization API
================

GET    /organization                 — org details + member list
PUT    /organization                 — update org name
POST   /organization/members         — invite a new member
DELETE /organization/members/{email} — remove a member
DELETE /organization                 — delete org (danger zone)

Organizations are persisted in PostgreSQL (agno_organizations table).
Falls back to in-memory for resilience when DB is unavailable.

The org_id is the multi-tenancy key: each org gets isolated KB tables
via db.session.get_tenant_kb(base_table, name, org_id).
"""

import json
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import getenv
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.tenancy import get_org_id, get_user_id
from db.url import db_url

# psycopg.connect() needs a plain postgresql:// URL, not the SQLAlchemy postgresql+psycopg:// variant
_psycopg_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organization", tags=["organization"])

# ---------------------------------------------------------------------------
# PostgreSQL helpers
# ---------------------------------------------------------------------------

def _ensure_table() -> None:
    """Create agno_organizations table if it doesn't exist."""
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS agno_organizations (
                        id          TEXT PRIMARY KEY,
                        name        TEXT NOT NULL DEFAULT 'My Organization',
                        owner_id    TEXT NOT NULL,
                        members     JSONB NOT NULL DEFAULT '[]',
                        plan        TEXT NOT NULL DEFAULT 'free',
                        kb_namespace TEXT NOT NULL,
                        updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
            conn.commit()
    except Exception as e:
        logger.warning("Could not create agno_organizations table: %s", e)


def _get_org_db(org_id: str) -> dict | None:
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, owner_id, members, plan, kb_namespace FROM agno_organizations WHERE id = %s",
                    (org_id,)
                )
                row = cur.fetchone()
                if row:
                    members = row[3] if isinstance(row[3], list) else json.loads(row[3] or "[]")
                    return {"id": row[0], "name": row[1], "owner_id": row[2],
                            "members": members, "plan": row[4], "kb_namespace": row[5]}
    except Exception as e:
        logger.warning("DB read error (org): %s", e)
    return None


def _upsert_org_db(org: dict) -> bool:
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agno_organizations (id, name, owner_id, members, plan, kb_namespace, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        owner_id = EXCLUDED.owner_id,
                        members = EXCLUDED.members,
                        plan = EXCLUDED.plan,
                        kb_namespace = EXCLUDED.kb_namespace,
                        updated_at = NOW()
                """, (org["id"], org["name"], org["owner_id"],
                      json.dumps(org["members"]), org["plan"], org["kb_namespace"]))
            conn.commit()
        return True
    except Exception as e:
        logger.warning("DB write error (org): %s", e)
        return False


def _delete_org_db(org_id: str) -> bool:
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM agno_organizations WHERE id = %s", (org_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.warning("DB delete error (org): %s", e)
        return False


# Ensure table exists at import time (non-fatal)
try:
    _ensure_table()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Email helper
# ---------------------------------------------------------------------------

def _send_invite_email(invitee_email: str, org_name: str, inviter_user_id: str) -> None:
    """Send a signup invite email. Silently skips if SMTP is not configured."""
    smtp_host = getenv("SMTP_HOST", "")
    smtp_port = int(getenv("SMTP_PORT", "587"))
    smtp_user = getenv("SMTP_USER", "")
    smtp_pass = getenv("SMTP_PASS", "")
    from_email = getenv("INVITE_FROM_EMAIL", smtp_user)
    app_url = getenv("APP_BASE_URL", "http://localhost:3000")

    if not smtp_host or not smtp_pass:
        logger.debug("SMTP not configured — skipping invite email to %s", invitee_email)
        return

    subject = f"You've been invited to join {org_name}"
    signup_url = f"{app_url}/signup?org={org_name}&invited_by={inviter_user_id}"
    body_html = f"""
    <p>Hi,</p>
    <p><strong>{inviter_user_id}</strong> has invited you to join <strong>{org_name}</strong>
    on Quality Autopilot.</p>
    <p><a href="{signup_url}" style="background:#3B82F6;color:#fff;padding:10px 18px;
    border-radius:6px;text-decoration:none;display:inline-block;">Accept Invite</a></p>
    <p>Or copy this link: {signup_url}</p>
    <p style="color:#888;font-size:12px;">If you weren't expecting this, you can safely ignore it.</p>
    """
    body_plain = f"{inviter_user_id} invited you to {org_name}. Accept: {signup_url}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = invitee_email
    msg.attach(MIMEText(body_plain, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, invitee_email, msg.as_string())
        logger.info("Invite email sent to %s", invitee_email)
    except Exception as e:
        logger.warning("Failed to send invite email to %s: %s", invitee_email, e)

# ---------------------------------------------------------------------------
# In-memory fallback store — keyed by org_id.
# ---------------------------------------------------------------------------
_orgs: dict[str, dict] = {}


class OrgUpdate(BaseModel):
    name: str


class MemberInvite(BaseModel):
    email: str
    role: str = "member"


def _get_or_create_org(org_id: str, owner_id: str) -> dict:
    """Return existing org (from DB first, then memory) or create a default one."""
    # 1. Try PostgreSQL
    row = _get_org_db(org_id)
    if row:
        _orgs[org_id] = row  # keep in-memory cache in sync
        return row
    # 2. Try in-memory cache
    if org_id in _orgs:
        return _orgs[org_id]
    # 3. Create new
    display = (
        org_id.replace("_", " ").replace("-", " ").title()
        if org_id != "default"
        else "My Organization"
    )
    org: dict = {
        "id": org_id,
        "name": display,
        "owner_id": owner_id,
        "members": [{"email": owner_id, "role": "owner"}],
        "plan": "free",
        "kb_namespace": org_id,
    }
    _upsert_org_db(org)
    _orgs[org_id] = org
    return org


def _save_org(org: dict) -> None:
    _upsert_org_db(org)
    _orgs[org["id"]] = org


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def get_org(authorization: Optional[str] = Header(default=None)) -> dict:
    """Return current tenant's organization details and member list."""
    org_id = get_org_id(authorization)
    user_id = get_user_id(authorization)
    return _get_or_create_org(org_id, user_id)


@router.put("")
async def update_org(
    body: OrgUpdate,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Update organization name. Owner-only."""
    org_id = get_org_id(authorization)
    user_id = get_user_id(authorization)
    org = _get_or_create_org(org_id, user_id)
    if org["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can update the organization")
    org["name"] = body.name
    _save_org(org)
    logger.info("Organization %s renamed to '%s' by %s", org_id, body.name, user_id)
    return org


@router.post("/members")
async def invite_member(
    body: MemberInvite,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Invite a new member. Owner-only."""
    org_id = get_org_id(authorization)
    user_id = get_user_id(authorization)
    org = _get_or_create_org(org_id, user_id)
    if org["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can invite members")
    if any(m["email"] == body.email for m in org["members"]):
        raise HTTPException(status_code=409, detail="Member already in organization")
    org["members"].append({"email": body.email, "role": body.role})
    _save_org(org)
    logger.info("Member %s invited to org %s by %s", body.email, org_id, user_id)
    # Send invite email (non-blocking, fire-and-forget — errors are logged, not raised)
    _send_invite_email(body.email, org["name"], user_id)
    return org


@router.delete("/members/{email}")
async def remove_member(
    email: str,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Remove a member. Owner-only. Cannot remove the owner."""
    org_id = get_org_id(authorization)
    user_id = get_user_id(authorization)
    org = _get_or_create_org(org_id, user_id)
    if org["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can remove members")
    if email == org["owner_id"]:
        raise HTTPException(status_code=400, detail="Cannot remove the organization owner")
    if not any(m["email"] == email for m in org["members"]):
        raise HTTPException(status_code=404, detail="Member not found")
    org["members"] = [m for m in org["members"] if m["email"] != email]
    _save_org(org)
    logger.info("Member %s removed from org %s by %s", email, org_id, user_id)
    return org


@router.delete("")
async def delete_org(authorization: Optional[str] = Header(default=None)) -> dict:
    """Permanently delete the organization and all its resources. Owner-only."""
    org_id = get_org_id(authorization)
    user_id = get_user_id(authorization)
    org = _get_org_db(org_id) or _orgs.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can delete the organization")
    _delete_org_db(org_id)
    _orgs.pop(org_id, None)
    logger.info("Organization %s deleted by %s", org_id, user_id)
    return {"deleted": True, "org_id": org_id}
