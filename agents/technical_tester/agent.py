"""
Technical Tester Agent
======================

Uses Playwright Test Agents (planner, generator, healer) for rapid test generation
and exploratory testing, complementing the existing BDD+POM workflow.
Primary Skill: test_generation
"""

import logging
from pathlib import Path

from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools
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
from app.settings import MODEL, agent_db
from db.session import get_automation_knowledge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Create Knowledge Base
# ---------------------------------------------------------------------------
# Share automation knowledge base with other agents
automation_knowledge = get_automation_knowledge()

if automation_knowledge is not None:
    logger.info("Technical Tester: Automation knowledge base loaded")
else:
    logger.warning("Technical Tester: Automation knowledge base is None - codebase context unavailable")

# ---------------------------------------------------------------------------
# Build Tools List
# ---------------------------------------------------------------------------
tools = [
    ReasoningTools(
        enable_think=True,
        enable_analyze=True,
        add_instructions=True,
        add_few_shot=True,
    ),
    FileTools(Path("automation")),
    KnowledgeTools(knowledge=automation_knowledge) if automation_knowledge else None,
    init_playwright_agents,
    create_seed_test,
    run_planner,
    run_generator,
    run_healer,
    list_generated_tests,
    run_tests,
]

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
        PIIDetectionGuardrail(),
        PromptInjectionGuardrail(),
    ],

    # Memory
    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,
    update_memory_on_run=True,
    enable_session_summaries=True,

    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,

    # Output
    markdown=True,
)
