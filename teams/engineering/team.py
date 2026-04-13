"""
Engineering Team
=================

Coordinates Engineer and Data Agent to produce automation code from specifications.
"""

from agno.team import Team, TeamMode

from agents.data_agent import data_agent
from agents.engineer import engineer
from teams.engineering.instructions import INSTRUCTIONS
from app.settings import MODEL

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
engineering_team = Team(
    # Identity
    id="engineering_team",
    name="Engineering Team",
    mode=TeamMode.coordinate,

    # Model
    model=MODEL,

    # Members
    members=[
        engineer,
        data_agent,
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
