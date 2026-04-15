"""
Engineer Agent
==============

Writes modular Playwright POMs and Step Definitions.
Primary Skill: file_writer
"""

from pathlib import Path

from agno.guardrails import OpenAIModerationGuardrail, PromptInjectionGuardrail
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools
from agno.tools.mcp import MCPTools
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
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
from db.session import get_automation_knowledge

# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------
try:
    automation_knowledge = get_automation_knowledge()
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
    ReasoningTools(
        enable_think=True,
        enable_analyze=True,
        add_instructions=True,
        add_few_shot=True,
    ),
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

engineer = SemanticaAgent(
    id="engineer",
    name="Engineer",
    role="Write modular Playwright POMs and Step Definitions (Look-Before-You-Leap)",
    model=MODEL,
    db=None,
    knowledge=automation_knowledge,
    search_knowledge=automation_knowledge is not None,
    tools=engineer_tools,
    instructions=INSTRUCTIONS,

    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        PromptInjectionGuardrail(),
        OpenAIModerationGuardrail(),
    ],

    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,
    update_memory_on_run=True,
    enable_session_summaries=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
