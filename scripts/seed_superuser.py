"""
scripts/seed_superuser.py
=========================

Creates the default super-admin account for Quality Autopilot.

Usage (run ONCE after first `docker compose up -d`):

    # Option A — inside the qap-api container
    docker compose exec qap-api python scripts/seed_superuser.py

    # Option B — from your host (with the venv active)
    python scripts/seed_superuser.py

    # Option C — override credentials via env vars before running
    QAP_ADMIN_EMAIL=me@example.com QAP_ADMIN_PASS=MyStr0ngPass! python scripts/seed_superuser.py

Default credentials (change immediately in production):
    email:    admin@qap.local
    password: Admin@QAP123!
    role:     admin
    org:      Quality Autopilot

The script is idempotent — running it twice will not create a duplicate account.
"""

import hashlib
import os
import secrets
import sys

# ── Build DB URL the same way the app does ──────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.url import db_url

_psycopg_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)

# ── Default credentials (override via env vars) ──────────────────────────────
DEFAULT_ORG = os.getenv("QAP_ADMIN_ORG", "Quality Autopilot")
DEFAULT_NAME = os.getenv("QAP_ADMIN_NAME", "Super Admin")
DEFAULT_EMAIL = os.getenv("QAP_ADMIN_EMAIL", "admin@quality-autopilot.dev")
DEFAULT_PASS = os.getenv("QAP_ADMIN_PASS", "Admin@QAP123!")


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${h}"


def seed() -> None:
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Run: pip install psycopg[binary]")
        sys.exit(1)

    print(f"\n🌱  Seeding super-admin account…")
    print(f"    Org   : {DEFAULT_ORG}")
    print(f"    Name  : {DEFAULT_NAME}")
    print(f"    Email : {DEFAULT_EMAIL}")
    print(f"    Role  : admin\n")

    try:
        with psycopg.connect(_psycopg_url) as conn:
            with conn.cursor() as cur:
                # Ensure tables exist (same DDL as auth.py)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS qap_users (
                        id            TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        email         TEXT NOT NULL UNIQUE,
                        name          TEXT NOT NULL DEFAULT '',
                        password_hash TEXT NOT NULL,
                        org_id        TEXT NOT NULL,
                        role          TEXT NOT NULL DEFAULT 'member',
                        is_active     BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS qap_sessions (
                        token      TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
                        user_id    TEXT NOT NULL REFERENCES qap_users(id) ON DELETE CASCADE,
                        org_id     TEXT NOT NULL,
                        expires_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """)

                # Idempotency check
                cur.execute("SELECT id, org_id, role FROM qap_users WHERE email = %s", (DEFAULT_EMAIL,))
                existing = cur.fetchone()
                if existing:
                    user_id, org_id, role = existing
                    print(f"✅  Account already exists (id={user_id}, role={role}). No changes made.")
                    conn.rollback()
                    return

                # Create org
                org_id = secrets.token_hex(8)
                cur.execute("""
                    INSERT INTO agno_organizations (id, name, owner_id, members, plan, kb_namespace)
                    VALUES (%s, %s, 'pending', '[]'::jsonb, 'enterprise', %s)
                    ON CONFLICT (id) DO NOTHING
                """, (org_id, DEFAULT_ORG, org_id))

                # Create user
                pw_hash = _hash_password(DEFAULT_PASS)
                cur.execute("""
                    INSERT INTO qap_users (email, name, password_hash, org_id, role)
                    VALUES (%s, %s, %s, %s, 'admin')
                    RETURNING id
                """, (DEFAULT_EMAIL, DEFAULT_NAME, pw_hash, org_id))
                user_id = cur.fetchone()[0]

                # Update org owner
                cur.execute(
                    "UPDATE agno_organizations SET owner_id = %s WHERE id = %s",
                    (user_id, org_id)
                )
            conn.commit()

        print(f"✅  Super-admin created successfully!")
        print(f"\n{'─'*50}")
        print(f"  Login at : http://localhost:3000/sign-in")
        print(f"  Email    : {DEFAULT_EMAIL}")
        print(f"  Password : {DEFAULT_PASS}")
        print(f"  Role     : admin")
        print(f"  Org      : {DEFAULT_ORG}")
        print(f"{'─'*50}")
        print(f"\n⚠️  Change the default password immediately in production!")
        print(f"   POST /auth/change-password  (or use /settings in the UI)\n")

    except Exception as e:
        print(f"\n❌  Seed failed: {e}")
        print("    Make sure the DB is running: docker compose up -d qap-db")
        sys.exit(1)


if __name__ == "__main__":
    seed()
