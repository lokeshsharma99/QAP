"""
Operations Team
===============

Squad 4: Detective + Medic
Mode: coordinate
"""

from agno.team import Team
from agno.team.mode import TeamMode

from agents.detective import detective
from agents.medic import medic
from app.settings import MODEL, agent_db
from teams.operations.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
operations_team = Team(
    # Identity
    id="operations",
    name="Operations Squad",
    mode=TeamMode.coordinate,
    # Model
    model=MODEL,
    # Members
    members=[detective, medic],
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
