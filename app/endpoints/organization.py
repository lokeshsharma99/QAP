"""
Organization API
================

GET    /organization                 — org details + member list
PUT    /organization                 — update org name
POST   /organization/members         — invite a new member
DELETE /organization/members/{email} — remove a member
DELETE /organization                 — delete org (danger zone)

Organizations are stored in-memory keyed by org_id extracted from JWT.
The org_id is the multi-tenancy key: each org gets isolated KB tables
via db.session.get_tenant_kb(base_table, name, org_id).

For production, replace _orgs dict with a PostgreSQL table.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.tenancy import get_org_id, get_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organization", tags=["organization"])

# ---------------------------------------------------------------------------
# In-memory store — keyed by org_id.
# ---------------------------------------------------------------------------
_orgs: dict[str, dict] = {}


class OrgUpdate(BaseModel):
    name: str


class MemberInvite(BaseModel):
    email: str
    role: str = "member"


def _get_or_create_org(org_id: str, owner_id: str) -> dict:
    """Return existing org or create a default one for this tenant."""
    if org_id not in _orgs:
        display = (
            org_id.replace("_", " ").replace("-", " ").title()
            if org_id != "default"
            else "My Organization"
        )
        _orgs[org_id] = {
            "id": org_id,
            "name": display,
            "owner_id": owner_id,
            "members": [{"email": owner_id, "role": "owner"}],
            "plan": "free",
            # Multi-tenancy: KB tables are namespaced as {base}_{safe_org_id}
            # e.g. qap_learnings_defra_qa, site_manifesto_vectors_defra_qa
            "kb_namespace": org_id,
        }
    return _orgs[org_id]


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
    """Update organization name.  Owner-only."""
    org_id = get_org_id(authorization)
    user_id = get_user_id(authorization)
    org = _get_or_create_org(org_id, user_id)
    if org["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can update the organization")
    org["name"] = body.name
    logger.info("Organization %s renamed to '%s' by %s", org_id, body.name, user_id)
    return org


@router.post("/members")
async def invite_member(
    body: MemberInvite,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Invite a new member.  Owner-only."""
    org_id = get_org_id(authorization)
    user_id = get_user_id(authorization)
    org = _get_or_create_org(org_id, user_id)
    if org["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can invite members")
    if any(m["email"] == body.email for m in org["members"]):
        raise HTTPException(status_code=409, detail="Member already in organization")
    org["members"].append({"email": body.email, "role": body.role})
    logger.info("Member %s invited to org %s by %s", body.email, org_id, user_id)
    return org


@router.delete("/members/{email}")
async def remove_member(
    email: str,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Remove a member.  Owner-only.  Cannot remove the owner."""
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
    logger.info("Member %s removed from org %s by %s", email, org_id, user_id)
    return org


@router.delete("")
async def delete_org(authorization: Optional[str] = Header(default=None)) -> dict:
    """Permanently delete the organization and all its resources.  Owner-only."""
    org_id = get_org_id(authorization)
    user_id = get_user_id(authorization)
    if org_id not in _orgs:
        raise HTTPException(status_code=404, detail="Organization not found")
    org = _orgs[org_id]
    if org["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can delete the organization")
    del _orgs[org_id]
    logger.info("Organization %s deleted by %s", org_id, user_id)
    return {"deleted": True, "org_id": org_id}
