"""
Judge Agent
===========

Primary skill: adversarial_review
Role: Run DoD checklist, auto-approve at >= 90% confidence.
"""

from agno.agent import Agent
from agno.compression.manager import CompressionManager
from agno.learn import LearningMachine, LearningMode, DecisionLogConfig, UserMemoryConfig
from agno.memory import MemoryManager
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.user_feedback import UserFeedbackTools

from agents.judge.instructions import INSTRUCTIONS
from agents.judge.tools import JudgeToolkit
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
from app.sonarqube_mcp import get_sonarqube_mcp_tools
from db import get_qap_learnings_kb, get_rca_kb, get_culture_manager

# ---------------------------------------------------------------------------
# SonarQube MCP tools (optional — loaded only if SONAR_TOKEN is set)
# ---------------------------------------------------------------------------
_sonar_tools = get_sonarqube_mcp_tools()

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
# Memory Manager
# ---------------------------------------------------------------------------
memory_manager = MemoryManager(
    db=agent_db,
    memory_capture_instructions=(
        "Only record quality gate decisions. For each verdict store: "
        "artifact_type, confidence score (0-100), pass/fail, and the primary "
        "rejection reason if failed. Ignore conversation pleasantries, "
        "clarifying questions, and administrative messages."
    ),
)

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

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
    memory_manager=memory_manager,
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    # ReasoningTools: adversarial reasoning (provides think/analyze once).
    # KnowledgeTools(rca_kb): check past healing/failure history when reviewing patches.
    # KnowledgeTools(qap_learnings_kb) dropped — redundant with native search_knowledge=True.
    # enable_think+analyze on rca_kb: Judge must formulate a targeted precedent query,
    # then analyze whether the current artifact matches or violates historical patterns.
    tools=[
        ReasoningTools(add_instructions=True),
        UserFeedbackTools(),
        KnowledgeTools(knowledge=rca_kb, enable_think=True, enable_search=True, enable_analyze=True),
        *_decision_tools,
        *_sonar_tools,
        JudgeToolkit(),
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail excluded — judge reviews Gherkin specs with
    # Example tables and RunContext test data containing synthetic email/phone values.
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
    learning=LearningMachine(
        # User memory: retain preferences from AgentUI sessions
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
        # Decision Log: audit trail of every verdict (confidence, reasoning, alternatives)
        # mode=AGENTIC — Judge decides when a decision is significant enough to log
        decision_log=DecisionLogConfig(mode=LearningMode.AGENTIC),
    ),
    search_past_sessions=True,
    num_past_sessions_to_search=5,
    tool_call_limit=30,
    # Context compression — KnowledgeTools(rca_kb) + JudgeToolkit can return verbose
    # RCA histories and artifact bodies. Compress after 4 000 tokens as a safety net.
    # History depth kept at 5 — Judge needs full past verdicts for consistency.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000),
    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,    # preserved: Judge needs full verdict history for consistency
    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
