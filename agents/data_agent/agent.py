"""
Data Agent
==========

Provisions test data with PII masking.
Primary Skill: data_factory
"""

import logging
from pathlib import Path

from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
from agents.data_agent.instructions import INSTRUCTIONS
from agents.data_agent.tools import (
    clear_data_cache,
    generate_dynamic_test_user,
    generate_run_context,
    get_test_data_on_demand,
)
from app.settings import MODEL, agent_db
from db.session import get_automation_knowledge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
data_agent = SemanticaAgent(
    id="data_agent",
    name="Data Agent",
    role="Provision test data with PII masking for automation tests",
    model=MODEL,
    db=agent_db,
    knowledge=get_automation_knowledge(),
    search_knowledge=True,
    tools=[
        CodingTools(),
        FileTools(Path("automation")),
        ReasoningTools(
            enable_think=True,
            enable_analyze=True,
            add_instructions=True,
            add_few_shot=True,
        ),
        KnowledgeTools(knowledge=get_automation_knowledge()),
        generate_dynamic_test_user,
        get_test_data_on_demand,
        generate_run_context,
        clear_data_cache,
    ],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,
    update_memory_on_run=True,
    enable_session_summaries=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
