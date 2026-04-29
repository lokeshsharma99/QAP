"""
Eval Runs Endpoint Override
============================

Replaces AgentOS's default /eval-runs handler with one that always uses
MODEL from app.settings (kilo-auto/free via Kilo AI) as the evaluator/judge
model, instead of the Agno default (o4-mini / OPENAI_API_KEY).

NOTE: AccuracyEval is NOT used for accuracy evals because it requires JSON
structured-output mode which kilo-auto/free (SiliconFlow) does not support.
Instead, accuracy scoring is done via a plain-text prompt parsed with regex.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from agno.agent import Agent
from agno.db.schemas.evals import EvalType
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
    """Custom accuracy eval — avoids AccuracyEval which requires JSON mode (unsupported by kilo-auto/free).

    Runs the agent/team, then asks MODEL to score the output 0-10 via plain text prompt.
    """
    if not ei.expected_output:
        raise HTTPException(status_code=400, detail="expected_output is required for accuracy evaluation")

    # Step 1: Run the component under test
    if agent:
        resp = await agent.arun(ei.input, stream=False)
        actual_output = str(resp.content) if resp.content else ""
        component_id = agent.id
        model_id = agent.model.id if agent.model else None
        model_provider = agent.model.provider if agent.model else None
    elif team:
        resp = await team.arun(ei.input, stream=False)
        actual_output = str(resp.content) if resp.content else ""
        component_id = team.id
        model_id = team.model.id if team.model else None
        model_provider = team.model.provider if team.model else None
    else:
        raise HTTPException(status_code=400, detail="Either agent_id or team_id must be provided")

    # Step 2: Score with MODEL using plain text (no JSON / response_model)
    guidelines_section = f"\n\nAdditional guidelines: {ei.additional_guidelines}" if ei.additional_guidelines else ""
    score_prompt = (
        f"You are an accuracy evaluator. Compare the actual output to the expected output and rate accuracy "
        f"on a scale from 0 to 10 (0=completely wrong, 10=perfect match).{guidelines_section}\n\n"
        f"Input: {ei.input}\n\n"
        f"Expected output: {ei.expected_output}\n\n"
        f"Actual output: {actual_output}\n\n"
        f"Reply with ONLY a single number from 0 to 10 and a one-sentence reason, e.g.: '8 - The answer is mostly correct but missing details.'"
    )
    evaluator = Agent(model=MODEL, markdown=False)
    score_resp = await evaluator.arun(score_prompt, stream=False)
    reasoning = str(score_resp.content or "").strip()

    # Parse the first number found in the response
    match = re.search(r"\b(\d+(?:\.\d+)?)\b", reasoning)
    score = float(match.group(1)) if match else 5.0
    score = max(0.0, min(10.0, score))

    # Step 3: Build EvalSchema directly (bypass the broken AccuracyEval.arun path)
    return EvalSchema(
        id=uuid.uuid4().hex,
        name=ei.name or f"accuracy-{component_id}",
        agent_id=agent.id if agent else None,
        team_id=team.id if team else None,
        model_id=model_id,
        model_provider=model_provider,
        eval_type=EvalType.ACCURACY,
        eval_data={
            "score": score,
            "avg_score": score,
            "num_iterations": 1,
            "input": ei.input,
            "expected_output": ei.expected_output,
            "actual_output": actual_output,
            "reasoning": reasoning,
        },
        created_at=datetime.now(timezone.utc),
    )


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
