# AGENTS.md — Quality Autopilot Ecosystem

> **READ THIS FILE FIRST.** This is the single source of truth for all coding work on the Quality Autopilot project. Every agent, team, workflow, and file you create MUST conform to the patterns, naming, and architecture defined here. Do not deviate. Do not improvise alternative architectures. Do not use frameworks other than Agno.

---

## I. Executive Vision

Quality Autopilot is an **Agentic Compiler** for the Software Testing Life Cycle (STLC). It treats AI as a **Senior SDET** that reasons through requirements, writes Playwright automation, and self-heals broken tests.

**Core Principle:** Use LLM tokens for high-value reasoning (design, coding, triage). Execute zero-cost static code (Playwright) for regression.

**Paradigm:** Moving from "testing the code" to "compiling the specification into a self-healing automation asset."

---

## II. Technology Stack (Non-Negotiable)

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Framework** | [Agno](https://docs.agno.com) (`agno[os]`) | Pure Python. Agents, Teams, Workflows. |
| **Runtime** | AgentOS (FastAPI) | Single process hosts all squads. Port `8000`. |
| **Database** | PostgreSQL 16+ with PgVector | `agnohq/pgvector:18` Docker image. |
| **Embeddings** | `text-embedding-3-small` (OpenAI) | Via `OpenAIEmbedder`. |
| **Search** | `SearchType.hybrid` | All Knowledge bases use hybrid search. |
| **Control Plane** | Agent UI (Next.js/TypeScript) | Fork of `agno-agi/agent-ui`. Port `3000`. |
| **Test Engine** | Playwright (Node.js) | Runs in isolated Docker containers. |
| **MCP Server** | Playwright MCP (`@playwright/mcp@latest`) | HTTP transport on port `8931`. Browser automation via MCP. |
| **Automation Framework** | Cucumber + Playwright (BDD+POM) | TypeScript-based test framework in `automation/`. |
| **Container** | Docker Compose | One `compose.yaml` for the full stack. |

**DO NOT** introduce LangChain, CrewAI, AutoGen, or any other agent framework. Agno is the sole runtime.

---

## III. Project Structure

Follow the `demo-os` directory layout exactly. Every file must match these conventions.

```
quality-autopilot/
├── app/
│   ├── __init__.py
│   ├── main.py                    # AgentOS entry point (registers all squads)
│   ├── settings.py                # Shared MODEL, agent_db, environment flags
│   ├── config.yaml                # Quick prompts for each agent
│   └── registry.py                # Shared tools, models, database connections
├── agents/
│   ├── __init__.py
│   ├── architect/                 # Squad 1: Requirement parser
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── instructions.py
│   │   └── __main__.py
│   ├── scribe/                    # Squad 1: BDD/Gherkin authoring
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── instructions.py
│   │   └── __main__.py
│   ├── discovery/                 # Squad 2: UI Crawling / Site Manifesto
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── instructions.py
│   │   ├── tools.py               # Playwright crawl tools (ui_crawler)
│   │   └── __main__.py
│   ├── librarian/                 # Squad 2: KB Sync / Codebase indexing
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── instructions.py
│   │   └── __main__.py
│   ├── engineer/                  # Squad 3: POM / Step-Def authoring
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── instructions.py
│   │   ├── tools.py               # Code generation, lint, git tools
│   │   └── __main__.py
│   ├── data_agent/                # Squad 3: Test data provisioning
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── instructions.py
│   │   └── __main__.py
│   ├── detective/                 # Squad 4: Failure triage / RCA
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── instructions.py
│   │   ├── tools.py               # Trace parser, log analyzer
│   │   └── __main__.py
│   ├── medic/                     # Squad 4: Self-healing patches
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── instructions.py
│   │   └── __main__.py
│   └── judge/                     # Cross-cutting: Agentic Judge (Quality Gate)
│       ├── __init__.py
│       ├── agent.py               # Adversarial reviewer agent
│       ├── instructions.py        # DoD checklist per artifact type
│       ├── tools.py               # Lint, validation, confidence scoring
│       └── __main__.py
├── teams/
│   ├── __init__.py
│   ├── strategy/                  # Squad 1: Architect + Scribe
│   │   ├── __init__.py
│   │   ├── team.py
│   │   └── instructions.py
│   ├── context/                   # Squad 2: Discovery + Librarian
│   │   ├── __init__.py
│   │   ├── team.py
│   │   └── instructions.py
│   ├── engineering/               # Squad 3: Engineer + Data Agent
│   │   ├── __init__.py
│   │   ├── team.py
│   │   └── instructions.py
│   └── operations/                # Squad 4: Detective + Medic
│       ├── __init__.py
│       ├── team.py
│       └── instructions.py
├── workflows/
│   ├── __init__.py
│   ├── spec_to_code/              # Requirement → Spec → Code pipeline
│   │   ├── __init__.py
│   │   ├── workflow.py
│   │   └── instructions.py
│   ├── discovery_onboard/         # AUT onboarding / Site Manifesto
│   │   ├── __init__.py
│   │   ├── workflow.py
│   │   └── instructions.py
│   ├── triage_heal/               # Failure → RCA → Patch pipeline
│   │   ├── __init__.py
│   │   ├── workflow.py
│   │   └── instructions.py
│   └── full_regression/           # End-to-end regression orchestration
│       ├── __init__.py
│       ├── workflow.py
│       └── instructions.py
│   └── automation_scaffold/      # BDD+POM framework scaffolding
│       ├── __init__.py
│       ├── workflow.py
│       └── instructions.py
├── automation/                   # BDD+POM Test Framework
│   ├── features/                 # BDD feature files (.feature)
│   ├── step_definitions/         # Cucumber step implementations (.ts)
│   ├── pages/                    # Playwright Page Object Models (.ts)
│   ├── hooks/                    # Test lifecycle hooks (.ts)
│   ├── fixtures/                 # Test data fixtures (.ts)
│   ├── config/                   # AUT-specific configuration
│   ├── package.json              # NPM dependencies
│   ├── cucumber.conf.ts          # Cucumber configuration
│   ├── playwright.config.ts      # Playwright configuration
│   └── tsconfig.json             # TypeScript configuration
├── contracts/
│   ├── __init__.py
│   ├── requirement_context.py     # Pydantic: RequirementContext (Execution Plan)
│   ├── gherkin_spec.py            # Pydantic: GherkinSpec + DataRequirements
│   ├── site_manifesto.py          # Pydantic: SiteManifesto
│   ├── execution_result.py        # Pydantic: ExecutionResult
│   ├── run_context.py             # Pydantic: RunContext (test data env)
│   ├── rca_report.py              # Pydantic: RCAReport
│   ├── healing_patch.py           # Pydantic: HealingPatch
│   ├── judge_verdict.py           # Pydantic: JudgeVerdict (quality gate)
│   └── automation_scaffold.py    # Automation scaffolding contract
├── db/
│   ├── __init__.py
│   ├── session.py                 # get_postgres_db(), create_knowledge()
│   └── url.py                     # build_db_url()
├── scripts/
│   ├── entrypoint.sh
│   ├── venv_setup.sh
│   ├── format.sh
│   └── validate.sh
├── evals/                         # Smoke tests, reliability, accuracy
│   └── __init__.py
├── compose.yaml
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── example.env
├── .env
├── AGENTS.md                      # THIS FILE
└── README.md
```

---

## IV. Coding Conventions (Mandatory)

These conventions are derived from the `demo-os` reference implementation. Every file MUST follow them.

### 4.1 Section Headers

Use `# ---` section headers (75-char wide) to separate logical blocks:

```python
# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
```

Common headers by file type:

| File Type | Headers |
|-----------|---------|
| Simple agent | `# Create Agent` |
| Agent with tools | `# Tools` / `# Create Agent` |
| Agent with hooks | `# Hooks` / `# Create Agent` |
| Team with members | `# Members` / `# Create Team` |
| Workflow | `# Agents` / `# Helpers` / `# Create Workflow` |

### 4.2 Agent Parameter Order

**ALWAYS** follow this exact parameter ordering. Omit groups that don't apply. Never reorder.

```python
# Identity
id, name, role                          # role for team members only

# Model
model, reasoning, reasoning_min_steps,
reasoning_max_steps, fallback_models

# Data
db, knowledge, search_knowledge

# Capabilities
tools, skills,
learning, add_learnings_to_context

# Instructions
instructions

# Hooks
pre_hooks, post_hooks

# Feature-specific
dependencies, add_dependencies_to_context
session_state, enable_agentic_state, add_session_state_to_context

# Memory
enable_agentic_memory,
search_past_sessions, num_past_sessions_to_search

# Context
add_datetime_to_context, add_history_to_context,
read_chat_history, num_history_runs

# Output
markdown
```

### 4.3 Team Parameter Order

```python
# Identity
id, name, mode

# Model
model

# Members
members

# Data
db

# Capabilities
tools,
learning, add_learnings_to_context

# Instructions
instructions

# Collaboration
share_member_interactions, show_members_responses

# Memory
enable_agentic_memory,
search_past_sessions, num_past_sessions_to_search

# Context
add_datetime_to_context, add_history_to_context,
read_chat_history, num_history_runs

# Output
markdown
```

### 4.4 Workflow Parameter Order

```python
id, name, steps
```

### 4.5 Imports

Use absolute imports rooted at the project package:

```python
# Database
from db import db_url, get_postgres_db, create_knowledge

# Settings
from app.settings import MODEL, agent_db

# Agents
from agents.architect import architect
from agents.scribe import scribe

# Teams
from teams.strategy import strategy_team

# Workflows
from workflows.spec_to_code import spec_to_code

# Contracts
from contracts.requirement_context import RequirementContext
```

### 4.6 Linting & Formatting

- Line length: 120 characters (`ruff`)
- Type checking: `mypy` with `check_untyped_defs = true`
- Always run before committing:

```bash
./scripts/format.sh
./scripts/validate.sh
```

---

## V. The Squad Definitions

### Agent Skill Reference

Every agent has a specific **Primary Skill** — the core capability it is built around.

| Agent | Primary Skill | Description |
|-------|--------------|-------------|
| Architect | `semantic_search` | Queries KB to analyze requirements and determine affected Page Objects |
| Scribe | `gherkin_formatter` | Translates structured requirements into reusable BDD Gherkin steps |
| Discovery Agent | `ui_crawler` | Launches browser, logs in, explores AUT Accessibility Tree |
| Librarian | `vector_indexing` | Watches Git, re-indexes POMs and Step Defs into PgVector |
| Engineer | `file_writer` | Writes modular Playwright POMs and Step Defs (Look-Before-You-Leap) |
| Data Agent | `data_factory` | Provisions fresh users, injects DB records, sets up API mocks |
| Detective | `trace_analyzer` | Parses Playwright trace.zip to classify failure root cause |
| Medic | `surgical_editor` | Patches only the specific locator line in the Page Object |
| Judge | `adversarial_review` | Runs DoD checklist, auto-approve at ≥90% confidence |

---

### Squad 1: Strategy (The Planners)

This squad acts as the bridge between Business Analysts (BAs) and the Technical team. Their goal is to create a "Contract" that the rest of the fleet must follow.

**Team Mode:** `TeamMode.coordinate`  
**Members:** Architect, Scribe

#### Agent: Architect (`agents/architect/`)

- **ID:** `architect`
- **Primary Skill:** `semantic_search`
- **Role:** High-level analysis of requirements and impact. Parses Jira/ADO tickets and PR descriptions into structured Execution Plan JSON. Queries the Knowledge Base to check if the feature already exists or is a new implementation. Determines which Page Objects will be affected.
- **Tools:** Jira/ADO API tools (custom), `ReasoningTools`, KB semantic search
- **Output:** `RequirementContext` / Execution Plan (Pydantic structured output)
- **DoD:** 100% coverage of Acceptance Criteria from the source ticket.

```python
# agents/architect/agent.py
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from agents.architect.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
architect = Agent(
    id="architect",
    name="Architect",
    role="Analyze requirements, query KB for impact, produce Execution Plan",
    model=MODEL,
    db=agent_db,
    tools=[ReasoningTools(add_instructions=True)],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
```

#### Agent: Scribe (`agents/scribe/`)

- **ID:** `scribe`
- **Primary Skill:** `gherkin_formatter`
- **Role:** Translating requirements into strictly formatted BDD Gherkin steps from the Architect's Execution Plan. Ensures steps are reusable (e.g., uses `Given the user is logged in` instead of re-writing login steps every time).
- **Tools:** `CodingTools`, `FileTools`
- **Output:** `.feature` files + `DataRequirements` JSON
- **DoD:** Gherkin linting passes. Traceability to Jira ticket. Steps are reusable and BA-readable.

```python
# agents/scribe/agent.py
from agno.agent import Agent
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools

from agents.scribe.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
scribe = Agent(
    id="scribe",
    name="Scribe",
    role="Author BDD Gherkin specs from RequirementContext",
    model=MODEL,
    db=agent_db,
    tools=[CodingTools(), FileTools()],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
```

#### Team: Strategy (`teams/strategy/`)

```python
# teams/strategy/team.py
from agno.team import Team
from agno.team.mode import TeamMode

from agents.architect import architect
from agents.scribe import scribe
from app.settings import MODEL, agent_db
from teams.strategy.instructions import LEADER_INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
strategy_team = Team(
    id="strategy",
    name="Strategy Squad",
    mode=TeamMode.coordinate,
    model=MODEL,
    members=[architect, scribe],
    db=agent_db,
    instructions=LEADER_INSTRUCTIONS,
    share_member_interactions=True,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
```

---

### Squad 2: Context (The Librarians)

**Team Mode:** `TeamMode.coordinate`  
**Members:** Discovery Agent, Librarian

#### Agent: Discovery (`agents/discovery/`)

- **ID:** `discovery`
- **Primary Skill:** `ui_crawler`
- **Role:** Launches a browser, authenticates with the AUT, and explores all pages. Identifies the **Accessibility Tree** of every page so the Engineer knows exactly which elements are interactable. Generates the Site Manifesto (JSON map of pages, components, locators).
- **Tools:** Custom Playwright crawl tools (in `tools.py` — the `ui_crawler`), `MCPTools` for browser interaction
- **Output:** `SiteManifesto` (Pydantic structured output)
- **DoD:** Zero "ghost" references. Successful auth handshake with AUT. Navigates ≥3 core pages. Accessibility Tree extracted per page.
- **Crawl Behavior:**
  - Logs in using `AUT_AUTH_USER` / `AUT_AUTH_PASS`
  - Visits each route and captures the Accessibility Tree snapshot
  - Records `data-testid`, `role`, and `text` locators for every interactable element
  - Identifies auth-gated vs. public pages

#### Agent: Librarian (`agents/librarian/`)

- **ID:** `librarian`
- **Primary Skill:** `vector_indexing`
- **Role:** Watches your Git repository. Every time you (or an agent) commit code, the Librarian re-indexes the Page Objects and Step Definitions so the fleet always has the latest "Digital Twin" of your test framework.
- **Tools:** `CodingTools`, Git reading tools
- **Knowledge:** PgVector knowledge base (`codebase_vectors` table)
- **Output:** Up-to-date Vectorized codebase in PgVector
- **DoD:** Retrieves correct Page Object for a specific UI component via semantic query.
- **Trigger:** Re-indexes on every Git commit to the main/develop branch (webhook or polling).

```python
# agents/librarian/agent.py
from agno.agent import Agent
from agno.tools.coding import CodingTools

from agents.librarian.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db.session import get_automation_knowledge

# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------
automation_knowledge = get_automation_knowledge()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
librarian = Agent(
    id="librarian",
    name="Librarian",
    role="Index and retrieve Page Objects and Step Definitions",
    model=MODEL,
    db=agent_db,
    knowledge=automation_knowledge,
    search_knowledge=True,
    tools=[CodingTools()],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
```

---

### Squad 3: Engineering (The Coders)

**Team Mode:** `TeamMode.coordinate`  
**Members:** Engineer, Data Agent

#### Agent: Engineer (`agents/engineer/`)

- **ID:** `engineer`
- **Primary Skill:** `file_writer`
- **Role:** The primary coder. Authors modular Page Object Models (POMs) and Step Definitions in Playwright/TypeScript.
- **Tools:** `CodingTools`, `FileTools`, custom lint/type-check tools
- **Knowledge:** Codebase KB (read), Site Manifesto (read)
- **Output:** Feature branch PR with validated code (GitHub Pull Request)
- **DoD:** `eslint` passes. Type-check passes. Local container execution is Green.
- **Engineering Pattern: "Look-Before-You-Leap"**
  1. **Check the Site Manifesto** — Verify the target page and components exist
  2. **Query the Codebase KB** — Check if a Page Object already exists (avoid duplicates)
  3. **Verify selectors via Playwright MCP** — Confirm locators are valid on the live AUT
  4. **Write modular, static code** — Generate POM + StepDefs
  5. **Run local container execution** — Verify green before PR
- **CRITICAL RULES for generated code:**
  - No hardcoded `sleep()` or `waitForTimeout()`. Use Playwright's auto-waiting.
  - Modular POM pattern. One class per page.
  - No hardcoded test data in steps. Use data fixtures from Data Agent.
  - Locators must use `data-testid`, `role`, or `text` strategies. No fragile CSS/XPath.

#### Agent: Data Agent (`agents/data_agent/`)

- **ID:** `data-agent`
- **Primary Skill:** `data_factory`
- **Role:** Ensures the test environment is ready. Creates fresh users, injects DB records, or sets up API mocks so tests don't fail due to data collisions.
- **Tools:** Custom data tools (`data_factory`), `SQLTools` for database seeding
- **Output:** `run_context.json` — Validated test data fixtures with environment context
- **DoD:** PII masking applied. Unique constraints validated. No production data used. No data collisions.

---

### Squad 4: Operations (The Guardians)

**Team Mode:** `TeamMode.coordinate`  
**Members:** Detective, Medic

#### Agent: Detective (`agents/detective/`)

- **ID:** `detective`
- **Primary Skill:** `trace_analyzer`
- **Role:** When a test fails in CI/CD (GitHub Actions / Azure Pipelines), the Detective pulls the `trace.zip`. It determines if the failure is a **real App Bug**, an **Env Issue**, or a **Script Issue** (broken locator).
- **Tools:** Custom trace parser tools (`trace_analyzer`), `ReasoningTools`
- **Output:** `RCAReport` (Pydantic structured output)
- **DoD:** Classification accuracy > 90%.
- **Classification categories:**
  - `LOCATOR_STALE` — UI element changed (Script Issue)
  - `DATA_MISMATCH` — Test data issue
  - `TIMING_FLAKE` — Race condition
  - `ENV_FAILURE` — Infrastructure issue
  - `LOGIC_CHANGE` — Actual business logic change (requires human — real App Bug)

#### Agent: Medic (`agents/medic/`)

- **ID:** `medic`
- **Primary Skill:** `surgical_editor`
- **Role:** If the Detective identifies a "Script Issue" (`LOCATOR_STALE`), the Medic goes to the live page, finds the moved element, and updates **only the specific line** in the Page Object. NEVER changes business logic.
- **Tools:** `CodingTools`, `FileTools`, Git tools
- **Output:** `HealingPatch` (Pydantic structured output — a GitHub PR)
- **DoD:** Verification run passes (test green 3x after patch). No logic changes.
- **CRITICAL RULES:**
  - Only allowed to modify locator selectors and wait strategies.
  - Must NOT change assertions, test flow, or business logic.
  - Must produce a diff that a human can review.
  - Edits must be **surgical** — one locator line, not a file rewrite.

---

## V-B. The Agentic Judge (The Quality Gate)

Every squad has an **invisible member**: the **Judge**. The Judge is the most critical agent in the autonomous pipeline.

- **ID:** `judge`
- **Primary Skill:** `adversarial_review`
- **Role:** Performs an **Adversarial Review** of its teammates' work. Runs the Definition of Done (DoD) checklist for each artifact type.
- **Tools:** Custom lint/validation tools, `ReasoningTools`
- **Output:** `JudgeVerdict` (Pydantic structured output)

### How the Judge Works

```
Agent produces artifact → Judge reviews against DoD checklist → Verdict
    ├── confidence ≥ 90% → AUTO-APPROVE → artifact passes to next step
    └── confidence < 90% → TRIGGER HumanReviewGateStep → wait for Human Lead
```

### Specialized Judge Variants

| Variant | Reviews | Key Checks |
|---------|---------|------------|
| **Gherkin Judge** | Scribe output | Is this step too technical for a BA? Are steps reusable? Syntax valid? |
| **Code Judge** | Engineer output | Is there a hardcoded sleep? Is the POM modular? Does `eslint` pass? |
| **Data Judge** | Data Agent output | Is PII masked? Are unique constraints satisfied? |
| **Healing Judge** | Medic output | Was only a locator changed? Did tests pass 3x? No logic changes? |

### Trust Logic

- **Confidence ≥ 90%**: Auto-approve. Artifact proceeds autonomously.
- **Confidence < 90%**: Trigger `HumanReviewGateStep`. The artifact is held in AgentUI for the Human Lead to approve/reject.
- **Confidence < 50%**: Auto-reject. Send back to the producing agent with specific feedback.

### Implementation in Agno

The Judge is implemented as a `post_hook` on each workflow step (not as a team member) to keep it "invisible" and non-delegatable:

```python
# agents/judge/agent.py
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from agents.judge.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
judge = Agent(
    id="judge",
    name="Judge",
    model=MODEL,
    db=agent_db,
    tools=[ReasoningTools(add_instructions=True)],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    markdown=True,
)
```

### JudgeVerdict Contract (`contracts/judge_verdict.py`)

```python
from pydantic import BaseModel

class JudgeVerdict(BaseModel):
    artifact_type: str          # "gherkin", "code", "data", "healing"
    agent_id: str               # ID of the agent that produced the artifact
    confidence: float           # 0.0 - 1.0
    passed: bool                # True if confidence >= 0.90
    checklist_results: dict[str, bool]  # Each DoD item and its pass/fail
    rejection_reasons: list[str]  # Empty if passed
    requires_human: bool        # True if confidence < 0.90
```

### Judge in Workflow Steps

The Judge is wired into each workflow as a `Condition` gate:

```python
# Example: Gherkin validation with Judge
from agno.workflow import Condition, Step, Workflow

def judge_approves(step_input):
    """Gate: only proceed if Judge confidence >= 90%."""
    content = str(step_input.previous_step_content or "")
    # Judge runs DoD checklist and returns confidence
    verdict = judge.run(f"Review this Gherkin spec against DoD checklist:\n{content}")
    confidence = extract_confidence(verdict.content)
    return confidence >= 0.90

spec_to_code = Workflow(
    id="spec-to-code",
    name="Spec to Code Pipeline",
    steps=[
        Step(name="Parse Requirements", agent=architect),
        Step(name="Author Gherkin", agent=scribe),
        Condition(
            name="Gherkin Judge Gate",
            evaluator=judge_approves,
            steps=[
                Step(name="Provision Data", agent=data_agent),
                Step(name="Generate Code", agent=engineer),
                Condition(
                    name="Code Judge Gate",
                    evaluator=judge_approves,
                    steps=[Step(name="Submit PR", agent=engineer)],
                ),
            ],
        ),
    ],
)
```

---

## VI. Hand-off Contracts (Pydantic Models)

No agent "guesses." Every transition uses a structured JSON contract defined as Pydantic models in `contracts/`.

### RequirementContext (`contracts/requirement_context.py`)

```python
from pydantic import BaseModel

class AcceptanceCriterion(BaseModel):
    id: str                     # e.g., "AC-001"
    description: str
    testable: bool

class RequirementContext(BaseModel):
    """Also referred to as the 'Execution Plan' — the Architect's output."""
    ticket_id: str              # Jira/ADO ticket ID
    title: str
    description: str
    acceptance_criteria: list[AcceptanceCriterion]
    priority: str               # P0, P1, P2, P3
    component: str              # e.g., "checkout", "auth", "dashboard"
    source_url: str             # Link to original ticket
    affected_page_objects: list[str]  # POMs the Architect determined will be affected
    is_new_feature: bool        # True if no existing coverage found in KB
```

### GherkinSpec (`contracts/gherkin_spec.py`)

```python
from pydantic import BaseModel

class DataRequirement(BaseModel):
    field: str
    type: str
    constraints: str            # e.g., "unique email", "valid US phone"
    pii_mask: bool

class GherkinSpec(BaseModel):
    ticket_id: str
    feature_file: str           # Relative path to .feature file
    feature_content: str        # Full Gherkin text
    data_requirements: list[DataRequirement]
    traceability: dict[str, str]  # AC-ID → Scenario name mapping
```

### SiteManifesto (`contracts/site_manifesto.py`)

```python
from pydantic import BaseModel

class UIComponent(BaseModel):
    name: str                   # e.g., "LoginForm"
    page: str                   # e.g., "/login"
    locator_strategy: str       # data-testid, role, text
    locator_value: str          # e.g., "login-submit-btn"
    component_type: str         # button, input, link, modal, etc.
    aria_role: str | None       # Accessibility Tree role (from ui_crawler)
    aria_label: str | None      # Accessibility Tree label

class PageEntry(BaseModel):
    url: str
    title: str
    requires_auth: bool
    components: list[UIComponent]
    accessibility_tree_hash: str  # Hash of the Accessibility Tree snapshot

class SiteManifesto(BaseModel):
    app_name: str
    base_url: str
    auth_strategy: str          # cookie, token, basic
    pages: list[PageEntry]
    generated_at: str           # ISO timestamp
```

### RCAReport (`contracts/rca_report.py`)

```python
from pydantic import BaseModel

class RCAReport(BaseModel):
    test_name: str
    trace_id: str
    classification: str         # LOCATOR_STALE, DATA_MISMATCH, etc.
    confidence: float           # 0.0 - 1.0
    root_cause: str             # Human-readable explanation
    affected_file: str          # Path to failing test/POM
    affected_locator: str | None
    suggested_fix: str          # What the Medic should do
    requires_human: bool        # True if LOGIC_CHANGE
```

### HealingPatch (`contracts/healing_patch.py`)

```python
from pydantic import BaseModel

class HealingPatch(BaseModel):
    test_name: str
    trace_id: str
    file_path: str
    old_locator: str
    new_locator: str
    diff: str                   # Unified diff format
    verification_passes: int    # Must be ≥ 3
    logic_changed: bool         # MUST be False
```

### RunContext (`contracts/run_context.py`)

```python
from pydantic import BaseModel

class TestUser(BaseModel):
    username: str
    email: str                  # PII masked if needed
    password: str
    role: str                   # e.g., "admin", "user", "guest"

class RunContext(BaseModel):
    """The Data Agent's output — everything the test environment needs."""
    ticket_id: str
    test_users: list[TestUser]
    db_seed_queries: list[str]  # SQL statements for data setup
    api_mocks: dict[str, str]   # endpoint → mock response mapping
    cleanup_queries: list[str]  # SQL statements for teardown
    pii_masked: bool            # Must be True
    unique_constraints_valid: bool  # Must be True
```

---

## VII. Workflow Definitions

### Spec-to-Code Pipeline (`workflows/spec_to_code/`)

```
Requirement (Jira) → Architect → Scribe → Data Agent → Engineer → Local Run → PR
```

Uses: `Step`, `Condition` (gate on Gherkin lint), `Router` (route to Data Agent if data needed)

```python
# workflows/spec_to_code/workflow.py
from agno.workflow import Condition, Step, Workflow

from agents.architect import architect
from agents.data_agent import data_agent
from agents.engineer import engineer
from agents.scribe import scribe
from app.settings import agent_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def gherkin_lint_passes(step_input):
    """Gate: only proceed if Gherkin spec is valid."""
    content = str(step_input.previous_step_content or "")
    # Check for valid Gherkin structure
    return "Feature:" in content and "Scenario:" in content

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
spec_to_code = Workflow(
    id="spec-to-code",
    name="Spec to Code Pipeline",
    steps=[
        Step(name="Parse Requirements", agent=architect),
        Step(name="Author Gherkin", agent=scribe),
        Condition(
            name="Gherkin Validation",
            evaluator=gherkin_lint_passes,
            steps=[
                Step(name="Provision Data", agent=data_agent),
                Step(name="Generate Code", agent=engineer),
            ],
        ),
    ],
)
```

### Triage & Heal Pipeline (`workflows/triage_heal/`)

```
Trace ZIP + Logs → Detective → (if healable) → Medic → Verify 3x
```

Uses: `Step`, `Condition` (gate on `requires_human == False`), `Loop` (verify 3x)

### Discovery Pipeline (`workflows/discovery_onboard/`)

```
AUT URL → Discovery Agent → Site Manifesto → Librarian → Vectorized KB
```

Uses: `Step`, sequential execution

---

## VIII. Database Setup

Follow `demo-os/db/` exactly:

```python
# db/url.py
from os import getenv
from urllib.parse import quote

def build_db_url() -> str:
    driver = getenv("DB_DRIVER", "postgresql+psycopg")
    user = getenv("DB_USER", "ai")
    password = quote(getenv("DB_PASS", "ai"), safe="")
    host = getenv("DB_HOST", "localhost")
    port = getenv("DB_PORT", "5432")
    database = getenv("DB_DATABASE", "ai")
    return f"{driver}://{user}:{password}@{host}:{port}/{database}"

db_url = build_db_url()
```

```python
# db/session.py
from agno.db.postgres import PostgresDb
from agno.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.pgvector import PgVector, SearchType
from db.url import db_url

DB_ID = "quality-autopilot-db"

def get_postgres_db(contents_table: str | None = None) -> PostgresDb:
    if contents_table is not None:
        return PostgresDb(id=DB_ID, db_url=db_url, knowledge_table=contents_table)
    return PostgresDb(id=DB_ID, db_url=db_url)

def create_knowledge(name: str, table_name: str) -> Knowledge:
    return Knowledge(
        name=name,
        vector_db=PgVector(
            db_url=db_url,
            table_name=table_name,
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
        contents_db=get_postgres_db(contents_table=f"{table_name}_contents"),
    )
```

### Knowledge Base Tables

| Knowledge Base | Table Name | Purpose |
|---------------|------------|---------|
| Codebase KB | `codebase_vectors` | POMs, Step Defs, utilities |
| Site Manifesto | `site_manifesto_vectors` | UI component catalog |
| Test Results | `test_results_vectors` | Historical pass/fail context |
| Learnings | `qap_learnings` | Patterns, gotchas, conventions |

---

## IX. App Entry Point

```python
# app/main.py
from agno.os import AgentOS
from pathlib import Path

from agents.architect import architect
from agents.scribe import scribe
from agents.discovery import discovery
from agents.librarian import librarian
from agents.engineer import engineer
from agents.data_agent import data_agent
from agents.detective import detective
from agents.medic import medic
from app.settings import RUNTIME_ENV, agent_db
from teams.strategy import strategy_team
from teams.context import context_team
from teams.engineering import engineering_team
from teams.operations import operations_team
from workflows.spec_to_code import spec_to_code
from workflows.discovery_onboard import discovery_onboard
from workflows.triage_heal import triage_heal

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
        scribe,
        discovery,
        librarian,
        engineer,
        data_agent,
        detective,
        medic,
    ],
    teams=[
        strategy_team,
        context_team,
        engineering_team,
        operations_team,
    ],
    workflows=[
        spec_to_code,
        discovery_onboard,
        triage_heal,
    ],
    config=str(Path(__file__).parent / "config.yaml"),
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=RUNTIME_ENV == "dev",
    )
```

---

## X. Settings

```python
# app/settings.py
from os import getenv
from agno.models.openai import OpenAIResponses
from db import get_postgres_db

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
agent_db = get_postgres_db()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
MODEL = OpenAIResponses(id="gpt-4o")

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
RUNTIME_ENV = getenv("RUNTIME_ENV", "dev")

# ---------------------------------------------------------------------------
# AUT Configuration
# ---------------------------------------------------------------------------
AUT_BASE_URL = getenv("AUT_BASE_URL", "http://localhost:3000")
AUT_AUTH_USER = getenv("AUT_AUTH_USER", "")
AUT_AUTH_PASS = getenv("AUT_AUTH_PASS", "")
```

---

## XI. Docker Compose

```yaml
# compose.yaml
services:
  qap-db:
    image: agnohq/pgvector:18
    container_name: qap-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER:-ai}
      POSTGRES_PASSWORD: ${DB_PASS:-ai}
      POSTGRES_DB: ${DB_DATABASE:-ai}
    volumes:
      - pgdata:/var/lib/postgresql
    ports:
      - "5432:5432"
    networks:
      - qap-net

  qap-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: qap-api
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - RUNTIME_ENV=dev
      - PYTHONPATH=/app
      - DB_HOST=qap-db
      - DB_PORT=5432
      - DB_USER=${DB_USER:-ai}
      - DB_PASS=${DB_PASS:-ai}
      - DB_DATABASE=${DB_DATABASE:-ai}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AUT_BASE_URL=${AUT_BASE_URL:-http://host.docker.internal:3000}
      - AUT_AUTH_USER=${AUT_AUTH_USER:-}
      - AUT_AUTH_PASS=${AUT_AUTH_PASS:-}
    depends_on:
      - qap-db
    networks:
      - qap-net
    extra_hosts:
      - "host.docker.internal:host-gateway"

  qap-playwright:
    image: mcr.microsoft.com/playwright:v1.52.0-noble
    container_name: qap-playwright
    working_dir: /tests
    volumes:
      - ./test-output:/tests
    network_mode: "none"  # Sandbox: no egress by default
    profiles:
      - runner

networks:
  qap-net:

volumes:
  pgdata:
```

---

## XII. The "Slow & Sturdy" Gated Roadmap

**Every phase has a GATE. Do not proceed to the next phase until the gate passes.**

### Phase 0: Infrastructure & Bootstrap

| Item | Target |
|------|--------|
| **Focus** | Docker Compose running. Agent writes to local disk. |
| **Milestone** | `docker compose up -d` succeeds. |
| **Gate** | `GET /health` returns 200. Volume mount verified. |
| **Files to create** | `compose.yaml`, `Dockerfile`, `app/main.py`, `app/settings.py`, `db/`, `example.env` |

### Phase 0.5: AUT Onboarding (Discovery)

| Item | Target |
|------|--------|
| **Focus** | Discovery Agent generates the Site Manifesto. |
| **Milestone** | `SiteManifesto` JSON is persisted in PgVector. |
| **Gate** | Agent performs autonomous login + navigates to 3 core pages. |
| **Files to create** | `agents/discovery/`, `contracts/site_manifesto.py` |

### Phase 1: Contextual Indexing

| Item | Target |
|------|--------|
| **Focus** | Existing POMs and Step Defs vectorized in PgVector. |
| **Milestone** | Librarian indexes all existing test code. |
| **Gate** | Semantic query returns correct Page Object for a UI component. |
| **Files to create** | `agents/librarian/`, KB loading scripts |

### Phase 2: Spec-Driven Development

| Item | Target |
|------|--------|
| **Focus** | Jira/ADO trigger → Gherkin workflow. |
| **Milestone** | Architect + Scribe produce valid `.feature` files. |
| **Gate** | Human Lead approves first 5 generated specs in AgentUI. |
| **Files to create** | `agents/architect/`, `agents/scribe/`, `teams/strategy/`, `contracts/requirement_context.py`, `contracts/gherkin_spec.py` |

### Phase 3: Autonomous Implementation

| Item | Target |
|------|--------|
| **Focus** | Engineer generates and verifies feature tests. |
| **Milestone** | End-to-end: Spec → Code → Local Green. |
| **Gate** | Local execution success rate > 90% before PR. |
| **Files to create** | `agents/engineer/`, `agents/data_agent/`, `teams/engineering/`, `workflows/spec_to_code/` |

### Phase 4: Triage & Surgical Healing

| Item | Target |
|------|--------|
| **Focus** | Detective diagnoses failures. Medic patches locators. |
| **Milestone** | Automated RCA + self-healing loop. |
| **Gate** | 10 consecutive locator breaks healed with 0 human code intervention. |
| **Files to create** | `agents/detective/`, `agents/medic/`, `teams/operations/`, `workflows/triage_heal/`, `contracts/rca_report.py`, `contracts/healing_patch.py` |

### Phase 5: Full Autonomy (The Autopilot)

| Item | Target |
|------|--------|
| **Focus** | Scale and harden. "Human-Gated" → "Audit-Mode." |
| **Milestone** | 95% regression maintenance autonomous for 30 days. |
| **Gate** | Continuous audit trail in `traces_table`. No regressions. |

---

## XIII. Definition of Done (DoD) Matrix

Every artifact produced by an agent MUST pass the Agentic Judge's review before the pipeline continues.

| Artifact | Mandatory Checks (Judge Checklist) | Approval Required |
|----------|--------------------------------------|-------------------|
| Gherkin Spec | Traceability to Jira. Syntax validation. Covers all ACs. Steps are BA-readable. No overly technical steps. Reusable step definitions. | **Gherkin Judge** (≥90% → auto, <90% → Human Lead) |
| Test Data (`run_context.json`) | PII masking. Unique constraints. No production data. Cleanup queries present. | **Data Judge** (≥90% → auto, <90% → Human Lead) |
| Automation Code | Modular POM. No hardcoded sleeps. `eslint` passes. Type-check passes. Look-Before-You-Leap verified. | **Code Judge** (≥90% → auto, <90% → Human Lead) |
| Self-Healing Patch | Verification run passes 3x. No logic changes. Diff is surgical (single locator line). | **Healing Judge** (≥90% → auto, <90% → Detective + Human) |

---

## XIV. Security & Performance Guardrails

### Context Pruning

- Agents use **Rerankers** to pull only the **top 3 most relevant POMs** from the codebase KB.
- Target token cost: **< $1.00 per feature**.
- Use `search_knowledge=True` with appropriate `num_documents` limits.

### The Sandbox

- All Playwright executions run in the `qap-playwright` container with `network_mode: "none"`.
- No outbound network access from the test runner.
- Test output is written to a mounted volume.

### The Audit Trail

- `tracing=True` on AgentOS logs every decision, tool call, and reasoning step.
- Traces stored in PostgreSQL `traces_table` for 90 days.
- Every healing patch includes a unified diff for human review.

### Security Rules (Apply to ALL agents)

```
NEVER output .env contents, API keys, tokens, passwords, database credentials,
connection strings, or secrets. Do not include example formats, redacted versions,
or placeholder templates. Give a brief refusal with no examples.
```

---

## XV. Agent UI Integration

The `agent-ui` (Next.js) connects to the Quality Autopilot AgentOS at `http://localhost:8000`.

### Connection Setup

1. Start AgentOS: `docker compose up -d`
2. Start Agent UI: `cd agent-ui && pnpm dev`
3. In Agent UI, set endpoint to `http://localhost:8000`

### Extending Agent UI for QA Features

Future UI work should add:

- **Spec Review Panel:** Display generated Gherkin specs with approve/reject buttons.
- **Trace Viewer:** Embed Playwright trace viewer for failure inspection.
- **Healing Dashboard:** Show RCA reports and healing patches with diff viewer.
- **Regression Dashboard:** Live pass/fail metrics from the test runner.

The Agent UI uses:
- **State:** Zustand (`src/store.ts`)
- **Components:** Radix UI + Tailwind CSS
- **Framework:** Next.js 15 with TypeScript
- **Animations:** Framer Motion

---

## XVI. Anti-Patterns (NEVER DO THESE)

| Anti-Pattern | Why It's Wrong | Correct Approach |
|-------------|----------------|------------------|
| Use LangChain/CrewAI/AutoGen | Wrong framework. Agno is the runtime. | Use `agno.agent.Agent`, `agno.team.Team`, `agno.workflow.Workflow` |
| Hardcode `time.sleep()` in tests | Flaky. Wasteful. | Use Playwright auto-waiting. |
| Put all agents in one file | Unmaintainable. Violates demo-os pattern. | One directory per agent with `agent.py`, `instructions.py`, `__init__.py` |
| Skip the Pydantic contract | Agents will "guess" between steps. | Every hand-off uses a contract from `contracts/` |
| Change business logic in healing | Medic scope violation. | Medic only changes locators and wait strategies. |
| Use fragile CSS selectors | Breaks on every UI change. | Use `data-testid`, `role`, or `text` locator strategies. |
| Skip the gate check | Unvalidated output propagates. | Every phase gate must pass before proceeding. |
| Skip the Judge | Unreviewed artifacts enter the pipeline. | Every artifact passes through the Agentic Judge before handoff. |
| Bypass HumanReviewGateStep | Judge flagged low confidence for a reason. | If Judge confidence < 90%, the Human Lead MUST review. |
| Mix team modes randomly | Unpredictable delegation. | Strategy/Context/Engineering/Operations all use `coordinate`. |
| Install packages not in pyproject.toml | Breaks Docker builds. | Add to `pyproject.toml` dependencies first. |
| Use SQLite in production | No vector search. No concurrent access. | PostgreSQL + PgVector via `db/session.py`. |
| Nest code more than 3 levels | Cognitive overload. | Flatten with early returns and helper functions. |
| Engineer writes code without checking Site Manifesto first | Hallucinated selectors. | Follow the Look-Before-You-Leap pattern (check Manifesto → query KB → verify MCP → write). |
| Librarian only indexes once | Stale KB causes drift. | Librarian re-indexes on every Git commit to main/develop. |

---

## XVII. Quick Reference: Creating a New Agent

1. Create `agents/my_agent/` directory:
   - `agent.py` — Agent definition following parameter order
   - `instructions.py` — `INSTRUCTIONS = """..."""`
   - `__init__.py` — `from agents.my_agent.agent import my_agent as my_agent`
   - `__main__.py` — CLI runner
   - `tools.py` — Custom tools (if needed)

2. Register in `app/main.py`:
   ```python
   from agents.my_agent import my_agent
   agent_os = AgentOS(agents=[..., my_agent], ...)
   ```

3. Add quick prompts to `app/config.yaml`

4. If the agent produces output for another agent, define the contract in `contracts/`

5. Run format and validation:
   ```bash
   ./scripts/format.sh
   ./scripts/validate.sh
   ```

---

## XVIII. Quick Reference: Creating a New Team

1. Create `teams/my_team/` directory:
   - `team.py` — Team definition following parameter order
   - `instructions.py` — `LEADER_INSTRUCTIONS = """..."""`
   - `__init__.py` — `from teams.my_team.team import my_team as my_team`

2. Register in `app/main.py`:
   ```python
   from teams.my_team import my_team
   agent_os = AgentOS(teams=[..., my_team], ...)
   ```

---

## XIX. Quick Reference: Creating a New Workflow

1. Create `workflows/my_workflow/` directory:
   - `workflow.py` — Workflow with Steps, Conditions, Routers
   - `instructions.py` — Agent instructions used within the workflow
   - `__init__.py` — `from workflows.my_workflow.workflow import my_workflow as my_workflow`

2. Register in `app/main.py`:
   ```python
   from workflows.my_workflow import my_workflow
   agent_os = AgentOS(workflows=[..., my_workflow], ...)
   ```

---

## XX. Environment Variables

```bash
# Required
OPENAI_API_KEY=                    # OpenAI API key

# Database
DB_USER=ai
DB_PASS=ai
DB_HOST=localhost
DB_PORT=5432
DB_DATABASE=ai

# AUT (Application Under Test)
AUT_BASE_URL=http://localhost:3000
AUT_AUTH_USER=
AUT_AUTH_PASS=

# Optional
RUNTIME_ENV=dev                    # dev for auto-reload, prd for RBAC
ANTHROPIC_API_KEY=                 # Fallback models
GOOGLE_API_KEY=                    # Gemini models
```

---

## XXI. Verification Commands

```bash
# Phase 0 Gate
curl http://localhost:8000/health

# Format & Lint
./scripts/format.sh
./scripts/validate.sh

# Smoke Tests
python -m evals smoke
python -m evals smoke --group agents
python -m evals smoke --entity architect

# Local Development
docker compose up -d --build
python -m app.main
```

---

## XXII. Responsibility Handoff Summary

This is the canonical flow. Every arrow is a Pydantic contract. Every gate is the Agentic Judge.

```
BA moves a ticket        → Architect creates the Execution Plan
Architect passes plan     → Scribe writes the Gherkin spec
Scribe produces .feature  → Gherkin Judge reviews → (≥90% auto-approve, <90% Human Lead)
Judge-approved spec       → Data Agent creates run_context.json
Data Agent passes context  → Engineer writes the Playwright code (Look-Before-You-Leap)
Engineer produces PR      → Code Judge reviews → (≥90% auto-approve, <90% Human Lead)
Engineer runs local test  → Green → PR submitted
CI/CD test fails          → Detective pulls trace.zip → RCA Report
Detective finds LOCATOR_STALE → Medic patches the locator → Healing Judge reviews
Medic produces patch PR   → Healing Judge verifies 3x → (≥90% auto-approve, <90% Human Lead)
```

---

> **REMEMBER:** This file is the law. If something conflicts with this file, this file wins. If you're unsure about a pattern, look at `demo-os/` for the reference implementation. If `demo-os/` doesn't cover your case, ask the Human Lead before inventing a new pattern.
