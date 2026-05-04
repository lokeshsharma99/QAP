# CLAUDE.md — Quality Autopilot

This file provides context for AI coding agents working on this repository.
For the full specification, read [AGENTS.md](./AGENTS.md) first.

## Project Overview

Quality Autopilot — An agentic compiler for the Software Testing Life Cycle (STLC).
Built on the Agno Framework. Uses LLM reasoning to design tests and Playwright for execution.

## Architecture

```
Quality Autopilot (app/main.py)
├── Agents (15)
│   ├── Concierge (agents/concierge/)          # routing → Chat entry-point
│   ├── Architect (agents/architect/)          # semantic_search → RequirementContext
│   ├── Scribe (agents/scribe/)                # gherkin_formatter → GherkinSpec (.feature)
│   ├── Discovery (agents/discovery/)          # ui_crawler → SiteManifesto (Accessibility Tree)
│   ├── Librarian (agents/librarian/)          # vector_indexing → codebase_vectors KB
│   ├── Engineer (agents/engineer/)            # file_writer → GitHub PR (Look-Before-You-Leap)
│   ├── Data Agent (agents/data_agent/)        # data_factory → RunContext
│   ├── Detective (agents/detective/)          # trace_analyzer → RCAReport
│   ├── Medic (agents/medic/)                  # surgical_editor → HealingPatch PR
│   ├── Judge (agents/judge/)                  # adversarial_review → JudgeVerdict (Quality Gate)
│   ├── Curator (agents/curator/)              # suite_curation → TestDeletionApproval
│   ├── Technical Tester (agents/technical_tester/) # test_generation → TestPlan
│   ├── CI Log Analyzer (agents/ci_log_analyzer/)   # rca_analysis → PipelineRCAReport
│   ├── Healing Judge (agents/healing_judge/)  # healing_validation → JudgeVerdict (heal)
│   └── Impact Analyst (agents/impact_analyst/) # impact_analysis → ImpactReport
├── Teams (6 Squads — all TeamMode.coordinate)
│   ├── Strategy (teams/strategy/)             # Architect + Scribe
│   ├── Context (teams/context/)               # Discovery + Librarian
│   ├── Engineering (teams/engineering/)       # Engineer + Data Agent
│   ├── Operations (teams/operations/)         # Detective + Medic
│   ├── Diagnostics (teams/diagnostics/)       # CI Log Analyzer + Detective
│   └── Grooming (teams/grooming/)             # Architect + Scribe + Impact Analyst
├── Workflows (10 pipelines)
│   ├── spec_to_code     # Requirement → Spec → Code → PR
│   ├── jira_to_pr       # Jira ticket → full STLC → PR
│   ├── discovery_onboard # AUT → Site Manifesto → KB
│   ├── triage_heal      # Failure → RCA → Patch → Verify
│   ├── automation_scaffold # BDD+POM framework scaffolding
│   ├── full_lifecycle   # All squads end-to-end
│   ├── full_regression  # Regression suite execution
│   ├── grooming         # Backlog → Gherkin batch
│   ├── regression_maintenance # Scheduled locator health checks
│   └── technical_testing # Exploratory test generation
└── Contracts (15 Pydantic models in contracts/)
    RequirementContext, GherkinSpec, SiteManifesto, RunContext,
    RCAReport, PipelineRCAReport, HealingPatch, JudgeVerdict,
    AutomationScaffold, ImpactReport, TestDeletionApproval,
    GroomingAssessment, SquadHandoff, WorkflowStatus, ExecutionResult

Automation Framework (automation/)
├── features/            - BDD feature files (.feature)
├── step_definitions/    - Cucumber step implementations (.ts)
├── pages/               - Playwright Page Object Models (.ts)
├── hooks/               - Test lifecycle hooks (.ts)
├── fixtures/            - Test data fixtures (.ts)
├── config/              - AUT-specific configuration
├── cucumber.conf.ts     - Cucumber configuration
├── playwright.config.ts - Playwright browser config
└── tsconfig.json        - TypeScript configuration
```

## Responsibility Handoff (Canonical Flow)

```
BA moves ticket → Architect → Scribe → Gherkin Judge (≥90% auto, <90% Human)
→ Data Agent → Engineer (Look-Before-You-Leap) → Code Judge (≥90% auto, <90% Human)
→ Local Green → PR submitted
CI/CD fail → Detective → Medic → Healing Judge → 3x verify → auto/Human
```

All agents share:
- PostgreSQL 16 + PgVector for persistence
- Multi-provider MODEL via `MODEL_PROVIDER` env var (default: NVIDIA NIM)
- `STLC_COMPRESSION_PROMPT` via `CompressionManager` for token-efficient context
- Chat history and context management (5-turn window)

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | AgentOS entry point, registers all agents, teams, workflows |
| `app/settings.py` | Shared MODEL, FOLLOWUP_MODEL, agent_db, STLC_COMPRESSION_PROMPT, AUT config |
| `db/session.py` | `get_postgres_db()` and `create_knowledge()` helpers |
| `db/url.py` | Builds database URL from environment |
| `contracts/` | Pydantic models for all agent hand-off protocols (15 models) |
| `compose.yaml` | Docker Compose for full stack (7 services) |
| `control-plane/public/system-guide.html` | In-app architecture guide (rendered at /guide) |

## Model Provider

Set `MODEL_PROVIDER` in `.env` to switch LLM backends:
| Value | Provider | Model |
|-------|----------|-------|
| `nvidia` *(default)* | NVIDIA NIM | qwen/qwen3-coder-480b-a35b-instruct |
| `kilo` | Kilo AI | kilo-auto/free (free tier) |
| `kilo_paid` | Kilo AI | kilo-auto/paid |
| `gemini` | Google | gemini-2.5-flash |
| `gpt4o_mini` | OpenAI | gpt-4o-mini |
| `haiku` | Anthropic | claude-3-5-haiku-latest |

## Development Setup

```bash
# Start services
docker compose up -d --build

# Rebuild UI after changes
docker compose up -d --force-recreate qap-ui

# Local development
python -m app.main

# Format & validate
./scripts/format.sh
./scripts/validate.sh
```

## Automation Framework Setup

```bash
# Install dependencies
cd automation
npm install

# Run tests
npm test

# Run tests with visible browser
npm run test:headed

# Run specific feature
npx cucumber-js features/login.feature --require hooks/**/*.ts --require step_definitions/**/*.ts --require-module ts-node/register
```

## Conventions

See [AGENTS.md](./AGENTS.md) for the full specification including:
- Parameter ordering (Agent, Team, Workflow)
- Section header format
- Import conventions
- File structure requirements
- Anti-patterns to avoid

## Gated Roadmap

Phase 0 → 0.5 → 1 → 2 → 3 → 4 → 5

Every phase has a gate. Do not proceed until the gate passes.
See Section XII of AGENTS.md for details.

## Environment Variables

Required:
- `OPENAI_API_KEY`

Automation Framework:
- `BASE_URL` - AUT base URL (default: https://demo.nopcommerce.com/)
- `HEADLESS` - Run tests in headless mode (default: true)
- `BROWSER` - Browser to use (default: chromium)

## Ports

- API: 8000
- Database: 5432
- Agent UI: 3000
- Playwright MCP: 8931
