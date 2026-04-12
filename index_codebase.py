"""
Index Codebase Script
=====================

This script scans the test codebase (Page Objects and Step Definitions)
and vectorizes them into the PgVector knowledge base for semantic search.
"""

from pathlib import Path

from agno.knowledge import Knowledge

from db.session import get_codebase_knowledge


def scan_page_objects() -> list[dict]:
    """Scan Page Object files from automation/pages/."""
    pages_dir = Path("automation/pages")
    documents = []

    for file_path in pages_dir.glob("*.ts"):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        documents.append({
            "name": f"PageObject: {file_path.name}",
            "content": content,
            "meta_data": {
                "type": "page_object",
                "file_path": str(file_path),
                "language": "typescript",
            }
        })
    
    return documents


def scan_step_definitions() -> list[dict]:
    """Scan Step Definition files from automation/step_definitions/."""
    steps_dir = Path("automation/step_definitions")
    documents = []

    for file_path in steps_dir.glob("*.ts"):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        documents.append({
            "name": f"StepDefinition: {file_path.name}",
            "content": content,
            "meta_data": {
                "type": "step_definition",
                "file_path": str(file_path),
                "language": "typescript",
            }
        })
    
    return documents


def index_codebase():
    """Index the test codebase into PgVector."""
    knowledge: Knowledge = get_codebase_knowledge()
    
    # Scan all codebase files
    documents = []
    documents.extend(scan_page_objects())
    documents.extend(scan_step_definitions())
    
    print(f"Found {len(documents)} codebase files to index")
    
    # Add documents to knowledge base
    for doc in documents:
        print(f"  - {doc['name']}")
        knowledge.insert(
            name=doc["name"],
            text_content=doc["content"],
            metadata=doc["meta_data"],
        )
    
    print(f"\n✓ Indexed {len(documents)} files to codebase_vectors table")


if __name__ == "__main__":
    index_codebase()
