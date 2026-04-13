"""
Healing Judge Agent
===================

Performs adversarial review of healing patches before application.
Primary Skill: healing_validation
"""

from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from agents.healing_judge.instructions import INSTRUCTIONS
from agents.healing_judge.tools import healing_judge_tools
from app.settings import MODEL, agent_db

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
healing_judge = Agent(
    # Identity
    id="healing_judge",
    name="Healing Judge",
    role="Perform adversarial review of healing patches with surgical edit validation",

    # Model
    model=MODEL,

    # Data
    db=agent_db,

    # Capabilities
    tools=[
        ReasoningTools(add_instructions=True),
        healing_judge_tools,
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
