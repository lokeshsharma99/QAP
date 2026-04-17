"""
Test Deletion Approval Contract
==============================

Pydantic models for test scenario deletion with HITL approval.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DeletionReason(str, Enum):
    """Reason for test deletion."""
    FEATURE_REMOVED = "feature_removed"
    DUPLICATE_TEST = "duplicate_test"
    OBSOLETE_FUNCTIONALITY = "obsolete_functionality"
    TEST_COVERAGE_REDUNDANT = "test_coverage_redundant"
    AUT_STRUCTURE_CHANGED = "aut_structure_changed"
    OTHER = "other"


class ApprovalStatus(str, Enum):
    """Approval status for test deletion."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TestDeletionRequest(BaseModel):
    """Request to delete a test scenario with justification."""
    
    test_type: str = Field(
        ...,
        description="Type of test: 'feature_scenario', 'step_definition', 'page_object', 'fixture'"
    )
    file_path: str = Field(..., description="Path to the test file to delete")
    scenario_name: Optional[str] = Field(None, description="Name of the scenario (for feature files)")
    reason: DeletionReason = Field(..., description="Reason for deletion")
    justification: str = Field(..., description="Detailed justification for deletion")
    affected_features: list[str] = Field(
        default_factory=list,
        description="AUT features that were removed or changed"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for deletion recommendation (0.0-1.0)"
    )
    detection_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when obsolescence was detected"
    )
    detected_by: str = Field(
        default="curator",
        description="Agent that detected the obsolescence"
    )


class TestDeletionApproval(BaseModel):
    """Approval status for test deletion request."""
    
    request_id: str = Field(..., description="Unique identifier for the deletion request")
    request: TestDeletionRequest = Field(..., description="The deletion request")
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Current approval status"
    )
    reviewer: Optional[str] = Field(None, description="Human reviewer who approved/rejected")
    review_timestamp: Optional[datetime] = Field(None, description="Timestamp of review")
    review_comments: Optional[str] = Field(None, description="Reviewer comments")
    auto_approved: bool = Field(
        default=False,
        description="Whether the deletion was auto-approved (confidence ≥ threshold)"
    )
    execution_timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp when deletion was executed"
    )


class TestDeletionAudit(BaseModel):
    """Audit trail entry for test deletion."""
    
    request_id: str = Field(..., description="Unique identifier for the deletion request")
    approval: TestDeletionApproval = Field(..., description="Approval details")
    deleted_file_path: str = Field(..., description="Path to the deleted file")
    deletion_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when deletion was executed"
    )
    deletion_method: str = Field(
        default="curator",
        description="Agent/method that performed the deletion"
    )
    backup_created: bool = Field(
        default=False,
        description="Whether a backup was created before deletion"
    )
    backup_path: Optional[str] = Field(None, description="Path to backup file if created")


class ObsolescenceReport(BaseModel):
    """Report of obsolete tests detected in the regression suite."""
    
    report_id: str = Field(..., description="Unique identifier for the report")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")
    site_manifesto_version: Optional[str] = Field(
        None,
        description="Version of Site Manifesto used for comparison"
    )
    obsolete_scenarios: list[TestDeletionRequest] = Field(
        default_factory=list,
        description="List of obsolete test scenarios"
    )
    obsolete_steps: list[TestDeletionRequest] = Field(
        default_factory=list,
        description="List of obsolete step definitions"
    )
    orphaned_pages: list[TestDeletionRequest] = Field(
        default_factory=list,
        description="List of orphaned Page Objects"
    )
    stale_fixtures: list[TestDeletionRequest] = Field(
        default_factory=list,
        description="List of stale test fixtures"
    )
    total_recommendations: int = Field(
        default=0,
        description="Total number of deletion recommendations"
    )
    high_confidence_count: int = Field(
        default=0,
        description="Number of recommendations with confidence ≥0.9"
    )


class BatchTestDeletionApproval(BaseModel):
    """Batch approval status for multiple test deletion requests."""
    
    batch_id: str = Field(..., description="Unique identifier for the batch deletion request")
    requests: list[TestDeletionRequest] = Field(
        ...,
        description="List of test deletion requests in this batch"
    )
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Current batch approval status"
    )
    reviewer: Optional[str] = Field(None, description="Human reviewer who approved/rejected the batch")
    review_timestamp: Optional[datetime] = Field(None, description="Timestamp of batch review")
    review_comments: Optional[str] = Field(None, description="Reviewer comments for the batch")
    auto_approved: bool = Field(
        default=False,
        description="Whether the batch was auto-approved (all items ≥ threshold)"
    )
    total_count: int = Field(
        ...,
        description="Total number of deletion requests in the batch"
    )
    high_confidence_count: int = Field(
        ...,
        description="Number of requests with confidence ≥0.9"
    )
    low_confidence_count: int = Field(
        ...,
        description="Number of requests with confidence <0.9"
    )
    batch_summary: str = Field(
        ...,
        description="Human-readable summary of the batch (e.g., '15 test cases: 12 high-confidence, 3 require review')"
    )
    execution_timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp when batch deletion was executed"
    )
