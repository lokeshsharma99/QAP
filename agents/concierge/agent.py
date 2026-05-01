"""
Concierge Agent
===============

Primary skill: routing
Role: Understand the user's goal and route them to the correct agent / team / workflow.
Does NOT perform any technical work — it is the front-door reception agent.
"""

from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from agents.concierge.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
concierge = Agent(
    # Identity
    id="concierge",
    name="Concierge",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    # Capabilities
    tools=[ReasoningTools(add_instructions=True)],
    # Instructions
    instructions=INSTRUCTIONS,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
