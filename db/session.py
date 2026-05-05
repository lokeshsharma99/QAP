"""
Database Session
================

PostgreSQL database connection for Quality Autopilot.
"""

from os import getenv

from agno.culture.manager import CultureManager
from agno.db.postgres import PostgresDb
from agno.knowledge import Knowledge
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.models.openrouter import OpenRouter
from agno.vectordb.pgvector import HNSW, PgVector, SearchType

from db.url import db_url

DB_ID = "quality-autopilot-db"

# Ollama host — inside Docker use host.docker.internal to reach the host machine

OLLAMA_HOST = getenv("OLLAMA_HOST", "http://host.docker.internal:11434")

# Embedding provider: "openai" (default, works in ACA) or "ollama" (local dev with Ollama).
# Change via EMBEDDING_PROVIDER env var.  Switching providers requires dropping the vector
# tables so they are recreated with the correct dimension — set RECREATE_VECTOR_TABLES=1
# on one restart after switching.
_EMBEDDING_PROVIDER = getenv("EMBEDDING_PROVIDER", "openai").lower()
_EMBEDDING_DIMS = 2560 if _EMBEDDING_PROVIDER == "ollama" else 1536


def _get_qap_model() -> OpenRouter:
    """Return the same OpenRouter model used by app.settings.MODEL.

    Defined here to avoid a circular import (db → app.settings → db).
    CultureManager and other DB-layer managers use this so they never fall
    back to the gpt-4o default (which requires OPENAI_API_KEY).
    """
    _kilo_key = getenv("KILO_API_KEY", "anonymous")
    _model_id = "kilo-auto/free" if _kilo_key == "anonymous" else "kilo-auto/balanced"
    return OpenRouter(
        id=_model_id,
        base_url="https://api.kilo.ai/api/openrouter/v1",
        api_key=_kilo_key,
    )


def _get_embedder() -> OllamaEmbedder | OpenAIEmbedder:
    """Return the embedder for vector knowledge bases.

    Provider is controlled by the EMBEDDING_PROVIDER environment variable:
    - ``openai`` (default): OpenAI ``text-embedding-3-small`` (1536 dims).
      Works in ACA without a sidecar. Requires OPENAI_API_KEY.
    - ``ollama``: local Ollama ``qwen3-embedding:4b`` (2560 dims).
      Use for local development when Ollama is running.

    When switching providers the vector tables must be dropped and recreated
    because the vector column dimension differs.  Set RECREATE_VECTOR_TABLES=1
    on the first restart after changing EMBEDDING_PROVIDER.
    """
    if _EMBEDDING_PROVIDER == "ollama":
        return OllamaEmbedder(
            id="qwen3-embedding:4b",
            dimensions=2560,
            host=OLLAMA_HOST,
            enable_batch=True,
            batch_size=32,
        )
    # Default — OpenAI (reliable, no sidecar required)
    return OpenAIEmbedder(
        id="text-embedding-3-small",
        dimensions=1536,
    )


def get_postgres_db(knowledge_table: str | None = None) -> PostgresDb:
    """Create a PostgresDb instance.

    Args:
        knowledge_table: Optional table name for storing knowledge contents.

    Returns:
        Configured PostgresDb instance.
    """
    if knowledge_table is not None:
        return PostgresDb(id=DB_ID, db_url=db_url, knowledge_table=knowledge_table)
    return PostgresDb(id=DB_ID, db_url=db_url)


def create_knowledge(name: str, table_name: str) -> Knowledge:
    """Create a Knowledge instance with PgVector hybrid search.

    The embedder is chosen via the EMBEDDING_PROVIDER environment variable
    (``openai`` by default; ``ollama`` for local dev).

    Args:
        name: Display name for the knowledge base.
        table_name: PostgreSQL table name for vector storage.

    Returns:
        Configured Knowledge instance with hybrid search enabled.
    """
    return Knowledge(
        name=name,
        vector_db=PgVector(
            db_url=db_url,
            table_name=table_name,
            search_type=SearchType.hybrid,
            vector_index=HNSW(m=16, ef_construction=200),
            embedder=_get_embedder(),
        ),
        # Each KB gets its own unique db_id. Sharing DB_ID across multiple
        # Knowledge instances causes AgentOS to raise "Multiple knowledge
        # instances found for db_id" (400) because it validates uniqueness.
        contents_db=PostgresDb(
            id=f"{DB_ID}-{table_name}",
            db_url=db_url,
            knowledge_table=f"{table_name}_contents",
        ),
    )


# ---------------------------------------------------------------------------
# Shared Knowledge Base Singletons
# Module-level instances ensure every agent that imports these shares the
# SAME Python object. AgentOS validates uniqueness by object identity, so
# having one instance per KB avoids the "Duplicate knowledge instances" error
# while still letting all agents read/write the same underlying PgVector table.
# ---------------------------------------------------------------------------

_qap_learnings_kb: Knowledge | None = None
_site_manifesto_kb: Knowledge | None = None
_automation_kb: Knowledge | None = None
_rca_kb: Knowledge | None = None
_rtm_kb: Knowledge | None = None


def get_qap_learnings_kb(org_id: str = "system") -> Knowledge:
    """Shared collective intelligence KB — ALL agents read and write here.

    Table: qap_learnings  (or qap_learnings_<org> for other orgs)
    Purpose: Patterns, conventions, gotchas discovered across all agents and runs.
    """
    global _qap_learnings_kb
    if org_id in ("", "default", "system"):
        if _qap_learnings_kb is None:
            _qap_learnings_kb = create_knowledge("QAP Shared Learnings", "qap_learnings")
        return _qap_learnings_kb
    return get_tenant_kb("qap_learnings", "QAP Shared Learnings", org_id)


# ---------------------------------------------------------------------------
# Multi-Tenancy Helpers
# ---------------------------------------------------------------------------

def kb_table_for_org(base_table: str, org_id: str) -> str:
    """Return a per-tenant vector table name.

    Examples::

        kb_table_for_org("qap_learnings", "default") → "qap_learnings"
        kb_table_for_org("qap_learnings", "system")  → "qap_learnings"   # system = default
        kb_table_for_org("qap_learnings", "acme")    → "qap_learnings_acme"

    ``system`` and ``default`` are treated identically: they both map to the
    base (unqualified) table names so the existing data is never orphaned.
    Each other org gets its own suffixed table, created on-demand by PgVector.
    """
    if org_id in ("", "default", "system"):
        return base_table
    safe = "".join(
        c if (c.isalnum() or c == "_") else "_"
        for c in org_id.lower().replace("-", "_").replace(" ", "_").replace(".", "_")
    )
    return f"{base_table}_{safe}"


# org_id → safe string for Postgres identifiers
def _safe_org(org_id: str) -> str:
    """Normalise org_id to a Postgres-safe identifier fragment."""
    if org_id in ("", "default", "system"):
        return "system"
    return "".join(
        c if (c.isalnum() or c == "_") else "_"
        for c in org_id.lower().replace("-", "_").replace(" ", "_").replace(".", "_")
    )


# Per-org PostgresDb cache — one entry per org.
# Holds org-namespaced table names for sessions, memory, culture, metrics, traces.
_org_dbs: dict[str, PostgresDb] = {}


def get_org_db(org_id: str = "system") -> PostgresDb:
    """Return a PostgresDb whose Agno-managed tables are namespaced to *org_id*.

    All agents in the same org share the same session, memory, culture, metrics
    and trace tables.  Different orgs have completely separate rows in their own
    tables inside the same PostgreSQL instance — no schema-level isolation is
    needed.

    The ``system`` org (and the legacy ``default``) use unprefixed table names
    so all existing data is preserved.

    Tables created per org (examples for org_id="acme")::

        agent_sessions_acme        ← Agno chat sessions
        agent_memory_acme          ← per-org shared memories
        agno_culture_acme          ← cultural knowledge
        agent_metrics_acme         ← run metrics
        agent_traces_acme          ← execution traces
        agent_spans_acme           ← trace spans
    """
    safe = _safe_org(org_id)
    if safe not in _org_dbs:
        if safe == "system":
            # System org → use Agno's default (unprefixed) table names
            _org_dbs[safe] = PostgresDb(id=DB_ID, db_url=db_url)
        else:
            _org_dbs[safe] = PostgresDb(
                id=f"{DB_ID}-{safe}",
                db_url=db_url,
                session_table=f"agent_sessions_{safe}",
                memory_table=f"agent_memory_{safe}",
                culture_table=f"agno_culture_{safe}",
                metrics_table=f"agent_metrics_{safe}",
                traces_table=f"agent_traces_{safe}",
                spans_table=f"agent_spans_{safe}",
            )
    return _org_dbs[safe]


def get_tenant_kb(base_table: str, name: str, org_id: str) -> Knowledge:
    """Create a per-tenant Knowledge instance namespaced by org_id.

    Usage in an endpoint or agent that has access to the request's Authorization
    header::

        from db.session import get_tenant_kb, get_qap_learnings_kb

        # Dynamic — resolves table for any org:
        kb = get_tenant_kb("qap_learnings", "QAP Shared Learnings", org_id)

        # Convenience wrappers (preferred):
        kb = get_qap_learnings_kb(org_id)

    The system / default org uses the same unqualified tables as the legacy
    singleton KBs so existing data is never lost.
    """
    table = kb_table_for_org(base_table, org_id)
    return create_knowledge(name, table)


def get_site_manifesto_kb(org_id: str = "system") -> Knowledge:
    """Site Manifesto KB — Discovery writes, Engineer/Architect/Medic read.

    Table: site_manifesto_vectors  (or site_manifesto_vectors_<org> for other orgs)
    Purpose: UI component catalog, locators, accessibility tree snapshots.
    """
    global _site_manifesto_kb
    if org_id in ("", "default", "system"):
        if _site_manifesto_kb is None:
            _site_manifesto_kb = create_knowledge("Site Manifesto", "site_manifesto_vectors")
        return _site_manifesto_kb
    return get_tenant_kb("site_manifesto_vectors", "Site Manifesto", org_id)


def get_automation_kb(org_id: str = "system") -> Knowledge:
    """Automation Codebase KB — Librarian writes, Engineer/Detective/Medic read.

    Table: codebase_vectors  (or codebase_vectors_<org> for other orgs)
    Purpose: Page Object Models, Step Definitions, utilities — vectorised for
    semantic look-up so Engineer never duplicates existing POMs.
    """
    global _automation_kb
    if org_id in ("", "default", "system"):
        if _automation_kb is None:
            _automation_kb = create_knowledge("Automation Codebase", "codebase_vectors")
        return _automation_kb
    return get_tenant_kb("codebase_vectors", "Automation Codebase", org_id)


def get_rca_kb(org_id: str = "system") -> Knowledge:
    """RCA History KB — Detective writes, Medic/Judge read.

    Table: rca_vectors  (or rca_vectors_<org> for other orgs)
    Purpose: Historical root cause analyses, healing outcomes, failure patterns.
    """
    global _rca_kb
    if org_id in ("", "default", "system"):
        if _rca_kb is None:
            _rca_kb = create_knowledge("RCA History", "rca_vectors")
        return _rca_kb
    return get_tenant_kb("rca_vectors", "RCA History", org_id)


_test_results_kb: Knowledge | None = None
_document_library_kb: Knowledge | None = None


def get_test_results_kb(org_id: str = "system") -> Knowledge:
    """Test Results KB — Data Agent writes, Detective/Judge read.

    Table: test_results_vectors  (or test_results_vectors_<org> for other orgs)
    Purpose: Historical test execution results, pass/fail trends, flaky test patterns.
    """
    global _test_results_kb
    if org_id in ("", "default", "system"):
        if _test_results_kb is None:
            _test_results_kb = create_knowledge("Test Results", "test_results_vectors")
        return _test_results_kb
    return get_tenant_kb("test_results_vectors", "Test Results", org_id)


def get_document_library_kb(org_id: str = "system") -> Knowledge:
    """Document Library KB — Architect/Scribe write, all agents read.

    Table: document_library_vectors  (or document_library_vectors_<org> for other orgs)
    Purpose: Requirements documents, ADO/Jira tickets, release notes, design docs.
    """
    global _document_library_kb
    if org_id in ("", "default", "system"):
        if _document_library_kb is None:
            _document_library_kb = create_knowledge("Document Library", "document_library_vectors")
        return _document_library_kb
    return get_tenant_kb("document_library_vectors", "Document Library", org_id)


def get_rtm_kb(org_id: str = "system") -> Knowledge:
    """RTM (Requirements Traceability Matrix) KB — Scribe writes, Architect/Concierge read.

    Table: rtm_vectors  (or rtm_vectors_<org> for other orgs)
    Purpose: Persistent AC-ID → Scenario → StepDef → PageObject → AUT-element chain.
    """
    global _rtm_kb
    if org_id in ("", "default", "system"):
        if _rtm_kb is None:
            _rtm_kb = create_knowledge("RTM", "rtm_vectors")
        return _rtm_kb
    return get_tenant_kb("rtm_vectors", "RTM", org_id)


# ---------------------------------------------------------------------------
# Per-Org Culture Manager
#
# Culture is org-scoped: each org gets its own agno_culture_<safe_org> table.
# The system / default org uses Agno's default table (agno_cultural_knowledge)
# so existing data is preserved.
#
# Agents are singletons and receive the system-org culture manager at
# construction time. The /culture REST endpoint resolves the caller's org_id
# and serves the correct per-org manager so the UI is always org-scoped.
# ---------------------------------------------------------------------------

_culture_manager: CultureManager | None = None            # system org (default)
_culture_managers: dict[str, CultureManager] = {}         # other orgs

_CULTURE_CAPTURE_INSTRUCTIONS = (
    "Focus only on universal, reusable principles that apply across multiple agents "
    "and sessions. Capture: (1) STLC patterns that consistently produce quality "
    "Gherkin specs or Page Objects, (2) locator strategies that proved resilient "
    "in the AUT (prefer data-testid > role > text), (3) communication patterns "
    "that improved BA readability or Judge approval rates, (4) anti-patterns "
    "discovered (e.g. CSS selectors that broke, over-broad step definitions, "
    "hardcoded test data). Ignore one-off session details, ticket IDs, or "
    "environment-specific observations."
)


def get_culture_manager(org_id: str = "system") -> CultureManager:
    """Return the CultureManager for *org_id*.

    The system / default org uses Agno's default ``agno_cultural_knowledge``
    table (backward-compatible).  Every other org gets an isolated
    ``agno_culture_<safe_org>`` table inside the same PostgreSQL instance.

    Args:
        org_id: Organisation identifier.  Defaults to ``"system"``.  Pass the
            value from ``request.state.org_id`` (set by OrgScopingMiddleware) in
            REST endpoints so the UI shows org-specific cultural knowledge.
    """
    global _culture_manager
    safe = _safe_org(org_id)

    if safe == "system":
        if _culture_manager is None:
            _culture_manager = CultureManager(
                model=_get_qap_model(),
                db=get_postgres_db(),
                culture_capture_instructions=_CULTURE_CAPTURE_INSTRUCTIONS,
            )
        return _culture_manager

    if safe not in _culture_managers:
        _culture_managers[safe] = CultureManager(
            model=_get_qap_model(),
            db=PostgresDb(
                id=f"{DB_ID}-culture-{safe}",
                db_url=db_url,
                culture_table=f"agno_culture_{safe}",
            ),
            culture_capture_instructions=_CULTURE_CAPTURE_INSTRUCTIONS,
        )
    return _culture_managers[safe]
