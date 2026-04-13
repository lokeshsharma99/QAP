"""
Scribe Agent
============

Converts RequirementContext to Gherkin specifications (.feature files).
Primary Skill: gherkin_formatter
"""

from pathlib import Path

from agno.agent import Agent
from agno.tools.file import FileTools
from agno.tools.reasoning import ReasoningTools

from agents.scribe.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
scribe = Agent(
    # Identity
    id="scribe",
    name="Scribe",
    role="Convert RequirementContext to Gherkin specifications (.feature files)",

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
        FileTools(Path("automation")),
    ],

    # Instructions
    instructions=INSTRUCTIONS,

    # Memory
    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,

    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,

    # Output
    markdown=True,
)
