"""
Grooming Team
=============

Coordinates Architect, Judge, and Engineer agents for 3 Amigos user story review.
"""

from agno.team import Team, TeamMode

from agents.architect import architect
from agents.engineer import engineer
from agents.judge import judge
from teams.grooming.instructions import INSTRUCTIONS
from app.settings import MODEL

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
grooming_team = Team(
    # Identity
    id="grooming_team",
    name="Grooming Team",
    mode=TeamMode.coordinate,

    # Model
    model=MODEL,

    # Members
    members=[
        architect,
        judge,
        engineer,
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
