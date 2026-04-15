"""
Librarian Agent
==============

The Librarian manages the vector knowledge base for the test codebase.
It scans and vectorizes Page Objects and Step Definitions for semantic search.
"""

from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
from agents.librarian.instructions import INSTRUCTIONS
from agents.librarian.tools import (
    check_and_re_index_changes,
    detect_obsolete_scenarios,
    detect_orphaned_pages,
    detect_unused_steps,
    generate_obsolescence_report,
    get_file_statistics,
    index_automation_codebase,
)
from app.settings import MODEL, agent_db
from db.session import get_automation_knowledge

# ---------------------------------------------------------------------------
# Create Librarian Agent
# ---------------------------------------------------------------------------
librarian = SemanticaAgent(
    id="librarian",
    name="Librarian",
    role="Manages vector knowledge base for test codebase",
    model=MODEL,
    db=agent_db,
    knowledge=get_automation_knowledge(),
    search_knowledge=True,
    tools=[
        ReasoningTools(
            enable_think=True,
            enable_analyze=True,
            add_instructions=True,
            add_few_shot=True,
        ),
        KnowledgeTools(knowledge=get_automation_knowledge()),
        index_automation_codebase,
        check_and_re_index_changes,
        get_file_statistics,
        detect_obsolete_scenarios,
        detect_unused_steps,
        detect_orphaned_pages,
        generate_obsolescence_report,
    ],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,
    update_memory_on_run=True,
    enable_session_summaries=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
