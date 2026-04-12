"""
Engineer Agent
==============

Writes modular Playwright POMs and Step Definitions.
Primary Skill: file_writer
"""

from agno.agent import Agent
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools
from agno.tools.mcp import MCPTools

from agents.engineer.instructions import INSTRUCTIONS
from agents.engineer.tools import (
    create_scaffold,
    run_playwright_script,
)
from app.settings import MODEL, agent_db
from db.session import get_automation_scaffold_knowledge

# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------
automation_knowledge = get_automation_scaffold_knowledge()

# ---------------------------------------------------------------------------
# Playwright MCP Tools
# ---------------------------------------------------------------------------
playwright_mcp = MCPTools(
    transport="streamable-http",
    url="http://qap-playwright-mcp:8931/mcp",
    exclude_tools=["browser_take_screenshot"],
)

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
engineer = Agent(
    id="engineer",
    name="Engineer",
    role="Write modular Playwright POMs and Step Definitions (Look-Before-You-Leap)",
    model=MODEL,
    db=agent_db,
    knowledge=automation_knowledge,
    search_knowledge=True,
    tools=[
        CodingTools(),
        FileTools(),
        playwright_mcp,
        create_scaffold,
        run_playwright_script,
        KnowledgeTools(knowledge=automation_knowledge),
    ],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
