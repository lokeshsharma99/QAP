"""
Knowledge Squad
===============

The front-door team for all project questions and navigation.

Members:
  Project Scout  — unified KB search across all knowledge bases
  Concierge      — routing and workflow triggering

Mode: coordinate (leader decides whether the question needs Scout or Concierge)
"""

from agno.team import Team
from agno.team.mode import TeamMode

from agents.concierge import concierge
from agents.scout import scout
from app.settings import MODEL, agent_db
from teams.knowledge.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
knowledge_team = Team(
    # Identity
    id="knowledge",
    name="Knowledge Squad",
    mode=TeamMode.coordinate,
    # Model
    model=MODEL,
    # Members
    members=[scout, concierge],
    # Data
    db=agent_db,
    # Instructions
    instructions=LEADER_INSTRUCTIONS,
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
