# QAP — Quality Autopilot

**Agentic Compiler for the Software Testing Life Cycle (STLC).**

Quality Autopilot treats AI as a Senior SDET that reasons through requirements, writes Playwright automation, and self-heals broken tests — with a full browser-based control plane at `localhost:3000`.

> **Status:** Phases 0–4 complete ✅ | Phase 5 (Full Autonomy) 🔄 next

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [First-Time Setup](#2-first-time-setup)
3. [Configure Environment Variables](#3-configure-environment-variables)
4. [Start the Stack](#4-start-the-stack)
5. [Verify Everything is Running](#5-verify-everything-is-running)
6. [Set Up Ollama (Embeddings)](#6-set-up-ollama-embeddings)
7. [Open the Control Plane](#7-open-the-control-plane)
8. [Architecture Overview](#8-architecture-overview)
9. [Agents Reference](#9-agents-reference)
10. [Workflows Reference](#10-workflows-reference)
11. [Automation Framework](#11-automation-framework)
12. [Gated Roadmap](#12-gated-roadmap)
13. [Tech Stack](#13-tech-stack)

---

## 1. Prerequisites

Install these on your machine before anything else:

| Dependency | Version | Install |
|-----------|---------|---------|
| **Docker Desktop** | 4.x+ | https://www.docker.com/products/docker-desktop/ |
| **Ollama** | latest | https://ollama.ai |
| **Node.js** | 20+ (LTS) | https://nodejs.org *(only needed for running automation tests locally)* |
| **Git** | any | https://git-scm.com |

> **Windows users:** Enable WSL2 in Docker Desktop settings for best performance.

---

## 2. First-Time Setup

```bash
# 1. Clone the repository
git clone https://github.com/lokeshsharma99/QAP.git
cd QAP

# 2. Copy the environment template
cp example.env .env
```

---

## 3. Configure Environment Variables

Open `.env` in your editor. The minimum required settings:

```bash
# ── Model provider (pick ONE) ──────────────────────────────────────────────

# Option A: Kilo AI (free tier — recommended for first run)
# Sign up at https://app.kilo.ai
KILO_API_KEY=your_kilo_key_here
OPENROUTER_BASE_URL=https://api.kilo.ai/api/openrouter/v1

# Option B: GitHub Copilot (local proxy via VS Code extension)
GITHUB_COPILOT_BASE_URL=http://127.0.0.1:3030/v1

# Option C: NVIDIA NIM
# NVIDIA_API_KEY=your_nvidia_key_here

# ── Ollama (embeddings — required) ────────────────────────────────────────
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_BASE_URL=http://host.docker.internal:11434

# ── GitHub token (for Engineer agent to create PRs) ───────────────────────
# Scopes required: repo, read:org, read:project, workflow
GITHUB_TOKEN=your_github_pat_here

# ── AUT — Application Under Test ──────────────────────────────────────────
AUT_BASE_URL=https://your-app.example.com
# AUT_AUTH_USER=testuser
# AUT_AUTH_PASS=testpass

# ── Jira / Atlassian (for Architect agent — ticket parsing) ───────────────
# ATLASSIAN_URL=https://your-domain.atlassian.net
# ATLASSIAN_EMAIL=you@example.com
# ATLASSIAN_API_TOKEN=your_atlassian_token

# ── Azure DevOps (for CI Log Analyzer + Pipeline Analyst) ─────────────────
# AZURE_DEVOPS_URL=https://dev.azure.com/your-org
# AZURE_DEVOPS_PAT=your_ado_pat
```

> **Tip:** You only need `KILO_API_KEY` + `OLLAMA_HOST` to get started. Everything else is optional and enables specific agents.

---

## 4. Start the Stack

```bash
# Build and start all services
docker compose up -d --build

# ── What gets started ────────────────────────────────────────
# qap-db          PostgreSQL 16 + PgVector         :5432
# qap-api         AgentOS (FastAPI)                :8000
# qap-ui          Control Plane (Next.js)           :3000
# github-mcp      GitHub MCP server                (internal)
# atlassian-mcp   Atlassian/Jira MCP server        (internal)
# ado-mcp         Azure DevOps MCP server          (internal)
# playwright-mcp  Browser automation MCP server    (internal)
```

To enable the browser automation service (Discovery + Medic agents):
```bash
docker compose --profile mcp up -d
```

---

## 5. Verify Everything is Running

```bash
# Check all containers are healthy
docker ps

# Confirm the API is up
curl http://localhost:8000/health
# → {"status":"ok","instantiated_at":"..."}

# Confirm the UI is serving
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# → 200
```

If `qap-api` takes 15–20 seconds to respond on first start, that's normal — it's loading all agent definitions and MCP tool registrations.

---

## 6. Set Up Ollama (Embeddings)

Quality Autopilot uses Ollama for local vector embeddings. Run these on your **host machine** (not inside Docker):

```bash
# Pull the embedding model used by all Knowledge Bases
ollama pull qwen3-embedding:4b

# Verify it's available
ollama list
# NAME                     ID              SIZE    MODIFIED
# qwen3-embedding:4b       ...             ...     ...
```

> **Why Ollama?** All KB search (Site Manifesto, Automation KB, RCA KB) runs through `qwen3-embedding:4b` at 2560 dimensions with hybrid search. This keeps embeddings local — no data sent to external embedding APIs.

---

## 7. Open the Control Plane

Open **http://localhost:3000** in your browser.

| Page | URL | Purpose |
|------|-----|---------|
| **Chat** | `/chat` | Talk to any agent, team, or workflow |
| **Registry** | `/registry` | Browse all registered agents, teams, workflows |
| **Sessions** | `/sessions` | Resume past conversations |
| **Memory** | `/memory` | View / manage agent memories |
| **Knowledge** | `/knowledge` | Browse PgVector KB documents |
| **Traces** | `/traces` | Step-level execution trace viewer |
| **Approvals** | `/approvals` | Human-in-the-Loop queue (Judge-flagged items) |
| **Healing** | `/healing` | RCA reports and patch diff viewer |
| **Metrics** | `/metrics` | Token usage, response times, donut charts |
| **Workflows** | `/workflows` | Workflow run status and step tracking |
| **Dashboard** | `/dashboard` | Live regression pass/fail summary |
| **Evals** | `/evals` | Accuracy and reliability evaluations |
| **Scheduler** | `/scheduler` | Recurring agent/workflow schedules |
| **Guide** | `/guide` | In-app architecture reference (this system) |

**First visit:** The Concierge agent loads automatically with suggested actions. Click a pill or type your request.

---

## 8. Architecture Overview

```
QAP/
├── agents/          15 agents
│   ├── concierge        routing / welcome              → Chat
│   ├── architect        semantic_search                → RequirementContext
│   ├── scribe           gherkin_formatter              → GherkinSpec
│   ├── discovery        ui_crawler                     → SiteManifesto
│   ├── librarian        vector_indexing                → PgVector KB
│   ├── engineer         file_writer                    → GitHub PR
│   ├── data_agent       data_factory                   → RunContext
│   ├── detective        trace_analyzer                 → RCAReport
│   ├── medic            surgical_editor                → HealingPatch
│   ├── judge            adversarial_review             → JudgeVerdict
│   ├── impact_analyst   impact_analysis                → ImpactReport
│   ├── pipeline_analyst pipeline_rca                   → PipelineRCAReport
│   ├── ci_log_analyzer  rca_analysis                   → ADO tickets
│   ├── technical_tester test_generation                → Playwright tests
│   └── healing_judge    healing_validation             → HealingVerdict
├── teams/           6 squads (all TeamMode.coordinate)
│   ├── strategy         Architect + Scribe
│   ├── context          Discovery + Librarian
│   ├── engineering      Engineer + Data Agent
│   ├── operations       Detective + Medic
│   ├── diagnostics      CI Log Analyzer + Detective
│   └── grooming         Architect + Scribe + Impact Analyst
├── workflows/       12 pipelines
│   ├── spec_to_code            Requirement → Spec → Code → PR
│   ├── discovery_onboard       AUT → Site Manifesto → KB
│   ├── triage_heal             Failure → RCA → Patch → Verify
│   ├── impact_assessment       PR/Issue → ImpactReport
│   ├── pipeline_failure_assessment  CI run → PipelineRCAReport
│   ├── jira_to_pr              Jira ticket → PR (end-to-end)
│   ├── grooming                Backlog → Gherkin batch
│   ├── full_lifecycle          Full STLC end-to-end
│   ├── full_regression         Regression suite execution
│   ├── regression_maintenance  Scheduled locator health checks
│   ├── technical_testing       Exploratory test generation
│   └── automation_scaffold     BDD+POM framework scaffolding
├── contracts/       12 Pydantic hand-off models
├── automation/      BDD+POM TypeScript framework
│   ├── features/            Gherkin .feature files
│   ├── step_definitions/    Cucumber steps
│   ├── pages/               Playwright Page Object Models
│   ├── hooks/               Before/After hooks
│   └── fixtures/            Test data fixtures
├── control-plane/   Next.js 15 dashboard (port 3000)
├── db/              PostgreSQL + PgVector helpers
└── app/             AgentOS entry point + settings
```

---

## 9. Agents Reference

### Core 9 (STLC Pipeline)

| Agent | ID | Primary Skill | Output Contract |
|-------|----|--------------|----------------|
| Architect | `architect` | `semantic_search` | `RequirementContext` |
| Scribe | `scribe` | `gherkin_formatter` | `GherkinSpec` |
| Discovery | `discovery` | `ui_crawler` | `SiteManifesto` |
| Librarian | `librarian` | `vector_indexing` | PgVector KB |
| Engineer | `engineer` | `file_writer` | GitHub PR |
| Data Agent | `data-agent` | `data_factory` | `RunContext` |
| Detective | `detective` | `trace_analyzer` | `RCAReport` |
| Medic | `medic` | `surgical_editor` | `HealingPatch` |
| Judge | `judge` | `adversarial_review` | `JudgeVerdict` |

### Extended Agents

| Agent | ID | Primary Skill | Purpose |
|-------|----|--------------|---------|
| Concierge | `concierge` | routing | Welcome + route user to right agent/team/workflow |
| Impact Analyst | `impact-analyst` | `impact_analysis` | PR/Issue → coverage gap report |
| Pipeline Analyst | `pipeline-analyst` | `pipeline_rca` | CI failure → ordered remediation plan |
| CI Log Analyzer | `ci-log-analyzer` | `rca_analysis` | Azure DevOps log → ADO ticket |
| Technical Tester | `technical-tester` | `test_generation` | Exploratory Playwright test generation |
| Healing Judge | `healing-judge` | `healing_validation` | Validate Medic patches before applying |

### Judge Quality Gate

```
confidence ≥ 0.90  → AUTO-APPROVE  → pipeline continues
confidence < 0.90  → Human review  → /approvals queue (Human Lead)
confidence < 0.50  → AUTO-REJECT   → back to producing agent with feedback
```

---

## 10. Workflows Reference

| Workflow | Trigger | Pipeline |
|----------|---------|---------|
| `spec-to-code` | Jira ticket / requirement text | Architect → Scribe → Data Agent → Engineer → PR |
| `discovery-onboard` | AUT URL | Discovery → Site Manifesto → Librarian → KB |
| `triage-heal` | CI trace.zip | Detective → Medic → Healing Judge → Verify 3× |
| `impact-assessment` | PR number / Issue number | Impact Analyst → ImpactReport |
| `pipeline-failure-assessment` | CI run ID | Pipeline Analyst → PipelineRCAReport |
| `jira-to-pr` | Jira ticket ID | Full STLC: ticket → spec → code → PR |
| `grooming` | Backlog of tickets | Grooming team → batch GherkinSpecs |
| `full-lifecycle` | Any requirement | All squads end-to-end |
| `regression-maintenance` | Scheduled | Locator health check + auto-heal loop |
| `technical-testing` | Exploratory request | Technical Tester → Playwright tests |

---

## 11. Automation Framework

```bash
cd automation
npm install

npm test                    # all Cucumber/Playwright tests (headless)
npm run test:headed         # visible browser
npx cucumber-js features/GDS-5-contact-details-form.feature  # single feature
```

**Locator strategy (in priority order):**
1. `data-testid` — most stable
2. `role` — accessibility-based
3. `text` — last resort, visible text

**Rules:** No CSS selectors. No XPath. No `waitForTimeout()` or `sleep()`. Use Playwright auto-waiting.

---

## 12. Gated Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Docker + `/health 200` | ✅ Done |
| 0.5 | Site Manifesto in PgVector | ✅ Done |
| 1 | Codebase KB indexed | ✅ Done |
| 2 | Gherkin workflow live | ✅ Done |
| 3 | Spec → Code → Green | ✅ Done |
| 4 | Triage + Heal loop | ✅ Done |
| 5 | 95% autonomous / 30 days | 🔄 Next |

---

## 13. Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Agent framework | [Agno](https://docs.agno.com) `agno[os]` | Agents, Teams, Workflows, AgentOS |
| Runtime | AgentOS (FastAPI) | Port 8000 |
| Control Plane | Next.js 15 App Router | Port 3000 |
| Database | PostgreSQL 16 + PgVector | `agnohq/pgvector:18` |
| Embeddings | Ollama `qwen3-embedding:4b` | 2560 dimensions, hybrid search |
| Model gateway | Kilo AI / OpenRouter | `kilo-auto/free` default |
| Test engine | Playwright + Cucumber (TypeScript) | BDD+POM pattern |
| MCP servers | GitHub, Atlassian, ADO, Playwright | Tool namespacing per agent |
| Container | Docker Compose | Single `compose.yaml` |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `qap-api` takes 20s to start | Normal — MCP tool registration. Wait for `/health` to return 200 |
| Embedding errors on KB search | Ensure Ollama is running and `qwen3-embedding:4b` is pulled |
| Discovery agent can't browse | Run `docker compose --profile mcp up -d` to start `playwright-mcp` |
| GitHub MCP tools missing | Set `GITHUB_TOKEN` in `.env` and restart `docker compose up -d` |
| `/approvals` queue not draining | A Judge confidence < 0.90 item needs human approval in the UI |

See `example.env` for the full environment variable reference.
