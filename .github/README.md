# GitHub Hooks and CI/CD Workflows

This document describes the local Git hooks and GitHub Actions workflows configured for Quality Autopilot.

## Local Git Hooks

### Pre-Commit Hook
- **Location**: `.githooks/pre-commit`
- **Purpose**: Validate code before committing
- **Checks**:
  - Python linting with black and flake8
  - TypeScript linting with eslint (on automation/ folder)
  - YAML file validation
  - Hardcoded secrets detection

### Post-Commit Hook
- **Location**: `.githooks/post-commit`
- **Purpose**: Trigger knowledge base re-index after commit
- **Triggers**: Only on main/develop branches
- **Actions**: Calls API endpoint to re-index codebase_vectors

### Enabling Hooks
The hooks are automatically enabled via `git config core.hooksPath .githooks`. To disable hooks temporarily:
```bash
git config --unset core.hooksPath
```

## GitHub Actions Workflows

### 1. CI Workflow (.github/workflows/ci.yml)
- **Triggers**: Push to main/develop, Pull Requests
- **Steps**:
  - Checkout code
  - Set up Python environment
  - Install dependencies
  - Run Python linting (black, flake8)
  - Run Python tests (Phase 2 DoD, Jira integration)
  - Build Docker images
  - Start services and health check

### 2. Jira Integration Workflow (.github/workflows/jira-trigger.yml)
- **Triggers**: Manual workflow dispatch, repository dispatch (jira-webhook)
- **Purpose**: Generate automation from Jira tickets
- **Steps**:
  - Fetch Jira ticket details
  - Build and start Docker services
  - Trigger Strategy Team via API
  - Generate Gherkin specs and automation

### 3. App Integration Workflow (.github/workflows/app-integration.yml)
- **Triggers**: Manual workflow dispatch, repository dispatch (app-update)
- **Purpose**: Trigger Discovery Agent when GDS-Demo-App changes
- **Steps**:
  - Build and start Docker services
  - Trigger Discovery Agent via webhook
  - Update site_manifesto and re-index KB

### 4. Automation Test Workflow (.github/workflows/test-automation.yml)
- **Triggers**: Push to automation/ folder, Pull Requests
- **Purpose**: Run Playwright tests when automation code changes
- **Steps**:
  - Set up Node.js environment
  - Install Playwright dependencies
  - Run Playwright tests
  - Upload test results and screenshots

## Webhook Endpoints

### /webhooks/jira
- **Purpose**: Receive Jira webhooks
- **Triggers**: Strategy Team when ticket status is "Ready for QA"
- **Payload**: JiraWebhookPayload (issue_key, issue_url, status, etc.)

### /webhooks/app-update
- **Purpose**: Receive webhooks from GDS-Demo-App
- **Triggers**: Discovery Agent to re-scan AUT
- **Payload**: AppWebhookPayload (repo, branch, commit_sha, etc.)

### /health
- **Purpose**: Health check endpoint for CI/CD
- **Returns**: Service health status

## GitHub Secrets

Required secrets to configure in GitHub repository settings:

### quality-autopilot Repository
- `GITHUB_PAT`: Personal Access Token for API calls between repos
- `JIRA_URL`: Jira instance URL
- `JIRA_USERNAME`: Jira username
- `JIRA_API_TOKEN`: Jira API token
- `DOCKER_USERNAME`: Docker Hub username (optional)
- `DOCKER_PASSWORD`: Docker Hub password (optional)

### GDS-Demo-App Repository
- `WEBHOOK_URL`: Quality Autopilot webhook URL
- `WEBHOOK_SECRET`: Secret for webhook validation (optional)

## Setting Up Webhooks

### GDS-Demo-App → Quality Autopilot
1. Go to GDS-Demo-App repository settings
2. Navigate to Webhooks
3. Add new webhook:
   - URL: `https://<quality-autopilot-host>/webhooks/app-update`
   - Content type: `application/json`
   - Events: Push, Pull Request

### Jira → Quality Autopilot
1. Go to Jira project settings
2. Navigate to Webhooks
3. Add new webhook:
   - URL: `https://<quality-autopilot-host>/webhooks/jira`
   - Events: Issue updated (status change to "Ready for QA")

## Manual Workflow Triggers

### Trigger Jira Integration Workflow
```bash
gh workflow run jira-trigger.yml -f ticket_key=GDS-4
```

### Trigger App Integration Workflow
```bash
gh workflow run app-integration.yml -f repo=lokeshsharma99/GDS-Demo-App -f branch=main
```
