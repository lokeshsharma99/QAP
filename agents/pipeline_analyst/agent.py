"""
Pipeline Analyst Agent
======================

Primary skill: pipeline_rca
Role: Analyse GitHub Actions pipeline execution logs for failed test runs.
      Classify the root cause (LOCATOR_CHANGE | FUNCTIONALITY_CHANGE | SCRIPT_ERROR |
      DATA_ISSUE | ENV_FAILURE | TEST_INFRA | FLAKY_TEST) and produce a
      PipelineRCAReport with a concrete, ordered remediation plan.
"""

from agno.agent import Agent
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.learn import LearningMachine, LearningMode, SessionContextConfig, UserMemoryConfig
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.scheduler import SchedulerTools

from agents.pipeline_analyst.instructions import INSTRUCTIONS
from agents.pipeline_analyst.tools import download_ci_artifact, parse_allure_results, parse_junit_xml
from app.ado_mcp import get_ado_mcp_for_pipeline_analyst
from app.atlassian_mcp import get_atlassian_mcp_for_pipeline_analyst
from app.github_mcp import get_github_mcp_for_pipeline_analyst
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
from db import get_qap_learnings_kb, get_rca_kb, get_culture_manager

# ---------------------------------------------------------------------------
# GitHub MCP Tools (requires GITHUB_TOKEN in .env)
# Toolsets: actions (workflow runs, job logs), repos (commits, diffs),
#           pull_requests (triggering PR), contexts (repo metadata)
# ---------------------------------------------------------------------------
_github_tools = get_github_mcp_for_pipeline_analyst()

# ---------------------------------------------------------------------------
# Azure DevOps MCP Tools (requires AZURE_DEVOPS_URL + AZURE_DEVOPS_PAT in .env)
# Domains: core, pipelines, repositories
# Pipeline Analyst uses these to read ADO pipeline runs, job logs, build
# definitions, and repo diffs to diagnose CI failures.
# ---------------------------------------------------------------------------
_ado_tools = get_ado_mcp_for_pipeline_analyst()

# ---------------------------------------------------------------------------
# Atlassian MCP Tools (requires ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN in .env)
# Domains: JiraWorkItem — look up Jira issues linked to failing CI run to
# understand intended behaviour before classifying FUNCTIONALITY_CHANGE.
# ---------------------------------------------------------------------------
_atlassian_tools = get_atlassian_mcp_for_pipeline_analyst()

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary:  qap_learnings (collective intelligence, native search_knowledge=True)
# Analysis: rca_kb — reads past RCA reports to spot recurring failures
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
rca_kb = get_rca_kb()

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
pipeline_analyst = Agent(
    # Identity
    id="pipeline-analyst",
    name="Pipeline Analyst",
    role="Analyse GitHub Actions pipeline logs, classify failures, produce PipelineRCAReport with remediation plan",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    # ReasoningTools: pipeline log reasoning (provides think/analyze once).
    # KnowledgeTools(rca_kb): find recurring failure patterns — primary secondary KB.
    # KnowledgeTools(automation_kb) dropped — Pipeline Analyst reads logs not code.
    tools=[
        ReasoningTools(add_instructions=True),
        SchedulerTools(
            db=agent_db,
            default_endpoint="/agents/pipeline-analyst/runs",
        ),
        KnowledgeTools(knowledge=rca_kb),
        *_github_tools,
        *_ado_tools,
        *_atlassian_tools,
        download_ci_artifact,
        parse_junit_xml,
        parse_allure_results,
    ],
    # Learning
    # UserMemoryConfig(ALWAYS): captures per-user patterns — e.g. "this user's pipelines
    # fail on node 3 due to flaky data setup" — improves first-guess classification.
    # SessionContextConfig(planning): tracks the 2-phase RCA (gather → classify) across
    # turns so long log-analysis sessions survive context reloads.
    learning=LearningMachine(
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
        session_context=SessionContextConfig(enable_planning=True),
    ),
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        pii_detection_guardrail,
        prompt_injection_guardrail,
    ],
    # Session state — tracks analysis context within a session
    session_state={
        "analysed_runs": [],
        "rca_reports": [],
        "recurring_failures": [],
        "current_run_id": None,
        "current_workflow": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory — learns failure patterns across sessions
    update_memory_on_run=True,
    search_past_sessions=True,
    num_past_sessions_to_search=5,
    compress_tool_results=True,
    tool_call_limit=50,
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
