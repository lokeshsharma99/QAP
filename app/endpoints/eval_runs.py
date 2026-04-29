"""
Eval Runs Endpoint Override
============================

Replaces AgentOS's default /eval-runs handler with one that always uses
MODEL from app.settings (kilo-auto/free via Kilo AI) as the evaluator/judge
model, instead of the Agno default (o4-mini / OPENAI_API_KEY).
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from agno.agent import Agent
from agno.db.schemas.evals import EvalType
from agno.eval.accuracy import AccuracyEval
from agno.eval.agent_as_judge import AgentAsJudgeEval
from agno.eval.performance import PerformanceEval
from agno.eval.reliability import ReliabilityEval
from agno.os.routers.evals.schemas import EvalRunInput, EvalSchema
from agno.team import Team

from app.settings import MODEL, agent_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent / team registry  (lazy — populated on first request)
# ---------------------------------------------------------------------------
_AGENT_REGISTRY: dict[str, Agent] = {}
_TEAM_REGISTRY: dict[str, Team] = {}


def _build_registry() -> None:
    """Import all agents and teams once and cache them by ID."""
    if _AGENT_REGISTRY:
        return

    # ---- agents ----
    from agents.architect import architect
    from agents.curator import curator
    from agents.data_agent import data_agent
    from agents.detective import detective
    from agents.discovery import discovery
    from agents.engineer import engineer
    from agents.impact_analyst import impact_analyst
    from agents.judge import judge
    from agents.librarian import librarian
    from agents.medic import medic
    from agents.pipeline_analyst import pipeline_analyst
    from agents.scribe import scribe

    for ag in [
        architect, curator, data_agent, detective, discovery, engineer,
        impact_analyst, judge, librarian, medic, pipeline_analyst, scribe,
    ]:
        if isinstance(ag, Agent) and ag.id:
            _AGENT_REGISTRY[ag.id] = ag

    # ---- teams ----
    from teams.context import context_team
    from teams.diagnostics import diagnostics_team
    from teams.engineering import engineering_team
    from teams.grooming import grooming_team
    from teams.operations import operations_team
    from teams.strategy import strategy_team

    for tm in [context_team, diagnostics_team, engineering_team,
               grooming_team, operations_team, strategy_team]:
        if isinstance(tm, Team) and tm.id:
            _TEAM_REGISTRY[tm.id] = tm


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(tags=["Evals"])


@router.post(
    "/eval-runs",
    response_model=EvalSchema,
    status_code=200,
    operation_id="run_eval_kilo",
    summary="Run Evaluation (Kilo)",
    description=(
        "Run an evaluation for an agent or team using kilo-auto/free via Kilo AI "
        "as the evaluator/judge model."
    ),
)
async def run_eval(
    eval_run_input: EvalRunInput,
    db_id: Optional[str] = Query(default=None),
    table: Optional[str] = Query(default=None),
) -> EvalSchema:
    _build_registry()

    if eval_run_input.agent_id and eval_run_input.team_id:
        raise HTTPException(status_code=400, detail="Only one of agent_id or team_id must be provided")
    if not eval_run_input.agent_id and not eval_run_input.team_id:
        raise HTTPException(status_code=400, detail="One of agent_id or team_id must be provided")

    agent: Optional[Agent] = None
    team: Optional[Team] = None

    if eval_run_input.agent_id:
        agent = _AGENT_REGISTRY.get(eval_run_input.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{eval_run_input.agent_id}' not found")

    elif eval_run_input.team_id:
        team = _TEAM_REGISTRY.get(eval_run_input.team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team '{eval_run_input.team_id}' not found")

    # ------------------------------------------------------------------
    # Dispatch by eval type — always pass MODEL as the judge/evaluator
    # ------------------------------------------------------------------
    if eval_run_input.eval_type == EvalType.ACCURACY:
        return await _run_accuracy(eval_run_input, agent, team)

    if eval_run_input.eval_type == EvalType.AGENT_AS_JUDGE:
        return await _run_agent_as_judge(eval_run_input, agent, team)

    if eval_run_input.eval_type == EvalType.PERFORMANCE:
        return await _run_performance(eval_run_input, agent, team)

    # RELIABILITY
    return await _run_reliability(eval_run_input, agent, team)


# ---------------------------------------------------------------------------
# Eval helpers — each injects MODEL
# ---------------------------------------------------------------------------

async def _run_accuracy(
    ei: EvalRunInput,
    agent: Optional[Agent],
    team: Optional[Team],
) -> EvalSchema:
    if not ei.expected_output:
        raise HTTPException(status_code=400, detail="expected_output is required for accuracy evaluation")

    accuracy_eval = AccuracyEval(
        db=agent_db,
        agent=agent,
        team=team,
        input=ei.input,
        expected_output=ei.expected_output,
        additional_guidelines=ei.additional_guidelines,
        additional_context=ei.additional_context,
        num_iterations=ei.num_iterations or 1,
        name=ei.name,
        model=MODEL,  # kilo-auto/free
    )
    result = await accuracy_eval.arun(print_results=False, print_summary=False)
    if not result:
        raise HTTPException(status_code=500, detail="Accuracy evaluation returned no result")
    return EvalSchema.from_accuracy_eval(accuracy_eval=accuracy_eval, result=result)


async def _run_agent_as_judge(
    ei: EvalRunInput,
    agent: Optional[Agent],
    team: Optional[Team],
) -> EvalSchema:
    if not ei.criteria:
        raise HTTPException(status_code=400, detail="criteria is required for agent-as-judge evaluation")

    if agent:
        resp = await agent.arun(ei.input, stream=False)
        output = str(resp.content) if resp.content else ""
        agent_id = agent.id
        team_id = None
    elif team:
        resp = await team.arun(ei.input, stream=False)
        output = str(resp.content) if resp.content else ""
        agent_id = None
        team_id = team.id
    else:
        raise HTTPException(status_code=400, detail="Either agent_id or team_id must be provided")

    judge_eval = AgentAsJudgeEval(
        db=agent_db,
        criteria=ei.criteria,
        scoring_strategy=ei.scoring_strategy or "binary",
        threshold=ei.threshold or 7,
        additional_guidelines=ei.additional_guidelines,
        name=ei.name,
        model=MODEL,  # kilo-auto/free
    )
    result = await judge_eval.arun(input=ei.input, output=output, print_results=False, print_summary=False)
    if not result:
        raise HTTPException(status_code=500, detail="Agent-as-judge evaluation returned no result")

    eval_model_id = judge_eval.model.id if judge_eval.model else None
    eval_model_provider = judge_eval.model.provider if judge_eval.model else None
    return EvalSchema.from_agent_as_judge_eval(
        agent_as_judge_eval=judge_eval,
        result=result,
        agent_id=agent_id,
        team_id=team_id,
        model_id=eval_model_id,
        model_provider=eval_model_provider,
    )


async def _run_performance(
    ei: EvalRunInput,
    agent: Optional[Agent],
    team: Optional[Team],
) -> EvalSchema:
    if agent:
        async def _run():
            return await agent.arun(ei.input, stream=False)
        model_id = agent.model.id if agent.model else None
        model_provider = agent.model.provider if agent.model else None
        agent_id = agent.id
        team_id = None
    elif team:
        async def _run():
            return await team.arun(ei.input, stream=False)
        model_id = team.model.id if team.model else None
        model_provider = team.model.provider if team.model else None
        agent_id = None
        team_id = team.id
    else:
        raise HTTPException(status_code=400, detail="Either agent_id or team_id must be provided")

    perf_eval = PerformanceEval(
        db=agent_db,
        name=ei.name,
        func=_run,
        num_iterations=ei.num_iterations or 10,
        agent_id=agent_id,
        team_id=team_id,
        model_id=model_id,
        model_provider=model_provider,
    )
    result = await perf_eval.arun(print_results=False, print_summary=False)
    if not result:
        raise HTTPException(status_code=500, detail="Performance evaluation returned no result")
    return EvalSchema.from_performance_eval(
        performance_eval=perf_eval,
        result=result,
        agent_id=agent_id,
        team_id=team_id,
        model_id=model_id,
        model_provider=model_provider,
    )


async def _run_reliability(
    ei: EvalRunInput,
    agent: Optional[Agent],
    team: Optional[Team],
) -> EvalSchema:
    if ei.expected_tool_calls is None:
        raise HTTPException(status_code=400, detail="expected_tool_calls is required for reliability evaluation")

    if agent:
        resp = await agent.arun(ei.input, stream=False)
        rel_eval = ReliabilityEval(
            db=agent_db,
            name=ei.name,
            agent_response=resp,
            expected_tool_calls=ei.expected_tool_calls,
            allow_additional_tool_calls=getattr(ei, "allow_additional_tool_calls", False),
            expected_tool_call_arguments=getattr(ei, "expected_tool_call_arguments", None),
        )
        model_id = agent.model.id if agent.model else None
        model_provider = agent.model.provider if agent.model else None
        agent_id = agent.id
        team_id = None
    elif team:
        resp = await team.arun(ei.input, stream=False)
        rel_eval = ReliabilityEval(
            db=agent_db,
            name=ei.name,
            team_response=resp,
            expected_tool_calls=ei.expected_tool_calls,
            allow_additional_tool_calls=getattr(ei, "allow_additional_tool_calls", False),
            expected_tool_call_arguments=getattr(ei, "expected_tool_call_arguments", None),
        )
        model_id = team.model.id if team.model else None
        model_provider = team.model.provider if team.model else None
        agent_id = None
        team_id = team.id
    else:
        raise HTTPException(status_code=400, detail="Either agent_id or team_id must be provided")

    result = await rel_eval.arun(print_results=False)
    if not result:
        raise HTTPException(status_code=500, detail="Reliability evaluation returned no result")
    return EvalSchema.from_reliability_eval(
        reliability_eval=rel_eval,
        result=result,
        agent_id=agent_id,
        team_id=team_id,
        model_id=model_id,
        model_provider=model_provider,
    )
