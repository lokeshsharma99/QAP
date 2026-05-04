"""
Engineering Team
================

Squad 3: Engineer + Data Agent
Mode: coordinate
"""

from agno.team import Team
from agno.team.mode import TeamMode
from agno.compression.manager import CompressionManager

from agents.data_agent import data_agent
from agents.engineer import engineer
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL, STLC_COMPRESSION_PROMPT
from teams.engineering.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
engineering_team = Team(
    # Identity
    id="engineering",
    name="Code Generation Squad",
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
    # Context compression — Engineer generates TypeScript code and reads multiple files;
    # Data Agent returns RunContext JSON. Both are verbose when captured in team history.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000, compress_tool_call_instructions=STLC_COMPRESSION_PROMPT),
    # Context — each feature build is scoped to one ticket. Session context on Engineer
    # tracks Look-Before-You-Leap steps; 3 team history runs covers cross-ticket continuity.
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=3,               # reduced from 5: generated code + file reads accumulate
    max_tool_calls_from_history=3,    # cap member tool results in team history
    # Output
    markdown=True,
    followups=True,
    num_followups=3,
)
