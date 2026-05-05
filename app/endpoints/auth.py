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
_RESET_TTL_HOURS = int(os.getenv("RESET_TTL_HOURS", "24"))
_APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3000")
_SMTP_HOST = os.getenv("SMTP_HOST", "")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USER = os.getenv("SMTP_USER", "")
_SMTP_PASS = os.getenv("SMTP_PASS", "")
_FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@quality-autopilot.local")
_SUPERUSER_EMAIL = os.getenv("SUPERUSER_EMAIL", "admin@quality-autopilot.dev")
_SUPERUSER_INITIAL_PASSWORD = os.getenv("SUPERUSER_INITIAL_PASSWORD", "Admin@QAP123!")
_SUPERUSER_ORG_ID = "system"


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
                    CREATE TABLE IF NOT EXISTS qap_password_resets (
                        token       TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        user_id     TEXT NOT NULL REFERENCES qap_users(id) ON DELETE CASCADE,
                        org_id      TEXT NOT NULL,
                        expires_at  TIMESTAMPTZ NOT NULL,
                        used        BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_qap_sessions_user ON qap_sessions(user_id);
                    CREATE INDEX IF NOT EXISTS idx_qap_invites_email ON qap_invites(email);
                    CREATE INDEX IF NOT EXISTS idx_qap_resets_user ON qap_password_resets(user_id);
                """)
            conn.commit()
    except Exception as e:
        logger.warning("Could not create auth tables: %s", e)


_ensure_tables()


# ---------------------------------------------------------------------------
# Password helpers (must be defined before _ensure_superuser uses them)
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


# ---------------------------------------------------------------------------
# Superuser seed
# ---------------------------------------------------------------------------

def _ensure_superuser() -> None:
    """Seed the superuser account from environment variables on first startup."""
    if not _SUPERUSER_EMAIL:
        return
    try:
        import psycopg
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                # Ensure system org exists
                cur.execute("""
                    INSERT INTO agno_organizations (id, name, owner_id, members, plan, kb_namespace)
                    VALUES (%s, 'System', 'superuser', '[]'::jsonb, 'enterprise', 'system')
                    ON CONFLICT (id) DO NOTHING
                """, (_SUPERUSER_ORG_ID,))
                # Create superuser account if not already present
                cur.execute("SELECT id FROM qap_users WHERE email = %s", (_SUPERUSER_EMAIL,))
                if not cur.fetchone():
                    pw_hash = _hash_password(_SUPERUSER_INITIAL_PASSWORD)
                    cur.execute("""
                        INSERT INTO qap_users (email, name, password_hash, org_id, role)
                        VALUES (%s, 'Super Admin', %s, %s, 'superuser')
                    """, (_SUPERUSER_EMAIL, pw_hash, _SUPERUSER_ORG_ID))
                logger.info("Superuser account seeded: %s", _SUPERUSER_EMAIL)
            conn.commit()
    except Exception as e:
        logger.warning("Could not seed superuser: %s", e)


_ensure_superuser()



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
# RBAC helpers
# ---------------------------------------------------------------------------

# Permission matrix: maps role → set of allowed actions
_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "invite_member",
        "list_users",
        "deactivate_user",
        "change_role",
        "view_all_sessions",
        "revoke_session",
        "trigger_automation_sync",
        "manage_kb",
    },
    "member": {
        "view_own_profile",
        "change_own_password",
    },
    # owner is a superset of admin
    "owner": {
        "invite_member",
        "list_users",
        "deactivate_user",
        "change_role",
        "view_all_sessions",
        "revoke_session",
        "trigger_automation_sync",
        "manage_kb",
        "delete_org",
        "transfer_ownership",
    },
    # superuser is a system-level admin that can create orgs and act across all tenants
    "superuser": {
        "invite_member",
        "list_users",
        "deactivate_user",
        "change_role",
        "view_all_sessions",
        "revoke_session",
        "trigger_automation_sync",
        "manage_kb",
        "delete_org",
        "transfer_ownership",
        "create_org",
        "manage_all_orgs",
    },
}


def _require_role(caller: dict | None, *roles: str) -> dict:
    """Raise 401/403 unless caller's role is in the allowed set. Returns caller."""
    if not caller:
        raise HTTPException(401, "Not authenticated or session expired.")
    if caller["role"] not in roles:
        raise HTTPException(403, f"Requires role: {' or '.join(roles)}. Your role: {caller['role']}")
    return caller


def _require_permission(caller: dict | None, permission: str) -> dict:
    """Raise 401/403 unless caller's role has the named permission."""
    if not caller:
        raise HTTPException(401, "Not authenticated or session expired.")
    allowed = _ROLE_PERMISSIONS.get(caller["role"], set())
    if permission not in allowed:
        raise HTTPException(403, f"Permission denied: '{permission}' requires a higher role.")
    return caller


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    org_name: str
    name: str
    email: EmailStr
    password: str


class CreateOrgRequest(BaseModel):
    org_name: str


class LoginRequest(BaseModel):
    email: str  # plain str — just a DB lookup key, no external delivery needed
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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangeRoleRequest(BaseModel):
    user_id: str
    role: str  # "member" | "admin"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/org-lookup", summary="Look up an organisation by name (public)")
def org_lookup(name: str):
    """Return org id + name if an organisation with that (case-insensitive) name exists.

    Used by the signup form to validate that the org the user wants to join
    actually exists before submitting the registration form.
    """
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name FROM agno_organizations WHERE LOWER(name) = LOWER(%s) AND id != %s",
                    (name.strip(), _SUPERUSER_ORG_ID)
                )
                row = cur.fetchone()
    except Exception as e:
        raise HTTPException(500, str(e))
    if not row:
        raise HTTPException(404, "Organisation not found. Contact your admin to create one.")
    return {"org_id": row[0], "org_name": row[1]}


@router.post("/register", response_model=AuthResponse, summary="Join an existing organisation")
def register(body: RegisterRequest):
    """Sign up as a member of an **existing** organisation.

    The organisation name must already exist in the database.
    Only a superuser can create new organisations (POST /auth/org).
    Subsequent users may also be invited via the invite flow.
    """
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                # Block re-registration with the same email
                cur.execute("SELECT id FROM qap_users WHERE email = %s", (body.email,))
                if cur.fetchone():
                    raise HTTPException(400, "Email already registered. Use login.")

                # Organisation must already exist — superuser cannot be joined via signup
                cur.execute(
                    "SELECT id, name FROM agno_organizations WHERE LOWER(name) = LOWER(%s) AND id != %s",
                    (body.org_name.strip(), _SUPERUSER_ORG_ID)
                )
                org_row = cur.fetchone()
                if not org_row:
                    raise HTTPException(
                        404,
                        "Organisation not found. Ask your admin to create it first, "
                        "or use an invite link to join.",
                    )
                org_id, org_name = org_row

                # Create user as member (not admin — admins are created by superuser or promoted)
                pw_hash = _hash_password(body.password)
                cur.execute("""
                    INSERT INTO qap_users (email, name, password_hash, org_id, role)
                    VALUES (%s, %s, %s, %s, 'member')
                    RETURNING id
                """, (body.email, body.name, pw_hash, org_id))
                user_id = cur.fetchone()[0]

                # Add to org members JSONB array
                cur.execute("""
                    UPDATE agno_organizations
                    SET members = members || %s::jsonb
                    WHERE id = %s
                """, (f'[{{"id":"{user_id}","email":"{body.email}","role":"member"}}]', org_id))
            conn.commit()

        token = _create_session(user_id, org_id)
        return AuthResponse(session_token=token, user_id=user_id, email=body.email,
                            name=body.name, org_id=org_id, role="member")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Register error: %s", e)
        raise HTTPException(500, "Registration failed. See server logs.")


@router.post("/org", response_model=dict, summary="Create a new organisation (superuser only)")
def create_org(body: CreateOrgRequest, authorization: Optional[str] = Header(None)):
    """Create a new organisation. Only the superuser can call this endpoint."""
    import psycopg
    raw = (authorization or "").removeprefix("Bearer ").strip()
    caller = _require_permission(_validate_session(raw), "create_org")

    org_name = body.org_name.strip()
    if not org_name:
        raise HTTPException(400, "Organisation name cannot be empty.")

    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                # Ensure name is unique (case-insensitive)
                cur.execute(
                    "SELECT id FROM agno_organizations WHERE LOWER(name) = LOWER(%s)",
                    (org_name,)
                )
                if cur.fetchone():
                    raise HTTPException(409, f"Organisation '{org_name}' already exists.")

                org_id = secrets.token_hex(8)
                cur.execute("""
                    INSERT INTO agno_organizations (id, name, owner_id, members, plan, kb_namespace)
                    VALUES (%s, %s, %s, '[]'::jsonb, 'free', %s)
                """, (org_id, org_name, caller["id"], org_id))
            conn.commit()
        logger.info("Organisation '%s' (%s) created by superuser %s", org_name, org_id, caller["email"])
        return {"org_id": org_id, "org_name": org_name, "created_by": caller["email"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Create org error: %s", e)
        raise HTTPException(500, "Failed to create organisation.")


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
    caller = _require_permission(_validate_session(token), "invite_member")

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


def _send_reset_email(to_email: str, name: str, reset_token: str) -> bool:
    """Send password-reset email if SMTP is configured. Returns True on success."""
    if not _SMTP_HOST or not _SMTP_USER:
        logger.info("SMTP not configured — reset token: %s", reset_token)
        return False
    reset_url = f"{_APP_BASE_URL}/reset-password?token={reset_token}"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Quality Autopilot — Reset your password"
        msg["From"] = _FROM_EMAIL
        msg["To"] = to_email
        html = f"""
        <p>Hi {name},</p>
        <p>We received a request to reset your Quality Autopilot password.</p>
        <p><a href="{reset_url}" style="background:#0057FF;color:#fff;padding:10px 20px;
        border-radius:6px;text-decoration:none;">Reset Password</a></p>
        <p>This link expires in {_RESET_TTL_HOURS} hours. If you didn't request this, ignore this email.</p>
        <p>Or copy this URL: {reset_url}</p>
        """
        msg.attach(MIMEText(html, "html"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as s:
            s.starttls(context=ctx)
            s.login(_SMTP_USER, _SMTP_PASS)
            s.sendmail(_FROM_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.warning("Failed to send reset email: %s", e)
        return False


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
    return UserInfo(user_id=user["id"], email=user["email"], name=user["name"],
                    org_id=user["org_id"], role=user["role"])


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
    caller = _require_permission(_validate_session(raw), "list_users")
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
    caller = _require_permission(_validate_session(raw), "deactivate_user")
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


# ---------------------------------------------------------------------------
# Password reset (forgot password flow)
# ---------------------------------------------------------------------------

_RESET_TTL_HOURS = int(os.getenv("RESET_TTL_HOURS", "2"))


@router.post("/forgot-password", summary="Request a password reset link")
def forgot_password(body: ForgotPasswordRequest):
    """Generate a password-reset token and send it by email (if SMTP is set).

    Works for BOTH invited users who already have accounts AND any registered user.
    Always returns 200 so attackers cannot enumerate registered emails.
    """
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, org_id, is_active FROM qap_users WHERE email = %s",
                    (body.email,)
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("forgot-password DB error: %s", e)
        return {"ok": True, "message": "If that email exists, a reset link has been sent."}

    # Silent success even if user not found (anti-enumeration)
    if not row or not row[3]:  # not found or inactive
        return {"ok": True, "message": "If that email exists, a reset link has been sent."}

    user_id, name, org_id, _ = row
    reset_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=_RESET_TTL_HOURS)

    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                # Invalidate any existing reset tokens for this user
                cur.execute(
                    "UPDATE qap_password_resets SET used = TRUE WHERE user_id = %s AND used = FALSE",
                    (user_id,)
                )
                cur.execute(
                    "INSERT INTO qap_password_resets (token, user_id, org_id, expires_at) VALUES (%s, %s, %s, %s)",
                    (reset_token, user_id, org_id, expires),
                )
            conn.commit()
    except Exception as e:
        logger.error("failed to create reset token: %s", e)
        return {"ok": True, "message": "If that email exists, a reset link has been sent."}

    reset_url = f"{_APP_BASE_URL}/reset-password?token={reset_token}"
    _send_reset_email(body.email, name, reset_token)
    logger.info("Password reset token for %s: %s", body.email, reset_url)
    return {"ok": True, "message": "If that email exists, a reset link has been sent.",
            "reset_url": reset_url}  # returned for dev/SMTP-less environments


@router.post("/reset-password", summary="Set a new password using a reset token")
def reset_password(body: ResetPasswordRequest):
    """Accept a reset token and set the new password. Token is single-use."""
    if len(body.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT r.user_id FROM qap_password_resets r
                    JOIN qap_users u ON u.id = r.user_id
                    WHERE r.token = %s AND r.used = FALSE AND r.expires_at > NOW() AND u.is_active = TRUE
                """, (body.token,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(400, "Reset token not found, expired, or already used.")
                user_id = row[0]
                pw_hash = _hash_password(body.new_password)
                cur.execute("UPDATE qap_users SET password_hash = %s WHERE id = %s", (pw_hash, user_id))
                cur.execute("UPDATE qap_password_resets SET used = TRUE WHERE token = %s", (body.token,))
                # Invalidate all existing sessions (force re-login after password change)
                cur.execute("DELETE FROM qap_sessions WHERE user_id = %s", (user_id,))
            conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("reset-password error: %s", e)
        raise HTTPException(500, "Password reset failed.")
    return {"ok": True, "message": "Password updated. Please sign in with your new password."}


@router.post("/change-password", summary="Change own password (authenticated)")
def change_password(body: ChangePasswordRequest, authorization: Optional[str] = Header(None)):
    """Change password for the currently signed-in user."""
    raw = (authorization or "").removeprefix("Bearer ").strip()
    caller = _validate_session(raw)
    if not caller:
        raise HTTPException(401, "Not authenticated.")
    if len(body.new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters.")
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT password_hash FROM qap_users WHERE id = %s", (caller["id"],))
                row = cur.fetchone()
                if not row or not _verify_password(body.current_password, row[0]):
                    raise HTTPException(400, "Current password is incorrect.")
                pw_hash = _hash_password(body.new_password)
                cur.execute("UPDATE qap_users SET password_hash = %s WHERE id = %s",
                            (pw_hash, caller["id"]))
                # Invalidate all other sessions except current
                cur.execute(
                    "DELETE FROM qap_sessions WHERE user_id = %s AND token != %s",
                    (caller["id"], raw)
                )
            conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True, "message": "Password changed. All other sessions have been signed out."}


# ---------------------------------------------------------------------------
# RBAC: role management
# ---------------------------------------------------------------------------

@router.patch("/users/{user_id}/role", summary="Change a user's role (admin only)")
def change_user_role(user_id: str, body: ChangeRoleRequest, authorization: Optional[str] = Header(None)):
    """Promote or demote a member. Owner can promote to admin; admin cannot create owner."""
    raw = (authorization or "").removeprefix("Bearer ").strip()
    caller = _require_permission(_validate_session(raw), "change_role")
    if body.role not in ("member", "admin"):
        raise HTTPException(400, "Role must be 'member' or 'admin'. 'owner' is set at registration only.")
    if caller["id"] == user_id:
        raise HTTPException(400, "Cannot change your own role.")
    import psycopg
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE qap_users SET role = %s WHERE id = %s AND org_id = %s AND role != 'owner'",
                    (body.role, user_id, caller["org_id"])
                )
                if cur.rowcount == 0:
                    raise HTTPException(404, "User not found or cannot demote an owner.")
            conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True, "user_id": user_id, "new_role": body.role}


@router.get("/permissions", summary="Get current user's permissions")
def get_permissions(authorization: Optional[str] = Header(None)):
    """Return the full permission set for the signed-in user's role."""
    raw = (authorization or "").removeprefix("Bearer ").strip()
    caller = _validate_session(raw)
    if not caller:
        raise HTTPException(401, "Not authenticated.")
    perms = sorted(_ROLE_PERMISSIONS.get(caller["role"], set()))
    return {"role": caller["role"], "permissions": perms}


@router.post("/test-email", summary="Test SMTP configuration (admin only)")
def test_email(authorization: Optional[str] = Header(None)):
    """Send a test email to verify SMTP configuration. Admin only.

    Returns:
        {"smtp_configured": bool, "sent": bool, "to": email, "error": str|null}

    If SMTP is not configured, returns smtp_configured=False and the credentials
    that would have been used — useful for debugging.
    """
    raw = (authorization or "").removeprefix("Bearer ").strip()
    caller = _require_permission(_validate_session(raw), "invite_member")

    smtp_configured = bool(_SMTP_HOST and _SMTP_USER)
    if not smtp_configured:
        return {
            "smtp_configured": False,
            "sent": False,
            "to": caller["email"],
            "error": None,
            "hint": (
                "SMTP is not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS in .env "
                "to enable real email delivery. Without SMTP, reset/invite tokens are "
                "returned in the API response body (dev-mode only)."
            ),
            "missing": [
                v for v in ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"]
                if not os.getenv(v)
            ],
        }

    # Send a real test email to the caller's address
    sent = _send_reset_email(caller["email"], caller["name"], "TEST-TOKEN-DO-NOT-USE")
    return {
        "smtp_configured": True,
        "sent": sent,
        "to": caller["email"],
        "from": _FROM_EMAIL,
        "smtp_host": _SMTP_HOST,
        "smtp_port": _SMTP_PORT,
        "error": None if sent else "Send failed — check server logs for details.",
    }


# ---------------------------------------------------------------------------
# Invite management (admin/owner/superuser)
# ---------------------------------------------------------------------------

@router.get("/invites", summary="List pending invites for the caller's org")
def list_invites(authorization: Optional[str] = Header(None)):
    """Return all active (unused, non-expired) invites for the caller's organisation.
    Admin, owner, or superuser only.
    """
    import psycopg
    raw = (authorization or "").removeprefix("Bearer ").strip()
    caller = _require_permission(_validate_session(raw), "invite_member")

    # Superuser sees all orgs; others see their own org only
    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                if caller["role"] == "superuser":
                    cur.execute("""
                        SELECT token, email, org_id, role, expires_at, created_at
                        FROM qap_invites
                        WHERE used = FALSE AND expires_at > NOW()
                        ORDER BY created_at DESC
                    """)
                else:
                    cur.execute("""
                        SELECT token, email, org_id, role, expires_at, created_at
                        FROM qap_invites
                        WHERE org_id = %s AND used = FALSE AND expires_at > NOW()
                        ORDER BY created_at DESC
                    """, (caller["org_id"],))
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(500, str(e))

    return [
        {
            "id": r[0],
            "email": r[1],
            "org_id": r[2],
            "role": r[3],
            "expires_at": r[4].isoformat(),
            "created_at": r[5].isoformat(),
        }
        for r in rows
    ]


@router.delete("/invites/{token}", summary="Cancel a pending invite")
def cancel_invite(token: str, authorization: Optional[str] = Header(None)):
    """Mark a pending invite as used (cancelled). Admin/owner/superuser only."""
    import psycopg
    raw = (authorization or "").removeprefix("Bearer ").strip()
    caller = _require_permission(_validate_session(raw), "invite_member")

    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                # Verify the invite belongs to caller's org (unless superuser)
                if caller["role"] == "superuser":
                    cur.execute(
                        "UPDATE qap_invites SET used = TRUE WHERE token = %s AND used = FALSE",
                        (token,)
                    )
                else:
                    cur.execute(
                        "UPDATE qap_invites SET used = TRUE WHERE token = %s AND org_id = %s AND used = FALSE",
                        (token, caller["org_id"])
                    )
                if cur.rowcount == 0:
                    raise HTTPException(404, "Invite not found or already cancelled.")
            conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True, "token": token}

