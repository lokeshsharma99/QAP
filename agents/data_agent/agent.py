"""
Data Agent
==========

Provisions test data with PII masking.
Primary Skill: data_factory
"""

import logging
from pathlib import Path

from agno.agent import Agent
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools

from agents.data_agent.instructions import INSTRUCTIONS
from agents.data_agent.tools import (
    clear_data_cache,
    generate_dynamic_test_user,
    generate_run_context,
    get_test_data_on_demand,
)
from app.settings import MODEL, agent_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
data_agent = Agent(
    id="data_agent",
    name="Data Agent",
    role="Provision test data with PII masking for automation tests",
    model=MODEL,
    db=agent_db,
    tools=[
        CodingTools(),
        FileTools(Path("automation")),
        generate_dynamic_test_user,
        get_test_data_on_demand,
        generate_run_context,
        clear_data_cache,
    ],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
