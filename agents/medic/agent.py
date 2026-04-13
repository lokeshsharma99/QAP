"""
Medic Agent
===========

Performs surgical edits to fix broken locators.
"""

from pathlib import Path

from agno.agent import Agent
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools

from agents.medic.instructions import INSTRUCTIONS
from agents.medic.tools import (
    apply_surgical_edit,
    generate_healing_patch,
    rollback_edit,
    run_verification_3x,
    verify_edit_safety,
)
from app.settings import MODEL
from db.session import get_learnings_knowledge

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
medic_tools = [
    CodingTools(),
    FileTools(Path("automation")),
    apply_surgical_edit,
    verify_edit_safety,
    rollback_edit,
    generate_healing_patch,
    run_verification_3x,
]

medic = Agent(
    id="medic",
    name="Medic",
    role="Perform surgical edits to fix broken locators (selector changes only, no logic changes)",
    model=MODEL,
    db=None,
    knowledge=get_learnings_knowledge(),
    search_knowledge=True,
    tools=medic_tools,
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
