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
from agno.compression.manager import CompressionManager

from agents.impact_analyst import impact_analyst
from agents.pipeline_analyst import pipeline_analyst
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL, STLC_COMPRESSION_PROMPT
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
    # Context compression — Impact Analyst processes PR diffs (GitHub/ADO/Atlassian MCP);
    # Pipeline Analyst parses CI log bodies. Both are verbose in shared team history.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000, compress_tool_call_instructions=STLC_COMPRESSION_PROMPT),
    # Context — each analysis is scoped to one PR or pipeline run. 3 history runs
    # preserves trend awareness without loading stale diff/log data.
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=3,               # reduced from 5: PR diffs + CI logs are very verbose
    max_tool_calls_from_history=3,    # cap member tool results in team history
    # Output
    markdown=True,
)
