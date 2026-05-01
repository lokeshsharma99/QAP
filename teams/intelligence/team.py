"""
Intelligence Team
=================

Squad: Impact Analyst + Pipeline Analyst
Mode: coordinate

Impact Analyst   — PR / Issue → ImpactReport (test suite gaps, priorities, actions)
Pipeline Analyst — CI failure → PipelineRCAReport (classification, remediation plan)

Together they form the intelligence layer of Quality Autopilot, answering:
  "What tests need to change given this PR?"  (Impact Analyst)
  "Why did this pipeline run fail?"           (Pipeline Analyst)
"""

from agno.team import Team
from agno.team.mode import TeamMode

from agents.impact_analyst import impact_analyst
from agents.pipeline_analyst import pipeline_analyst
from app.settings import MODEL, agent_db
from teams.intelligence.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
intelligence_team = Team(
    # Identity
    id="intelligence",
    name="Impact Analysis Squad",
    mode=TeamMode.coordinate,
    # Model
    model=MODEL,
    # Members
    members=[impact_analyst, pipeline_analyst],
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
