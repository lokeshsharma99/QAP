"""
Librarian Agent
==============

The Librarian manages the vector knowledge base for the test codebase.
It scans and vectorizes Page Objects and Step Definitions for semantic search.
"""

from agno.agent import Agent
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.librarian.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db.session import get_codebase_knowledge

# ---------------------------------------------------------------------------
# Create Librarian Agent
# ---------------------------------------------------------------------------
librarian = Agent(
    id="librarian",
    name="Librarian",
    role="Manages vector knowledge base for test codebase",
    model=MODEL,
    db=agent_db,
    knowledge=get_codebase_knowledge(),
    search_knowledge=True,
    tools=[
        ReasoningTools(add_instructions=True),
        KnowledgeTools(knowledge=get_codebase_knowledge()),
    ],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
