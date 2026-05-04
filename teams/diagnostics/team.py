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
from agno.compression.manager import CompressionManager

from agents.ci_log_analyzer import ci_log_analyzer
from agents.detective import detective
from agents.pipeline_analyst import pipeline_analyst
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL, STLC_COMPRESSION_PROMPT
from teams.diagnostics.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
diagnostics_team = Team(
    # Identity
    id="diagnostics",
    name="CI Failure Squad",
    mode=TeamMode.coordinate,
    # Model
    model=MODEL,
    # Members
    # pipeline_analyst  — GitHub Actions CI failure analysis (workflow runs, job logs)
    # ci_log_analyzer   — Azure DevOps CI failure analysis (ADO pipelines, creates work items)
    # detective         — Playwright trace.zip analysis (locator failures, screenshots)
    members=[pipeline_analyst, ci_log_analyzer, detective],
    # Data
    db=agent_db,
    # Instructions
    instructions=LEADER_INSTRUCTIONS,
    # Collaboration
    share_member_interactions=True,
    show_members_responses=True,
    # Memory
    update_memory_on_run=True,
    # Context compression — trace ZIP parse results (Detective) and CI log bodies
    # (Pipeline Analyst) are the most verbose outputs in the system. With
    # share_member_interactions=True, 5 prior runs = potentially hundreds of KB of
    # tool call results in context. Compress and reduce depth aggressively.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000, compress_tool_call_instructions=STLC_COMPRESSION_PROMPT),
    # Context — each failure triage is independent. 2 history runs provides enough
    # coordinator context while members' own session_context tracks per-failure state.
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=2,               # reduced from 5: trace+log results are huge
    max_tool_calls_from_history=3,    # cap member tool results in team history
    # Output
    markdown=True,
    followups=True,
    num_followups=3,
)
