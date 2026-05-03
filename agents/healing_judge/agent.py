"""
Healing Judge Agent
===================

Performs adversarial review of healing patches before application.
Primary Skill: healing_validation
"""

from agno.compression.manager import CompressionManager
from agno.learn import LearningMachine, LearningMode, UserMemoryConfig
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
from agents.healing_judge.instructions import INSTRUCTIONS
from agents.healing_judge.tools import healing_judge_tools
from db import get_culture_manager
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
healing_judge = SemanticaAgent(
    # Identity
    id="healing-judge",
    name="Healing Judge",
    role="Perform adversarial review of healing patches with surgical edit validation",

    # Model
    model=MODEL,

    # Data
    db=agent_db,

    # Capabilities
    tools=[
        ReasoningTools(
            enable_think=True,
            enable_analyze=True,
            add_instructions=True,
            add_few_shot=True,
        ),
        healing_judge_tools,
    ],

    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail excluded — reviews healing patches containing
    # locator strings and test data patterns (e.g. email input selectors).

    # Memory
    # UserMemoryConfig(ALWAYS): silently learns healing patterns — e.g.
    # "this project's locators frequently drift in the checkout flow" —
    # so the Judge calibrates confidence thresholds based on past patch history.
    learning=LearningMachine(
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
    # Context compression — healing patch diffs and verification logs can be verbose.
    # Compress as safety net while preserving full history for accurate surgical review.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000),
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,    # preserved: Healing Judge needs patch history for consistency

    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
