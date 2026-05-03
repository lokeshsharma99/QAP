"""
Scribe Agent
============

Primary skill: gherkin_formatter
Role: Author BDD Gherkin specs from RequirementContext.
"""

from agno.agent import Agent
from agno.compression.manager import CompressionManager
from agno.learn import LearningMachine, LearningMode, SessionContextConfig, UserMemoryConfig, UserProfileConfig
from app.guardrails import prompt_injection_guardrail
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools

from agents.architect.tools import create_jira_issue, add_jira_comment
from agents.scribe.instructions import INSTRUCTIONS
from app.atlassian_mcp import get_atlassian_mcp_for_scribe
from agno.tools.user_control_flow import UserControlFlowTools
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
from db import get_qap_learnings_kb, get_culture_manager

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings — Scribe reads prior Gherkin patterns and conventions
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()

# ---------------------------------------------------------------------------
# Atlassian MCP Tools (requires ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN in .env)
# Scribe verifies all Jira ACs are covered and links .feature files to issues
# ---------------------------------------------------------------------------
_atlassian_tools = get_atlassian_mcp_for_scribe()

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
scribe = Agent(
    # Identity
    id="scribe",
    name="Scribe",
    role="Author BDD Gherkin specs from RequirementContext",
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
        UserControlFlowTools(),
        create_jira_issue,
        add_jira_comment,
        *_atlassian_tools,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail is intentionally excluded — Scribe is a team member
    # that receives team-internal content (Gherkin specs, ticket descriptions, test data)
    # which legitimately contains PII-like patterns (email formats in examples, etc.).
    # Prompt injection protection is kept to prevent relay attacks.
    pre_hooks=[
        prompt_injection_guardrail,
    ],
    # Feature-specific
    session_state={
        "created_features": [],
        "created_scenarios": [],
        "requirement_contexts": [],
        "current_feature": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    # SessionContextConfig: tracks feature file being written across turns — Scribe
    # often needs multiple turns to refine Gherkin (BA review → revise → finalise).
    # UserMemoryConfig(ALWAYS): learns Gherkin style preferences per user — e.g.
    # "prefers Given/When/Then without And" or "always tag with @smoke".
    learning=LearningMachine(
        # UserProfileConfig(ALWAYS): captures structured profile fields (name, team, BA vs SDET
        # role, preferred Gherkin style) — Scribe auto-applies style preferences and skips
        # onboarding questions for returning users.
        user_profile=UserProfileConfig(mode=LearningMode.ALWAYS),
        session_context=SessionContextConfig(),
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
    ),
    update_memory_on_run=True,
    tool_call_limit=50,
    # Context compression — Atlassian/Jira MCP results and existing .feature file
    # contents can be verbose. Compress after 4 000 tokens.
    # History kept at 4 (not 3) — Scribe needs recent spec context to avoid
    # duplicating Gherkin steps across features.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000),
    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=4,    # reduced from 5; 4 preserves step-reuse context without overflow
    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
