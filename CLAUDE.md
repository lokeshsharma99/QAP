# CLAUDE.md — Quality Autopilot

This file provides context for AI coding agents working on this repository.
For the full specification, read [AGENTS.md](./AGENTS.md) first.

---

## ⚡ CLAUDE CODE HANDOFF — Current Working State

> **Last updated:** Session ending commit `1604fb9` — June 2025
> **GitHub (`origin/main`):** ✅ Up to date at `1604fb9`
> **ADO backup branch:** `local-main-2025` at `1604fb9`

### What Is Running Right Now

All 7 Docker containers are up (after `docker compose up -d --build`):

| Container | Port | Status |
|-----------|------|--------|
| `qap-api` | 8000 | ✅ Running (uvicorn --reload) |
| `qap-ui` | 3000 | ✅ Running (Next.js 15 standalone) |
| `qap-db` | 5432 | ✅ Running (agnohq/pgvector:18) |
| `atlassian-mcp` | 8933 | ✅ Running (sooperset/mcp-atlassian) |
| `github-mcp` | 8080 | ✅ Running |
| `ado-mcp` | 8932 | ✅ Running (supergateway + @azure-devops/mcp) |
| `playwright-mcp` | 8931 | ✅ Running (custom Dockerfile.playwright-mcp) |

### Active Model: NVIDIA NIM

The API uses NVIDIA NIM (NOT OpenAI) when `MODEL_PROVIDER=nvidia` and `NVIDIA_API_KEY` are set in `.env`:

```python
# app/settings.py — current model selection
MODEL = OpenAIChat(
    id=NVIDIA_MODEL,                                          # qwen/qwen3-coder-480b-a35b-instruct
    api_key=NVIDIA_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)
```

**TTFT:** ~1–3s with NVIDIA vs ~33s with Kilo fallback. NVIDIA is active when `.env` has:
```
MODEL_PROVIDER=nvidia
NVIDIA_API_KEY=<your-key>
NVIDIA_MODEL=qwen/qwen3-coder-480b-a35b-instruct
```

---

## 📋 PHASE STATUS

```
Phase 0   → Docker + /health 200          ✅ DONE
Phase 0.5 → Site Manifesto in PgVector    ✅ DONE
Phase 1   → Codebase KB indexed           ✅ DONE
Phase 2   → Gherkin workflow live         ✅ DONE
Phase 3   → Spec → Code → Green          ✅ DONE
Phase 4   → Triage + Heal loop           ✅ DONE
Phase 5   → 95% autonomous / 30 days     🔄 NEXT
```

**DO NOT start Phase 5 work until Phase 4 gate is verified in `docs/CHECKLIST.md`.**

---

## 🔑 Critical .env Variables (DO NOT COMMIT)

The `.env` file is gitignored. Do not commit it. Key values for running the stack:

```env
MODEL_PROVIDER=nvidia
NVIDIA_API_KEY=<see Lokesh's key manager>
NVIDIA_MODEL=qwen/qwen3-coder-480b-a35b-instruct
NEXT_PUBLIC_AGENTOS_URL=http://192.168.1.243:8000   # or http://localhost:8000
APP_BASE_URL=http://192.168.1.243:3000
ATLASSIAN_URL=https://lokeshsharma2.atlassian.net
ATLASSIAN_EMAIL=kirtisharma0691@gmail.com
ATLASSIAN_API_TOKEN=<from Atlassian account settings>
AUT_BASE_URL=https://lokeshsharma99.github.io/GDS-Demo-App/
DB_USER=ai
DB_PASS=ai
DB_DATABASE=ai
```

---

## 🏗️ Architecture

## Project Overview

Quality Autopilot — An agentic compiler for the Software Testing Life Cycle (STLC).
Built on the Agno Framework (v2.6.3+). Uses LLM reasoning to design tests and Playwright for execution.

## Architecture

```
Quality Autopilot (app/main.py)
├── Agents (15+)
│   ├── Architect (agents/architect/)          # semantic_search → Execution Plan JSON
│   ├── Scribe (agents/scribe/)                # gherkin_formatter → .feature files
│   ├── Discovery (agents/discovery/)          # ui_crawler → Site Manifesto via Crawl4AI BFS
│   ├── Librarian (agents/librarian/)          # vector_indexing → Up-to-date Vector KB (Git-triggered)
│   ├── Engineer (agents/engineer/)            # file_writer → GitHub PR (Look-Before-You-Leap)
│   ├── Data Agent (agents/data_agent/)        # data_factory → run_context.json
│   ├── Detective (agents/detective/)          # trace_analyzer → RCA Report
│   ├── Medic (agents/medic/)                  # surgical_editor → Healing Patch PR
│   ├── Judge (agents/judge/)                  # adversarial_review → JudgeVerdict (Quality Gate)
│   ├── Healing Judge (agents/healing_judge/)  # validates Medic patches before apply
│   ├── CI Log Analyzer (agents/ci_log_analyzer/) # Azure DevOps pipeline log RCA
│   ├── Concierge (agents/concierge/)          # front-door routing agent
│   ├── Scout (agents/scout/)                  # project indexer / codebase watcher
│   ├── Curator (agents/curator/)              # KB pruning and obsolescence detection
│   ├── Impact Analyst (agents/impact_analyst/) # change impact across POMs/StepDefs
│   └── Pipeline Analyst (agents/pipeline_analyst/) # CI/CD trend analysis
├── Teams (6 Squads)
│   ├── Strategy (teams/strategy/)             # Architect + Scribe (coordinate)
│   ├── Context (teams/context/)               # Discovery + Librarian (coordinate)
│   ├── Engineering (teams/engineering/)        # Engineer + Data Agent (coordinate)
│   ├── Operations (teams/operations/)         # Detective + Medic (coordinate)
│   ├── Diagnostics (teams/diagnostics/)       # CI Log Analyzer + Detective
│   └── Grooming (teams/grooming/)             # Architect + Scribe + Impact Analyst
├── Workflows (many)
│   ├── Spec to Code (workflows/spec_to_code/) # Requirement → Spec → Code → PR
│   ├── Discovery (workflows/discovery_onboard/)# AUT → Site Manifesto → KB
│   ├── Triage Heal (workflows/triage_heal/)   # Failure → RCA → Patch → Verify
│   ├── Full Lifecycle (workflows/full_lifecycle/) # end-to-end
│   ├── Automation Scaffold (workflows/automation_scaffold/) # BDD+POM framework bootstrap
│   └── Full Regression (workflows/full_regression/) # regression suite orchestration
└── Contracts (14 Pydantic models in contracts/)
    ├── RequirementContext, GherkinSpec, SiteManifesto, RunContext
    ├── ExecutionResult, RCAReport, HealingPatch, JudgeVerdict
    ├── AutomationScaffold, ImpactReport, GroomingAssessment
    └── PipelineRCAReport, WorkflowInputs, WorkflowStatus

Control Plane (control-plane/)  ← Next.js 15 App Router + TypeScript
├── src/store.ts                # Zustand: selectedEndpoint, authToken, agents, sessions
├── src/api/routes.ts           # Centralized API URL builders
├── src/components/chat/ChatPage.tsx  # Main chat UI + HITL ApprovalBlock
├── src/hooks/useAIStreamHandler.tsx  # SSE event dispatcher
└── src/hooks/useAIResponseStream.tsx # SSE buffer parser

Automation Framework (automation/)
├── features/                   # BDD feature files (.feature)
├── step_definitions/           # Cucumber step implementations (.ts)
├── pages/                      # Playwright Page Object Models (.ts)
├── hooks/                      # Test lifecycle hooks (.ts)
├── fixtures/                   # Test data fixtures (.ts)
├── config/                     # AUT-specific configuration
├── cucumber.conf.js            # Cucumber config (CJS — NOT .ts, this matters)
├── playwright.config.ts        # Playwright browser config
└── tsconfig.json               # TypeScript configuration
```

## Responsibility Handoff (Canonical Flow)

```
BA moves ticket → Architect → Scribe → Gherkin Judge (≥90% auto, <90% Human)
→ Data Agent → Engineer (Look-Before-You-Leap) → Code Judge (≥90% auto, <90% Human)
→ Local Green → PR submitted
CI/CD fail → Detective → Medic → Healing Judge → 3x verify → auto/Human
```

All agents share:
- PostgreSQL 16+ with PgVector for persistence (`agnohq/pgvector:18`)
- NVIDIA NIM model (`qwen/qwen3-coder-480b-a35b-instruct`) via `app/settings.py`
- SSE streaming (`stream=True, stream_events=True`) — never batch responses
- Chat history and session state management

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | AgentOS entry point, registers all agents/teams/workflows |
| `app/settings.py` | Shared MODEL (NVIDIA NIM), agent_db, AUT config |
| `db/session.py` | `get_postgres_db()` and `create_knowledge()` helpers |
| `db/url.py` | Builds database URL from environment |
| `contracts/` | Pydantic models for all agent hand-off protocols |
| `compose.yaml` | Docker Compose — 7 services |
| `control-plane/Dockerfile` | Multi-stage Next.js build; ARG NEXT_PUBLIC_AGENTOS_URL baked here |
| `control-plane/src/store.ts` | Zustand store: `selectedEndpoint`, `authToken`, `ChatEvent` type |
| `control-plane/src/components/chat/ChatPage.tsx` | Full chat UI + ApprovalBlock HITL component |
| `control-plane/src/hooks/useAIStreamHandler.tsx` | SSE event dispatcher; flushSync on RunCompleted |
| `control-plane/src/hooks/useAIResponseStream.tsx` | SSE buffer parser (brace-matching) |

## SSE Streaming Architecture

Backend emits `event: X\ndata: {...}\n\n` format. The front-end pipeline:

```
fetch() SSE stream
→ useAIResponseStream.tsx (buffer parser, brace-matching JSON extraction)
→ useAIStreamHandler.tsx (event dispatcher → React state)
→ ChatPage.tsx (renders ThinkingBubble, MessageBubble, ApprovalBlock)
```

**Critical:** Use `flushSync(() => setState(...))` on `RunCompleted` and `StepCompleted` to force immediate React render.

## HITL (Human-in-the-Loop) Flow

1. Backend pauses run → emits `RunPaused` SSE event
2. `useAIStreamHandler` sets `isPaused=true`
3. `ApprovalBlock` component renders (inline in ChatPage below last message)
4. Fetches `GET /approvals?run_id=...&status=pending`
5. User clicks Approve/Reject → `POST /approvals/{id}/resolve`
6. Backend resumes → emits `RunContinued` → `isPaused=false`

## Control Plane UI Pages

| Route | Purpose |
|-------|---------|
| `/chat` | Main multi-agent chat (streaming, HITL, markdown, Mermaid) |
| `/sessions` | View / resume past agent sessions |
| `/memory` | Browse, search, delete agent memories |
| `/knowledge` | Browse PgVector knowledge base documents |
| `/traces` | Execution trace viewer with DSL search |
| `/evals` | Run accuracy / performance / reliability evals |
| `/approvals` | HITL approval queue (Judge-flagged artifacts) |
| `/registry` | Browse registered agents, teams, workflows |
| `/automation` | Automation health dashboard |
| `/rtm` | Requirements Traceability Matrix |
| `/scheduler` | Schedule recurring agent runs |
| `/settings` | API endpoint, auth token, theme |

## Development Setup

```bash
# Start all services
docker compose up -d --build

# Check all 7 containers are up
docker ps

# Watch API logs
docker logs qap-api -f

# Watch UI logs
docker logs qap-ui -f

# Local Python development (no Docker)
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

# Run all tests
npm test

# Run tests with visible browser
npm run test:headed

# Run specific feature (CJS config, NOT .ts)
npx cucumber-js features/login.feature
```

**Important:** Cucumber config is `cucumber.conf.js` (CommonJS). The `.ts` version is legacy — do not use it. The `require` in scripts must point to `cucumber.conf.js`.

## Git Remotes

```
origin  → https://github.com/lokeshsharma99/QAP.git   (primary)
ado     → https://dev.azure.com/vibecode/QAP/_git/QAP  (ADO backup)
```

ADO `main` branch has Azure Container Apps deployment work (separate history, ~55 commits ahead).
Local `main` = GitHub `origin/main` = canonical working branch.
ADO `local-main-2025` branch = copy of current local state pushed as backup.

## Conventions

See [AGENTS.md](./AGENTS.md) for the full specification including:
- Parameter ordering (Agent, Team, Workflow) — mandatory, never reorder
- Section header format (`# ---` 75-char separators)
- Import conventions (absolute imports only)
- File structure requirements (one directory per agent)
- Anti-patterns to avoid

## TypeScript Conventions (Control Plane)

- Import hooks directly: `import { useState, useEffect } from 'react'` — **NOT** `React.useState`
- Never use `React.FC` — use inline prop types: `const Foo = ({ bar }: { bar: string }) => ...`
- Framer Motion `ease`: use named strings (`'easeOut'`, `'linear'`) — NOT bezier arrays
- All page components wrap root in `<motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}>`
- Agent dropdown response: always handle `Array.isArray(d) ? d : d?.agents ?? d?.data ?? []`
- Always send `Authorization: Bearer ${authToken}` header on API calls

## Gated Roadmap

```
Phase 0   → Docker + /health 200          ✅ DONE
Phase 0.5 → Site Manifesto in PgVector    ✅ DONE
Phase 1   → Codebase KB indexed           ✅ DONE
Phase 2   → Gherkin workflow live         ✅ DONE
Phase 3   → Spec → Code → Green          ✅ DONE
Phase 4   → Triage + Heal loop           ✅ DONE
Phase 5   → 95% autonomous / 30 days     🔄 NEXT
```

Every phase has a gate. Do not proceed until the gate passes.
See `docs/CHECKLIST.md` and Section XII of `AGENTS.md` for details.

## Environment Variables

Required for NVIDIA NIM model (`.env`, DO NOT COMMIT):
- `MODEL_PROVIDER=nvidia`
- `NVIDIA_API_KEY=<key>`
- `NVIDIA_MODEL=qwen/qwen3-coder-480b-a35b-instruct`

Database:
- `DB_USER=ai`, `DB_PASS=ai`, `DB_HOST=localhost`, `DB_PORT=5432`, `DB_DATABASE=ai`

AUT (Application Under Test):
- `AUT_BASE_URL=https://lokeshsharma99.github.io/GDS-Demo-App/`
- `AUT_AUTH_USER=`, `AUT_AUTH_PASS=`

Integrations:
- `ATLASSIAN_URL=https://lokeshsharma2.atlassian.net`
- `ATLASSIAN_EMAIL=kirtisharma0691@gmail.com`
- `ATLASSIAN_API_TOKEN=<from Atlassian settings>`

UI:
- `NEXT_PUBLIC_AGENTOS_URL=http://192.168.1.243:8000`  ← baked at Docker build time via ARG in control-plane/Dockerfile
- `APP_BASE_URL=http://192.168.1.243:3000`

## Ports

- qap-api: 8000
- qap-ui (Control Plane): 3000
- qap-db (PostgreSQL+PgVector): 5432
- playwright-mcp: 8931
- ado-mcp: 8932
- atlassian-mcp: 8933
- github-mcp: 8080

## Known Issues / Gotchas

1. **NVIDIA NIM fallback**: If `MODEL_PROVIDER` is not `nvidia` or `NVIDIA_API_KEY` is missing, it falls back to Kilo (slow, ~33s TTFT). Always check `.env` first.

2. **Dockerfile ARG order matters**: In `control-plane/Dockerfile`, the `ARG NEXT_PUBLIC_AGENTOS_URL` declaration must appear BEFORE the `ENV` assignment and `RUN pnpm build`. Otherwise Next.js never sees the value.

3. **API restart drops SSE**: If `qap-api` restarts while a chat stream is active, the browser fetch will throw `TypeError: network error`. The UI catches this and shows an error message. Restart is caused by Python file changes (uvicorn --reload).

4. **Atlassian MCP**: Uses `sooperset/mcp-atlassian` on port 8933. `app/atlassian_mcp.py` does a TCP probe; if it succeeds it uses HTTP transport, otherwise falls back to stdio. 72 tools registered total.

5. **cucumber.conf.js not .ts**: Use CommonJS config (`cucumber.conf.js`). The TypeScript config was removed to fix `loadFile` errors.

6. **tiktoken + tokenizers**: Both required to suppress Agno token counting warnings. Added to `requirements.txt` and `pyproject.toml`.

7. **ADO remote diverged**: `ado/main` has Azure Container Apps deployment work (~55 extra commits). `ado/local-main-2025` = backup of current local state. Do NOT `git merge ado/main` without a careful conflict resolution plan.

## Absolute Prohibitions (Never Do These)

| NEVER | DO INSTEAD |
|-------|-----------|
| `import from 'langchain...'` or `from crewai...` | `from agno.*` only |
| `time.sleep()` in tests | Playwright auto-waiting |
| Hardcoded secrets in code | `os.getenv(...)` / environment variables |
| CSS or XPath locators | `data-testid`, `role`, or `text` strategies |
| One mega-file with all agents | One directory per agent |
| Skip Pydantic contracts between agents | Define in `contracts/`, use everywhere |
| `React.useState` / `React.useEffect` | Import `{ useState, useEffect }` from 'react' |
| `React.FC` type annotation | Inline prop types |
| `ease: [0.4, 0, 0.2, 1]` in framer-motion v12 | `ease: 'easeOut'` |
| Working on Phase N+1 before Phase N gate | Check `docs/CHECKLIST.md` |
| Commit `.env` | It's gitignored — keep it local only |

## Ports

- API: 8000
- Database: 5432
- Agent UI: 3000
- Playwright MCP: 8931
