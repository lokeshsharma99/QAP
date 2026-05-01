"""
Context Team
============

Squad 2: Discovery + Librarian
Mode: coordinate
"""

from agno.team import Team
from agno.team.mode import TeamMode

from agents.discovery import discovery
from agents.librarian import librarian
from app.settings import MODEL, agent_db
from teams.context.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
context_team = Team(
    # Identity
    id="context",
    name="Discovery & Indexing Squad",
    mode=TeamMode.coordinate,
    # Model
    model=MODEL,
    # Members
    members=[discovery, librarian],
    # Data
    db=agent_db,
    # Instructions
    instructions=LEADER_INSTRUCTIONS,
    # Collaboration
    share_member_interactions=True,
    show_members_responses=True,
    # Memory
    update_memory_on_run=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
    followups=True,
    num_followups=3,
)
