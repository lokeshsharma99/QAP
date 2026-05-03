"""
Auth API
========

Invite-only authentication for Quality Autopilot.

Flow:
  1. Admin registers the first org (POST /auth/register)          → creates org + owner account
  2. Owner invites members (POST /auth/invite)                    → generates invite_token + (optional) sends email
  3. Invitee accepts invite (POST /auth/accept-invite)            → sets password, gets session_token
  4. All users sign in (POST /auth/login)                         → gets session_token
  5. All subsequent API calls include Authorization: Bearer <session_token>
  6. GET /auth/me validates the session and returns user info

Anonymous access is BLOCKED at the middleware level (app/main.py).

Tables:
  qap_users         — user accounts (id, email, hashed_password, org_id, role, is_active)
  qap_invites       — pending invites (token, email, org_id, invited_by, expires_at, used)
  qap_sessions      — active sessions (token, user_id, org_id, expires_at)
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr

from db.url import db_url

_psycopg_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))
_INVITE_TTL_HOURS = int(os.getenv("INVITE_TTL_HOURS", "72"))
_APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3000")
_SMTP_HOST = os.getenv("SMTP_HOST", "")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USER = os.getenv("SMTP_USER", "")
_SMTP_PASS = os.getenv("SMTP_PASS", "")
_FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@quality-autopilot.local")


# ---------------------------------------------------------------------------
# DB bootstrap
# ---------------------------------------------------------------------------

def _ensure_tables() -> None:
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS qap_users (
                        id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        email       TEXT NOT NULL UNIQUE,
                        name        TEXT NOT NULL DEFAULT '',
                        password_hash TEXT NOT NULL,
                        org_id      TEXT NOT NULL,
                        role        TEXT NOT NULL DEFAULT 'member',
                        is_active   BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS qap_invites (
                        token       TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        email       TEXT NOT NULL,
                        org_id      TEXT NOT NULL,
                        invited_by  TEXT NOT NULL,
                        role        TEXT NOT NULL DEFAULT 'member',
                        expires_at  TIMESTAMPTZ NOT NULL,
                        used        BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS qap_sessions (
                        token       TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        user_id     TEXT NOT NULL REFERENCES qap_users(id) ON DELETE CASCADE,
                        org_id      TEXT NOT NULL,
                        expires_at  TIMESTAMPTZ NOT NULL,
                        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_qap_sessions_user ON qap_sessions(user_id);
                    CREATE INDEX IF NOT EXISTS idx_qap_invites_email ON qap_invites(email);
                """)
            conn.commit()
    except Exception as e:
        logger.warning("Could not create auth tables: %s", e)


_ensure_tables()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    """SHA-256 hash with per-user random salt (stored as 'salt$hash')."""
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${h}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$", 1)
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == h
    except Exception:
        return False


def _create_session(user_id: str, org_id: str) -> str:
    """Insert a new session row and return the token."""
    import psycopg
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=_SESSION_TTL_DAYS)
    with psycopg.connect(_psycopg_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO qap_sessions (token, user_id, org_id, expires_at) VALUES (%s, %s, %s, %s)",
                (token, user_id, org_id, expires),
            )
        conn.commit()
    return token


def _validate_session(token: str) -> dict | None:
    """Return user dict if session is valid and not expired, else None."""
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT u.id, u.email, u.name, u.org_id, u.role, s.expires_at
                    FROM qap_sessions s
                    JOIN qap_users u ON u.id = s.user_id
                    WHERE s.token = %s AND s.expires_at > NOW() AND u.is_active = TRUE
                """, (token,))
                row = cur.fetchone()
                if row:
                    return {"id": row[0], "email": row[1], "name": row[2],
                            "org_id": row[3], "role": row[4]}
    except Exception as e:
        logger.warning("Session validation error: %s", e)
    return None


def _send_invite_email(to_email: str, invite_token: str, inviter_name: str, org_name: str) -> bool:
    """Send invite email if SMTP is configured. Returns True on success."""
    if not _SMTP_HOST or not _SMTP_USER:
        logger.info("SMTP not configured — invite token: %s", invite_token)
        return False
    accept_url = f"{_APP_BASE_URL}/accept-invite?token={invite_token}"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"You're invited to join {org_name} on Quality Autopilot"
        msg["From"] = _FROM_EMAIL
        msg["To"] = to_email
        html = f"""
        <p>Hi,</p>
        <p><strong>{inviter_name}</strong> has invited you to join <strong>{org_name}</strong>
        on Quality Autopilot.</p>
        <p><a href="{accept_url}" style="background:#0057FF;color:#fff;padding:10px 20px;
        border-radius:6px;text-decoration:none;">Accept Invitation</a></p>
        <p>This link expires in {_INVITE_TTL_HOURS} hours.</p>
        <p>Or copy this URL: {accept_url}</p>
        """
        msg.attach(MIMEText(html, "html"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as s:
            s.starttls(context=ctx)
            s.login(_SMTP_USER, _SMTP_PASS)
            s.sendmail(_FROM_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.warning("Failed to send invite email: %s", e)
        return False


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    org_name: str
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str


class AuthResponse(BaseModel):
    session_token: str
    user_id: str
    email: str
    name: str
    org_id: str
    role: str


class UserInfo(BaseModel):
    user_id: str
    email: str
    name: str
    org_id: str
    role: str


class InviteResponse(BaseModel):
    invite_token: str
    email: str
    expires_at: str
    email_sent: bool
    accept_url: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=AuthResponse, summary="Register first org + admin account")
def register(body: RegisterRequest):
    """Create the first organisation and an admin user.

    Can only be called once (if no users exist) or when the org name is new.
    Subsequent users must be invited.
    """
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                # Block re-registration if users already exist for this email
                cur.execute("SELECT id FROM qap_users WHERE email = %s", (body.email,))
                if cur.fetchone():
                    raise HTTPException(400, "Email already registered. Use login.")

                # Create org
                org_id = secrets.token_hex(8)
                cur.execute("""
                    INSERT INTO agno_organizations (id, name, owner_id, members, plan, kb_namespace)
                    VALUES (%s, %s, %s, %s::jsonb, 'free', %s)
                    ON CONFLICT (id) DO NOTHING
                """, (org_id, body.org_name, "pending", "[]", org_id))

                # Create user
                pw_hash = _hash_password(body.password)
                cur.execute("""
                    INSERT INTO qap_users (email, name, password_hash, org_id, role)
                    VALUES (%s, %s, %s, %s, 'admin')
                    RETURNING id
                """, (body.email, body.name, pw_hash, org_id))
                user_id = cur.fetchone()[0]

                # Update org owner
                cur.execute(
                    "UPDATE agno_organizations SET owner_id = %s WHERE id = %s",
                    (user_id, org_id)
                )
            conn.commit()

        token = _create_session(user_id, org_id)
        return AuthResponse(session_token=token, user_id=user_id, email=body.email,
                            name=body.name, org_id=org_id, role="admin")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Register error: %s", e)
        raise HTTPException(500, "Registration failed. See server logs.")


@router.post("/login", response_model=AuthResponse, summary="Sign in with email + password")
def login(body: LoginRequest):
    """Authenticate with email and password. Returns a session token."""
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, password_hash, org_id, role, is_active FROM qap_users WHERE email = %s",
                    (body.email,)
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Login DB error: %s", e)
        raise HTTPException(500, "Login failed.")

    if not row or not row[5]:
        raise HTTPException(401, "Invalid email or password.")
    user_id, name, pw_hash, org_id, role, is_active = row
    if not _verify_password(body.password, pw_hash):
        raise HTTPException(401, "Invalid email or password.")

    token = _create_session(user_id, org_id)
    return AuthResponse(session_token=token, user_id=user_id, email=body.email,
                        name=name, org_id=org_id, role=role)


@router.post("/invite", response_model=InviteResponse, summary="Invite a member by email")
def invite_member(
    body: InviteRequest,
    authorization: Optional[str] = Header(None),
):
    """Generate an invite token for a new member. Admin/owner only."""
    import psycopg
    token = (authorization or "").removeprefix("Bearer ").strip()
    caller = _validate_session(token)
    if not caller:
        raise HTTPException(401, "Not authenticated.")
    if caller["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Only admins can invite members.")

    expires = datetime.now(timezone.utc) + timedelta(hours=_INVITE_TTL_HOURS)
    invite_token = secrets.token_urlsafe(32)

    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                # Cancel any existing unused invite for this email+org
                cur.execute(
                    "UPDATE qap_invites SET used = TRUE WHERE email = %s AND org_id = %s AND used = FALSE",
                    (body.email, caller["org_id"])
                )
                cur.execute("""
                    INSERT INTO qap_invites (token, email, org_id, invited_by, role, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (invite_token, body.email, caller["org_id"], caller["id"], body.role, expires))
            conn.commit()
    except Exception as e:
        logger.error("Invite DB error: %s", e)
        raise HTTPException(500, "Failed to create invite.")

    # Get org name for email
    org_name = "Quality Autopilot"
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM agno_organizations WHERE id = %s", (caller["org_id"],))
                row = cur.fetchone()
                if row:
                    org_name = row[0]
    except Exception:
        pass

    email_sent = _send_invite_email(body.email, invite_token, caller["name"], org_name)
    accept_url = f"{_APP_BASE_URL}/accept-invite?token={invite_token}"

    return InviteResponse(
        invite_token=invite_token,
        email=body.email,
        expires_at=expires.isoformat(),
        email_sent=email_sent,
        accept_url=accept_url,
    )


@router.get("/invite/{token}", summary="Validate an invite token")
def validate_invite(token: str):
    """Check if an invite token is valid and return the associated email."""
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT i.email, i.role, i.expires_at, o.name
                    FROM qap_invites i
                    JOIN agno_organizations o ON o.id = i.org_id
                    WHERE i.token = %s AND i.used = FALSE AND i.expires_at > NOW()
                """, (token,))
                row = cur.fetchone()
    except Exception as e:
        raise HTTPException(500, str(e))

    if not row:
        raise HTTPException(404, "Invite not found, expired, or already used.")
    return {"email": row[0], "role": row[1], "expires_at": row[2].isoformat(), "org_name": row[3]}


@router.post("/accept-invite", response_model=AuthResponse, summary="Accept invite and set password")
def accept_invite(body: AcceptInviteRequest):
    """Accept an invite token and create an account. Returns a session token."""
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT email, org_id, role FROM qap_invites
                    WHERE token = %s AND used = FALSE AND expires_at > NOW()
                """, (body.token,))
                invite = cur.fetchone()
                if not invite:
                    raise HTTPException(400, "Invite not found, expired, or already used.")
                email, org_id, role = invite

                # Check if user already exists (re-invite scenario)
                cur.execute("SELECT id FROM qap_users WHERE email = %s", (email,))
                existing = cur.fetchone()
                if existing:
                    raise HTTPException(400, "Account already exists. Use login.")

                pw_hash = _hash_password(body.password)
                cur.execute("""
                    INSERT INTO qap_users (email, name, password_hash, org_id, role)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id
                """, (email, body.name, pw_hash, org_id, role))
                user_id = cur.fetchone()[0]

                # Mark invite as used
                cur.execute("UPDATE qap_invites SET used = TRUE WHERE token = %s", (body.token,))

                # Add to org members
                cur.execute("""
                    UPDATE agno_organizations
                    SET members = members || %s::jsonb
                    WHERE id = %s
                """, (f'[{{"id":"{user_id}","email":"{email}","role":"{role}"}}]', org_id))
            conn.commit()

        token = _create_session(user_id, org_id)
        return AuthResponse(session_token=token, user_id=user_id, email=email,
                            name=body.name, org_id=org_id, role=role)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Accept invite error: %s", e)
        raise HTTPException(500, "Failed to accept invite.")


@router.get("/me", response_model=UserInfo, summary="Get current user info")
def get_me(authorization: Optional[str] = Header(None)):
    """Validate session and return current user. Used by middleware."""
    raw = (authorization or "").removeprefix("Bearer ").strip()
    user = _validate_session(raw)
    if not user:
        raise HTTPException(401, "Not authenticated or session expired.")
    return UserInfo(**user)


@router.post("/logout", summary="Invalidate current session")
def logout(authorization: Optional[str] = Header(None)):
    """Delete the current session token."""
    raw = (authorization or "").removeprefix("Bearer ").strip()
    if not raw:
        return {"ok": True}
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM qap_sessions WHERE token = %s", (raw,))
            conn.commit()
    except Exception:
        pass
    return {"ok": True}


@router.get("/users", summary="List org members")
def list_users(authorization: Optional[str] = Header(None)):
    """List all active users in the caller's org. Admin only."""
    raw = (authorization or "").removeprefix("Bearer ").strip()
    caller = _validate_session(raw)
    if not caller:
        raise HTTPException(401, "Not authenticated.")
    if caller["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Admin access required.")
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, email, name, role, is_active, created_at
                    FROM qap_users WHERE org_id = %s ORDER BY created_at
                """, (caller["org_id"],))
                rows = cur.fetchall()
        return [{"id": r[0], "email": r[1], "name": r[2], "role": r[3],
                 "is_active": r[4], "created_at": r[5].isoformat()} for r in rows]
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/users/{user_id}", summary="Deactivate a user")
def deactivate_user(user_id: str, authorization: Optional[str] = Header(None)):
    """Soft-delete (deactivate) a user. Admin only. Cannot deactivate yourself."""
    raw = (authorization or "").removeprefix("Bearer ").strip()
    caller = _validate_session(raw)
    if not caller:
        raise HTTPException(401, "Not authenticated.")
    if caller["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Admin access required.")
    if caller["id"] == user_id:
        raise HTTPException(400, "Cannot deactivate yourself.")
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE qap_users SET is_active = FALSE WHERE id = %s AND org_id = %s",
                    (user_id, caller["org_id"])
                )
            conn.commit()
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True}
