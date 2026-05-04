"""
Grooming Team
=============

INVEST User Story Scoring Squad.
Members: Architect (Jira tools + requirement analysis) + Judge (quality reasoning)
Goal: Score user stories against 10 INVEST/GDS criteria, rewrite to perfection,
      post full assessment as Jira comment for BA review.
"""

from agno.team import Team, TeamMode
from agno.compression.manager import CompressionManager

from agents.architect import architect
from agents.judge import judge
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL, STLC_COMPRESSION_PROMPT
from teams.grooming.instructions import INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
grooming_team = Team(
    # Identity
    id="grooming",
    name="User Story Grooming Squad",
    mode=TeamMode.coordinate,

    # Model
    model=MODEL,

    # Members
    members=[
        architect,   # Jira tools: fetch_jira_ticket, add_jira_comment; requirement analysis
        judge,       # Adversarial quality review; reasoning over criteria scores
    ],

    # Data
    db=agent_db,

    # Instructions
    instructions=INSTRUCTIONS,

    # Collaboration
    share_member_interactions=True,
    show_members_responses=True,

    # Memory
    update_memory_on_run=True,

    # Context compression — scoring + Jira comment formatting can be verbose.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000, compress_tool_call_instructions=STLC_COMPRESSION_PROMPT),

    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,

    # Output
    markdown=True,
    followups=True,
    num_followups=3,
)
