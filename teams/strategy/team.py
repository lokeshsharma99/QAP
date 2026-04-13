"""
Strategy Team
==============

Coordinates Architect and Scribe to produce specifications from requirements.
"""

from agno.team import Team, TeamMode

from agents.architect import architect
from agents.scribe import scribe
from teams.strategy.instructions import INSTRUCTIONS
from app.settings import MODEL

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
strategy_team = Team(
    # Identity
    id="strategy_team",
    name="Strategy Team",
    mode=TeamMode.coordinate,

    # Model
    model=MODEL,

    # Members
    members=[
        architect,
        scribe,
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
