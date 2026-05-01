"""
Technical Tester Agent
======================

Uses Playwright Test Agents (planner, generator, healer) for rapid test generation
and exploratory testing, complementing the existing BDD+POM workflow.
Primary Skill: test_generation
"""

import logging
from pathlib import Path

from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.file import FileTools
from agno.tools.reasoning import ReasoningTools

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
    pre_hooks=[
        pii_detection_guardrail,
        prompt_injection_guardrail,
    ],

    # Memory
    update_memory_on_run=True,
    enable_session_summaries=True,

    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
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
