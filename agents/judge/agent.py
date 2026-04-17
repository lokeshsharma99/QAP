"""
Judge Agent
===========

Performs adversarial review of generated specifications.
Primary Skill: adversarial_review
"""

from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from agents.judge.instructions import INSTRUCTIONS
from agents.judge.tools import judge_tools
from app.semantica_context import get_judge_context
from app.settings import AUTO_APPROVE_CONFIDENCE_THRESHOLD, AUTONOMOUS_MODE, MODEL, agent_db

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
judge = Agent(
    # Identity
    id="judge",
    name="Judge",
    role="Perform adversarial review of generated specifications with DoD checklist",

    # Model
    model=MODEL,

    # Data
    db=agent_db,

    # Capabilities
    tools=[
        ReasoningTools(
            enable_think=True,
            enable_analyze=True,
            add_instructions=True,
            add_few_shot=True,
        ),
        judge_tools,
    ],

    # Instructions
    instructions=INSTRUCTIONS,

    # Memory
    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,
    update_memory_on_run=True,
    enable_session_summaries=True,

    # Session State - persist review context across runs
    session_state={
        "reviewed_artifacts": [],
        "review_findings": [],
        "approval_decisions": [],
        "current_artifact": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,

    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,

    # Output
    markdown=True,
)
