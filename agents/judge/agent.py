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
        ReasoningTools(add_instructions=True),
        judge_tools,
    ],

    # Instructions
    instructions=INSTRUCTIONS,

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
