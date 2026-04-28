# QAP — Quality Autopilot

**Agentic Compiler for the Software Testing Life Cycle (STLC).**

Quality Autopilot treats AI as a Senior SDET that reasons through requirements, writes Playwright automation, and self-heals broken tests.

> **Status:** Phases 0–4 complete ✅ | Phase 5 (Full Autonomy) 🔄 next

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running
- `.env` configured (copy from `example.env`)

```bash
cp example.env .env
# Edit .env — set OPENAI_API_KEY at minimum
docker compose up -d --build
curl http://localhost:8000/health
# → {"status":"ok","instantiated_at":"..."}
```

### Access

| Service | URL |
|---------|-----|
| AgentOS API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| PostgreSQL / PgVector | localhost:5432 |

---

## Architecture

```
QAP/
├── agents/          9 agents
│   ├── architect    semantic_search  → RequirementContext
│   ├── scribe       gherkin_formatter → GherkinSpec
│   ├── discovery    ui_crawler       → SiteManifesto
│   ├── librarian    vector_indexing  → PgVector KB
│   ├── engineer     file_writer      → GitHub PR
│   ├── data_agent   data_factory     → RunContext
│   ├── detective    trace_analyzer   → RCAReport
│   ├── medic        surgical_editor  → HealingPatch
│   └── judge        adversarial_review → JudgeVerdict
├── teams/           4 squads (all TeamMode.coordinate)
│   ├── strategy     Architect + Scribe
│   ├── context      Discovery + Librarian
│   ├── engineering  Engineer + Data Agent
│   └── operations   Detective + Medic
├── workflows/       3 pipelines
│   ├── spec_to_code          Requirement → Spec → Code → PR
│   ├── discovery_onboard     AUT → Site Manifesto → KB
│   └── triage_heal           Failure → RCA → Patch → Verify
├── contracts/       9 Pydantic hand-off models
├── automation/      BDD+POM TypeScript framework
│   ├── features/            Gherkin .feature files
│   ├── step_definitions/    Cucumber steps
│   ├── pages/               Playwright Page Object Models
│   ├── hooks/               Before/After hooks
│   └── fixtures/            Test data fixtures
├── db/              PostgreSQL + PgVector helpers
└── app/             AgentOS entry point + settings
```

---

## Agents

| Agent | ID | Primary Skill | Output |
|-------|----|--------------|--------|
| Architect | `architect` | `semantic_search` | `RequirementContext` |
| Scribe | `scribe` | `gherkin_formatter` | `GherkinSpec` |
| Discovery | `discovery` | `ui_crawler` | `SiteManifesto` |
| Librarian | `librarian` | `vector_indexing` | PgVector KB |
| Engineer | `engineer` | `file_writer` | GitHub PR |
| Data Agent | `data-agent` | `data_factory` | `RunContext` |
| Detective | `detective` | `trace_analyzer` | `RCAReport` |
| Medic | `medic` | `surgical_editor` | `HealingPatch` |
| Judge | `judge` | `adversarial_review` | `JudgeVerdict` |

---

## Judge Quality Gate

```
confidence ≥ 0.90  → AUTO-APPROVE  → pipeline continues
confidence < 0.90  → Human review  → hold for Human Lead
confidence < 0.50  → AUTO-REJECT   → back to producing agent
```

---

## Automation Framework

```bash
cd automation
npm install

npm test                   # all tests (headless)
npm run test:headed        # visible browser
```

Locator strategy: `data-testid` → `role` → `text`. No CSS/XPath. No `waitForTimeout`.

---

## Gated Roadmap

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

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | [Agno](https://docs.agno.com) (`agno[os]`) |
| Runtime | AgentOS (FastAPI) on port 8000 |
| Database | PostgreSQL 16 + PgVector |
| Model | OpenRouter via Kilo AI Gateway |
| Embeddings | OllamaEmbedder `qwen3-embedding:4b` |
| Test engine | Playwright + Cucumber (TypeScript) |
| Container | Docker Compose |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | Model API key |
| `DB_USER` | ✅ | PostgreSQL user (default: `ai`) |
| `DB_PASS` | ✅ | PostgreSQL password (default: `ai`) |
| `AUT_BASE_URL` | Optional | Application Under Test URL |
| `AUT_AUTH_USER` | Optional | AUT login username |
| `AUT_AUTH_PASS` | Optional | AUT login password |

See `example.env` for the full template.
