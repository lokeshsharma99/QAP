"""
Optimize Memories Endpoint Override
====================================

Replaces AgentOS's default /optimize-memories handler with one that uses
MODEL from app.settings (kilo-auto/free via Kilo AI) instead of the
MemoryManager default (gpt-4o / OPENAI_API_KEY).
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from agno.db.base import AsyncBaseDb
from agno.memory import MemoryManager
from agno.memory.strategies.summarize import SummarizeStrategy
from agno.memory.strategies.types import MemoryOptimizationStrategyType
from agno.os.routers.memory.schemas import (
    OptimizeMemoriesRequest,
    OptimizeMemoriesResponse,
    UserMemorySchema,
)

from app.settings import MODEL, agent_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(tags=["Memory"])


@router.post(
    "/optimize-memories",
    response_model=OptimizeMemoriesResponse,
    status_code=200,
    operation_id="optimize_memories_kilo",
    summary="Optimize User Memories (Kilo)",
    description=(
        "Optimize all memories for a given user using the summarize strategy "
        "powered by kilo-auto/free via Kilo AI OpenRouter. "
        "Set apply=false to preview results without saving."
    ),
)
async def optimize_memories(
    http_request: Request,
    request: OptimizeMemoriesRequest,
    db_id: Optional[str] = Query(default=None, description="Database ID (ignored — uses QAP agent_db)"),
    table: Optional[str] = Query(default=None, description="Table (ignored — uses QAP agent_db)"),
) -> OptimizeMemoriesResponse:
    """Override: use MODEL (kilo-auto/free) instead of MemoryManager's gpt-4o default.

    If OrgScopingMiddleware set request.state.org_id (i.e. the caller is an authenticated
    QAP user), optimise memories for the whole org — not just the individual user_id sent
    by the Agno UI.  This keeps the optimize-memories action in sync with the org-scoped
    memory written by the run endpoints.
    """
    org_id = getattr(http_request.state, "org_id", None)
    if org_id:
        request.user_id = org_id
    elif hasattr(http_request.state, "user_id") and http_request.state.user_id is not None:
        request.user_id = http_request.state.user_id

    try:
        memory_manager = MemoryManager(model=MODEL, db=agent_db)

        if isinstance(agent_db, AsyncBaseDb):
            memories_before = await memory_manager.aget_user_memories(user_id=request.user_id)
        else:
            memories_before = memory_manager.get_user_memories(user_id=request.user_id)

        if not memories_before:
            raise HTTPException(status_code=404, detail=f"No memories found for user {request.user_id}")

        strategy = SummarizeStrategy()
        tokens_before = strategy.count_tokens(memories_before)
        memories_before_count = len(memories_before)

        if isinstance(agent_db, AsyncBaseDb):
            optimized_memories = await memory_manager.aoptimize_memories(
                user_id=request.user_id,
                strategy=MemoryOptimizationStrategyType.SUMMARIZE,
                apply=request.apply,
            )
        else:
            optimized_memories = memory_manager.optimize_memories(
                user_id=request.user_id,
                strategy=MemoryOptimizationStrategyType.SUMMARIZE,
                apply=request.apply,
            )

        tokens_after = strategy.count_tokens(optimized_memories)
        memories_after_count = len(optimized_memories)
        # Clamp to non-negative — summarization can occasionally produce longer output
        tokens_saved = max(0, tokens_before - tokens_after)
        raw_reduction = ((tokens_before - tokens_after) / tokens_before * 100.0) if tokens_before > 0 else 0.0
        reduction_percentage = max(0.0, raw_reduction)

        optimized_memory_schemas = [
            UserMemorySchema(
                memory_id=mem.memory_id or "",
                memory=mem.memory or "",
                topics=mem.topics,
                agent_id=mem.agent_id,
                team_id=mem.team_id,
                user_id=mem.user_id,
                updated_at=mem.updated_at,
            )
            for mem in optimized_memories
        ]

        return OptimizeMemoriesResponse(
            memories=optimized_memory_schemas,
            memories_before=memories_before_count,
            memories_after=memories_after_count,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            tokens_saved=tokens_saved,
            reduction_percentage=reduction_percentage,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to optimize memories for user %s", request.user_id)
        raise HTTPException(status_code=500, detail=f"Failed to optimize memories: {str(e)}")
