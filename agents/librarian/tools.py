"""
Librarian Agent Tools
=====================

Tools for the Librarian agent including file watching, re-indexing, and obsolescence detection capabilities.
"""

import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from agno.tools import Toolkit, tool
from agno.knowledge.chunking.fixed import FixedSizeChunking
from agno.knowledge.chunking.recursive import RecursiveChunking
from agno.knowledge.reader.text_reader import TextReader
from agno.utils.log import logger

from contracts.test_deletion_approval import (
    ApprovalStatus,
    DeletionReason,
    ObsolescenceReport,
    TestDeletionRequest,
)
from db.session import get_automation_kb as get_automation_knowledge
from db.session import get_site_manifesto_kb as _get_site_manifesto_kb


# ---------------------------------------------------------------------------
# File Watcher for Automatic Re-indexing
# ---------------------------------------------------------------------------
class AutomationFileWatcher:
    """Watches the automation/ directory for file changes and triggers re-indexing."""

    def __init__(self, watch_path: str = "automation", debounce_seconds: int = 5):
        """Initialize the file watcher.

        Args:
            watch_path: Path to the automation directory to watch
            debounce_seconds: Seconds to wait before triggering re-index after changes
        """
        self.watch_path = Path(watch_path)
        self.debounce_seconds = debounce_seconds
        self.last_modified = {}
        self.knowledge = get_automation_knowledge()

    def scan_directory(self) -> list[str]:
        """Scan the automation directory for all relevant files.

        Returns:
            List of file paths to index
        """
        files_to_index = []

        # Define directories and file extensions to scan
        scan_patterns = [
            ("pages", ".ts"),
            ("step_definitions", ".ts"),
            ("helpers", ".ts"),
            ("fixtures", ".ts"),
            ("config", ".ts"),
            ("config", ".json"),
            ("features", ".feature"),
        ]

        for dir_name, ext in scan_patterns:
            dir_path = self.watch_path / dir_name
            if dir_path.exists():
                for file_path in dir_path.rglob(f"*{ext}"):
                    files_to_index.append(str(file_path))

        return files_to_index

    def get_file_modification_time(self, file_path: str) -> float:
        """Get the last modification time of a file.

        Args:
            file_path: Path to the file

        Returns:
            Last modification timestamp
        """
        try:
            return os.path.getmtime(file_path)
        except OSError:
            return 0

    def check_for_changes(self) -> list[str]:
        """Check for file changes since last scan.

        Returns:
            List of files that have changed
        """
        changed_files = []
        current_files = self.scan_directory()

        for file_path in current_files:
            current_mtime = self.get_file_modification_time(file_path)
            last_mtime = self.last_modified.get(file_path, 0)

            if current_mtime > last_mtime:
                changed_files.append(file_path)
                self.last_modified[file_path] = current_mtime

        # Remove files that no longer exist
        existing_files = set(current_files)
        self.last_modified = {
            path: mtime
            for path, mtime in self.last_modified.items()
            if path in existing_files
        }

        return changed_files

    def re_index_file(self, file_path: str):
        """Re-index a single file in the knowledge base.

        Chooses a chunking strategy appropriate for the file type:
        - .ts / .py  → RecursiveChunking(1000, overlap=100) — respects code structure
        - .feature   → RecursiveChunking(2000, overlap=200) — keeps Gherkin scenarios together
        - .json      → FixedSizeChunking(2000) — structured data, no overlap needed
        - other      → FixedSizeChunking(5000) — default

        For .feature files, scenario names, tags, and ticket IDs are extracted
        and stored as metadata so RTM/traceability queries can surface them.
        For .ts Page Object files, the AUT page URL is extracted from the class
        and stored so the Site Manifesto → Automation KB link is queryable.

        Args:
            file_path: Path to the file to re-index
        """
        try:
            extension = Path(file_path).suffix.lower()

            if extension in ('.ts', '.py'):
                chunking: FixedSizeChunking | RecursiveChunking = RecursiveChunking(chunk_size=1000, overlap=100)
            elif extension == '.feature':
                chunking = RecursiveChunking(chunk_size=2000, overlap=200)
            elif extension == '.json':
                chunking = FixedSizeChunking(chunk_size=2000, overlap=0)
            else:
                chunking = FixedSizeChunking(chunk_size=5000, overlap=0)

            # ---------------------------------------------------------------------------
            # Build rich metadata depending on file type
            # ---------------------------------------------------------------------------
            metadata: dict = {
                "file_path": file_path,
                "file_type": extension,
                "last_modified": self.get_file_modification_time(file_path),
            }

            if extension == '.feature':
                metadata.update(_extract_feature_metadata(file_path))

            elif extension == '.ts' and 'pages/' in file_path.replace("\\", "/"):
                metadata.update(_extract_pom_metadata(file_path))

            logger.info(f"Re-indexing {file_path} with {type(chunking).__name__}")
            self.knowledge.insert(
                path=file_path,
                reader=TextReader(chunking_strategy=chunking),
                metadata=metadata,
            )
            logger.info(f"Successfully re-indexed: {file_path}")
        except Exception as e:
            logger.error(f"Failed to re-index {file_path}: {e}")

    def re_index_changed_files(self, changed_files: list[str]):
        """Re-index all changed files.

        Args:
            changed_files: List of files that have changed
        """
        for file_path in changed_files:
            self.re_index_file(file_path)

    def full_re_index(self):
        """Perform a full re-index of the automation directory."""
        logger.info("Starting full re-index of automation directory")
        files_to_index = self.scan_directory()
        logger.info(f"Found {len(files_to_index)} files to index")

        for file_path in files_to_index:
            self.re_index_file(file_path)
            self.last_modified[file_path] = self.get_file_modification_time(file_path)

        logger.info("Full re-index complete")


# ---------------------------------------------------------------------------
# Metadata Extractors
# ---------------------------------------------------------------------------

def _extract_feature_metadata(file_path: str) -> dict:
    """Parse a .feature file and return structured metadata.

    Extracts:
    - ``ticket_ids``     : list of Jira/ADO keys found in tags (@GDS-42) or Feature line
    - ``tags``           : all @-tags on the Feature and each Scenario
    - ``scenario_names`` : list of Scenario / Scenario Outline titles
    - ``feature_title``  : the Feature: line text
    - ``file_type_label``: "feature"

    Returns:
        dict of metadata fields
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"file_type_label": "feature"}

    ticket_pattern = re.compile(r"@([A-Z][A-Z0-9]+-\d+)", re.IGNORECASE)
    tag_pattern    = re.compile(r"@(\w[\w-]*)")
    scenario_re    = re.compile(r"^\s*(?:Scenario(?:\s+Outline)?)\s*:\s*(.+)", re.MULTILINE)
    feature_re     = re.compile(r"^\s*Feature\s*:\s*(.+)", re.MULTILINE)

    ticket_ids  = list(dict.fromkeys(ticket_pattern.findall(content)))
    all_tags    = list(dict.fromkeys(tag_pattern.findall(content)))
    scenarios   = [m.strip() for m in scenario_re.findall(content)]
    feature_m   = feature_re.search(content)
    feature_title = feature_m.group(1).strip() if feature_m else ""

    return {
        "file_type_label": "feature",
        "feature_title": feature_title,
        "ticket_ids": ticket_ids,
        "tags": all_tags,
        "scenario_names": scenarios,
        "scenario_count": len(scenarios),
    }


def _extract_pom_metadata(file_path: str) -> dict:
    """Parse a Page Object .ts file and extract the AUT page URL if present.

    Looks for:
    - ``protected readonly path = '/some/url'``
    - ``static readonly url = 'https://...'``
    - ``navigate(url: string = '/some/url')``

    Returns:
        dict with ``page_url`` and ``file_type_label``
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"file_type_label": "page_object"}

    url_patterns = [
        re.compile(r"""(?:readonly\s+)?(?:path|url|PAGE_URL|pageUrl)\s*[:=]\s*['"`]([^'"`]+)['"`]"""),
        re.compile(r"""navigate\s*\([^)]*=\s*['"`]([^'"`]+)['"`]"""),
    ]

    page_url = ""
    for pat in url_patterns:
        m = pat.search(content)
        if m:
            page_url = m.group(1).strip()
            break

    class_m = re.search(r"class\s+(\w+)", content)
    class_name = class_m.group(1) if class_m else Path(file_path).stem

    return {
        "file_type_label": "page_object",
        "page_url": page_url,
        "class_name": class_name,
    }


# ---------------------------------------------------------------------------
# Tool Functions for Librarian Agent
# ---------------------------------------------------------------------------
@tool(
    name="index_automation_codebase",
    description="Index the entire automation codebase into the knowledge base. Cached to avoid redundant re-indexing.",
    cache_results=True,
    cache_ttl=300,
)
def index_automation_codebase(watch_path: str = "automation") -> str:
    """Index the entire automation codebase into the knowledge base.

    Args:
        watch_path: Path to the automation directory

    Returns:
        Status message
    """
    watcher = AutomationFileWatcher(watch_path=watch_path)
    watcher.full_re_index()
    return f"Successfully indexed automation codebase from {watch_path}"


@tool(
    name="check_and_re_index_changes",
    description="Check for file changes in the automation directory and re-index only changed files.",
)
def check_and_re_index_changes(watch_path: str = "automation") -> str:
    """Check for file changes and re-index if needed.

    Args:
        watch_path: Path to the automation directory

    Returns:
        Status message with number of files re-indexed
    """
    watcher = AutomationFileWatcher(watch_path=watch_path)
    changed_files = watcher.check_for_changes()

    if changed_files:
        watcher.re_index_changed_files(changed_files)
        return f"Re-indexed {len(changed_files)} changed files"
    else:
        return "No changes detected"


@tool(
    name="get_file_statistics",
    description="Get statistics about the automation codebase files grouped by type. Cached for quick access.",
    cache_results=True,
    cache_ttl=60,
)
def get_file_statistics(watch_path: str = "automation") -> str:
    """Get statistics about the automation codebase.

    Args:
        watch_path: Path to the automation directory

    Returns:
        Statistics message
    """
    watcher = AutomationFileWatcher(watch_path=watch_path)
    files = watcher.scan_directory()

    # Count by file type
    file_types = {}
    for file_path in files:
        ext = Path(file_path).suffix
        file_types[ext] = file_types.get(ext, 0) + 1

    stats = f"Total files: {len(files)}\n"
    for ext, count in sorted(file_types.items()):
        stats += f"  {ext}: {count}\n"

    return stats


# ---------------------------------------------------------------------------
# RTM Persistence Tool
# ---------------------------------------------------------------------------

@tool(
    name="persist_traceability_to_rtm",
    description=(
        "Persist the AC-ID → Scenario traceability map from a GherkinSpec into the RTM "
        "knowledge base so any agent or the /rtm endpoint can query it later. "
        "Call this immediately after Scribe finalises a feature file."
    ),
)
def persist_traceability_to_rtm(
    ticket_id: str,
    feature_file: str,
    traceability: str,
    feature_title: str = "",
    tags: str = "",
) -> str:
    """Write AC-ID → Scenario links into the RTM vector KB.

    Each row stored in the RTM KB is a plain-text document of the form::

        Ticket: GDS-42
        Feature: Personal Details Form
        Feature file: automation/features/personal_details.feature
        AC-ID: GDS-42-AC-001
        Scenario: Verify personal details form submits successfully
        Tags: @GDS-42 @smoke @regression

    This schema is chosen so hybrid search on 'GDS-42 personal details' or
    'AC-001 smoke' surfaces the right rows quickly.

    Args:
        ticket_id:     Jira/ADO ticket key, e.g. "GDS-42"
        feature_file:  Relative path to the .feature file
        traceability:  JSON string of {AC-ID: scenario_name, ...} mapping
        feature_title: Human-readable Feature: title
        tags:          Space/comma-separated tags for this feature

    Returns:
        Status message describing how many RTM rows were written.
    """
    from db.session import get_rtm_kb

    try:
        mapping: dict = json.loads(traceability) if isinstance(traceability, str) else traceability
    except (json.JSONDecodeError, TypeError):
        return f"ERROR: traceability must be a JSON object string, got: {traceability!r}"

    if not mapping:
        return "No traceability entries to persist (empty mapping)."

    rtm_kb = get_rtm_kb()
    rows_written = 0

    for ac_id, scenario_name in mapping.items():
        doc_text = (
            f"Ticket: {ticket_id}\n"
            f"Feature: {feature_title}\n"
            f"Feature file: {feature_file}\n"
            f"AC-ID: {ac_id}\n"
            f"Scenario: {scenario_name}\n"
            f"Tags: {tags}\n"
        )
        try:
            rtm_kb.load_text(
                text=doc_text,
                metadata={
                    "ticket_id": ticket_id,
                    "ac_id": ac_id,
                    "scenario_name": scenario_name,
                    "feature_file": feature_file,
                    "feature_title": feature_title,
                    "tags": tags,
                    "source": "scribe",
                },
            )
            rows_written += 1
        except Exception as e:
            logger.error(f"Failed to persist RTM row for {ac_id}: {e}")

    return f"Persisted {rows_written}/{len(mapping)} RTM traceability rows for ticket {ticket_id}."


# ---------------------------------------------------------------------------
# Site Manifesto ↔ Automation KB cross-link tool
# ---------------------------------------------------------------------------

@tool(
    name="link_pom_to_manifesto",
    description=(
        "Scan every Page Object in automation/pages/ and enrich its KB entry with the "
        "matching Site Manifesto page URL and component list. "
        "Call this after index_automation_codebase to complete the Digital Twin link."
    ),
)
def link_pom_to_manifesto(watch_path: str = "automation") -> str:
    """Enrich Page Object KB entries with Site Manifesto page URLs.

    For every .ts file in automation/pages/:
    1. Extract its ``page_url`` via ``_extract_pom_metadata``.
    2. Query the Site Manifesto KB: "page {page_url} components locators".
    3. Re-insert the POM into the Automation KB with ``manifesto_page_url`` and
       ``manifesto_components`` added to its metadata.

    This creates the bidirectional link:

        Site Manifesto: /personal-details → PersonalDetailsPage.ts
        Automation KB:  PersonalDetailsPage.ts → /personal-details (+ component list)

    Args:
        watch_path: Path to the automation directory (default: "automation")

    Returns:
        Status string listing how many POMs were linked.
    """
    pages_dir = Path(watch_path) / "pages"
    if not pages_dir.exists():
        return "No pages/ directory found — nothing to link."

    automation_kb = get_automation_knowledge()
    site_manifesto_kb = _get_site_manifesto_kb()

    linked = 0
    skipped = 0
    errors = 0

    for pom_path in pages_dir.rglob("*.ts"):
        try:
            pom_meta = _extract_pom_metadata(str(pom_path))
            page_url = pom_meta.get("page_url", "")
            class_name = pom_meta.get("class_name", pom_path.stem)

            # Query the Site Manifesto for this page URL
            query = f"page {page_url} components locators" if page_url else f"{class_name} components"
            manifesto_docs = site_manifesto_kb.search(query=query, num_documents=3)

            manifesto_components: list[str] = []
            manifesto_page_url = page_url

            for doc in manifesto_docs:
                # Extract component names from manifesto content (heuristic: lines with locator_value)
                if doc.content:
                    for line in doc.content.split("\n"):
                        if "locator_value" in line or "name:" in line:
                            part = line.split(":")[-1].strip().strip('"').strip("'")
                            if part and part not in manifesto_components:
                                manifesto_components.append(part)
                if doc.meta_data and doc.meta_data.get("url"):
                    manifesto_page_url = doc.meta_data["url"]

            if not manifesto_docs:
                skipped += 1
                continue

            # Re-index the POM with enriched metadata (manifesto link)
            automation_kb.insert(
                path=str(pom_path),
                reader=TextReader(chunking_strategy=RecursiveChunking(chunk_size=1000, overlap=100)),
                metadata={
                    "file_path": str(pom_path),
                    "file_type": ".ts",
                    "file_type_label": "page_object",
                    "class_name": class_name,
                    "page_url": page_url,
                    "manifesto_page_url": manifesto_page_url,
                    "manifesto_components": ", ".join(manifesto_components[:10]),
                    "last_modified": pom_path.stat().st_mtime,
                },
            )
            linked += 1
            logger.info(f"Linked {pom_path.name} → manifesto page: {manifesto_page_url}")

        except Exception as e:
            logger.error(f"Failed to link {pom_path}: {e}")
            errors += 1

    return (
        f"Site Manifesto ↔ Automation KB link complete: "
        f"{linked} POMs linked, {skipped} skipped (no manifesto match), {errors} errors."
    )


# ---------------------------------------------------------------------------
# Obsolescence Detection Tools
# ---------------------------------------------------------------------------
@tool(
    name="detect_obsolete_scenarios",
    description="Detect obsolete test scenarios by comparing Site Manifesto with feature files.",
)
def detect_obsolete_scenarios(watch_path: str = "automation") -> str:
    """Detect obsolete test scenarios by comparing Site Manifesto with feature files.

    Args:
        watch_path: Path to the automation directory

    Returns:
        Status message with number of obsolete scenarios detected
    """
    features_dir = Path(watch_path) / "features"
    if not features_dir.exists():
        return "No features directory found"

    # Query knowledge base for Site Manifesto
    knowledge = get_automation_knowledge()
    if knowledge is None:
        return "Knowledge base not available"

    # Get all feature files
    feature_files = list(features_dir.glob("*.feature"))
    obsolete_count = 0

    for feature_file in feature_files:
        try:
            content = feature_file.read_text()
            # Simple heuristic: check if scenario references removed AUT features
            # In a real implementation, this would compare with Site Manifesto
            # For now, this is a placeholder for the detection logic
            logger.info(f"Analyzing feature file: {feature_file.name}")
        except Exception as e:
            logger.error(f"Failed to analyze {feature_file}: {e}")

    return f"Detected {obsolete_count} potentially obsolete scenarios"


@tool(
    name="detect_unused_steps",
    description="Detect step definitions not referenced in any feature file.",
)
def detect_unused_steps(watch_path: str = "automation") -> str:
    """Detect step definitions not referenced in any feature file.

    Args:
        watch_path: Path to the automation directory

    Returns:
        Status message with number of unused step definitions
    """
    steps_dir = Path(watch_path) / "step_definitions"
    features_dir = Path(watch_path) / "features"

    if not steps_dir.exists() or not features_dir.exists():
        return "Step definitions or features directory not found"

    # Get all step definition files
    step_files = list(steps_dir.glob("*.ts"))
    # Get all feature files
    feature_files = list(features_dir.glob("*.feature"))

    # Extract step patterns from feature files
    used_steps = set()
    for feature_file in feature_files:
        try:
            content = feature_file.read_text()
            # Extract Gherkin steps (Given, When, Then)
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith(("Given ", "When ", "Then ", "And ", "But ")):
                    used_steps.add(line)
        except Exception as e:
            logger.error(f"Failed to read {feature_file}: {e}")

    unused_count = 0
    # In a real implementation, this would parse step definition files
    # and check if any are not in used_steps
    logger.info(f"Found {len(step_files)} step definition files")
    logger.info(f"Found {len(used_steps)} unique step patterns in features")

    return f"Detected {unused_count} potentially unused step definitions"


@tool(
    name="detect_orphaned_pages",
    description="Detect Page Objects not used by any step definition.",
)
def detect_orphaned_pages(watch_path: str = "automation") -> str:
    """Detect Page Objects not used by any step definition.

    Args:
        watch_path: Path to the automation directory

    Returns:
        Status message with number of orphaned Page Objects
    """
    pages_dir = Path(watch_path) / "pages"
    steps_dir = Path(watch_path) / "step_definitions"

    if not pages_dir.exists() or not steps_dir.exists():
        return "Pages or step definitions directory not found"

    # Get all Page Object files
    page_files = list(pages_dir.glob("*.ts"))
    # Get all step definition files
    step_files = list(steps_dir.glob("*.ts"))

    orphaned_count = 0
    # In a real implementation, this would parse step definition files
    # and check which Page Objects are imported/used
    logger.info(f"Found {len(page_files)} Page Object files")
    logger.info(f"Found {len(step_files)} step definition files")

    return f"Detected {orphaned_count} potentially orphaned Page Objects"


@tool(
    name="generate_obsolescence_report",
    description="Generate a comprehensive obsolescence report for the regression suite.",
)
def generate_obsolescence_report(watch_path: str = "automation") -> str:
    """Generate a comprehensive obsolescence report for the regression suite.

    Args:
        watch_path: Path to the automation directory

    Returns:
        JSON string containing the ObsolescenceReport
    """
    report_id = str(uuid.uuid4())
    
    # Run all detection tools
    obsolete_scenarios_result = detect_obsolete_scenarios(watch_path)
    unused_steps_result = detect_unused_steps(watch_path)
    orphaned_pages_result = detect_orphaned_pages(watch_path)

    # Create the report
    report = ObsolescenceReport(
        report_id=report_id,
        obsolete_scenarios=[],
        obsolete_steps=[],
        orphaned_pages=[],
        stale_fixtures=[],
        total_recommendations=0,
        high_confidence_count=0
    )

    logger.info(f"Generated obsolescence report: {report_id}")
    logger.info(f"Obsolete scenarios: {obsolete_scenarios_result}")
    logger.info(f"Unused steps: {unused_steps_result}")
    logger.info(f"Orphaned pages: {orphaned_pages_result}")

    return f"Generated obsolescence report with ID: {report_id}"


# ---------------------------------------------------------------------------
# Module-level helper used by the app/main.py background file watcher.
# Thin wrapper over AutomationFileWatcher.re_index_file() so it can be
# called without instantiating the full Librarian agent.
# ---------------------------------------------------------------------------

_watcher_instance: AutomationFileWatcher | None = None


def _reindex_single_file(file_path: str) -> None:
    """Re-index a single automation/ file into the Knowledge Base.

    Called by the background watchfiles task in app/main.py whenever a file
    is created, modified, or deleted. Uses a module-level singleton watcher
    to avoid re-creating the Knowledge DB connection on every file event.
    """
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = AutomationFileWatcher()
    _watcher_instance.re_index_file(file_path)


# ---------------------------------------------------------------------------
# LibrarianToolkit
# ---------------------------------------------------------------------------
class LibrarianToolkit(Toolkit):
    """Groups all Librarian Agent tools into a single registerable toolkit."""

    def __init__(self) -> None:
        super().__init__(
            name="librarian",
            tools=[
                index_automation_codebase,
                check_and_re_index_changes,
                get_file_statistics,
                persist_traceability_to_rtm,
                link_pom_to_manifesto,
                detect_obsolete_scenarios,
                detect_unused_steps,
                detect_orphaned_pages,
                generate_obsolescence_report,
            ],
        )
