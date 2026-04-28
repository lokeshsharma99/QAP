"""
Database Session
================

PostgreSQL database connection for Quality Autopilot.
"""

from os import getenv

from agno.db.postgres import PostgresDb
from agno.knowledge import Knowledge
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.vectordb.pgvector import PgVector, SearchType

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
            embedder=OllamaEmbedder(
                id="qwen3-embedding:4b",
                dimensions=2560,
                host=OLLAMA_HOST,
            ),
        ),
        contents_db=get_postgres_db(knowledge_table=f"{table_name}_contents"),
    )


# ---------------------------------------------------------------------------
# Named Knowledge Base Factories
# Each returns a fresh Knowledge instance pointing at the shared PgVector table.
# Multiple agents importing the same factory get separate Python objects but
# they all read/write the SAME underlying PostgreSQL table — enabling true
# cross-agent knowledge sharing.
# ---------------------------------------------------------------------------

def get_qap_learnings_kb() -> Knowledge:
    """Shared collective intelligence KB — ALL agents read and write here.

    Table: qap_learnings
    Purpose: Patterns, conventions, gotchas discovered across all agents and runs.
    Every agent attaches this as its primary knowledge= so cross-agent learnings
    are always in context.
    """
    return create_knowledge("QAP Shared Learnings", "qap_learnings")


def get_site_manifesto_kb() -> Knowledge:
    """Site Manifesto KB — Discovery writes, Engineer/Architect/Medic read.

    Table: site_manifesto_vectors
    Purpose: UI component catalog, locators, accessibility tree snapshots.
    """
    return create_knowledge("Site Manifesto", "site_manifesto_vectors")


def get_automation_kb() -> Knowledge:
    """Automation Codebase KB — Librarian writes, Engineer/Detective/Medic read.

    Table: codebase_vectors
    Purpose: Page Object Models, Step Definitions, utilities — vectorised for
    semantic look-up so Engineer never duplicates existing POMs.
    """
    return create_knowledge("Automation Codebase", "codebase_vectors")


def get_rca_kb() -> Knowledge:
    """RCA History KB — Detective writes, Medic/Judge read.

    Table: rca_vectors
    Purpose: Historical root cause analyses, healing outcomes, failure patterns.
    """
    return create_knowledge("RCA History", "rca_vectors")
