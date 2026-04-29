"""
Judge Agent
===========

Primary skill: adversarial_review
Role: Run DoD checklist, auto-approve at >= 90% confidence.
"""

from agno.agent import Agent
from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.judge.instructions import INSTRUCTIONS
from agents.judge.tools import check_code_quality, lint_gherkin, score_confidence
from app.settings import MODEL, agent_db
from db import get_qap_learnings_kb, get_rca_kb

# ---------------------------------------------------------------------------
# Semantica Decision Intelligence (optional — activated via SEMANTICA_ENABLED)
# ---------------------------------------------------------------------------
_decision_tools: list = []
try:
    from app.semantica_config import SemanticaContext
    if SemanticaContext.is_agent_enabled("judge"):
        from integrations.agno import AgnoDecisionKit  # type: ignore[import]
        from app.semantica_context import get_shared_context
        _shared_ctx = get_shared_context()
        if _shared_ctx is not None:
            _decision_tools = [AgnoDecisionKit(context=_shared_ctx)]
except Exception:
    pass

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings — Judge reads prior approval decisions for consistency
#                          Judge WRITES its verdicts as learnings for future runs
# Domain:  rca_kb        — Judge reads RCA history when reviewing healing patches
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
rca_kb = get_rca_kb()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
judge = Agent(
    # Identity
    id="judge",
    name="Judge",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    tools=[
        ReasoningTools(add_instructions=True),
        KnowledgeTools(knowledge=qap_learnings_kb),
        KnowledgeTools(knowledge=rca_kb),
        *_decision_tools,
        lint_gherkin,
        check_code_quality,
        score_confidence,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        PIIDetectionGuardrail(),
        PromptInjectionGuardrail(),
    ],
    # Feature-specific
    session_state={
        "reviewed_artifacts": [],
        "review_findings": [],
        "approval_decisions": [],
        "current_artifact": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    enable_agentic_memory=True,
    # Context
    add_datetime_to_context=True,
    # Output
    markdown=True,
)
