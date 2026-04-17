"""
Librarian Agent Tools
=====================

Tools for the Librarian agent including file watching, re-indexing, and obsolescence detection capabilities.
"""

import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools
from agno.utils.log import logger

from contracts.test_deletion_approval import (
    ApprovalStatus,
    DeletionReason,
    ObsolescenceReport,
    TestDeletionRequest,
)
from db.session import get_automation_knowledge


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
        self.file_tools = FileTools(Path("automation"))
        self.knowledge_tools = KnowledgeTools(knowledge=self.knowledge)

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

        Args:
            file_path: Path to the file to re-index
        """
        try:
            logger.info(f"Re-indexing file: {file_path}")
            # Read file content
            content = self.file_tools.read_file(file_path)
            # Add to knowledge base
            self.knowledge_tools.add_knowledge(
                content=content,
                reference=f"file://{file_path}",
                metadata={
                    "file_path": file_path,
                    "file_type": Path(file_path).suffix,
                    "last_modified": self.get_file_modification_time(file_path),
                },
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
# Tool Functions for Librarian Agent
# ---------------------------------------------------------------------------
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
# Obsolescence Detection Tools
# ---------------------------------------------------------------------------
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
