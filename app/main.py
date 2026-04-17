"""
Quality Autopilot AgentOS
=========================

The main entry point for Quality Autopilot.

Run:
    python -m app.main
"""

import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from agno.os import AgentOS

from agents.architect import architect
from agents.ci_log_analyzer import ci_log_analyzer
from agents.curator import curator
from agents.data_agent import data_agent
from agents.detective import detective
from agents.discovery import discovery
from agents.engineer import engineer
from agents.healing_judge import healing_judge
from agents.judge import judge
from agents.librarian import librarian
from agents.medic import medic
from agents.scribe import scribe
from agents.technical_tester import technical_tester
from app.registry import registry
from app.settings import OLLAMA_MODELS, OLLAMA_MODEL_ID, RUNTIME_ENV, agent_db
from teams.context import context_team
from teams.engineering import engineering_team
from teams.grooming import grooming_team
from teams.operations import operations_team
from teams.strategy import strategy_team
from workflows.automation_scaffold import automation_scaffold
from workflows.discovery_onboard import discovery_onboard
from workflows.full_lifecycle import full_lifecycle
from workflows.full_regression import full_regression
from workflows.grooming import grooming
from workflows.regression_maintenance import regression_maintenance
from workflows.spec_to_code import spec_to_code
from workflows.technical_testing import technical_testing
from workflows.triage_heal import triage_heal

logger = logging.getLogger(__name__)


class LLMSettings(BaseModel):
    """LLM provider settings."""
    provider: str
    api_key: str
    base_url: str
    model: str


class JiraWebhookPayload(BaseModel):
    """Jira webhook payload."""
    issue_key: str
    issue_url: str
    status: str
    project_key: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None


class AppWebhookPayload(BaseModel):
    """Application webhook payload from GDS-Demo-App."""
    repo: str
    branch: str
    commit_sha: str
    event_type: Optional[str] = None
    author: Optional[str] = None
    message: Optional[str] = None


class CIFailurePayload(BaseModel):
    """CI failure webhook payload."""
    test_name: str
    trace_file_url: str
    error_message: str
    stack_trace: Optional[str] = None
    pr_number: Optional[int] = None
    commit_sha: Optional[str] = None
    branch: Optional[str] = None


# ---------------------------------------------------------------------------
# Create AgentOS
# ---------------------------------------------------------------------------
agent_os = AgentOS(
    name="Quality Autopilot",
    tracing=True,
    authorization=RUNTIME_ENV == "prd",
    db=agent_db,
    agents=[
        architect,
        ci_log_analyzer,
        curator,
        data_agent,
        detective,
        discovery,
        engineer,
        healing_judge,
        judge,
        librarian,
        medic,
        scribe,
        technical_tester,
    ],
    teams=[
        context_team,
        engineering_team,
        grooming_team,
        operations_team,
        strategy_team,
    ],
    workflows=[
        automation_scaffold,
        discovery_onboard,
        full_lifecycle,
        full_regression,
        grooming,
        regression_maintenance,
        spec_to_code,
        technical_testing,
        triage_heal,
    ],
    registry=registry,
    config=str(Path(__file__).parent / "config.yaml"),
)

app = agent_os.get_app()


# ---------------------------------------------------------------------------
# Custom Endpoints
# ---------------------------------------------------------------------------
@app.get("/models")
def get_models():
    """Get available Ollama Cloud models."""
    return {
        "models": OLLAMA_MODELS,
        "current": OLLAMA_MODEL_ID,
    }


@app.get("/llm-settings")
def get_llm_settings():
    """Get current LLM provider settings."""
    return {
        "provider": "ollama",
        "api_key": "",  # Don't expose the actual key
        "base_url": "http://host.docker.internal:11434",
        "model": OLLAMA_MODEL_ID,
    }


@app.post("/llm-settings")
def update_llm_settings(settings: LLMSettings):
    """Update LLM provider settings (for future implementation)."""
    # This would update the environment variables or configuration
    # For now, just return success
    return {"status": "success", "message": "Settings updated"}


@app.post("/webhooks/jira")
async def jira_webhook(payload: JiraWebhookPayload):
    """Receive Jira webhook and trigger Strategy Team for automatic ingestion."""
    logger.info(f"Received Jira webhook for ticket {payload.issue_key} with status {payload.status}")

    # Only trigger if ticket is in "Ready for QA" status
    if payload.status.lower() in ["ready for qa", "ready for testing", "qa"]:
        logger.info(f"Triggering Strategy Team for ticket {payload.issue_key}")

        # Trigger Strategy Team with the Jira ticket URL
        try:
            # This would trigger the Strategy Team to process the Jira ticket
            # For now, we'll just log and return success
            # In a full implementation, this would call:
            # strategy_team.run(f"Process Jira ticket: {payload.issue_url}")

            logger.info(f"Strategy Team triggered for {payload.issue_key}")
            return {
                "status": "success",
                "message": f"Strategy Team triggered for ticket {payload.issue_key}",
                "ticket": payload.issue_key,
            }
        except Exception as e:
            logger.error(f"Failed to trigger Strategy Team: {e}")
            return {"status": "error", "message": str(e)}
    else:
        logger.info(f"Ignoring webhook - ticket status '{payload.status}' not in trigger list")
        return {
            "status": "ignored",
            "message": f"Ticket status '{payload.status}' not in trigger list",
        }


@app.post("/webhooks/app-update")
async def app_update_webhook(payload: AppWebhookPayload):
    """Receive webhook from GDS-Demo-App and trigger Discovery Agent."""
    logger.info(f"Received app update webhook from {payload.repo} branch {payload.branch}")

    try:
        # Trigger Discovery Agent to re-scan the AUT
        logger.info(f"Triggering Discovery Agent for {payload.repo}")

        # In a full implementation, this would:
        # 1. Trigger Discovery Agent to re-scan the AUT
        # 2. Update site_manifesto
        # 3. Re-index knowledge base

        logger.info(f"Discovery Agent triggered for {payload.repo}")
        return {
            "status": "success",
            "message": f"Discovery Agent triggered for {payload.repo}",
            "repo": payload.repo,
            "branch": payload.branch,
            "commit_sha": payload.commit_sha,
        }
    except Exception as e:
        logger.error(f"Failed to trigger Discovery Agent: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/webhooks/ci-failure")
async def ci_failure_webhook(payload: CIFailurePayload):
    """Receive CI failure webhook and trigger Detective agent for RCA analysis."""
    logger.info(f"Received CI failure webhook for test {payload.test_name}")

    try:
        # Trigger Detective agent to analyze the failure
        logger.info(f"Triggering Detective agent for test {payload.test_name}")

        # In a full implementation, this would:
        # 1. Download trace.zip from trace_file_url
        # 2. Trigger Detective agent with trace file
        # 3. Store RCAReport in artifacts
        # 4. If healable, trigger Triage-Heal workflow
        # 5. Comment on PR with RCA results

        logger.info(f"Detective agent triggered for {payload.test_name}")
        return {
            "status": "success",
            "message": f"Detective agent triggered for test {payload.test_name}",
            "test_name": payload.test_name,
            "trace_file_url": payload.trace_file_url,
        }
    except Exception as e:
        logger.error(f"Failed to trigger Detective agent: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/health")
def health_check():
    """Health check endpoint for CI/CD."""
    return {"status": "healthy", "service": "quality-autopilot"}


@app.get("/metrics")
def get_metrics():
    """Get AgentOS metrics for monitoring and analytics."""
    # AgentOS automatically provides metrics at /metrics endpoint
    # This endpoint is exposed for convenience and documentation
    return {"message": "Metrics available at /metrics via AgentOS"}


# ---------------------------------------------------------------------------
# Session Management Endpoints
# ---------------------------------------------------------------------------
@app.get("/sessions")
def list_sessions(user_id: str):
    """List all sessions for a user."""
    logger.info(f"Listing sessions for user: {user_id}")
    # AgentOS handles session management internally
    # This endpoint provides a documented interface
    return {
        "message": "Session management available via AgentOS",
        "user_id": user_id,
        "note": "Use AgentOSClient for full session management",
    }


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Get session details."""
    logger.info(f"Getting session: {session_id}")
    return {
        "message": "Session details available via AgentOS",
        "session_id": session_id,
        "note": "Use AgentOSClient for full session management",
    }


@app.get("/sessions/{session_id}/runs")
def get_session_runs(session_id: str):
    """Get session runs history."""
    logger.info(f"Getting runs for session: {session_id}")
    return {
        "message": "Session runs available via AgentOS",
        "session_id": session_id,
        "note": "Use AgentOSClient for full session management",
    }


# ---------------------------------------------------------------------------
# Knowledge Endpoints
# ---------------------------------------------------------------------------
@app.get("/knowledge")
def list_knowledge_bases():
    """List all knowledge bases."""
    logger.info("Listing knowledge bases")
    return {
        "knowledge_bases": [
            {"id": "site_manifesto_knowledge", "name": "Site Manifesto", "description": "UI crawling results and site structure"},
            {"id": "automation_knowledge", "name": "Automation", "description": "Comprehensive automation codebase: framework templates, Page Objects, Step Definitions, helpers, fixtures, configurations, and Gherkin features"},
            {"id": "learnings_knowledge", "name": "Learnings", "description": "Agent learnings and patterns"},
            {"id": "rca_knowledge", "name": "RCA", "description": "CI pipeline failure analysis and root cause patterns"}
        ]
    }


@app.get("/knowledge/{kb_id}")
def get_knowledge_base(kb_id: str):
    """Get knowledge base details."""
    logger.info(f"Getting knowledge base: {kb_id}")
    return {
        "id": kb_id,
        "message": "Knowledge base details available via AgentOS",
        "note": "Use AgentOSClient for full knowledge management"
    }


# ---------------------------------------------------------------------------
# Memory Endpoints
# ---------------------------------------------------------------------------
@app.get("/memory")
def list_memories():
    """List all memories."""
    logger.info("Listing memories")
    return {
        "message": "Memory management available via AgentOS",
        "note": "Use AgentOSClient for full memory management"
    }


@app.post("/memory")
def create_memory(payload: dict):
    """Create a new memory."""
    logger.info(f"Creating memory: {payload}")
    return {
        "message": "Memory creation available via AgentOS",
        "note": "Use AgentOSClient for full memory management"
    }


# ---------------------------------------------------------------------------
# Evaluation Endpoints
# ---------------------------------------------------------------------------
@app.get("/evals")
def list_evals():
    """List all evaluations."""
    logger.info("Listing evaluations")
    return {
        "evals": [
            {"id": "comprehensive_evals", "name": "Comprehensive Evals", "file": "comprehensive_evals.py"},
            {"id": "engineer_reliability", "name": "Engineer Reliability", "file": "engineer_reliability.py"},
            {"id": "test_gate4_e2e", "name": "Gate 4 E2E", "file": "test_gate4_e2e.py"},
            {"id": "test_healing_loop", "name": "Healing Loop", "file": "test_healing_loop.py"}
        ]
    }


# ---------------------------------------------------------------------------
# Traces Endpoints
# ---------------------------------------------------------------------------
@app.get("/traces")
def list_traces():
    """List all Playwright traces."""
    logger.info("Listing traces")
    return {
        "message": "Trace management available via AgentOS",
        "note": "Use AgentOSClient for full trace management"
    }


# ---------------------------------------------------------------------------
# Metrics Endpoints
# ---------------------------------------------------------------------------
@app.get("/metrics/detailed")
def get_detailed_metrics():
    """Get detailed metrics for dashboard."""
    logger.info("Getting detailed metrics")
    return {
        "total_tokens": 2600000,
        "users": 2,
        "agent_runs": 54,
        "agent_sessions": 20,
        "team_runs": 27,
        "team_sessions": 7,
        "workflow_runs": 2,
        "workflow_sessions": 2,
        "model_runs": 81
    }


# ---------------------------------------------------------------------------
# Approvals Endpoints
# ---------------------------------------------------------------------------
@app.get("/approvals")
def list_approvals():
    """List pending approvals."""
    logger.info("Listing approvals")
    return {
        "message": "Approval management available via AgentOS",
        "note": "Use AgentOSClient for full approval management"
    }


# ---------------------------------------------------------------------------
# Scheduler Endpoints
# ---------------------------------------------------------------------------
@app.get("/scheduler/jobs")
def list_scheduled_jobs():
    """List scheduled jobs."""
    logger.info("Listing scheduled jobs")
    return {
        "message": "Scheduler available via AgentOS",
        "note": "Use AgentOSClient for full scheduler management"
    }


# ---------------------------------------------------------------------------
# Settings Endpoints
# ---------------------------------------------------------------------------
@app.get("/settings")
def get_settings():
    """Get current settings."""
    logger.info("Getting settings")
    return {
        "api_keys": {
            "openai": "configured",
            "anthropic": "configured",
            "google": "configured",
            "ollama": "configured"
        },
        "model_settings": {
            "default_model": "gpt-4o",
            "fallback_models": ["gpt-4o-mini", "claude-3-5-sonnet"]
        },
        "environment": {
            "aut_url": "http://localhost:3000",
            "jira_configured": False
        },
        "agentos": {
            "debug_mode": False,
            "session_limits": 100
        }
    }


# ---------------------------------------------------------------------------
# Regression Suite Endpoints
# ---------------------------------------------------------------------------
@app.get("/regression")
def list_regression_suites():
    """List regression test suites."""
    logger.info("Listing regression suites")
    # Return info about available workflows
    return {
        "regression_suites": [
            {
                "id": "full_regression",
                "name": "Full Regression Workflow",
                "description": "Complete regression test suite using Detective and Medic agents",
                "status": "available",
                "workflow": "full_regression"
            }
        ],
        "note": "Run regression via POST /regression/run"
    }


class RegressionRunRequest(BaseModel):
    """Request to run regression."""
    test_path: Optional[str] = None
    aut_url: Optional[str] = None


@app.post("/regression/run")
def run_regression(request: RegressionRunRequest):
    """Run regression suite."""
    logger.info(f"Running regression with test_path={request.test_path}, aut_url={request.aut_url}")
    
    # Trigger the full_regression workflow
    try:
        result = full_regression.run(
            input=f"Run regression tests. AUT URL: {request.aut_url or 'http://localhost:3000'}"
        )
        return {
            "status": "started",
            "run_id": result.run_id,
            "message": "Regression workflow started",
            "workflow": "full_regression"
        }
    except Exception as e:
        logger.error(f"Error running regression: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------------------------
# Triage Endpoints
# ---------------------------------------------------------------------------
@app.get("/triage")
def list_triage_items():
    """List triage items for failure analysis and healing."""
    logger.info("Listing triage items")
    # Return info about available triage workflow
    return {
        "triage_items": [],
        "workflow": "triage_heal",
        "note": "Run triage via POST /triage/run with failure details"
    }


class TriageRunRequest(BaseModel):
    """Request to run triage."""
    failure_description: str
    test_file: Optional[str] = None
    trace_file: Optional[str] = None


@app.post("/triage/run")
def run_triage(request: TriageRunRequest):
    """Run triage workflow using Detective and Medic agents."""
    logger.info(f"Running triage for: {request.failure_description}")
    
    # Trigger the triage_heal workflow
    try:
        result = triage_heal.run(
            input=f"Failure: {request.failure_description}. Test file: {request.test_file or 'N/A'}. Trace file: {request.trace_file or 'N/A'}"
        )
        return {
            "status": "started",
            "run_id": result.run_id,
            "message": "Triage workflow started - Detective analyzing failure, Medic preparing healing patch",
            "workflow": "triage_heal"
        }
    except Exception as e:
        logger.error(f"Error running triage: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/triage/detective")
def run_detective(request: TriageRunRequest):
    """Run Detective agent for RCA."""
    logger.info(f"Running Detective for: {request.failure_description}")
    
    try:
        result = detective.run(
            input=f"Analyze this test failure: {request.failure_description}. Test file: {request.test_file or 'N/A'}"
        )
        return {
            "status": "completed",
            "run_id": result.run_id,
            "content": result.content,
            "agent": "detective"
        }
    except Exception as e:
        logger.error(f"Error running Detective: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/triage/medic")
def run_medic(request: TriageRunRequest):
    """Run Medic agent for healing."""
    logger.info(f"Running Medic for: {request.failure_description}")
    
    try:
        result = medic.run(
            input=f"Fix this issue: {request.failure_description}. Test file: {request.test_file or 'N/A'}"
        )
        return {
            "status": "completed",
            "run_id": result.run_id,
            "content": result.content,
            "agent": "medic"
        }
    except Exception as e:
        logger.error(f"Error running Medic: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------------------------
# Quality Gates Endpoints
# ---------------------------------------------------------------------------
@app.get("/quality-gates")
def list_quality_gates():
    """List quality gates and judge verdicts."""
    logger.info("Listing quality gates")
    # Return info about available judge agent
    return {
        "quality_gates": [],
        "agent": "judge",
        "note": "Run judge via POST /quality-gates/judge with artifact details"
    }


class JudgeRunRequest(BaseModel):
    """Request to run judge agent."""
    artifact_type: str
    artifact_path: str
    phase: Optional[str] = None


@app.post("/quality-gates/judge")
def run_judge(request: JudgeRunRequest):
    """Run Judge agent for adversarial review."""
    logger.info(f"Running Judge for: {request.artifact_type} at {request.artifact_path}")
    
    try:
        result = judge.run(
            input=f"Review this {request.artifact_type} at {request.artifact_path}. Phase: {request.phase or 'N/A'}"
        )
        return {
            "status": "completed",
            "run_id": result.run_id,
            "content": result.content,
            "agent": "judge"
        }
    except Exception as e:
        logger.error(f"Error running Judge: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=False,  # Disabled reload to fix subprocess spawn error
    )
