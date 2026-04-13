"""
Operations Team
===============

Coordinates Detective and Medic agents for automated failure triage and self-healing.
"""

from agno.team import Team, TeamMode

from agents.detective import detective
from agents.medic import medic
from teams.operations.instructions import INSTRUCTIONS
from app.settings import MODEL

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
operations_team = Team(
    # Identity
    id="operations_team",
    name="Operations Team",
    mode=TeamMode.coordinate,

    # Model
    model=MODEL,

    # Members
    members=[
        detective,
        medic,
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
