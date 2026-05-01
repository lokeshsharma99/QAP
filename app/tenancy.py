"""
Tenant Context
==============

Extracts org_id and user_id from JWT Bearer tokens and provides
per-tenant helpers.  Works in both dev (no token → defaults) and
prd (AgentOS JWT middleware validates before requests reach here).

No signature verification is performed here — Agno's AgentOS JWT
middleware already validates the token.  We only read the claims
to resolve the tenant namespace.
"""

import base64
import json
from typing import Optional


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT claims without signature verification."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return {}
        padding = 4 - (len(parts[1]) % 4)
        payload = base64.urlsafe_b64decode(parts[1] + "=" * padding)
        return json.loads(payload)
    except Exception:
        return {}


def _claims(authorization: Optional[str]) -> dict:
    """Extract claims dict from a raw Authorization header value."""
    if not authorization:
        return {}
    token = authorization.removeprefix("Bearer ").strip()
    return _decode_jwt_payload(token)


def get_user_id(authorization: Optional[str]) -> str:
    """Return user_id from JWT claims, falling back to 'anonymous'.

    Checks: sub → user_id → email → 'anonymous'
    """
    c = _claims(authorization)
    return c.get("sub", c.get("user_id", c.get("email", "anonymous")))


def get_org_id(authorization: Optional[str]) -> str:
    """Return org_id from JWT claims, falling back to 'default'.

    Checks: org_id → organization_id → tenant_id → 'default'
    """
    c = _claims(authorization)
    return c.get("org_id", c.get("organization_id", c.get("tenant_id", "default")))


def get_team_ids(authorization: Optional[str]) -> list[str]:
    """Return list of team IDs the user belongs to, from JWT custom claims."""
    c = _claims(authorization)
    raw = c.get("teams", c.get("team_ids", []))
    if isinstance(raw, str):
        return [raw]
    return list(raw)


def get_rbac_scopes(authorization: Optional[str]) -> set[str]:
    """Return the set of RBAC scope strings from the JWT.

    Agno AgentOS uses scopes like:
      agents:<agent-id>:run
      teams:<team-id>:run
      workflows:<workflow-id>:run

    Returns empty set when no JWT is present (dev mode — all access).
    """
    c = _claims(authorization)
    raw = c.get("scope", c.get("scopes", ""))
    if isinstance(raw, list):
        return set(raw)
    return set(raw.split()) if raw else set()
