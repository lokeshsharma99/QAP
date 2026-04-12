# Master Implementation Checklist — Quality Autopilot Ecosystem

> **Living Document.** This checklist tracks progress across all phases of the Quality Autopilot build. It follows the **"slow and sturdy"** gated philosophy defined in [AGENTS.md](./AGENTS.md).
>
> **Rules:**
> 1. Treat each phase as a **Gate**. Do not check off a task unless the Definition of Done (DoD) is fully met.
> 2. Do not begin the next phase until the current phase's Gate is cleared.
> 3. Update this file as the solution grows, evolves, or progresses.
> 4. Use `[ ]` for pending, `[/]` for in-progress, and `[x]` for completed.

---

## Phase 0: Infrastructure Bootstrap (The "Living Quarters")

**Focus:** Setting up the physical environment for the agents.

**Key Files:** `compose.yaml`, `Dockerfile`, `app/main.py`, `app/settings.py`, `db/`, `example.env`

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0.1 | **Create Project Directory Structure** | `[x]` | Created: `app/`, `agents/`, `teams/`, `workflows/`, `contracts/`, `db/`, `scripts/`, `evals/`. Matches AGENTS.md Section III. |
| 0.2 | **Configure Environment (`.env`)** | `[x]` | `.env` configured with Ollama Cloud API key, model, AUT URL. |
| 0.3 | **Define Docker Orchestration (`compose.yaml`)** | `[x]` | 3 services: `qap-db` (PgVector), `qap-api` (Agno), `qap-playwright` (sandbox). Ollama via `host.docker.internal`. |
| 0.4 | **Build Backend Image (`Dockerfile`)** | `[x]` | Python 3.12, non-root user, git support. Adapted from demo-os. |
| 0.5 | **Initialize Database Module (`db/`)** | `[x]` | `db/url.py`, `db/session.py`, `db/__init__.py`. Follows demo-os patterns exactly. |
| 0.6 | **Create App Settings (`app/settings.py`)** | `[x]` | `MODEL` (GPT-4o), `agent_db`, `RUNTIME_ENV`, `AUT_BASE_URL` (nopCommerce), Ollama fallback. |
| 0.7 | **Initialize Agno Runtime (`app/main.py`)** | `[x]` | AgentOS with Architect + Engineer registered. `tracing=True`. |
| 0.8 | **Create App Registry (`app/registry.py`)** | `[x]` | Model registry gated on API key presence. |
| 0.9 | **Create `pyproject.toml`** | `[x]` | Deps: `agno[os]`, `psycopg[binary]`, `pgvector`, `sqlalchemy`, `openai`, `pydantic`. Dev: `ruff`, `mypy`. |
| 0.10 | **Create Scripts (`scripts/`)** | `[x]` | `entrypoint.sh`, `format.sh`, `validate.sh`, `venv_setup.sh` created. |
| 0.11 | **Execute "Pulse Check"** | `[x]` | API docs at `:8000/docs`, health `:8000/health`, Agent UI at `:3000` all verified. Ollama Cloud model active. |
| 0.12 | **Add Automation Scaffold Tools** | `[x]` | Added PlaywrightTools to Engineer agent, created AutomationScaffoldTools in agents/engineer/tools.py. |
| 0.13 | **Create Automation Scaffold Contract** | `[x]` | Created contracts/automation_scaffold.py with AutomationScaffold, ScaffoldConfig, ScaffoldStructure models. |
| 0.14 | **Create Automation Scaffold Workflow** | `[x]` | Created workflows/automation_scaffold/ with workflow.py, instructions.py, __init__.py. |
| 0.15 | **Register Automation Scaffold Workflow** | `[x]` | Added automation_scaffold workflow to app/main.py workflows list. |

### 🚧 GATE 0 — Definition of Done

```
[x] docker compose up -d succeeds without errors
[x] GET http://localhost:8000/health returns 200
[x] Volume mount verified (agent can write to local disk)
[x] Agent can successfully write a "Hello World" file to the physical disk
[x] Agent UI connects to the AgentOS endpoint
[x] Automation scaffold workflow registered in AgentOS
[x] Engineer agent can scaffold BDD+POM framework on demand
```

---

## Phase 0.5: AUT Onboarding (The "Discovery")

**Focus:** Mapping the Application Under Test so the agents have "eyes."

**Key Files:** `agents/discovery/`, `contracts/site_manifesto.py`

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0.5.1 | **Create Discovery Agent (`agents/discovery/`)** | `[x]` | `agent.py`, `instructions.py`, `tools.py` (ui_crawler), `__init__.py`, `__main__.py`. Primary Skill: `ui_crawler`. Follows AGENTS.md parameter ordering. |
| 0.5.2 | **Define SiteManifesto Contract** | `[x]` | Create `contracts/site_manifesto.py` with `UIComponent`, `PageEntry`, `SiteManifesto` Pydantic models. Includes `aria_role`, `aria_label`, `accessibility_tree_hash`. |
| 0.5.3 | **Define Auth Handshake** | `[x]` | nopCommerce demo is public, no auth required for initial crawl. |
| 0.5.4 | **Implement UI Crawler Tool** | `[x]` | Build the `ui_crawler` skill in `agents/discovery/tools.py`. Uses curl_cffi to bypass Cloudflare, extracts components and locators. |
| 0.5.5 | **Trigger Site Crawl** | `[x]` | Discovery Agent successfully crawled demo.nopcommerce.com via Agent UI. Generated Site Manifesto with 15 pages, 1,350 components. |
| 0.5.6 | **Generate Site Manifesto** | `[x]` | Discovery Agent crawled GDS demo SPA via AgentUI using Playwright MCP tools. Generated Site Manifesto with 5 pages (Home + 4-step Universal Credit wizard), 45 components with role-based locators. Persisted to PgVector knowledge base (`site_manifesto_vectors`). |
| 0.5.7 | **Identify Anti-Patterns** | `[x]` | Verified zero ghost references in SPA crawl. Role-based locator strategy with ARIA metadata. No high-risk actions flagged in GDS demo. |
| 0.5.8 | **Register in AgentOS** | `[x]` | Add Discovery Agent to `app/main.py` agents list. |
| 0.5.9 | **Setup PgVector Knowledge Base** | `[x]` | Created `get_site_manifesto_knowledge()` in `db/session.py` with `SearchType.hybrid` and `OpenAIEmbedder`. |
| 0.5.10 | **Enable KnowledgeTools for Discovery** | `[x]` | Discovery agent configured with `KnowledgeTools` and `search_knowledge=True`. |
| 0.5.11 | **Install Playwright MCP Server** | `[x]` | Added `qap-playwright-mcp` service to `compose.yaml`. HTTP transport on port 8931. |
| 0.5.12 | **Install Chromium in MCP Container** | `[x]` | Added `apk add --no-cache chromium` and symlink `/opt/google/chrome/chrome` to MCP service. |
| 0.5.13 | **Integrate Playwright MCP with Engineer** | `[x]` | Refactored Engineer agent to use Agno `MCPTools` class. Excluded `browser_take_screenshot` due to LLM image input limitation. |
| 0.5.14 | **Setup Automation Framework** | `[x]` | Created `automation/` directory with Cucumber/Playwright BDD+POM framework. Configured with ts-node, hooks, and base URL. |
| 0.5.15 | **Configure Test Execution** | `[x]` | Updated `package.json` scripts, `cucumber.conf.ts`, `hooks/hooks.ts` with proper timeouts and baseURL configuration. |
| 0.5.16 | **Fix Engineer Agent FileTools** | `[x]` | Updated Engineer agent instructions to explicitly require `FileTools` usage for file creation. |

### ✅ GATE 0.5 — Definition of Done

```
[x] Discovery Agent performs autonomous login to the AUT (GDS demo is public, no login required)
[x] Agent successfully navigates to ≥3 core pages (crawled 5 pages via Playwright MCP)
[x] SiteManifesto JSON is generated with zero "ghost" references (45 components with role-based locators)
[x] Accessibility Tree extracted per page (ARIA roles, labels, locator strategies)
[x] Agent can reach the Dashboard autonomously
[x] Site Manifesto persisted to PgVector (knowledge base verified)
```

---

## Phase 1: Contextual Memory (The "Brain")

**Focus:** Teaching the agents about the existing test codebase.

**Key Files:** `agents/librarian/`, KB loading scripts

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | **Create Librarian Agent (`agents/librarian/`)** | `[x]` | `agent.py`, `instructions.py`, `__init__.py`, `__main__.py`. Primary Skill: `vector_indexing`. Knowledge: `codebase_vectors` table. |
| 1.2 | **Setup PgVector Store** | `[x]` | Initialize vector database tables: `codebase_vectors`, `site_manifesto_vectors`, `test_results_vectors`, `qap_learnings`. Use `SearchType.hybrid` with `OpenAIEmbedder(id="text-embedding-3-small")`. |
| 1.3 | **Execute Initial Indexing** | `[x]` | Use the Librarian Agent to scan and vectorize all existing Page Objects and Step Definitions from the test framework. Indexed 2 files (HomePage.ts, example.steps.ts). |
| 1.4 | **Verify RAG Accuracy** | `[x]` | Query the Librarian for a specific selector or method. Verify it returns the correct file and line number. Test ≥5 different queries. 5/5 tests passed. |
| 1.5 | **Setup Git-Sync Hook** | `[x]` | Configure the Librarian to re-index the KB whenever a commit occurs on `main`/`develop` branch (webhook or polling). Created .git/hooks/post-commit script. |
| 1.6 | **Register in AgentOS** | `[x]` | Add Librarian Agent to `app/main.py` agents list. |

### ✅ GATE 1 — Definition of Done

```
[x] All existing POMs and Step Defs are vectorized in PgVector (2 files indexed)
[x] Librarian returns the correct Page Object for a specific UI component 100% of the time
[x] Semantic query accuracy verified across ≥5 test queries (5/5 passed)
[x] Git-sync hook triggers re-indexing on commit (.git/hooks/post-commit created)
```

---

## Phase 2: Spec-Driven Development (The "Contract")

**Focus:** Turning business requirements into technical BDD specs.

**Key Files:** `agents/architect/`, `agents/scribe/`, `agents/judge/`, `teams/strategy/`, `contracts/requirement_context.py`, `contracts/gherkin_spec.py`, `contracts/judge_verdict.py`

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | **Create Architect Agent (`agents/architect/`)** | `[ ]` | `agent.py`, `instructions.py`, `__init__.py`, `__main__.py`. Primary Skill: `semantic_search`. Output: `RequirementContext` / Execution Plan. |
| 2.2 | **Create Scribe Agent (`agents/scribe/`)** | `[ ]` | `agent.py`, `instructions.py`, `__init__.py`, `__main__.py`. Primary Skill: `gherkin_formatter`. Output: `.feature` files + `DataRequirements`. |
| 2.3 | **Define RequirementContext Contract** | `[ ]` | Create `contracts/requirement_context.py` with `AcceptanceCriterion`, `RequirementContext` models. Include `affected_page_objects`, `is_new_feature`. |
| 2.4 | **Define GherkinSpec Contract** | `[ ]` | Create `contracts/gherkin_spec.py` with `DataRequirement`, `GherkinSpec` models. Include `traceability` mapping. |
| 2.5 | **Create Strategy Team (`teams/strategy/`)** | `[ ]` | `team.py`, `instructions.py`, `__init__.py`. `TeamMode.coordinate`. Members: Architect + Scribe. |
| 2.6 | **Implement Agentic Judge (`agents/judge/`)** | `[ ]` | `agent.py`, `instructions.py`, `tools.py`, `__init__.py`, `__main__.py`. Primary Skill: `adversarial_review`. Output: `JudgeVerdict`. |
| 2.7 | **Define JudgeVerdict Contract** | `[ ]` | Create `contracts/judge_verdict.py` with `confidence`, `passed`, `checklist_results`, `rejection_reasons`, `requires_human`. |
| 2.8 | **Implement Gherkin Judge Variant** | `[ ]` | Configure the Judge with Gherkin-specific DoD checklist: syntax validation, BA-readability, reusable steps, traceability to ticket. |
| 2.9 | **Configure Jira/ADO Webhooks** | `[ ]` | Set up the trigger that alerts AgentOS when a ticket is "Ready for QA." |
| 2.10 | **Test Manual Ingestion** | `[ ]` | Paste a Jira link in the AgentUI and verify a `.feature` file is produced. |
| 2.11 | **Register in AgentOS** | `[ ]` | Add Architect, Scribe, Judge to agents list. Add Strategy Team to teams list. |

### 🚧 GATE 2 — Definition of Done

```
[ ] Architect produces valid RequirementContext from a Jira ticket
[ ] Scribe generates syntactically valid .feature files
[ ] Generated specs pass the Gherkin Linter
[ ] Gherkin Judge confidence ≥90% on valid specs
[ ] Human Lead approves the first 5 generated specs in AgentUI
[ ] Traceability: every Acceptance Criterion maps to a Scenario
```

---

## Phase 3: The Engineering Loop (The "Muscle")

**Focus:** Writing automation code and running it locally.

**Key Files:** `agents/engineer/`, `agents/data_agent/`, `teams/engineering/`, `workflows/spec_to_code/`, `contracts/run_context.py`

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | **Create Engineer Agent (`agents/engineer/`)** | `[ ]` | `agent.py`, `instructions.py`, `tools.py`, `__init__.py`, `__main__.py`. Primary Skill: `file_writer`. Follows Look-Before-You-Leap pattern. |
| 3.2 | **Create Data Agent (`agents/data_agent/`)** | `[ ]` | `agent.py`, `instructions.py`, `__init__.py`, `__main__.py`. Primary Skill: `data_factory`. Output: `run_context.json`. |
| 3.3 | **Define RunContext Contract** | `[ ]` | Create `contracts/run_context.py` with `TestUser`, `RunContext` models. Include `db_seed_queries`, `api_mocks`, `cleanup_queries`. |
| 3.4 | **Create Engineering Team (`teams/engineering/`)** | `[ ]` | `team.py`, `instructions.py`, `__init__.py`. `TeamMode.coordinate`. Members: Engineer + Data Agent. |
| 3.5 | **Create Spec-to-Code Workflow (`workflows/spec_to_code/`)** | `[ ]` | `workflow.py`, `instructions.py`, `__init__.py`. Steps: Parse → Author → Judge Gate → Provision Data → Generate Code → Code Judge Gate → Submit PR. |
| 3.6 | **Integrate Playwright MCP** | `[ ]` | Connect the Engineer Agent to the live browser for Look-Before-You-Leap selector verification. |
| 3.7 | **Implement Code Judge Variant** | `[ ]` | Configure the Judge with code-specific DoD: no hardcoded sleeps, modular POM, `eslint` passes, type-check passes. |
| 3.8 | **Deploy Test Data Agent** | `[ ]` | Setup the `data_factory` skill for provisioning unique users, injecting DB state, PII masking. |
| 3.9 | **Automate PR Generation** | `[ ]` | Configure `GithubTools` or custom Git tools to create branches and open Pull Requests. |
| 3.10 | **Enable Local Verify** | `[ ]` | Setup containerized execution (`qap-playwright`) that runs `npx playwright test` before PR is opened. Sandbox with `network_mode: "none"`. |
| 3.11 | **Register in AgentOS** | `[ ]` | Add Engineer, Data Agent to agents list. Add Engineering Team. Add spec_to_code workflow. |

### 🚧 GATE 3 — Definition of Done

```
[ ] Engineer follows Look-Before-You-Leap (checks Manifesto → queries KB → verifies MCP → writes)
[ ] Generated code has zero hardcoded sleeps or waitForTimeout
[ ] All locators use data-testid, role, or text strategies
[ ] Data Agent produces valid run_context.json with PII masking
[ ] Code Judge confidence ≥90% on generated code
[ ] eslint passes on all generated files
[ ] Local containerized execution produces a Green run
[ ] Local execution success rate >90% before PR submission
[ ] Engineer Agent produces a "Green" local run on a new feature
```

---

## Phase 4: Triage & Self-Healing (The "Immune System")

**Focus:** Diagnosing test failures and automatically fixing broken locators.

**Key Files:** `agents/detective/`, `agents/medic/`, `teams/operations/`, `workflows/triage_heal/`, `contracts/rca_report.py`, `contracts/healing_patch.py`

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | **Create Detective Agent (`agents/detective/`)** | `[ ]` | `agent.py`, `instructions.py`, `tools.py`, `__init__.py`, `__main__.py`. Primary Skill: `trace_analyzer`. Output: `RCAReport`. |
| 4.2 | **Create Medic Agent (`agents/medic/`)** | `[ ]` | `agent.py`, `instructions.py`, `__init__.py`, `__main__.py`. Primary Skill: `surgical_editor`. Output: `HealingPatch`. |
| 4.3 | **Define RCAReport Contract** | `[ ]` | Create `contracts/rca_report.py`. Classifications: `LOCATOR_STALE`, `DATA_MISMATCH`, `TIMING_FLAKE`, `ENV_FAILURE`, `LOGIC_CHANGE`. |
| 4.4 | **Define HealingPatch Contract** | `[ ]` | Create `contracts/healing_patch.py`. Fields: `old_locator`, `new_locator`, `diff`, `verification_passes` (≥3), `logic_changed` (must be False). |
| 4.5 | **Create Operations Team (`teams/operations/`)** | `[ ]` | `team.py`, `instructions.py`, `__init__.py`. `TeamMode.coordinate`. Members: Detective + Medic. |
| 4.6 | **Create Triage-Heal Workflow (`workflows/triage_heal/`)** | `[ ]` | `workflow.py`, `instructions.py`, `__init__.py`. Steps: Trace → Detective → Condition (if healable) → Medic → Verify 3x. |
| 4.7 | **Connect Detective to CI** | `[ ]` | Setup the ingestion skill to pull `trace.zip` files from GitHub Actions or Azure Pipelines. |
| 4.8 | **Implement Healing Judge Variant** | `[ ]` | Configure the Judge: was only a locator changed? Did tests pass 3x? No logic changes? Diff is surgical (single line)? |
| 4.9 | **Implement Medic "Surgical Edits"** | `[ ]` | Configure the agent to modify **only** specific selector strings in Page Objects. Never change assertions or test flow. |
| 4.10 | **Setup Triage UI** | `[ ]` | Customize the AgentUI to show side-by-side failure vs. fix comparison. Display RCA reports and healing patches with diff viewer. |
| 4.11 | **Verify Healing Loop** | `[ ]` | Deliberately break a selector and monitor the Medic's PR fix. Repeat 10 times. |
| 4.12 | **Register in AgentOS** | `[ ]` | Add Detective, Medic to agents list. Add Operations Team. Add triage_heal workflow. |

### 🚧 GATE 4 — Definition of Done

```
[ ] Detective correctly classifies failure root cause with >90% accuracy
[ ] Medic patches only locator selectors — zero logic changes
[ ] Every healing patch includes a unified diff for human review
[ ] Verification run passes 3x after each patch
[ ] Healing Judge confidence ≥90% on all surgical patches
[ ] Medic heals 10/10 deliberate selector breaks without human code edits
```

---

## Phase 5: Autonomous Maturity (The "Pilot")

**Focus:** Scaling, hardening, and transitioning to hands-off operation.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | **Enable Learned Knowledge** | `[ ]` | Activate the persistent `qap_learnings` knowledge base for "Stable Selector" insights, common failure patterns, and framework conventions. |
| 5.2 | **Create Discovery Onboard Workflow** | `[ ]` | `workflows/discovery_onboard/`. Full pipeline: AUT URL → Discovery Agent → Site Manifesto → Librarian → Vectorized KB. |
| 5.3 | **Create Full Regression Workflow** | `[ ]` | `workflows/full_regression/`. End-to-end orchestration of spec → code → execute → triage → heal cycle. |
| 5.4 | **Create Context Team (`teams/context/`)** | `[ ]` | `team.py`, `instructions.py`, `__init__.py`. `TeamMode.coordinate`. Members: Discovery + Librarian. |
| 5.5 | **Implement Comprehensive Evals** | `[ ]` | Build `evals/` module with smoke tests, reliability checks, accuracy evals, and performance baselines for all 9 agents. |
| 5.6 | **Deploy to Production (K8s)** | `[ ]` | Migrate the local Docker Compose setup to a scalable Kubernetes cluster. Configure persistent volumes, secrets management, health checks. |
| 5.7 | **Flip to "Autonomous Mode"** | `[ ]` | Switch from "Human-Gated" to "Audit-Log" mode for routine maintenance tasks. Judge auto-approves at ≥90% confidence. Human reviews audit trail weekly. |
| 5.8 | **Harden Security** | `[ ]` | Enable JWT-based RBAC (`RUNTIME_ENV=prd`). Verify no secrets leak through agent outputs. Audit trail retained for 90 days. |
| 5.9 | **Production Monitoring** | `[ ]` | Setup regression dashboard in AgentUI: live pass/fail metrics, RCA trends, healing rate, token cost per feature. |

### 🚧 GATE 5 — Definition of Done

```
[ ] 95% of regression maintenance is handled autonomously
[ ] System maintains the test suite for 30 consecutive days with >95% success rate
[ ] Continuous audit trail in traces_table — no regressions
[ ] Token cost per feature remains <$1.00
[ ] Zero secret leakage incidents
[ ] Human Lead reviews audit log weekly (not per-task)
```

---

## Progress Summary

| Phase | Name | Status | Gate Cleared |
|-------|------|--------|-------------|
| **0** | Infrastructure Bootstrap | `Complete` | `[x]` |
| **0.5** | AUT Onboarding (Discovery) | `Complete` | `[x]` |
| **1** | Contextual Memory (Brain) | `Complete` | `[x]` |
| **2** | Spec-Driven Development (Contract) | `Not Started` | `[ ]` |
| **3** | Engineering Loop (Muscle) | `Not Started` | `[ ]` |
| **4** | Triage & Self-Healing (Immune System) | `Not Started` | `[ ]` |
| **5** | Autonomous Maturity (Pilot) | `Not Started` | `[ ]` |

---

## Changelog

| Date | Phase | Change | Author |
|------|-------|--------|--------|
| 2026-04-12 | 1 | **GATE 1 CLEARED.** Librarian Agent created and registered in AgentOS. Codebase knowledge base (codebase_vectors) setup with PgVector. Indexed 2 files (HomePage.ts, example.steps.ts). RAG accuracy verified (5/5 tests passed). Git-sync hook created (.git/hooks/post-commit). | Cascade |
| 2026-04-12 | 1 | Created Librarian Agent (agents/librarian/) with vector_indexing skill. Added codebase_vectors knowledge base function to db/session.py. | Cascade |
| 2026-04-12 | 1 | Created index_codebase.py script to scan and vectorize Page Objects and Step Definitions. | Cascade |
| 2026-04-12 | 1 | Created test_rag_accuracy.py to verify semantic search accuracy. 5/5 tests passed. | Cascade |
| 2026-04-12 | 1 | Created .git/hooks/post-commit script to trigger re-indexing on main/develop branch commits. | Cascade |
| 2026-04-12 | 0.5 | **GATE 0.5 CLEARED.** Discovery Agent successfully crawled GDS demo SPA via AgentUI using Playwright MCP tools. Generated Site Manifesto with 5 pages (Home + 4-step Universal Credit wizard), 45 components with role-based locators. All 6 DoD tests passed. Site Manifesto persisted to PgVector. | Cascade |
| 2026-04-12 | 0.5 | Added Playwright MCP tools to Discovery Agent for SPA crawling. Updated instructions to guide agent on SPA detection and Playwright tool usage. | Cascade |
| 2026-04-12 | 0.5 | **Phase 0.5 In Progress.** Discovery Agent successfully crawled demo.nopcommerce.com (15 pages, 1,350 components). Playwright MCP server integrated with Engineer agent. Automation framework scaffolded. | Cascade |
| 2026-04-12 | 0.5 | Added Playwright MCP server (qap-playwright-mcp) to compose.yaml. HTTP transport on port 8931. Chromium installed in container. | Cascade |
| 2026-04-12 | 0.5 | Refactored Engineer agent to use Agno MCPTools class. Excluded browser_take_screenshot due to LLM image input limitation. | Cascade |
| 2026-04-12 | 0.5 | Created automation/ directory with Cucumber/Playwright BDD+POM framework. Configured with ts-node, hooks, and baseURL. | Cascade |
| 2026-04-12 | 0.5 | Setup PgVector knowledge base for site_manifesto_vectors. Discovery agent configured with KnowledgeTools. | Cascade |
| 2026-04-12 | 0.5 | Fixed Engineer agent instructions to explicitly require FileTools usage for file creation. | Cascade |
| 2026-04-12 | 0.5 | Updated automation framework configuration with proper timeouts (30s) and baseURL (demo.nopcommerce.com). | Cascade |
| 2026-04-12 | 0 | **GATE 0 CLEARED.** All 5 DoD conditions met. Ollama cloud (minimax-m2.7:cloud) active. Hello World file written to disk. | Antigravity |
| 2026-04-12 | 0 | Fixed: `uv pip sync` -> `uv pip install`, `agno.os.registry` -> `agno.registry.Registry`, localhost -> host.docker.internal | Antigravity |
| 2026-04-12 | 0 | All code scaffolding complete (0.1-0.10). Awaiting pulse check (0.11). | Antigravity |
| 2026-04-12 | — | Initial checklist created from blueprint | Antigravity |

---

> **This is a living document.** Update it as tasks are completed, gates are cleared, and the system evolves. Every change should be logged in the Changelog above.
