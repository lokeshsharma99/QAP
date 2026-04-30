"""
Seed QAP Cultural Knowledge
============================

Run once (or idempotently re-run) to establish the foundational principles
every Quality Autopilot agent should know from day one.

Usage:
    python -m scripts.seed_culture
    # or inside Docker:
    docker exec qap-api python -m scripts.seed_culture
"""

from agno.db.schemas.culture import CulturalKnowledge
from db import get_culture_manager

cm = get_culture_manager()
cm.initialize()

SEEDS: list[CulturalKnowledge] = [
    # ── Locator Strategy ────────────────────────────────────────────────────
    CulturalKnowledge(
        name="Locator Priority Order",
        summary="Prefer data-testid > ARIA role > visible text. Never CSS class or XPath.",
        categories=["engineering", "locators"],
        content=(
            "Always choose locators in this order:\n"
            "1. data-testid attribute (most stable, intent-documenting)\n"
            "2. ARIA role + accessible name (e.g. getByRole('button', {name:'Submit'}))\n"
            "3. Visible text via getByText (acceptable for read-only labels)\n"
            "4. NEVER use CSS class selectors or XPath — they break on UI refactors\n"
            "Rationale: data-testid survives visual redesigns; role+name survives text changes."
        ),
        notes=["Enforced by Code Judge DoD checklist"],
    ),

    # ── Playwright Timing ───────────────────────────────────────────────────
    CulturalKnowledge(
        name="No Hardcoded Waits",
        summary="Use Playwright auto-waiting. Never sleep(), waitForTimeout(), or fixed delays.",
        categories=["engineering", "timing"],
        content=(
            "Playwright auto-waits for actionability before every interaction.\n"
            "- Use waitForLoadState('networkidle') only when page triggers multiple XHR\n"
            "- Use waitForSelector/waitForResponse for specific signals\n"
            "- page.waitForTimeout() is forbidden — it makes tests brittle and slow\n"
            "- time.sleep() in Python step definitions is equally forbidden\n"
            "Every hardcoded wait is a ticking time bomb on slow CI."
        ),
        notes=["Medic is NOT allowed to introduce waits when healing locators"],
    ),

    # ── Gherkin Authoring ───────────────────────────────────────────────────
    CulturalKnowledge(
        name="Gherkin Step Reusability",
        summary="Steps must be BA-readable, reusable, and behaviour-focused — not implementation-focused.",
        categories=["scribe", "gherkin"],
        content=(
            "Rules for every Gherkin scenario:\n"
            "1. Given/When/Then should describe INTENT, not implementation ('the user clicks submit'\n"
            "   is bad; 'the user submits the login form' is good)\n"
            "2. Prefer existing steps over creating new ones — check the Step Registry first\n"
            "3. Background section for repeated Given steps across a feature\n"
            "4. Scenario Outline + Examples table for data-driven cases\n"
            "5. No technical locators in step text (no 'when the user clicks #btn-submit')\n"
            "6. Each scenario covers exactly one acceptance criterion"
        ),
    ),

    # ── POM Design ──────────────────────────────────────────────────────────
    CulturalKnowledge(
        name="Page Object Model Design Principles",
        summary="One class per page. Expose actions, not raw locators. No assertions in POM.",
        categories=["engineering", "pom"],
        content=(
            "Page Object Model conventions:\n"
            "1. One TypeScript class per distinct page/modal — never mix multiple pages\n"
            "2. Expose high-level actions: login(user, pass), addToCart(productId)\n"
            "3. Never expose raw locators as public properties\n"
            "4. Never put expect() assertions inside POMs — assertions belong in step defs\n"
            "5. Constructor receives Playwright Page object only\n"
            "6. Use private readonly properties for locators, built in constructor\n"
            "7. Before writing: check Automation KB for an existing POM to extend"
        ),
    ),

    # ── Judge Approval ──────────────────────────────────────────────────────
    CulturalKnowledge(
        name="Judge Confidence Threshold",
        summary="≥90% confidence = auto-approve. <90% = Human Lead review. <50% = auto-reject.",
        categories=["judge", "quality-gate"],
        content=(
            "The Agentic Judge gates every artifact:\n"
            "- confidence ≥ 0.90 → AUTO-APPROVE, pipeline continues\n"
            "- 0.50 ≤ confidence < 0.90 → HumanReviewGateStep — artifact held for Human Lead\n"
            "- confidence < 0.50 → AUTO-REJECT — artifact returned to producing agent with reasons\n\n"
            "Producing agents should pre-validate against the DoD checklist before handoff\n"
            "to avoid unnecessary Human review cycles. The top rejection reasons are:\n"
            "1. Hardcoded sleeps or CSS selectors in Playwright code\n"
            "2. Gherkin steps with implementation detail\n"
            "3. Missing traceability to Acceptance Criteria\n"
            "4. POM with assertions"
        ),
    ),

    # ── Look-Before-You-Leap ─────────────────────────────────────────────────
    CulturalKnowledge(
        name="Engineer Look-Before-You-Leap Protocol",
        summary="Always check Site Manifesto → Automation KB → MCP verify before writing any code.",
        categories=["engineer", "protocol"],
        content=(
            "Before writing any Playwright code, the Engineer MUST:\n"
            "1. Query Site Manifesto KB for the target page and its components\n"
            "2. Query Automation KB to check if a POM already exists (avoid duplication)\n"
            "3. Use Playwright MCP pw__browser_navigate + pw__browser_snapshot to confirm\n"
            "   live locators on the real AUT match the Manifesto\n"
            "4. Only THEN write the POM and Step Definitions\n\n"
            "Skipping any of these steps leads to hallucinated selectors and wasted cycles."
        ),
    ),

    # ── Data Safety ──────────────────────────────────────────────────────────
    CulturalKnowledge(
        name="Test Data Safety Rules",
        summary="No production data. PII always masked. Unique constraints validated pre-run.",
        categories=["data-agent", "security"],
        content=(
            "Test data non-negotiables:\n"
            "1. NEVER copy production data — always generate synthetic data\n"
            "2. PII fields (email, phone, SSN) must be masked or use fake generators\n"
            "3. Validate unique constraints (e.g. unique emails) before inserting\n"
            "4. Every DB seed must have a corresponding cleanup_queries list\n"
            "5. Test users must use a test-domain email pattern (e.g. test+{uuid}@example.com)\n"
            "6. RunContext.pii_masked must be True before handoff to Engineer"
        ),
    ),

    # ── Medic Scope ──────────────────────────────────────────────────────────
    CulturalKnowledge(
        name="Medic Surgical Scope",
        summary="Medic changes locators and wait strategies ONLY. Never business logic, assertions, or flow.",
        categories=["medic", "healing"],
        content=(
            "The Medic's mandate is strictly surgical:\n"
            "- ALLOWED: Update a single locator string (data-testid value, role name, text)\n"
            "- ALLOWED: Replace waitForTimeout with a proper waitForSelector/waitForLoadState\n"
            "- FORBIDDEN: Changing assertion values or test expectations\n"
            "- FORBIDDEN: Modifying test flow, control flow, or step logic\n"
            "- FORBIDDEN: Adding new test coverage or removing existing scenarios\n\n"
            "If the fix requires logic changes → classify as LOGIC_CHANGE → escalate to Human Lead.\n"
            "A Healing Judge verifies the patch is surgical before it is applied."
        ),
    ),

    # ── Communication Standards ───────────────────────────────────────────────
    CulturalKnowledge(
        name="Agent Response Communication Standard",
        summary="Lead with actionable output. Use structured markdown. Cite sources and ACs.",
        categories=["communication", "all-agents"],
        content=(
            "All agent responses should follow this structure:\n"
            "1. LEAD with the primary output (spec, code, verdict, patch) — not with preamble\n"
            "2. Use structured markdown: headers, numbered lists, code blocks\n"
            "3. Cite the source AC or ticket ID for every decision\n"
            "4. End with a concise summary of what was produced and what the next step is\n"
            "5. Never output credentials, secrets, or connection strings\n"
            "6. When uncertain, express confidence level explicitly rather than hallucinating"
        ),
    ),
]

added = 0
skipped = 0
for ck in SEEDS:
    existing = cm.get_all_knowledge(name=ck.name)
    if existing:
        print(f"  [skip]  {ck.name}")
        skipped += 1
    else:
        cm.add_cultural_knowledge(ck)
        print(f"  [added] {ck.name}")
        added += 1

print(f"\nCulture seeding complete — {added} added, {skipped} already present.")
