"""
Healing Patch Contract
======================

Represents a surgical edit to fix a broken locator.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class HealingPatch(BaseModel):
    """Represents a surgical edit to fix a broken locator."""
    
    # Locator information
    old_locator: str = Field(description="The original locator that failed")
    new_locator: str = Field(description="The new locator to replace it with")
    
    # File information
    file_path: str = Field(description="Path to the file containing the locator")
    page_name: str = Field(description="Name of the Page Object class")
    line_number: Optional[int] = Field(default=None, description="Line number of the locator")
    
    # Diff information
    diff: str = Field(description="Unified diff showing the change")
    
    # Validation
    logic_changed: bool = Field(default=False, description="Whether logic was changed (must be False)")
    verification_passes: int = Field(description="Number of verification passes (must be ≥3)", ge=0)
    
    # Verification results
    verification_results: List[bool] = Field(default_factory=list, description="Results of verification runs")
    
    # Metadata
    timestamp: str = Field(description="Timestamp when the patch was created")
    agent_id: str = Field(description="ID of the agent that created the patch")
    rca_report_id: Optional[str] = Field(default=None, description="ID of the RCA report that led to this patch")
    
    # Status
    status: str = Field(default="pending", description="Status of the patch: pending, applied, rejected")
    pr_url: Optional[str] = Field(default=None, description="URL of the PR if created")
    
    class Config:
        json_schema_extra = {
            "example": {
                "old_locator": "button[name=\"continue\"]",
                "new_locator": "page.getByRole('button', {name: /continue/i})",
                "file_path": "automation/pages/UniversalCreditPersonalDetailsPage.ts",
                "page_name": "UniversalCreditPersonalDetailsPage",
                "line_number": 29,
                "diff": "@@ -27 +27 @@\n-    this.continueButton = page.locator('button[name=\"continue\"]');\n+    this.continueButton = page.getByRole('button', {name: /continue/i});",
                "logic_changed": False,
                "verification_passes": 3,
                "verification_results": [True, True, True],
                "timestamp": "2025-04-13T01:35:00Z",
                "agent_id": "medic",
                "rca_report_id": "rca-001",
                "status": "pending",
                "pr_url": None
            }
        }
    
    def is_valid(self) -> bool:
        """Check if the patch meets all validation criteria."""
        return (
            not self.logic_changed and
            self.verification_passes >= 3 and
            all(self.verification_results) and
            self.old_locator != self.new_locator
        )
