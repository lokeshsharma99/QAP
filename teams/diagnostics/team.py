"""
Diagnostics Team
================

Squad: Detective + Pipeline Analyst
Mode: coordinate

Detective owns trace-level analysis (Playwright trace.zip → RCAReport).
Pipeline Analyst owns CI-level analysis (GitHub Actions logs → PipelineRCAReport).
Together they produce a unified, two-layer root cause analysis for any CI failure.
"""

from agno.team import Team
from agno.team.mode import TeamMode

from agents.detective import detective
from agents.pipeline_analyst import pipeline_analyst
from app.settings import MODEL, agent_db
from teams.diagnostics.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
diagnostics_team = Team(
    # Identity
    id="diagnostics",
    name="Diagnostics Squad",
    mode=TeamMode.coordinate,
    # Model
    model=MODEL,
    # Members
    members=[pipeline_analyst, detective],
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
