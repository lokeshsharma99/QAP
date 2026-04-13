"""
Detective Agent
===============

Analyzes test failures to identify root causes.
"""

from pathlib import Path

from agno.agent import Agent
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools

from agents.detective.instructions import INSTRUCTIONS
from agents.detective.tools import analyze_trace_file
from app.settings import MODEL
from db.session import get_learnings_knowledge

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
detective_tools = [
    CodingTools(),
    FileTools(Path("automation")),
    analyze_trace_file,
]

detective = Agent(
    id="detective",
    name="Detective",
    role="Analyze test failures to identify root causes and determine healability",
    model=MODEL,
    db=None,
    knowledge=get_learnings_knowledge(),
    search_knowledge=True,
    tools=detective_tools,
    instructions=INSTRUCTIONS,
    learning=True,
    add_learnings_to_context=True,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
