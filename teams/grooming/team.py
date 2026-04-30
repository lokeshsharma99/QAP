"""
Grooming Team
=============

The Curators — keeps the regression suite clean via HITL-gated deletions.
Members: Curator + Librarian
Goal: Detect and safely remove obsolete/duplicate tests, re-index after cleanup.
"""

from agno.team import Team, TeamMode

from agents.curator import curator
from agents.librarian import librarian
from app.settings import MODEL, agent_db
from teams.grooming.instructions import INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
grooming_team = Team(
    # Identity
    id="grooming_team",
    name="The Curators",
    mode=TeamMode.coordinate,

    # Model
    model=MODEL,

    # Members
    members=[
        curator,
        librarian,
    ],

    # Data
    db=agent_db,

    # Instructions
    instructions=INSTRUCTIONS,

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
