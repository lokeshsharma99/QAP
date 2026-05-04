"""
Operations Team
===============

Squad 4: Detective + Medic
Mode: coordinate
"""

from agno.team import Team
from agno.team.mode import TeamMode
from agno.compression.manager import CompressionManager

from agents.detective import detective
from agents.medic import medic
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL, STLC_COMPRESSION_PROMPT
from teams.operations.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
operations_team = Team(
    # Identity
    id="operations",
    name="Self-Healing Squad",
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
    # Context compression — Detective produces trace parse output; Medic reads POM files
    # and produces diffs. Both are verbose when captured in shared team history.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000, compress_tool_call_instructions=STLC_COMPRESSION_PROMPT),
    # Context — each heal cycle is per-failure. Session context on members tracks progress.
    # 3 history runs preserves enough coordinator continuity for recurring failures.
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=3,               # reduced from 5: trace + diff outputs accumulate
    max_tool_calls_from_history=3,    # cap member tool results in team history
    # Output
    markdown=True,
    followups=True,
    num_followups=3,
)
