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

# ---------------------------------------------------------------------------
# Embedder Configuration
# ---------------------------------------------------------------------------
OLLAMA_API_KEY = getenv("OLLAMA_API_KEY", "")
OLLAMA_BASE_URL = getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")


def get_postgres_db(contents_table: str | None = None) -> PostgresDb:
    """Create a PostgresDb instance.

    Args:
        contents_table: Optional table name for storing knowledge contents.

    Returns:
        Configured PostgresDb instance.
    """
    if contents_table is not None:
        return PostgresDb(id=DB_ID, db_url=db_url, knowledge_table=contents_table)
    return PostgresDb(id=DB_ID, db_url=db_url)


def create_knowledge(name: str, table_name: str) -> Knowledge:
    """Create a Knowledge instance with PgVector hybrid search.

    Args:
        name: Display name for the knowledge base.
        table_name: PostgreSQL table name for vector storage.

    Returns:
        Configured Knowledge instance.
    """
    return Knowledge(
        name=name,
        vector_db=PgVector(
            db_url=db_url,
            table_name=table_name,
            search_type=SearchType.hybrid,
            embedder=OllamaEmbedder(
                id="nomic-embed-text",
                dimensions=768,
            ),
        ),
        contents_db=get_postgres_db(contents_table=f"{table_name}_contents"),
    )


def create_site_manifesto_knowledge() -> Knowledge:
    """Create the Site Manifesto knowledge base for Discovery agent output.

    Returns:
        Configured Knowledge instance for storing SiteManifesto data.
    """
    return create_knowledge("Site Manifesto KB", "site_manifesto_vectors")


def create_automation_scaffold_knowledge() -> Knowledge:
    """Create the Automation Scaffolding knowledge base for framework templates.

    Returns:
        Configured Knowledge instance for storing automation scaffolding patterns.
    """
    return create_knowledge("Automation Scaffold KB", "automation_scaffold_vectors")


def create_codebase_knowledge() -> Knowledge:
    """Create the Codebase knowledge base for Page Objects and Step Definitions.

    Returns:
        Configured Knowledge instance for storing test codebase vectors.
    """
    return create_knowledge("Codebase KB", "codebase_vectors")


# ---------------------------------------------------------------------------
# Shared Knowledge Base Instances
# ---------------------------------------------------------------------------
# Create single shared instances to avoid duplicates when multiple agents use the same KB
_site_manifesto_knowledge: Knowledge | None = None
_automation_scaffold_knowledge: Knowledge | None = None
_codebase_knowledge: Knowledge | None = None


def get_site_manifesto_knowledge() -> Knowledge:
    """Get or create the shared Site Manifesto knowledge base instance.

    Returns:
        Shared Knowledge instance for storing SiteManifesto data.
    """
    global _site_manifesto_knowledge
    if _site_manifesto_knowledge is None:
        _site_manifesto_knowledge = create_site_manifesto_knowledge()
    return _site_manifesto_knowledge


def get_automation_scaffold_knowledge() -> Knowledge:
    """Get or create the shared Automation Scaffold knowledge base instance.

    Returns:
        Shared Knowledge instance for storing automation scaffolding patterns.
    """
    global _automation_scaffold_knowledge
    if _automation_scaffold_knowledge is None:
        _automation_scaffold_knowledge = create_automation_scaffold_knowledge()
    return _automation_scaffold_knowledge


def get_codebase_knowledge() -> Knowledge:
    """Get or create the shared Codebase knowledge base instance.

    Returns:
        Shared Knowledge instance for storing test codebase vectors.
    """
    global _codebase_knowledge
    if _codebase_knowledge is None:
        _codebase_knowledge = create_codebase_knowledge()
    return _codebase_knowledge
