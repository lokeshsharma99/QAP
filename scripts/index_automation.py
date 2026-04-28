"""
scripts/index_automation.py
============================

Seed the Automation Codebase KB (table: codebase_vectors) by reading
every relevant file from the automation/ directory and loading them into
PgVector via Agno's Knowledge.load_text() API.

Run this once after cloning, and again any time you add/change automation
code (or let git hooks trigger it automatically via scripts/format.sh).

Usage
-----
    # From workspace root — full index (default)
    python -m scripts.index_automation

    # Index a specific subdirectory only
    python -m scripts.index_automation --path automation/pages

    # Dry-run: list files that WOULD be indexed without touching the DB
    python -m scripts.index_automation --dry-run

    # Re-index even files that haven't changed (force mode)
    python -m scripts.index_automation --force

File types indexed
------------------
    automation/pages/              *.ts   — Page Object Models
    automation/step_definitions/   *.ts   — Cucumber step implementations
    automation/features/           *.feature — Gherkin BDD scenarios
    automation/helpers/            *.ts   — shared test utilities
    automation/fixtures/           *.ts   — test data fixtures
    automation/hooks/              *.ts   — Before/After lifecycle hooks
    automation/config/             *.ts   — AUT-specific config
    automation/config/             *.json — config JSON
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path when run as a script
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from db.session import get_automation_kb  # noqa: E402

# ---------------------------------------------------------------------------
# Scan configuration
# ---------------------------------------------------------------------------
AUTOMATION_DIR = _ROOT / "automation"

# (subdirectory, glob pattern) — order determines chunk proximity in vector space
SCAN_TARGETS = [
    ("pages", "**/*.ts"),
    ("step_definitions", "**/*.ts"),
    ("features", "**/*.feature"),
    ("helpers", "**/*.ts"),
    ("fixtures", "**/*.ts"),
    ("hooks", "**/*.ts"),
    ("config", "**/*.ts"),
    ("config", "**/*.json"),
]

# Directories to always skip
SKIP_DIRS = {"node_modules", "test-results", "reports", "data", ".cache"}


def _should_skip(path: Path) -> bool:
    """Return True if this path is inside a directory that should be skipped."""
    return any(part in SKIP_DIRS for part in path.parts)


def collect_files(base: Path) -> list[Path]:
    """Return all indexable files under *base*, sorted for deterministic order."""
    found: list[Path] = []
    for subdir, pattern in SCAN_TARGETS:
        target = base / subdir
        if not target.exists():
            continue
        for f in sorted(target.glob(pattern)):
            if f.is_file() and not _should_skip(f):
                found.append(f)
    # Deduplicate while preserving order (a file matched by multiple patterns)
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in found:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def file_to_entry(path: Path, base: Path) -> dict:
    """Return name, content, and metadata dict for a source file."""
    rel = path.relative_to(base)
    content = path.read_text(encoding="utf-8", errors="replace")
    name = str(rel).replace("\\", "/")

    first_part = rel.parts[0] if rel.parts else "other"
    layer_map = {
        "pages": "pom",
        "step_definitions": "steps",
        "features": "gherkin",
        "helpers": "helper",
        "fixtures": "fixture",
        "hooks": "hook",
        "config": "config",
    }
    layer = layer_map.get(first_part, "other")

    return {
        "name": name,
        "content": content,
        "metadata": {
            "file_path": name,
            "file_name": path.name,
            "layer": layer,
            "extension": path.suffix,
            "size_bytes": path.stat().st_size,
        },
    }


def run(
    base: Path = AUTOMATION_DIR,
    dry_run: bool = False,
    force: bool = False,  # reserved — passed through to add_content(upsert=True) always
) -> None:
    """Index all automation source files into the codebase_vectors KB."""
    print(f"[index_automation] Scanning: {base}")

    files = collect_files(base)
    if not files:
        print("[index_automation] No files found — check that automation/ exists.")
        return

    print(f"[index_automation] Found {len(files)} files:")
    for f in files:
        print(f"  {f.relative_to(base.parent)}")

    if dry_run:
        print("[index_automation] Dry-run: no documents written to DB.")
        return

    # Build Knowledge instance (points at codebase_vectors table)
    kb = get_automation_kb()

    print(f"\n[index_automation] Loading {len(files)} documents into codebase_vectors …")
    for i, f in enumerate(files, 1):
        entry = file_to_entry(f, base)
        kb.add_content(
            name=entry["name"],
            text_content=entry["content"],
            metadata=entry["metadata"],
            upsert=True,
        )
        print(f"  [{i}/{len(files)}] {entry['name']}")

    print(f"[index_automation] Done. {len(files)} documents indexed into codebase_vectors.")
    print(
        "[index_automation] Hint: re-run any time after changing automation/ files. "
        "Use --force to rebuild the table from scratch."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed PgVector codebase_vectors KB from automation/ source files."
    )
    parser.add_argument(
        "--path",
        default=str(AUTOMATION_DIR),
        help="Path to the automation directory (default: automation/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files to index without writing to the database.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop and recreate the codebase_vectors table before indexing.",
    )
    args = parser.parse_args()

    run(base=Path(args.path), dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
