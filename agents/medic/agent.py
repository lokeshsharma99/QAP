"""
Medic Agent
===========

Primary skill: surgical_editor
Role: Patch only the specific locator line in the Page Object.
"""

from agno.agent import Agent
from agno.compression.manager import CompressionManager
from agno.learn import LearningMachine, LearningMode, SessionContextConfig, UserMemoryConfig
from app.guardrails import prompt_injection_guardrail
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools

from agents.medic.instructions import INSTRUCTIONS
from agents.medic.tools import MedicToolkit
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
from db import get_qap_learnings_kb, get_rca_kb, get_site_manifesto_kb, get_culture_manager

# ---------------------------------------------------------------------------
# Semantica Decision Intelligence (optional — activated via SEMANTICA_ENABLED)
# Records every healing patch decision so Healing Judge can check precedents
# ("was this exact locator already healed 3x this sprint?")
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Playwright MCP Tools (optional — verifies healed locators on live AUT)
# ---------------------------------------------------------------------------
from app.playwright_mcp import get_playwright_mcp_for_medic
_playwright_tools = get_playwright_mcp_for_medic()

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
# Primary: qap_learnings (shared, native search_knowledge=True)
# Domain:  rca_kb       — Medic reads Detective's RCA to know what to patch
#          site_manifesto — Medic looks up the new correct locator from live AUT map
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
rca_kb = get_rca_kb()
site_manifesto_kb = get_site_manifesto_kb()

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

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
    # KnowledgeTools(rca_kb): read Detective's RCA report to know what locator to patch.
    # KnowledgeTools(site_manifesto_kb): find the new correct locator from live AUT map.
    # KnowledgeTools(qap_learnings_kb) dropped — redundant with native search_knowledge=True.
    # KnowledgeTools(automation_kb) dropped — Medic reads POM files via FileTools directly.
    # enable_think+analyze on both: Medic must reason about what the RCA says, search for the
    # current correct locator in the manifesto, then analyze validity before any file edit.
    tools=[
        CodingTools(requires_confirmation_tools=["run_shell"]),
        FileTools(),
        KnowledgeTools(knowledge=rca_kb, enable_think=True, enable_search=True, enable_analyze=True),
        KnowledgeTools(knowledge=site_manifesto_kb, enable_think=True, enable_search=True, enable_analyze=True),
        *_playwright_tools,
        *_decision_tools,
        MedicToolkit(),
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail excluded — patches locator strings in page objects;
    # code context can contain email/phone selector patterns and test data.
    pre_hooks=[
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
    # SessionContextConfig(planning): Medic has 3 explicit steps — identify stale locator,
    # verify new locator in SiteManifesto, create surgical PR. Planning mode marks each
    # step done so partial heals can be resumed without re-running the full analysis.
    # UserMemoryConfig(ALWAYS): learns per-user preferences silently (e.g. PR branch
    # naming conventions, review requirements).
    learning=LearningMachine(
        session_context=SessionContextConfig(enable_planning=True),
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
    ),
    update_memory_on_run=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    tool_call_limit=50,
    # Context compression — Medic reads POM files via FileTools + does live Playwright
    # verification (verbose snapshots). Compress after 4 000 tokens to prevent context
    # overflow on kilo-auto/free during a multi-step heal-and-verify cycle.
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
