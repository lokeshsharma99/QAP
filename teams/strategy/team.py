"""
Strategy Team
=============

Squad 1: Architect + Scribe
Mode: coordinate
"""

from agno.team import Team
from agno.team.mode import TeamMode

from agents.architect import architect
from agents.scribe import scribe
from app.settings import MODEL, agent_db
from teams.strategy.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
strategy_team = Team(
    # Identity
    id="strategy",
    name="Strategy Squad",
    mode=TeamMode.coordinate,
    # Model
    model=MODEL,
    # Members
    members=[architect, scribe],
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
)
