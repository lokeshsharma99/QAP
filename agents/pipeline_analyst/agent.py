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
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.pipeline_analyst.instructions import INSTRUCTIONS
from agents.pipeline_analyst.tools import download_ci_artifact, parse_allure_results, parse_junit_xml
from app.github_mcp import get_github_mcp_for_pipeline_analyst
from app.settings import MODEL, agent_db
from db import get_automation_kb, get_qap_learnings_kb, get_rca_kb

# ---------------------------------------------------------------------------
# GitHub MCP Tools (requires GITHUB_TOKEN in .env)
# Pipeline Analyst reads GitHub Actions workflow runs, job logs, and artifacts
# to diagnose CI failures and correlate them with triggering code changes.
# Toolsets: actions (workflow runs, job logs), repos (commits, diffs),
#           pull_requests (triggering PR), contexts (repo metadata)
# ---------------------------------------------------------------------------
_github_tools = get_github_mcp_for_pipeline_analyst()

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary:  qap_learnings (collective intelligence — pattern recognition)
# Analysis: rca_kb        — reads past RCA reports to spot recurring failures
#           automation_kb  — finds the automation code for the failing test
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
rca_kb = get_rca_kb()
automation_kb = get_automation_kb()

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
    tools=[
        ReasoningTools(add_instructions=True),
        KnowledgeTools(knowledge=rca_kb),
        KnowledgeTools(knowledge=automation_kb),
        *_github_tools,
        download_ci_artifact,
        parse_junit_xml,
        parse_allure_results,
    ],
    learning=True,
    add_learnings_to_context=True,
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
    enable_agentic_memory=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
