"""
Org-Scoping ASGI Middleware
============================

Intercepts POST requests to Agno run endpoints:
    /v1/agents/<id>/runs
    /v1/teams/<id>/runs
    /v1/workflows/<id>/runs

For every such request that carries a valid ``Authorization: Bearer <qap_session_token>``
header, the middleware:

1. Looks up the caller's ``org_id`` from the ``qap_sessions`` table.
2. Overwrites the ``user_id`` field in the JSON request body with that ``org_id``.

Effect: Agno stores **all** memory, session state, learnings, and traces under
``user_id = <org_id>`` rather than the individual user's ID.  Every member of the
same org therefore shares a single Agno identity — their memory, sessions, and
traces are visible to and inherited by all team-mates.  Different orgs remain
fully isolated because they use different ``org_id`` values.

This is a raw ASGI middleware (not Starlette's ``BaseHTTPMiddleware``) so it
never buffers or blocks the SSE streaming response that Agno sends back.

Architecture note
-----------------
Knowledge Bases (PgVector tables) and Culture Managers are scoped per-org via
``db.session.get_qap_learnings_kb(org_id)`` and ``db.session.get_culture_manager(org_id)``.
Agents themselves are module-level singletons that always use the default (system-org)
KBs; the per-org KB helpers are consumed by the /knowledge and /culture REST endpoints
so that the UI shows only org-relevant data.
"""

import asyncio
import json
import logging
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Matches Agno's run endpoints (with or without trailing slash / query string)
_RUN_PATH_RE = re.compile(r"^/v1/(agents|teams|workflows)/[^/]+/runs/?(\?.*)?$")


# ---------------------------------------------------------------------------
# Database helper (sync — run inside asyncio.to_thread)
# ---------------------------------------------------------------------------

def _sync_lookup_org_id(token: str) -> str | None:
    """Return org_id for a valid QAP session token, or None."""
    try:
        from db.url import db_url
        import psycopg  # noqa: PLC0415

        pg_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
        with psycopg.connect(pg_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT org_id FROM qap_sessions "
                    "WHERE token = %s AND expires_at > NOW()",
                    (token,),
                )
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as exc:
        logger.debug("Tenancy middleware: session lookup failed — %s", exc)
        return None


async def _get_org_id(token: str) -> str | None:
    return await asyncio.to_thread(_sync_lookup_org_id, token)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class OrgScopingMiddleware:
    """ASGI middleware — replaces user_id with org_id on Agno run requests."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict,
        receive: Callable,
        send: Callable,
    ) -> None:
        # Only process HTTP requests
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "")
        path: str = scope.get("path", "")

        # Determine whether this is an Agno run endpoint needing body injection
        run_endpoint = method == "POST" and bool(_RUN_PATH_RE.match(path))

        # Extract Bearer token from Authorization header
        token: str = ""
        for name, value in scope.get("headers", []):
            if name.lower() == b"authorization":
                raw = value.decode("utf-8", errors="ignore")
                token = raw.removeprefix("Bearer ").strip()
                break

        if not token:
            await self.app(scope, receive, send)
            return

        # Look up org_id (async-safe — runs sync DB call in a thread)
        org_id = await _get_org_id(token)

        if not org_id:
            await self.app(scope, receive, send)
            return

        # Always store org_id in ASGI scope state so ALL endpoints can read it
        # via request.state.org_id (e.g. /culture, /optimize-memories).
        scope.setdefault("state", {})["org_id"] = org_id

        if not run_endpoint:
            # Non-run endpoints only need org_id in state — pass through unchanged.
            await self.app(scope, receive, send)
            return

        # ------------------------------------------------------------------
        # Wrap receive() to inject user_id = org_id into the request body.
        # Strategy: buffer ALL body chunks on the first http.request call
        # (bodies for Agno runs are tiny JSON objects, never streamed), then
        # return the modified full body in a single message.
        # ------------------------------------------------------------------
        _body_injected = False
        _buffered: bytes | None = None

        async def receive_with_org() -> dict:
            nonlocal _body_injected, _buffered

            if _body_injected:
                # Body already served — any subsequent receive() is a disconnect
                return await receive()

            # Collect all body chunks
            chunks: list[bytes] = []
            while True:
                message = await receive()
                msg_type = message.get("type")

                if msg_type != "http.request":
                    # Unexpected message (e.g., http.disconnect before body)
                    _body_injected = True
                    return message

                chunks.append(message.get("body", b""))

                if not message.get("more_body", False):
                    break

            full_body = b"".join(chunks)

            # Inject user_id into the JSON payload
            try:
                data = json.loads(full_body)
                if isinstance(data, dict):
                    data["user_id"] = org_id
                    full_body = json.dumps(data, separators=(",", ":")).encode()
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # not JSON — leave body unchanged

            _body_injected = True
            return {"type": "http.request", "body": full_body, "more_body": False}

        await self.app(scope, receive_with_org, send)
