"""
Engineer Agent
==============

Primary skill: file_writer
Role: Author modular Playwright POMs and Step Definitions (Look-Before-You-Leap).
"""

from agno.agent import Agent
from agno.memory import MemoryManager
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools

from agents.engineer.instructions import INSTRUCTIONS
from agents.engineer.tools import run_typecheck, write_feature, write_pom, write_step_def
from agents.librarian.agent import automation_knowledge
from app.settings import MODEL, agent_db
from db import get_qap_learnings_kb, get_site_manifesto_kb

# ---------------------------------------------------------------------------
# GitHub MCP Tools (optional — requires GITHUB_TOKEN in .env)
# Engineer reads existing repo structure + creates PRs with generated code
# ---------------------------------------------------------------------------
from app.github_mcp import get_github_mcp_for_engineer
_github_tools = get_github_mcp_for_engineer()

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: automation_kb (from Librarian — shared object, same PG table)
# Domain:  site_manifesto — Engineer reads Discovery's output before writing code
# Shared:  qap_learnings — Engineer reads patterns, writes learnings after PRs
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
site_manifesto_kb = get_site_manifesto_kb()

# ---------------------------------------------------------------------------
# Memory Manager
# ---------------------------------------------------------------------------
memory_manager = MemoryManager(
    db=agent_db,
    memory_capture_instructions=(
        "Only store automation coding patterns: successful locator strategies "
        "per UI component type, Page Object class patterns that worked, and "
        "AUT-specific UI quirks discovered. Ignore file paths, branch names, "
        "and one-off code snippets."
    ),
)

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
engineer = Agent(
    # Identity
    id="engineer",
    name="Engineer",
    role="Author modular Playwright POMs and Step Definitions (Look-Before-You-Leap)",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    memory_manager=memory_manager,
    knowledge=automation_knowledge,
    search_knowledge=True,
    # Capabilities
    # KnowledgeTools(site_manifesto_kb): Look-Before-You-Leap — verify locators before writing.
    # KnowledgeTools(qap_learnings_kb): read coding patterns and conventions.
    # KnowledgeTools(automation_knowledge) dropped — redundant with native search_knowledge=True.
    tools=[
        CodingTools(requires_confirmation_tools=["run_shell"]),
        FileTools(),
        KnowledgeTools(knowledge=site_manifesto_kb),
        KnowledgeTools(knowledge=qap_learnings_kb),
        *_github_tools,
        write_pom,
        write_step_def,
        write_feature,
        run_typecheck,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        pii_detection_guardrail,
        prompt_injection_guardrail,
    ],
    # Feature-specific
    session_state={
        "created_files": [],
        "created_poms": [],
        "created_step_defs": [],
        "validation_results": {},
        "current_feature": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    update_memory_on_run=True,
    enable_session_summaries=True,
    add_session_summary_to_context=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    tool_call_limit=50,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
