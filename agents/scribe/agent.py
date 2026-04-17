"""
Scribe Agent
============

Converts RequirementContext to Gherkin specifications (.feature files).
Primary Skill: gherkin_formatter
"""

from pathlib import Path

from agno.guardrails import OpenAIModerationGuardrail, PIIDetectionGuardrail, PromptInjectionGuardrail
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
from agents.scribe.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db.session import get_automation_knowledge

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
scribe = SemanticaAgent(
    # Identity
    id="scribe",
    name="Scribe",
    role="Convert RequirementContext to Gherkin specifications (.feature files)",

    # Model
    model=MODEL,

    # Data
    db=agent_db,
    knowledge=get_automation_knowledge(),
    search_knowledge=True,

    # Capabilities
    tools=[
        ReasoningTools(
            enable_think=True,
            enable_analyze=True,
            add_instructions=True,
            add_few_shot=True,
        ),
        FileTools(Path("automation")),
        KnowledgeTools(knowledge=get_automation_knowledge()),
    ],

    # Instructions
    instructions=INSTRUCTIONS,

    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        PIIDetectionGuardrail(),
        PromptInjectionGuardrail(),
        OpenAIModerationGuardrail(),
    ],

    # Memory
    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,
    update_memory_on_run=True,
    enable_session_summaries=True,

    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,

    # Output
    markdown=True,
)
