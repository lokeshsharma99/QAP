# Quality Autopilot

**Agentic Compiler for the Software Testing Life Cycle (STLC).**

Quality Autopilot treats AI as a Senior SDET that reasons through requirements, writes Playwright automation, and self-heals broken tests.

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Ollama Cloud API key (or configure your own OpenAI-compatible endpoint)

### Setup

```bash
# 1. Copy environment file and configure your API keys
cp example.env .env
# Edit .env and set at minimum:
#   - OLLAMA_API_KEY=your_api_key
#   - OLLAMA_BASE_URL=http://host.docker.internal:11434 (or your Ollama Cloud endpoint)
#   - OLLAMA_MODEL=gpt-oss:120b-cloud (or your preferred model)

# 2. Start all services (includes qap-db, qap-api, qap-ui)
docker compose up -d --build

# 3. Verify the API is healthy
curl http://localhost:8000/health
# Expected response: {"status":"ok","instantiated_at":"..."}
```

### Access

| Service | URL | Purpose |
|---------|-----|---------|
| **AgentOS API** | http://localhost:8000 | FastAPI backend for agents |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Agent UI** | http://localhost:3000 | Web interface to interact with agents |
| **PostgreSQL** | localhost:5432 | Vector database (PgVector) |

## Architecture

```
Quality Autopilot
├── 10 Agents — Architect, Scribe, Discovery, Librarian, Engineer,
│                Data Agent, Detective, Medic, Judge, Healing Judge
├── 5 Squads  — Strategy, Context, Engineering, Operations, Grooming
├── 5 Flows   — Spec-to-Code, Discovery Onboard, Triage-Heal, Grooming, Full Regression
└── 8 Contracts — Pydantic hand-off models
```

## Agents

Quality Autopilot uses 10 specialized AI agents, each with a specific Primary Skill and tool set.

### Architect
- **Primary Skill:** `semantic_search`
- **Role:** Analyzes requirements, queries knowledge base for impact, produces RequirementContext
- **Tools:** KnowledgeTools (site_manifesto, codebase), ReasoningTools, Jira API tools
- **When to Use:** Converting Jira tickets or requirement documents into structured RequirementContext
- **Input:** Jira ticket URL, requirement description
- **Output:** RequirementContext (acceptance criteria, affected page objects, execution plan)

### Scribe
- **Primary Skill:** `gherkin_formatter`
- **Role:** Converts RequirementContext to Gherkin specifications (.feature files)
- **Tools:** FileTools, ReasoningTools
- **When to Use:** Translating structured requirements into BDD test scenarios
- **Input:** RequirementContext
- **Output:** .feature files with reusable Gherkin steps

### Discovery Agent
- **Primary Skill:** `ui_crawler`
- **Role:** Crawls AUT, extracts UI structure, produces Site Manifesto
- **Tools:** MCPTools (Playwright), KnowledgeTools, ReasoningTools, crawl_site, crawl_page
- **When to Use:** Onboarding a new AUT or updating site structure after changes
- **Input:** AUT URL
- **Output:** SiteManifesto (pages, components, locators)

### Librarian
- **Primary Skill:** `vector_indexing`
- **Role:** Manages vector knowledge base for test codebase
- **Tools:** KnowledgeTools, ReasoningTools
- **When to Use:** Indexing Page Objects and Step Definitions for semantic search
- **Input:** Codebase changes
- **Output:** Updated vector index in PostgreSQL/PgVector

### Engineer
- **Primary Skill:** `file_writer`
- **Role:** Writes modular Playwright POMs and Step Definitions (Look-Before-You-Leap pattern)
- **Tools:** CodingTools, FileTools, KnowledgeTools, MCPTools (Playwright), custom tools
- **When to Use:** Generating automation code from Gherkin specifications
- **Input:** Gherkin .feature files
- **Output:** Playwright Page Objects, Step Definitions, test code

### Data Agent
- **Primary Skill:** `data_factory`
- **Role:** Provisions test data with PII masking
- **Tools:** CodingTools, FileTools, custom data tools
- **When to Use:** Setting up test data for automation execution
- **Input:** Test data requirements
- **Output:** run_context.json with test users, DB seeds, API mocks

### Detective
- **Primary Skill:** `trace_analyzer`
- **Role:** Analyzes test failures to identify root causes
- **Tools:** CodingTools, FileTools, analyze_trace_file
- **When to Use:** Triaging test failures to determine healability
- **Input:** Playwright trace.zip, error message
- **Output:** RCAReport (failure type, confidence, root cause, recommendations)

### Medic
- **Primary Skill:** `surgical_editor`
- **Role:** Performs surgical edits to fix broken locators
- **Tools:** CodingTools, FileTools, custom healing tools
- **When to Use:** Applying automated healing to healable failures
- **Input:** RCAReport
- **Output:** HealingPatch (surgical locator replacement)

### Judge
- **Primary Skill:** `adversarial_review`
- **Role:** Performs adversarial review of generated specifications with DoD checklist
- **Tools:** ReasoningTools, judge_tools
- **When to Use:** Quality gate for generated specs, code, or healing patches
- **Input:** Generated artifact (spec, code, patch)
- **Output:** JudgeVerdict (confidence, passed, checklist results)

### Healing Judge
- **Primary Skill:** `healing_validation`
- **Role:** Performs adversarial review of healing patches before application
- **Tools:** ReasoningTools, healing_judge_tools
- **When to Use:** Validating healing patches for safety and compliance
- **Input:** HealingPatch
- **Output:** Validation results (confidence, surgical edit check)

## Teams

Quality Autopilot organizes agents into 5 cross-functional squads, each using TeamMode.coordinate for collaboration.

### Strategy Team
- **Members:** Architect, Scribe
- **Mode:** TeamMode.coordinate
- **Purpose:** Bridge between Business Analysts and Technical team to create test specifications
- **When to Use:** Converting Jira tickets or requirements into Gherkin specifications
- **Workflow Integration:** Spec-to-Code workflow (first phase)
- **Output:** Gherkin .feature files + DataRequirements

### Context Team
- **Members:** Discovery, Librarian
- **Mode:** TeamMode.coordinate
- **Purpose:** Maintains AUT knowledge base through crawling and codebase indexing
- **When to Use:** Onboarding new AUTs or updating site structure
- **Workflow Integration:** Discovery Onboard workflow
- **Output:** SiteManifesto, indexed codebase knowledge

### Engineering Team
- **Members:** Engineer, Data Agent
- **Mode:** TeamMode.coordinate
- **Purpose:** Generates automation code and provisions test data
- **When to Use:** Converting Gherkin specs to Playwright automation
- **Workflow Integration:** Spec-to-Code workflow (code generation phase)
- **Output:** Playwright POMs, Step Definitions, run_context.json

### Operations Team
- **Members:** Detective, Medic
- **Mode:** TeamMode.coordinate
- **Purpose:** Diagnoses test failures and applies automated healing
- **When to Use:** Triage and self-healing of broken tests
- **Workflow Integration:** Triage-Heal workflow
- **Output:** RCAReport, HealingPatch, verified tests

### Grooming Team
- **Members:** Architect, Judge, Engineer
- **Mode:** TeamMode.coordinate
- **Purpose:** 3 Amigos review from BA, SDET, and Dev perspectives
- **When to Use:** User story grooming and assessment
- **Workflow Integration:** Grooming workflow
- **Output:** GroomingAssessment, Jira comment

## Workflows

Quality Autopilot provides 5 end-to-end workflows for common STLC scenarios.

### Spec-to-Code Workflow
- **Purpose:** Convert requirements to automated Playwright tests
- **Steps:**
  1. Parse Feature File (Engineer)
  2. Provision Test Data (Data Agent)
  3. Generate Page Objects (Engineer)
  4. Generate Step Definitions (Engineer)
  5. Code Quality Gate (Judge)
  6. Local Verification (Engineer)
  7. Create Pull Request (Engineer)
- **Input:** Gherkin .feature file
- **Output:** Playwright automation code + PR
- **When to Use:** End-to-end automation generation from specs

### Discovery Onboard Workflow
- **Purpose:** Onboard AUT and populate knowledge base
- **Steps:**
  1. Crawl AUT (Discovery)
  2. Index Site Manifesto (Librarian)
  3. Index Codebase (Librarian)
  4. Verify Knowledge Base (Librarian)
- **Input:** AUT URL
- **Output:** SiteManifesto + indexed knowledge base
- **When to Use:** Initial AUT onboarding or site structure updates

### Triage-Heal Workflow
- **Purpose:** Diagnose failures and apply automated healing
- **Steps:**
  1. Analyze Failure (Detective)
  2. Assess Healability (Detective)
  3. Generate Healing Patch (Medic)
  4. Validate Healing Patch (Healing Judge)
  5. Apply Healing Patch (Medic)
  6. Verify Healing (3x) (Medic)
  7. Update Knowledge Base (Librarian)
- **Input:** Playwright trace.zip, error message
- **Output:** Healed tests + learnings in KB
- **When to Use:** Self-healing of broken locators

### Grooming Workflow
- **Purpose:** 3 Amigos review of user stories
- **Steps:**
  1. BA Assessment (Architect)
  2. SDET Assessment (Judge)
  3. Synthesize Assessment (Judge)
  4. Post to Jira (Architect)
- **Input:** User story requirements
- **Output:** GroomingAssessment + Jira comment
- **When to Use:** User story grooming and testability assessment

### Full Regression Workflow
- **Purpose:** End-to-end regression testing orchestration
- **Steps:**
  1. Generate Automation (Engineer)
  2. Execute Tests (Engineer)
  3. Analyze Failures (Detective)
  4. Generate Healing Patch (Medic)
  5. Validate Healing Patch (Healing Judge)
  6. Verify Healing (Medic)
  7. Update Knowledge Base (Librarian)
- **Input:** Requirements
- **Output:** Regression results + healed tests
- **When to Use:** Full regression with self-healing

## How to Use

### Converting a Jira Ticket to Automation

1. **Fetch Ticket:** Use Architect agent with Jira ticket URL
   ```
   Input: "https://lokeshsharma2.atlassian.net/browse/QA-123"
   Output: RequirementContext with acceptance criteria
   ```

2. **Generate Gherkin:** Use Scribe agent to convert to .feature file
   ```
   Input: RequirementContext
   Output: automation/features/ticket-qa-123.feature
   ```

3. **Generate Code:** Use Engineer agent to create Playwright code
   ```
   Input: .feature file
   Output: Page Objects, Step Definitions
   ```

4. **Quality Gate:** Use Judge agent to validate generated code
   ```
   Input: Generated code
   Output: JudgeVerdict (confidence ≥90% required)
   ```

### Onboarding a New AUT

1. **Run Discovery Onboard workflow** via Agent UI
   ```
   Input: AUT URL (e.g., https://demo.nopcommerce.com/)
   Output: SiteManifesto + indexed knowledge base
   ```

2. **Verify Knowledge Base** is searchable
   ```
   Use Librarian agent to query for specific page elements
   ```

### Healing a Broken Test

1. **Collect Failure Data:** Get trace.zip from Playwright
   ```
   Located in: test-results/trace.zip
   ```

2. **Run Triage-Heal workflow** via Agent UI
   ```
   Input: trace.zip, error message
   Output: RCAReport + HealingPatch
   ```

3. **Apply Healing:** Medic agent applies the patch
   ```
   Output: Healed test file
   ```

### Running Full Regression

1. **Execute Full Regression workflow** via Agent UI
   ```
   Input: Requirements or .feature files
   Output: Regression results + healed tests
   ```

2. **Review Results:** Check Agent UI for test results
   ```
   Green tests: Passed
   Red tests: Healed automatically
   ```

## Current Status

**Phase 0: Infrastructure Bootstrap** ✅ Complete
- Docker Compose stack (qap-db, qap-api, qap-ui) running
- AgentOS API accessible at http://localhost:8000
- Agent UI accessible at http://localhost:3000
- PostgreSQL with PgVector configured

**Phase 0.5: AUT Onboarding (Discovery)** ✅ Complete
- Discovery agent created and registered
- SiteManifesto contract defined
- UI Crawler tool with curl_cffi (Cloudflare bypass) implemented
- MCP Playwright integration configured
- Discovery Onboard workflow created

**Phase 1: Spec-Driven Development** ✅ Complete
- Architect and Scribe agents created
- Strategy Team formed (Architect + Scribe)
- RequirementContext and GherkinSpec contracts defined
- Jira API integration configured
- Judge agent with Gherkin-specific DoD checklist
- Gate 2 Cleared (6/6 criteria passing)

**Phase 2: Engineering Loop (Muscle)** 🚧 In Progress
- Engineer and Data Agent agents created
- Engineering Team formed (Engineer + Data Agent)
- RunContext contract defined
- Spec-to-Code workflow created
- PR generation automation implemented
- Local verification tool implemented
- Gate 3 Status: 5/9 criteria passing (eslint configured, test infrastructure created)

**Phase 4: Triage & Self-Healing** ✅ Complete
- Detective and Medic agents created
- Operations Team formed (Detective + Medic)
- Healing Judge agent created
- RCAReport and HealingPatch contracts defined
- Triage-Heal workflow created
- Surgical edit tools implemented
- Healing loop verification: 8/8 tests passed
- Gate 4 Cleared (6/6 criteria passing)

**Phase 5: Autonomous Maturity** 🚧 In Progress
- Context Team created (Discovery + Librarian)
- Learned Knowledge enabled (qap_learnings KB)
- Discovery Onboard workflow created
- Full Regression workflow created
- Comprehensive evals implemented
- Autonomous mode configured (auto-approve at ≥90% confidence)
- Remaining: Deploy to Production, Harden Security, Production Monitoring

## AUT (Application Under Test)

Default target: [nopCommerce Demo](https://demo.nopcommerce.com/)

Configure in `.env`:
```bash
AUT_BASE_URL=https://demo.nopcommerce.com/
AUT_AUTH_USER=your_username
AUT_AUTH_PASS=your_password
```

## Documentation

| File | Purpose |
|------|---------|
| [AGENTS.md](./AGENTS.md) | Full architecture specification |
| [CHECKLIST.md](./CHECKLIST.md) | Implementation progress tracker |
| [CLAUDE.md](./CLAUDE.md) | Quick reference overview |
| [.instructions.md](./.instructions.md) | AI agent system instructions |

## Development

```bash
# View service logs
docker compose logs -f qap-api
docker compose logs -f qap-ui

# Stop all services
docker compose down

# Restart a specific service
docker compose restart qap-api

# Format & validate code
./scripts/format.sh
./scripts/validate.sh
```

## Testing the Discovery Agent

1. Open Agent UI at http://localhost:3000
2. Select the **Discovery** agent
3. Enter prompt: "Crawl https://demo.nopcommerce.com/ and generate a Site Manifesto"
4. The agent will use curl_cffi to bypass Cloudflare and extract the site structure
5. Review the generated SiteManifesto JSON output

## Troubleshooting

**Services not starting?**
```bash
# Check Docker is running
docker ps

# View logs for errors
docker compose logs
```

**Agent UI not connecting?**
- Ensure qap-api is running: `docker compose ps qap-api`
- Check API health: `curl http://localhost:8000/health`
- Verify NEXT_PUBLIC_API_URL in compose.yaml points to qap-api

## License

Proprietary. All rights reserved.
