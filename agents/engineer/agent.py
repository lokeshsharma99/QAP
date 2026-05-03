"""
Engineer Agent
==============

Primary skill: file_writer
Role: Author modular Playwright POMs and Step Definitions (Look-Before-You-Leap).
"""

from agno.agent import Agent
from agno.compression.manager import CompressionManager
from agno.learn import EntityMemoryConfig, LearningMachine, LearningMode, SessionContextConfig, UserMemoryConfig
from agno.memory import MemoryManager
from app.guardrails import prompt_injection_guardrail
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools

from agents.engineer.instructions import INSTRUCTIONS
from agents.engineer.tools import run_typecheck, write_feature, write_pom, write_step_def, run_tests, parse_test_report, write_run_context, run_eslint, run_ruff
from agents.librarian.agent import automation_knowledge
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
from db import get_qap_learnings_kb, get_site_manifesto_kb, get_culture_manager

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
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

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
    # enable_think+analyze on both: Engineer must reason about which component to search for,
    # then analyze whether the found locator/pattern is valid before writing any code.
    tools=[
        CodingTools(requires_confirmation_tools=["run_shell"]),
        FileTools(),
        KnowledgeTools(knowledge=site_manifesto_kb, enable_think=True, enable_search=True, enable_analyze=True),
        KnowledgeTools(knowledge=qap_learnings_kb, enable_think=True, enable_search=True, enable_analyze=True),
        *_github_tools,
        write_pom,
        write_step_def,
        write_feature,
        write_run_context,
        run_typecheck,
        run_eslint,
        run_ruff,
        run_tests,
        parse_test_report,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail excluded — engineer receives Gherkin specs with
    # Example tables containing test emails/phones and Site Manifesto component data.
    pre_hooks=[
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
    # SessionContextConfig(planning): tracks PR build steps (Manifesto→KB→MCP verify→write→run→PR)
    # across turns. Engineer is the most step-oriented agent — planning mode lets it mark
    # each step done/in-progress so a resumed session continues from the right point.
    # UserMemoryConfig(ALWAYS): silently captures per-user coding conventions — e.g.
    # "this user prefers aria-label over data-testid" — without cluttering responses.
    learning=LearningMachine(
        session_context=SessionContextConfig(enable_planning=True),
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
        # EntityMemoryConfig(ALWAYS): Engineer extracts AUT entities on every PR build —
        # selector patterns, component class names, page URLs. Cross-session entity store
        # means a new session "knows" all previously written POMs without a KB search.
        entity_memory=EntityMemoryConfig(mode=LearningMode.ALWAYS),
    ),
    update_memory_on_run=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    tool_call_limit=50,
    # Context compression — CodingTools + FileTools + KnowledgeTools produce verbose
    # results (file contents, lint output, KB docs). Compress after 4 000 tokens to
    # prevent context overflow on kilo-auto/free during multi-step PR builds.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000),
    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=3,               # reduced from 5: each run is tool-call-heavy
    max_tool_calls_from_history=3,    # keep only last 3 tool results per history run
    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
