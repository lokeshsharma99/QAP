"""
Context Team
============

Coordinates Discovery and Librarian to build AUT knowledge base.
"""

from agno.team import Team, TeamMode

from agents.discovery import discovery
from agents.librarian import librarian
from teams.context.instructions import INSTRUCTIONS
from app.settings import MODEL

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
context_team = Team(
    # Identity
    id="context_team",
    name="Context Team",
    mode=TeamMode.coordinate,

    # Model
    model=MODEL,

    # Members
    members=[
        discovery,
        librarian,
    ],

    # Instructions
    instructions=INSTRUCTIONS,

    # Collaboration
    share_member_interactions=True,
    show_members_responses=True,

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
