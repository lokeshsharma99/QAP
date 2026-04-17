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
    knowledge = Knowledge(
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

    # Augment with Semantica context graph if enabled
    try:
        from app.semantica_config import SemanticaContext

        if SemanticaContext.is_enabled():
            context_graph = SemanticaContext.get_context_graph()
            if context_graph is not None:
                # Attach context graph to knowledge instance for hybrid search
                # The graph search runs alongside vector search
                knowledge._semantica_context_graph = context_graph
    except ImportError:
        # Semantica not installed, skip augmentation
        pass

    return knowledge


def create_site_manifesto_knowledge() -> Knowledge:
    """Create the Site Manifesto knowledge base for Discovery agent output.

    Returns:
        Configured Knowledge instance for storing SiteManifesto data.
    """
    return create_knowledge("Site Manifesto KB", "site_manifesto_vectors")


def create_automation_knowledge() -> Knowledge:
    """Create the comprehensive Automation knowledge base.

    Stores:
    - Framework templates and scaffolding patterns
    - Page Objects and Step Definitions
    - Helper utilities and functions
    - Test fixtures and configurations
    - Gherkin feature files

    Returns:
        Configured Knowledge instance for storing all automation-related content.
    """
    return create_knowledge("Automation KB", "automation_vectors")


def create_learnings_knowledge() -> Knowledge:
    """Create the Learnings knowledge base for persistent agent insights.

    Stores:
    - Stable Selector insights from successful healing
    - Common failure patterns from Detective analysis
    - Framework conventions from codebase analysis

    Returns:
        Configured Knowledge instance for storing agent learnings.
    """
    return create_knowledge("Agent Learnings KB", "qap_learnings_vectors")


def create_rca_knowledge() -> Knowledge:
    """Create the RCA knowledge base for CI Log Analyzer agent.

    Stores:
    - Historical RCA findings from CI pipeline failures
    - Root cause patterns and classifications
    - Successful resolution strategies
    - Common failure signatures

    Returns:
        Configured Knowledge instance for storing RCA learnings.
    """
    return create_knowledge("RCA KB", "rca_vectors")


# ---------------------------------------------------------------------------
# Shared Knowledge Base Instances
# ---------------------------------------------------------------------------
# Create single shared instances to avoid duplicates when multiple agents use the same KB
_site_manifesto_knowledge: Knowledge | None = None
_automation_knowledge: Knowledge | None = None
_learnings_knowledge: Knowledge | None = None
_rca_knowledge: Knowledge | None = None


def get_site_manifesto_knowledge() -> Knowledge:
    """Get or create the shared Site Manifesto knowledge base instance.

    Returns:
        Shared Knowledge instance for storing SiteManifesto data.
    """
    global _site_manifesto_knowledge
    if _site_manifesto_knowledge is None:
        _site_manifesto_knowledge = create_site_manifesto_knowledge()
    return _site_manifesto_knowledge


def get_automation_knowledge() -> Knowledge:
    """Get or create the shared Automation knowledge base instance.

    Returns:
        Shared Knowledge instance for storing all automation-related content.
    """
    global _automation_knowledge
    if _automation_knowledge is None:
        _automation_knowledge = create_automation_knowledge()
    return _automation_knowledge


def get_learnings_knowledge() -> Knowledge:
    """Get or create the shared Learnings knowledge base instance.

    Returns:
        Shared Knowledge instance for storing agent learnings.
    """
    global _learnings_knowledge
    if _learnings_knowledge is None:
        _learnings_knowledge = create_learnings_knowledge()
    return _learnings_knowledge


def get_rca_knowledge() -> Knowledge:
    """Get or create the shared RCA knowledge base instance.

    Returns:
        Shared Knowledge instance for storing RCA learnings.
    """
    global _rca_knowledge
    if _rca_knowledge is None:
        _rca_knowledge = create_rca_knowledge()
    return _rca_knowledge


def create_used_data_table():
    """Create the used_data tracking table for shared state tracking.

    This table tracks generated test data to prevent duplicates across test runs.
    """
    postgres_db = get_postgres_db()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS used_data (
        id SERIAL PRIMARY KEY,
        unique_id VARCHAR(255) UNIQUE NOT NULL,
        field_name VARCHAR(100) NOT NULL,
        field_value TEXT NOT NULL,
        test_run_id VARCHAR(255),
        generated_at TIMESTAMP DEFAULT NOW(),
        used_at TIMESTAMP,
        status VARCHAR(50) DEFAULT 'available'
    );
    
    CREATE INDEX IF NOT EXISTS idx_used_data_unique_id ON used_data(unique_id);
    CREATE INDEX IF NOT EXISTS idx_used_data_field_value ON used_data(field_name, field_value);
    CREATE INDEX IF NOT EXISTS idx_used_data_status ON used_data(status);
    """
    
    postgres_db.run_sql(create_table_sql)
    return postgres_db


def check_data_exists(field_name: str, field_value: str) -> bool:
    """Check if data already exists in used_data tracking table.

    Args:
        field_name: Name of the field to check
        field_value: Value to check for existence

    Returns:
        True if data exists, False otherwise
    """
    postgres_db = get_postgres_db()
    
    check_sql = """
    SELECT COUNT(*) as count FROM used_data 
    WHERE field_name = %s AND field_value = %s AND status = 'available'
    """
    
    result = postgres_db.run_sql(check_sql, params=(field_name, field_value))
    return result[0]['count'] > 0 if result else False


def insert_used_data(unique_id: str, field_name: str, field_value: str, test_run_id: str = None):
    """Insert generated data into used_data tracking table.

    Args:
        unique_id: Unique identifier for the test user
        field_name: Name of the field
        field_value: Value of the field
        test_run_id: Optional test run identifier
    """
    postgres_db = get_postgres_db()
    
    insert_sql = """
    INSERT INTO used_data (unique_id, field_name, field_value, test_run_id, generated_at)
    VALUES (%s, %s, %s, %s, NOW())
    ON CONFLICT (unique_id) DO NOTHING
    """
    
    postgres_db.run_sql(insert_sql, params=(unique_id, field_name, field_value, test_run_id))


def mark_data_used(unique_id: str):
    """Mark data as used in the tracking table.

    Args:
        unique_id: Unique identifier for the test user
    """
    postgres_db = get_postgres_db()
    
    update_sql = """
    UPDATE used_data 
    SET status = 'used', used_at = NOW() 
    WHERE unique_id = %s
    """
    
    postgres_db.run_sql(update_sql, params=(unique_id))


def cleanup_old_data(days_old: int = 7):
    """Clean up old data from the tracking table.

    Args:
        days_old: Number of days to keep data (default: 7)
    """
    postgres_db = get_postgres_db()
    
    cleanup_sql = """
    DELETE FROM used_data 
    WHERE generated_at < NOW() - INTERVAL '%s days'
    """
    
    postgres_db.run_sql(cleanup_sql, params=(days_old,))
