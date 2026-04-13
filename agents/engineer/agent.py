"""
Engineer Agent
==============

Writes modular Playwright POMs and Step Definitions.
Primary Skill: file_writer
"""

from pathlib import Path

from agno.agent import Agent
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools
from agno.tools.mcp import MCPTools

from agents.engineer.instructions import INSTRUCTIONS
from agents.engineer.tools import (
    create_github_pr,
    create_scaffold,
    run_linting,
    run_local_verify,
    run_playwright_script,
    validate_files_created,
)
from app.settings import MODEL, agent_db
from db.session import get_automation_scaffold_knowledge

# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------
try:
    automation_knowledge = get_automation_scaffold_knowledge()
except Exception:
    automation_knowledge = None

# ---------------------------------------------------------------------------
# Playwright MCP Tools
# ---------------------------------------------------------------------------
try:
    playwright_mcp = MCPTools(
        transport="streamable-http",
        url="http://qap-playwright-mcp:8931/mcp",
        exclude_tools=["browser_take_screenshot"],
    )
except Exception:
    playwright_mcp = None

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
engineer_tools = [
    CodingTools(),
    FileTools(Path("automation")),
    create_scaffold,
    run_playwright_script,
    run_linting,
    run_local_verify,
    validate_files_created,
    create_github_pr,
]

# Add KnowledgeTools if knowledge base is available
if automation_knowledge:
    engineer_tools.append(KnowledgeTools(knowledge=automation_knowledge))

# Add Playwright MCP tools if available
if playwright_mcp:
    engineer_tools.append(playwright_mcp)

engineer = Agent(
    id="engineer",
    name="Engineer",
    role="Write modular Playwright POMs and Step Definitions (Look-Before-You-Leap)",
    model=MODEL,
    db=None,
    knowledge=automation_knowledge,
    search_knowledge=automation_knowledge is not None,
    tools=engineer_tools,
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
