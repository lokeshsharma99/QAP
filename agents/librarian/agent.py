"""
Librarian Agent
===============

Primary skill: vector_indexing
Role: Index Page Objects and Step Definitions into PgVector KB.
"""

from agno.agent import Agent
from agno.compression.manager import CompressionManager
from agno.learn import EntityMemoryConfig, LearningMachine, LearningMode
from agno.tools.coding import CodingTools
from agno.tools.knowledge import KnowledgeTools

from agents.librarian.instructions import INSTRUCTIONS
from agents.librarian.tools import LibrarianToolkit
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
from db import get_automation_kb, get_qap_learnings_kb, get_culture_manager

# ---------------------------------------------------------------------------
# Semantica KG Toolkit (optional — activated via SEMANTICA_ENABLED)
# AgnoKGToolkit adds 7 KG pipeline tools: build, query, enrich, export, dedup.
# Librarian uses it to detect contradictions when two sources define the same
# locator differently (e.g., Discovery says data-testid="submit" but an old POM
# uses role="button" with text "Submit" — Semantica's conflict module flags it).
# ---------------------------------------------------------------------------
_kg_tools: list = []
try:
    from app.semantica_config import SemanticaContext
    if SemanticaContext.is_agent_enabled("librarian"):
        from integrations.agno import AgnoKGToolkit  # type: ignore[import]
        from app.semantica_context import get_shared_context
        _shared_ctx = get_shared_context()
        if _shared_ctx is not None:
            _kg_tools = [AgnoKGToolkit(context=_shared_ctx)]
except Exception:
    pass

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: automation_kb — Librarian is the WRITER of this KB
# Shared:  qap_learnings — Librarian records indexing patterns and conventions
# Note: automation_knowledge is imported by Engineer — keep the same object name
# ---------------------------------------------------------------------------
automation_knowledge = get_automation_kb()
qap_learnings_kb = get_qap_learnings_kb()

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
librarian = Agent(
    # Identity
    id="librarian",
    name="Librarian",
    role="Index and retrieve Page Objects and Step Definitions from automation/",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    knowledge=automation_knowledge,
    search_knowledge=True,
    # Capabilities
    # KnowledgeTools(qap_learnings_kb): read/write indexing conventions and patterns.
    # KnowledgeTools(automation_knowledge) dropped — redundant with native search_knowledge=True.
    tools=[
        CodingTools(),
        KnowledgeTools(knowledge=qap_learnings_kb),
        *_kg_tools,
        LibrarianToolkit(),
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail excluded — indexes code files containing
    # test email/phone constants (e.g. TEST_EMAIL = 'user@example.com').
    # Feature-specific
    session_state={
        "indexed_files": [],
        "obsolescence_reports": [],
        "file_statistics": {},
        "current_indexing_session": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    # EntityMemoryConfig(ALWAYS): auto-extracts codebase entities (file paths, class names,
    # locator patterns, step definition signatures) during indexing and stores them as structured
    # facts in the shared entity store — allowing other agents (Engineer, Detective) to query
    # what Page Objects exist without a full KB search.
    learning=LearningMachine(
        entity_memory=EntityMemoryConfig(mode=LearningMode.ALWAYS),
    ),
    update_memory_on_run=True,
    tool_call_limit=50,
    # Context compression — CodingTools reads many source files during indexing;
    # KB graph queries return verbose JSON. Compress after 4 000 tokens.
    # Indexing progress is tracked in session_state so history depth can be reduced.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000),
    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context — indexing is per-commit work; session_state tracks progress.
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=3,               # reduced from 5: file-read results accumulate quickly
    max_tool_calls_from_history=3,    # keep only last 3 tool results per history run
    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
