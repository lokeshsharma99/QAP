"""
Medic Agent
===========

Primary skill: surgical_editor
Role: Patch only the specific locator line in the Page Object.
"""

from agno.agent import Agent
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools

from agents.medic.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db import get_automation_kb, get_qap_learnings_kb, get_rca_kb, get_site_manifesto_kb

# ---------------------------------------------------------------------------
# Semantica Decision Intelligence (optional — activated via SEMANTICA_ENABLED)
# Records every healing patch decision so Healing Judge can check precedents
# ("was this exact locator already healed 3x this sprint?")
# ---------------------------------------------------------------------------
_decision_tools: list = []
try:
    from app.semantica_config import SemanticaContext
    if SemanticaContext.is_agent_enabled("medic"):
        from integrations.agno import AgnoDecisionKit  # type: ignore[import]
        from app.semantica_context import get_shared_context
        _shared_ctx = get_shared_context()
        if _shared_ctx is not None:
            _decision_tools = [AgnoDecisionKit(context=_shared_ctx)]
except Exception:
    pass

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings (shared)
# Domain:  rca_kb       — Medic reads Detective's RCA to know what to patch
#          automation_kb — Medic reads the actual POM file to make surgical edit
#          site_manifesto — Medic looks up the new correct locator from live AUT map
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
rca_kb = get_rca_kb()
automation_kb = get_automation_kb()
site_manifesto_kb = get_site_manifesto_kb()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
medic = Agent(
    # Identity
    id="medic",
    name="Medic",
    role="Patch only the specific stale locator in the Page Object — surgical edits only",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    tools=[
        CodingTools(requires_confirmation_tools=["run_shell"]),
        FileTools(),
        KnowledgeTools(knowledge=qap_learnings_kb),
        KnowledgeTools(knowledge=rca_kb),
        KnowledgeTools(knowledge=automation_kb),
        KnowledgeTools(knowledge=site_manifesto_kb),
        *_decision_tools,
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
        "applied_edits": [],
        "generated_patches": [],
        "verification_results": {},
        "current_file": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    enable_agentic_memory=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
