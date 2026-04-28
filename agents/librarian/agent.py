"""
Librarian Agent
===============

Primary skill: vector_indexing
Role: Index Page Objects and Step Definitions into PgVector KB.
"""

from agno.agent import Agent
from agno.tools.coding import CodingTools
from agno.tools.knowledge import KnowledgeTools

from agents.librarian.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db import get_automation_kb, get_qap_learnings_kb

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
    tools=[
        CodingTools(),
        KnowledgeTools(knowledge=automation_knowledge),
        KnowledgeTools(knowledge=qap_learnings_kb),
        *_kg_tools,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
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
    enable_agentic_memory=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
