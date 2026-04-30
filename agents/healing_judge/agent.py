"""
Healing Judge Agent
===================

Performs adversarial review of healing patches before application.
Primary Skill: healing_validation
"""

from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
from agents.healing_judge.instructions import INSTRUCTIONS
from agents.healing_judge.tools import healing_judge_tools
from app.settings import MODEL, agent_db
from contracts.judge_verdict import JudgeVerdict

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
healing_judge = SemanticaAgent(
    # Identity
    id="healing_judge",
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
    pre_hooks=[
        pii_detection_guardrail,
        prompt_injection_guardrail,
    ],

    # Memory
    update_memory_on_run=True,
    enable_session_summaries=True,

    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,

    # Output
    output_schema=JudgeVerdict,
    markdown=True,
    followups=True,
    num_followups=3,
)
