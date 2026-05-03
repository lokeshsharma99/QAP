"""
scripts/seed_test_users.py
==========================

Seeds a demo organisation and four test accounts:
  - viewer@qap.dev     (role: member  — read-only persona)
  - member@qap.dev     (role: member)
  - admin@qap.dev      (role: admin)
  - owner@qap.dev      (role: owner  — org owner)

All share the same org: "QAP Demo Org"
Default password for all: TestUser@2026!

Run with:
    docker exec qap-api python3 /app/scripts/seed_test_users.py
"""

import hashlib
import os
import secrets
import sys

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed in this environment")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def _build_url() -> str:
    from urllib.parse import quote
    user = os.getenv("DB_USER", "ai")
    pw   = quote(os.getenv("DB_PASS", "ai"), safe="")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    db   = os.getenv("DB_DATABASE", "ai")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"

DB_URL = _build_url()

ORG_ID   = "demo-org"
ORG_NAME = "QAP Demo Org"
PASSWORD = "TestUser@2026!"

USERS = [
    {"email": "owner@qap.dev",  "name": "Demo Owner",  "role": "owner"},
    {"email": "admin@qap.dev",  "name": "Demo Admin",  "role": "admin"},
    {"email": "member@qap.dev", "name": "Demo Member", "role": "member"},
    {"email": "viewer@qap.dev", "name": "Demo Viewer", "role": "member"},  # viewer = read-only member
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${h}"

# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------
def seed() -> None:
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            # 1. Ensure tables exist (no-op if already created by the API)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agno_organizations (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    owner_id    TEXT NOT NULL DEFAULT 'pending',
                    members     JSONB NOT NULL DEFAULT '[]'::jsonb,
                    plan        TEXT NOT NULL DEFAULT 'free',
                    kb_namespace TEXT NOT NULL DEFAULT '',
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS qap_users (
                    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email         TEXT NOT NULL UNIQUE,
                    name          TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    org_id        TEXT NOT NULL DEFAULT 'default',
                    role          TEXT NOT NULL DEFAULT 'member',
                    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            # 2. Create demo org
            cur.execute("""
                INSERT INTO agno_organizations (id, name, owner_id, members, plan, kb_namespace)
                VALUES (%s, %s, 'pending', '[]'::jsonb, 'free', %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
            """, (ORG_ID, ORG_NAME, ORG_ID))
            print(f"✓ Org '{ORG_NAME}' (id={ORG_ID}) upserted")

            # 3. Seed users
            owner_id = None
            for u in USERS:
                pw_hash = hash_password(PASSWORD)
                cur.execute("""
                    INSERT INTO qap_users (email, name, password_hash, org_id, role)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (email) DO UPDATE
                        SET name = EXCLUDED.name,
                            role = EXCLUDED.role,
                            org_id = EXCLUDED.org_id
                    RETURNING id
                """, (u["email"], u["name"], pw_hash, ORG_ID, u["role"]))
                row = cur.fetchone()
                uid = str(row[0])
                print(f"  ✓ {u['role']:8s}  {u['email']}  (id={uid})")
                if u["role"] == "owner":
                    owner_id = uid

            # 4. Set org owner_id
            if owner_id:
                cur.execute(
                    "UPDATE agno_organizations SET owner_id = %s WHERE id = %s",
                    (owner_id, ORG_ID)
                )

        conn.commit()
    print(f"\n✓ Done. Login with any address above, password: {PASSWORD}")


if __name__ == "__main__":
    seed()
