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
from agno.vectordb.pgvector import HNSW, PgVector, SearchType

from db.url import db_url

DB_ID = "quality-autopilot-db"

# Ollama host — inside Docker use host.docker.internal to reach the host machine
OLLAMA_HOST = getenv("OLLAMA_HOST", "http://host.docker.internal:11434")


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

    Uses a local Ollama embedding model (qwen3-embedding:4b) to avoid
    requiring an OpenAI API key for embeddings.

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
            embedder=OllamaEmbedder(
                id="qwen3-embedding:4b",
                dimensions=2560,
                host=OLLAMA_HOST,
                enable_batch=True,
                batch_size=32,
            ),
        ),
        contents_db=get_postgres_db(knowledge_table=f"{table_name}_contents"),
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


def get_qap_learnings_kb() -> Knowledge:
    """Shared collective intelligence KB — ALL agents read and write here.

    Table: qap_learnings
    Purpose: Patterns, conventions, gotchas discovered across all agents and runs.
    """
    global _qap_learnings_kb
    if _qap_learnings_kb is None:
        _qap_learnings_kb = create_knowledge("QAP Shared Learnings", "qap_learnings")
    return _qap_learnings_kb


def get_site_manifesto_kb() -> Knowledge:
    """Site Manifesto KB — Discovery writes, Engineer/Architect/Medic read.

    Table: site_manifesto_vectors
    Purpose: UI component catalog, locators, accessibility tree snapshots.
    """
    global _site_manifesto_kb
    if _site_manifesto_kb is None:
        _site_manifesto_kb = create_knowledge("Site Manifesto", "site_manifesto_vectors")
    return _site_manifesto_kb


def get_automation_kb() -> Knowledge:
    """Automation Codebase KB — Librarian writes, Engineer/Detective/Medic read.

    Table: codebase_vectors
    Purpose: Page Object Models, Step Definitions, utilities — vectorised for
    semantic look-up so Engineer never duplicates existing POMs.
    """
    global _automation_kb
    if _automation_kb is None:
        _automation_kb = create_knowledge("Automation Codebase", "codebase_vectors")
    return _automation_kb


def get_rca_kb() -> Knowledge:
    """RCA History KB — Detective writes, Medic/Judge read.

    Table: rca_vectors
    Purpose: Historical root cause analyses, healing outcomes, failure patterns.
    """
    global _rca_kb
    if _rca_kb is None:
        _rca_kb = create_knowledge("RCA History", "rca_vectors")
    return _rca_kb


_test_results_kb: Knowledge | None = None
_document_library_kb: Knowledge | None = None


def get_test_results_kb() -> Knowledge:
    """Test Results KB — Data Agent writes, Detective/Judge read.

    Table: test_results_vectors
    Purpose: Historical test execution results, pass/fail trends, flaky test patterns.
    """
    global _test_results_kb
    if _test_results_kb is None:
        _test_results_kb = create_knowledge("Test Results", "test_results_vectors")
    return _test_results_kb


def get_document_library_kb() -> Knowledge:
    """Document Library KB — Architect/Scribe write, all agents read.

    Table: document_library_vectors
    Purpose: Requirements documents, ADO/Jira tickets, release notes, design docs.
    """
    global _document_library_kb
    if _document_library_kb is None:
        _document_library_kb = create_knowledge("Document Library", "document_library_vectors")
    return _document_library_kb


# ---------------------------------------------------------------------------
# Shared Culture Manager Singleton
# One CultureManager per process — all agents share the same cultural knowledge
# table (agno_cultural_knowledge). Agents read culture via add_culture_to_context=True
# and update it via enable_agentic_culture=True.
# ---------------------------------------------------------------------------

_culture_manager: CultureManager | None = None


def get_culture_manager() -> CultureManager:
    """Shared CultureManager — all agents read/write universal QAP principles here.

    Table: agno_cultural_knowledge (auto-created by Agno)
    Purpose: Universal principles, best practices, and patterns discovered across
    all agent runs. Unlike Memory (user-specific), Culture stores 'how we do things'
    so every agent benefits from collective intelligence from day one.

    capture_instructions focus on:
    - STLC patterns and conventions that proved effective
    - Locator strategies that work best with the AUT
    - Communication and reasoning patterns that produce quality output
    - Anti-patterns to avoid (learned from failures/rejections)
    """
    global _culture_manager
    if _culture_manager is None:
        _culture_manager = CultureManager(
            db=get_postgres_db(),
            culture_capture_instructions=(
                "Focus only on universal, reusable principles that apply across multiple agents "
                "and sessions. Capture: (1) STLC patterns that consistently produce quality "
                "Gherkin specs or Page Objects, (2) locator strategies that proved resilient "
                "in the AUT (prefer data-testid > role > text), (3) communication patterns "
                "that improved BA readability or Judge approval rates, (4) anti-patterns "
                "discovered (e.g. CSS selectors that broke, over-broad step definitions, "
                "hardcoded test data). Ignore one-off session details, ticket IDs, or "
                "environment-specific observations."
            ),
        )
    return _culture_manager
