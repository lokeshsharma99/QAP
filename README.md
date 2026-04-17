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
├── 13 Agents — Architect, Scribe, Discovery, Librarian, Curator, Engineer,
│                Data Agent, Detective, Medic, Judge, Healing Judge,
│                CI Log Analyzer, Technical Tester
├── 5 Squads  — Strategy, Context, Engineering, Operations, Grooming
├── 8 Flows   — Spec-to-Code, Discovery Onboard, Triage-Heal, Grooming,
│                Full Regression, Full Lifecycle, Technical Testing,
│                Regression Maintenance
├── 12 Contracts — Pydantic hand-off models
└── Semantica — Decision intelligence, context graphs, provenance tracking
```

## Agents

Quality Autopilot uses 13 specialized AI agents, each with a specific Primary Skill and tool set.

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
- **Role:** Manages vector knowledge base for test codebase with obsolescence detection capabilities
- **Tools:** KnowledgeTools, ReasoningTools, custom obsolescence detection tools (detect_obsolete_scenarios, detect_unused_steps, detect_orphaned_pages, generate_obsolescence_report)
- **When to Use:** Indexing Page Objects and Step Definitions for semantic search, detecting obsolete tests
- **Input:** Codebase changes, obsolescence detection requests
- **Output:** Updated vector index in PostgreSQL/PgVector, ObsolescenceReport

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

### CI Log Analyzer
- **Primary Skill:** `rca_analysis`
- **Role:** Analyzes Azure DevOps CI pipeline logs, performs RCA with historical knowledge, creates work items after HITL approval
- **Tools:** Azure DevOps API tools (pipeline logs, failed test filtering, work item creation), ReasoningTools
- **When to Use:** Analyzing CI pipeline failures and creating Azure DevOps work items with RCA findings
- **Input:** Azure DevOps project, pipeline ID, run ID
- **Output:** RCA findings, Azure DevOps work item (after HITL approval)
- **Knowledge Base:** RCA knowledge base for storing historical RCA learnings and patterns

### Curator
- **Primary Skill:** `suite_curation`
- **Role:** Maintains regression suite by detecting obsolete tests and recommending deletions with HITL approval
- **Tools:** FileTools, KnowledgeTools, ReasoningTools, custom curation tools (request_deletion_approval, execute_test_deletion, log_deletion_to_audit)
- **When to Use:** Regression suite maintenance, obsolescence detection, test scenario deletion
- **Input:** AUT changes, obsolescence detection results
- **Output:** ObsolescenceReport, deleted test files (after HITL approval), audit trail entries
- **Knowledge Base:** Automation knowledge base for comparing Site Manifesto versions
- **HITL Approval:** Uses Agno's native approval mechanism (OnError.pause) for test deletions

### Technical Tester
- **Primary Skill:** `test_generation`
- **Role:** Uses Playwright Test Agents (planner, generator, healer) for rapid test generation, smoke tests, and exploratory testing (complements BDD+POM)
- **Tools:** Playwright CLI tools (init-agents, planner, generator, healer), FileTools, ReasoningTools
- **When to Use:** AUT onboarding validation, smoke tests, exploratory testing, rapid prototyping before formal BDD
- **Input:** AUT URL, test requirements
- **Output:** Playwright tests in automation/technical-tests/, Markdown test plans
- **Relationship:** Complementary to Engineer agent (technical_tester for rapid testing, Engineer for production BDD+POM)

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

## Contracts

Quality Autopilot uses 12 Pydantic contracts for structured hand-offs between agents and teams.

### Core Contracts
- **RequirementContext** - Structured analysis of business requirements (Architect output)
- **GherkinSpec** - BDD specification with scenarios and data requirements (Scribe output)
- **RunContext** - Test data provisioning and execution context (Data Agent output)
- **SiteManifesto** - Complete map of Application Under Test (Discovery output)

### Quality & Healing Contracts
- **JudgeVerdict** - Adversarial review results with confidence score (Judge output)
- **RCAReport** - Root Cause Analysis for test failures (Detective output)
- **HealingPatch** - Surgical edit to fix broken locators (Medic output)
- **GroomingAssessment** - 3 Amigos review assessment (Grooming output)

### New Contracts
- **ExecutionResult** - Test execution results with detailed pass/fail information
- **WorkflowStatus** - Workflow orchestration status tracking
- **SquadHandoff** - Inter-squad communication with contract-based data passing
- **AutomationScaffold** - Automation framework scaffolding structure
- **TestDeletionApproval** - Test deletion request with HITL approval workflow (Curator output)

## Semantica Decision Intelligence

Quality Autopilot integrates Semantica for advanced decision tracking, context graphs, and provenance in high-stakes domains.

### Key Capabilities

- **Decision Tracking**: Every decision recorded with causal chains and reasoning
- **Precedent Search**: Find similar past decisions for consistency
- **Impact Analysis**: Understand decision influence on downstream systems
- **Provenance**: W3C PROV-O compliant audit trails
- **Conflict Detection**: Detect contradictory facts across knowledge bases

### Integration Status

| Agent | Semantica Features | Status |
|-------|-------------------|--------|
| Judge | Decision tracking, precedent search, impact analysis | ✅ Pilot Complete |
| Detective | Reasoning engines (forward chaining, abductive, Rete) | 🔄 Planned Phase 2 |
| Librarian | Conflict detection, entity resolution, temporal conflicts | 🔄 Planned Phase 2 |
| Architect | Context graphs, traceability graphs | 🔄 Planned Phase 3 |

### Judge Agent Semantica Tools

- `record_judge_decision`: Record approval/rejection with causal chains
- `find_judge_precedents`: Search similar past decisions
- `analyze_decision_impact`: Understand decision influence
- `get_decision_insights`: View decision pattern analytics

### Benefits

- **Explainability**: Every decision has causal chain and reasoning path
- **Consistency**: Precedent search ensures consistent decisions across sessions
- **Compliance**: W3C PROV-O provenance for audit trails
- **Trust**: Full decision audit trail builds trust in autonomous decisions

## Workflows

Quality Autopilot provides 8 end-to-end workflows for common STLC scenarios.

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

### Full Lifecycle Workflow
- **Purpose:** End-to-end workflow from requirement to execution/report using individual agents
- **Steps:**
  1. Requirement Analysis (Architect) - RequirementContext
  2. Gherkin Generation (Scribe) - GherkinSpec
  3. Quality Gate - Spec (Judge) - JudgeVerdict
  4. Context Discovery (Discovery) - SiteManifesto
  5. Index Knowledge Base (Librarian) - Indexed KB
  6. Test Data Provisioning (Data Agent) - RunContext
  7. Page Object Generation (Engineer) - Page Objects
  8. Step Definition Generation (Engineer) - Step Definitions
  9. Code Quality Gate (Judge) - Quality verdict
  10. Test Execution (Engineer) - ExecutionResult
  11. Failure Analysis (Detective) - RCAReport
  12. Healing Patch Generation (Medic) - HealingPatch
  13. Healing Patch Validation (Healing Judge) - Validation
  14. Apply and Verify Healing (Medic) - Verified fix
  15. Update Knowledge Base (Librarian) - Learnings
  16. Final Quality Gate (Judge) - JudgeVerdict
  17. Report Generation (Scribe) - FinalReport
- **Input:** Jira ticket ID or requirement description
- **Output:** Final report with all phases summarized
- **When to Use:** Complete STLC orchestration from requirement to report

### Technical Testing Workflow
- **Purpose:** Generate rapid test suites using Playwright Test Agents for smoke testing, exploratory testing, and AUT validation
- **Steps:**
  1. Initialize Playwright Agents (Technical Tester) - Agent definitions
  2. Create Seed Test (Technical Tester) - Seed test file
  3. Generate Test Plan (Technical Tester) - Markdown test plan
  4. Generate Playwright Tests (Technical Tester) - Playwright test files
  5. Execute Tests (Technical Tester) - Test execution results
  6. Heal Failures (Technical Tester) - Repaired tests
- **Input:** AUT URL, test requirements
- **Output:** Playwright tests in automation/technical-tests/, Markdown test plans
- **When to Use:** AUT onboarding validation, smoke tests, exploratory testing, rapid prototyping
- **Note:** Complements BDD+POM workflow (technical_tester for rapid testing, Engineer for production BDD+POM)

### Regression Maintenance Workflow
- **Purpose:** End-to-end regression suite curation to keep tests up to date as the AUT evolves
- **Steps:**
  1. Detect AUT Changes (Discovery Agent) - Current Site Manifesto
  2. Compare Site Manifesto (Curator Agent) - Version comparison
  3. Identify Obsolete Tests (Curator Agent) - Use Librarian's obsolescence detection tools
  4. Generate Deletion Recommendations (Curator Agent) - TestDeletionRequest with justifications
  5. HITL Approval (Curator Agent) - Agno's native approval mechanism (OnError.pause)
  6. Execute Approved Deletions (Curator Agent) - Delete tests with backups
  7. Update Knowledge Base (Librarian Agent) - Re-index automation codebase
  8. Generate Maintenance Report (Curator Agent) - ObsolescenceReport
- **Input:** AUT changes, obsolescence detection requests
- **Output:** ObsolescenceReport, deleted test files (after HITL approval), updated knowledge base, audit trail
- **When to Use:** Regression suite maintenance, obsolescence detection, test scenario deletion
- **HITL Approval:** Test deletions require human approval unless confidence ≥ AUTO_APPROVE_CONFIDENCE_THRESHOLD (default 0.9)

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

### Regression Suite Curation

The Quality Autopilot system includes automated regression suite curation to keep tests up to date as the AUT evolves.

**How it works:**
1. **Obsolescence Detection** - Librarian agent detects obsolete tests by comparing Site Manifesto versions
2. **Deletion Recommendations** - Curator agent generates TestDeletionRequest objects with justifications
3. **HITL Approval** - Test deletions require human approval via Agno's native approval mechanism (OnError.pause)
4. **Auto-Approval** - High-confidence recommendations (≥0.9) can be auto-approved (configurable threshold)
5. **Audit Trail** - All deletions are logged to an audit trail for compliance

**Running Regression Maintenance:**

1. **Execute Regression Maintenance workflow** via Agent UI
   ```
   Input: AUT changes or obsolescence detection request
   Output: ObsolescenceReport + deleted tests (after approval) + audit trail
   ```

2. **Review Deletion Recommendations:**
   ```
   Curator will generate deletion requests with:
   - Test type (feature_scenario, step_definition, page_object, fixture)
   - File path and scenario name
   - Reason for deletion (feature_removed, duplicate_test, etc.)
   - Confidence score (0.0-1.0)
   - Justification and affected AUT features
   ```

3. **Approve or Reject Deletions:**
   ```
   - Batch approval: All deletions grouped into a single approval request
   - Batch summary shows: "15 test case(s): 12 high-confidence, 3 require review"
   - If all items have confidence ≥0.9: Auto-approved
   - If any item has confidence <0.9: Requires human approval
   - Reviewer sees total count and confidence breakdown before approving
   - Reviewer can add comments before approval/rejection
   ```

**HITL Approval Flow:**
- Curator collects all deletion recommendations into a batch
- System calculates batch statistics (total count, high-confidence count, low-confidence count)
- If all items have confidence ≥ AUTO_APPROVE_CONFIDENCE_THRESHOLD: Auto-approve entire batch
- If any item has confidence < threshold: Triggers OnError.pause for human review with batch summary
- Human reviews batch summary showing total count and approves/rejects the entire batch
- If approved: Curator deletes all tests with optional backup
- Each deletion logged to audit trail
- Knowledge base re-indexed by Librarian

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

## Advanced Features

### Memory and Session Management

All agents are configured with:
- **update_memory_on_run=True**: Automatically updates user memories on each run
- **enable_session_summaries=True**: Generates session summaries for better context
- **learning=True**: Enables learned knowledge storage and retrieval
- **add_learnings_to_context=True**: Adds learnings to agent context

These features enable agents to learn from interactions and maintain context across sessions.

### Metrics and Monitoring

AgentOS provides built-in metrics at `/metrics` endpoint:
- Token usage metrics (input, output, total, cached, reasoning)
- Agent/team/workflow run counts
- User counts and model metrics
- Daily aggregated analytics

Query metrics:
```bash
curl http://localhost:8000/metrics
```

### Session Management API

Quality Autopilot exposes session management endpoints:
- `GET /sessions?user_id={user_id}` - List sessions for a user
- `GET /sessions/{session_id}` - Get session details
- `GET /sessions/{session_id}/runs` - Get session runs history

For full session management capabilities, use the AgentOSClient:
```python
from agno.client import AgentOSClient

client = AgentOSClient(base_url="http://localhost:8000")
sessions = await client.get_sessions(user_id="user123")
```

### Event Streaming

AgentOS supports real-time event streaming for monitoring agent/team/workflow runs:

**Event Types:**
- `RunStarted`: Triggered when a run starts
- `RunCompleted`: Triggered when a run completes
- `ToolCallStarted`: Triggered when a tool call begins
- `ToolCallCompleted`: Triggered when a tool call completes
- `ToolCallError`: Triggered when a tool call fails
- `MemoryUpdateStarted`: Triggered when memory update begins
- `MemoryUpdateCompleted`: Triggered when memory update completes

**Enable Event Streaming:**
```python
result = await agent.arun(
    "Analyze this requirement",
    stream_events=True
)
```

**Team Event Streaming:**
```python
async for event in team.arun(
    prompt,
    stream=True,
    stream_events=True
):
    print(f"Event: {event.event}")
```

### AgentOSClient Integration

For remote execution and session management, use the AgentOSClient:

```python
import asyncio
from agno.client import AgentOSClient

async def main():
    client = AgentOSClient(base_url="http://localhost:8000")

    # Get configuration
    config = await client.aget_config()

    # Run an agent
    result = await client.run_agent(
        agent_id="architect",
        message="Analyze this requirement"
    )

    # Manage sessions
    session = await client.create_session(
        agent_id="architect",
        user_id="user123",
        session_name="My Session"
    )

asyncio.run(main())
```

See `examples/agentos_client_example.py` for a complete example.

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

## Security

Quality Autopilot implements multiple layers of security through Agno guardrails to protect against common threats:

### Guardrails

**PII Detection Guardrail**
- Applied to: Architect, Scribe
- Purpose: Prevents personally identifiable information from entering the system
- Detects: Email addresses, phone numbers, SSNs, credit card numbers, addresses
- Action: Blocks input containing PII and requests sanitized input

**Prompt Injection Guardrail**
- Applied to: Architect, Scribe, Engineer
- Purpose: Prevents malicious prompt injection attacks
- Detects: Attempts to bypass agent instructions, jailbreak attempts, system prompt overrides
- Action: Blocks suspicious input and maintains agent instruction integrity

**OpenAI Moderation Guardrail**
- Applied to: Scribe, Engineer
- Purpose: Ensures generated content complies with OpenAI content policies
- Detects: NSFW content, hate speech, violence, self-harm, sexual content
- Action: Blocks policy-violating content generation

### Quality Gate Pause Mechanism

Critical quality gates use `OnError.pause` for human-in-the-loop intervention:
- Quality Gate - Spec (Judge)
- Code Quality Gate (Judge)
- Healing Patch Validation (Healing Judge)
- Final Quality Gate (Judge)

When a quality gate fails (confidence < 90%):
- Workflow pauses at the quality gate step
- User can choose to retry (send back for rework) or skip (escalate to human)
- Retry count is tracked to prevent infinite loops
- Enables flexible intervention without forcing automatic rework

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
