"""
Discovery Onboard Workflow
==========================

Workflow for automating AUT onboarding and knowledge base population.
End-to-end orchestration of AUT URL → Discovery → Manifesto → Librarian → KB.
"""

from agno.workflow import Workflow, Step

from agents.discovery import discovery
from agents.librarian import librarian

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
discovery_onboard = Workflow(
    id="discovery-onboard",
    name="Discovery Onboard",
    steps=[
        Step(
            name="Crawl AUT",
            agent=discovery,
            description="""As the Discovery Agent, crawl the AUT URL to extract UI elements and generate Site Manifesto.

Input: AUT URL provided in workflow input (e.g., https://universal-credit.service.gov.uk)

Your task:
1. Use Playwright to navigate to the AUT URL
2. Crawl all accessible pages and routes
3. Extract interactive elements (buttons, forms, inputs, navigation)
4. Generate Site Manifesto with page structure and element locators

Output: Provide Site Manifesto with:
- Page URLs and navigation structure
- Interactive elements with locators (data-testid, role, text)
- Form fields and validation rules
- Page metadata (titles, descriptions)

Focus on: Comprehensive coverage of all interactive elements for semantic search.""",
        ),
        Step(
            name="Index Site Manifesto",
            agent=librarian,
            description="""As the Librarian Agent, index the Site Manifesto into the knowledge base.

Input: Site Manifesto from previous step

Your task:
1. Parse Site Manifesto into searchable chunks
2. Generate embeddings using text-embedding-3-small
3. Index with hybrid search (vector + keyword)
4. Add metadata (source, timestamp, relevance)

Output: Confirm Site Manifesto indexed with:
- Document count
- Vector index status
- Searchability confirmation

Focus on: Ensuring Site Manifesto is searchable for semantic queries.""",
        ),
        Step(
            name="Index Codebase",
            agent=librarian,
            description="""As the Librarian Agent, index the automation codebase into the knowledge base.

Input: Path to automation/ directory (default: automation/)

Your task:
1. Scan all TypeScript files in automation/
2. Parse Page Objects, step definitions, and config files
3. Generate embeddings for code chunks
4. Index with hybrid search (vector + keyword)

Output: Confirm codebase indexed with:
- File count
- Vector index status
- Searchability confirmation

Focus on: Making automation code discoverable for impact analysis.""",
        ),
        Step(
            name="Verify Knowledge Base",
            agent=librarian,
            description="""As the Librarian Agent, verify the knowledge base is searchable and contains relevant information.

Input: Previous indexing operations

Your task:
1. Perform test queries for Site Manifesto and codebase
2. Verify search results are relevant
3. Check hybrid search is working (vector + keyword)
4. Confirm metadata is properly attached

Output: Provide verification report with:
- Test query results
- Search relevance score
- Hybrid search status
- Any issues or gaps

Focus on: Ensuring knowledge base is fully functional for semantic search.""",
        ),
    ],
)
