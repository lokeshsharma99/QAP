"""
Context Team
============

Squad 2: Discovery + Librarian
Mode: coordinate
"""

from agno.team import Team
from agno.team.mode import TeamMode
from agno.compression.manager import CompressionManager

from agents.discovery import discovery
from agents.librarian import librarian
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
from teams.context.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
context_team = Team(
    # Identity
    id="context",
    name="Discovery & Indexing Squad",
    mode=TeamMode.coordinate,
    # Model
    model=MODEL,
    # Members
    members=[discovery, librarian],
    # Data
    db=agent_db,
    # Instructions
    instructions=LEADER_INSTRUCTIONS,
    # Collaboration
    share_member_interactions=True,
    show_members_responses=True,
    # Memory
    update_memory_on_run=True,
    # Context compression — share_member_interactions=True means every history run
    # includes all Discovery + Librarian member outputs (20+ tool calls from Discovery
    # alone per crawl). Compress aggressively to prevent context overflow.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000),
    # Context — crawl sessions are self-contained; session_state on members tracks
    # page progress. 2 history runs is sufficient context for the team coordinator.
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=2,               # reduced from 5: each run contains full Discovery crawl
    max_tool_calls_from_history=3,    # cap member tool results flooding team context
    # Output
    markdown=True,
    followups=True,
    num_followups=3,
)
