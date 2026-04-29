"""
Engineering Team
================

Squad 3: Engineer + Data Agent
Mode: coordinate
"""

from agno.team import Team
from agno.team.mode import TeamMode

from agents.data_agent import data_agent
from agents.engineer import engineer
from app.settings import MODEL, agent_db
from teams.engineering.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
engineering_team = Team(
    # Identity
    id="engineering",
    name="Engineering Squad",
    mode=TeamMode.coordinate,
    # Model
    model=MODEL,
    # Members
    members=[engineer, data_agent],
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
