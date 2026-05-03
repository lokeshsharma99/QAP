"""
Technical Tester Agent
======================

Uses Playwright Test Agents (planner, generator, healer) for rapid test generation
and exploratory testing, complementing the existing BDD+POM workflow.
Primary Skill: test_generation
"""

import logging
from pathlib import Path

from agno.compression.manager import CompressionManager
from agno.learn import LearningMachine, LearningMode, SessionContextConfig, UserMemoryConfig, UserProfileConfig
from agno.tools.file import FileTools
from agno.tools.reasoning import ReasoningTools
from app.guardrails import prompt_injection_guardrail

from agents.base.semantica_agent import SemanticaAgent
from agents.technical_tester.instructions import INSTRUCTIONS
from agents.technical_tester.tools import (
    create_seed_test,
    init_playwright_agents,
    list_generated_tests,
    run_generator,
    run_healer,
    run_planner,
    run_tests,
)
from db import get_culture_manager
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
from db import get_automation_kb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Create Knowledge Base
# ---------------------------------------------------------------------------
# Share automation knowledge base with other agents
automation_knowledge = get_automation_kb()

if automation_knowledge is not None:
    logger.info("Technical Tester: Automation knowledge base loaded")
else:
    logger.warning("Technical Tester: Automation knowledge base is None - codebase context unavailable")

# ---------------------------------------------------------------------------
# Build Tools List
# ---------------------------------------------------------------------------
# KnowledgeTools(automation_knowledge) dropped: redundant with native search_knowledge=True.
# ReasoningTools provides think/analyze. Native KB search covers automation_knowledge.
tools = [
    ReasoningTools(
        enable_think=True,
        enable_analyze=True,
        add_instructions=True,
        add_few_shot=True,
    ),
    FileTools(Path("automation")),
    init_playwright_agents,
    create_seed_test,
    run_planner,
    run_generator,
    run_healer,
    list_generated_tests,
    run_tests,
]

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
technical_tester = SemanticaAgent(
    # Identity
    id="technical_tester",
    name="Technical Tester",
    role="Use Playwright Test Agents for rapid test generation, smoke tests, and exploratory testing (complements BDD+POM)",

    # Model
    model=MODEL,

    # Data
    db=agent_db,
    knowledge=automation_knowledge if automation_knowledge else None,
    search_knowledge=automation_knowledge is not None,

    # Capabilities
    tools=tools,

    # Instructions
    instructions=INSTRUCTIONS,

    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail excluded — generates Playwright tests with synthetic
    # test data (fake emails, phones, names) as part of its core function.
    pre_hooks=[
        prompt_injection_guardrail,
    ],

    # Memory
    # UserProfileConfig(ALWAYS): remembers the user's preferred AUT, test scope,
    # and coverage goals so Technical Tester starts test planning immediately.
    # UserMemoryConfig(ALWAYS): learns which page flows are fragile, which selectors
    # succeed, and what test patterns the user tends to approve.
    # SessionContextConfig(planning): tracks multi-step test generation plans so
    # planner → generator → healer sessions resume at the correct step.
    learning=LearningMachine(
        user_profile=UserProfileConfig(mode=LearningMode.ALWAYS),
        session_context=SessionContextConfig(enable_planning=True),
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
    ),
    update_memory_on_run=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    enable_session_summaries=True,

    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context compression — run_tests / run_generator produce very verbose output
    # (test results, generated TypeScript code). Compress after 4 000 tokens.
    # Each technical test session is self-contained; 3 history runs is sufficient.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000),
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=3,               # reduced from 5: test-run output accumulates quickly
    max_tool_calls_from_history=3,    # keep only last 3 tool results per history run

    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
