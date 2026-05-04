"""
Strategy Team
=============

Squad 1: Architect + Scribe
Mode: coordinate
"""

from agno.team import Team
from agno.team.mode import TeamMode
from agno.compression.manager import CompressionManager

from agents.architect import architect
from agents.scribe import scribe
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL, STLC_COMPRESSION_PROMPT
from teams.strategy.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
strategy_team = Team(
    # Identity
    id="strategy",
    name="Spec Writing Squad",
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
    # Context compression — Architect fetches Jira/GitHub/ADO ticket bodies + KB docs;
    # Scribe generates full .feature file content. All captured in shared team history.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000, compress_tool_call_instructions=STLC_COMPRESSION_PROMPT),
    # Context — session_context planning on members tracks per-ticket steps. 3 history
    # runs gives the team coordinator cross-ticket step-reuse awareness.
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=3,               # reduced from 5: ticket bodies + .feature content verbose
    max_tool_calls_from_history=3,    # cap member tool results in team history
    # Output
    markdown=True,
    followups=True,
    num_followups=3,
)
