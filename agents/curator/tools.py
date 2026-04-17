"""
Curator Agent Tools
===================

Tools for the Curator agent including HITL approval workflow for test deletion.
"""

import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools
from agno.utils.log import logger

from app.settings import AUTO_APPROVE_CONFIDENCE_THRESHOLD
from contracts.test_deletion_approval import (
    ApprovalStatus,
    BatchTestDeletionApproval,
    DeletionReason,
    TestDeletionApproval,
    TestDeletionAudit,
    TestDeletionRequest,
)
from db.session import get_automation_knowledge


# ---------------------------------------------------------------------------
# HITL Approval Tools
# ---------------------------------------------------------------------------
def request_deletion_approval(
    test_type: str,
    file_path: str,
    scenario_name: Optional[str],
    reason: DeletionReason,
    justification: str,
    affected_features: list[str],
    confidence_score: float,
) -> str:
    """Request HITL approval for test deletion.

    Args:
        test_type: Type of test (feature_scenario, step_definition, page_object, fixture)
        file_path: Path to the test file
        scenario_name: Name of the scenario (for feature files)
        reason: Reason for deletion
        justification: Detailed justification
        affected_features: AUT features that were removed or changed
        confidence_score: Confidence score (0.0-1.0)

    Returns:
        Status message with request ID and approval status
    """
    request_id = str(uuid.uuid4())

    # Create deletion request
    request = TestDeletionRequest(
        test_type=test_type,
        file_path=file_path,
        scenario_name=scenario_name,
        reason=reason,
        justification=justification,
        affected_features=affected_features,
        confidence_score=confidence_score,
        detection_timestamp=datetime.utcnow(),
        detected_by="curator",
    )

    # Check if auto-approval threshold is met
    auto_approve = confidence_score >= AUTO_APPROVE_CONFIDENCE_THRESHOLD

    # Create approval
    approval = TestDeletionApproval(
        request_id=request_id,
        request=request,
        status=ApprovalStatus.APPROVED if auto_approve else ApprovalStatus.PENDING,
        auto_approved=auto_approve,
    )

    if auto_approve:
        logger.info(f"Auto-approved deletion request {request_id} (confidence: {confidence_score:.2f} ≥ {AUTO_APPROVE_CONFIDENCE_THRESHOLD})")
        approval.review_timestamp = datetime.utcnow()
        approval.reviewer = "auto-approve"
    else:
        logger.info(f"HITL approval required for deletion request {request_id} (confidence: {confidence_score:.2f} < {AUTO_APPROVE_CONFIDENCE_THRESHOLD})")

    return f"Deletion request {request_id} created. Status: {approval.status.value} (auto-approved: {auto_approve})"


def request_batch_deletion_approval(
    requests: list[TestDeletionRequest],
) -> str:
    """Request HITL approval for batch test deletion.

    Args:
        requests: List of TestDeletionRequest objects for batch approval

    Returns:
        Status message with batch ID, approval status, and test case count
    """
    batch_id = str(uuid.uuid4())

    # Calculate batch statistics
    total_count = len(requests)
    high_confidence_count = sum(1 for r in requests if r.confidence_score >= AUTO_APPROVE_CONFIDENCE_THRESHOLD)
    low_confidence_count = total_count - high_confidence_count

    # Generate batch summary
    batch_summary = f"{total_count} test case(s): {high_confidence_count} high-confidence, {low_confidence_count} require review"

    # Check if all items meet auto-approval threshold
    auto_approve = low_confidence_count == 0 and total_count > 0

    # Create batch approval
    batch_approval = BatchTestDeletionApproval(
        batch_id=batch_id,
        requests=requests,
        status=ApprovalStatus.APPROVED if auto_approve else ApprovalStatus.PENDING,
        auto_approved=auto_approve,
        total_count=total_count,
        high_confidence_count=high_confidence_count,
        low_confidence_count=low_confidence_count,
        batch_summary=batch_summary,
    )

    if auto_approve:
        logger.info(f"Auto-approved batch deletion {batch_id} ({batch_summary})")
        batch_approval.review_timestamp = datetime.utcnow()
        batch_approval.reviewer = "auto-approve"
    else:
        logger.info(f"HITL approval required for batch deletion {batch_id} ({batch_summary})")
        # In a real implementation, this would trigger OnError.pause with the batch summary

    return f"Batch deletion request {batch_id} created. Status: {batch_approval.status.value}. {batch_summary} (auto-approved: {auto_approve})"


def approve_deletion(request_id: str, reviewer: str, comments: Optional[str]) -> str:
    """Approve a test deletion request.

    Args:
        request_id: Unique identifier for the deletion request
        reviewer: Human reviewer name
        comments: Reviewer comments

    Returns:
        Status message
    """
    # In a real implementation, this would load the approval from storage
    logger.info(f"Deletion request {request_id} approved by {reviewer}")
    if comments:
        logger.info(f"Reviewer comments: {comments}")

    return f"Deletion request {request_id} approved by {reviewer}"


def reject_deletion(request_id: str, reviewer: str, comments: Optional[str]) -> str:
    """Reject a test deletion request.

    Args:
        request_id: Unique identifier for the deletion request
        reviewer: Human reviewer name
        comments: Reviewer comments

    Returns:
        Status message
    """
    # In a real implementation, this would load the approval from storage
    logger.info(f"Deletion request {request_id} rejected by {reviewer}")
    if comments:
        logger.info(f"Reviewer comments: {comments}")

    return f"Deletion request {request_id} rejected by {reviewer}"


# ---------------------------------------------------------------------------
# Deletion Execution Tools
# ---------------------------------------------------------------------------
def execute_test_deletion(
    file_path: str,
    create_backup: bool = True,
    backup_dir: str = "automation/backups/deleted",
) -> str:
    """Execute deletion of a test file.

    Args:
        file_path: Path to the test file to delete
        create_backup: Whether to create a backup before deletion
        backup_dir: Directory for backups

    Returns:
        Status message
    """
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        return f"File not found: {file_path}"

    # Create backup if requested
    if create_backup:
        backup_path_obj = Path(backup_dir)
        backup_path_obj.mkdir(parents=True, exist_ok=True)

        backup_file = backup_path_obj / f"{file_path_obj.name}.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.bak"
        shutil.copy2(file_path_obj, backup_file)
        logger.info(f"Backup created: {backup_file}")

    # Delete the file
    file_path_obj.unlink()
    logger.info(f"Deleted test file: {file_path}")

    return f"Successfully deleted: {file_path} (backup: {create_backup})"


def delete_scenario_from_feature(
    file_path: str,
    scenario_name: str,
    create_backup: bool = True,
    backup_dir: str = "automation/backups/deleted",
) -> str:
    """Delete a specific scenario from a feature file.

    Args:
        file_path: Path to the feature file
        scenario_name: Name of the scenario to delete
        create_backup: Whether to create a backup before deletion
        backup_dir: Directory for backups

    Returns:
        Status message
    """
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        return f"File not found: {file_path}"

    # Create backup if requested
    if create_backup:
        backup_path_obj = Path(backup_dir)
        backup_path_obj.mkdir(parents=True, exist_ok=True)

        backup_file = backup_path_obj / f"{file_path_obj.name}.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.bak"
        shutil.copy2(file_path_obj, backup_file)
        logger.info(f"Backup created: {backup_file}")

    # Read and modify the file
    content = file_path_obj.read_text()
    lines = content.split("\n")

    # Find and remove the scenario
    in_scenario = False
    scenario_start = -1
    scenario_end = -1
    indent_level = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("Scenario:") and scenario_name in stripped:
            in_scenario = True
            scenario_start = i
            indent_level = len(line) - len(line.lstrip())
        elif in_scenario:
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level and stripped and not stripped.startswith("#"):
                scenario_end = i
                break

    if scenario_start == -1:
        return f"Scenario not found: {scenario_name}"

    # Remove the scenario (or mark as obsolete)
    if scenario_end == -1:
        # Scenario is at the end of file
        lines = lines[:scenario_start]
    else:
        lines = lines[:scenario_start] + lines[scenario_end:]

    # Write back
    file_path_obj.write_text("\n".join(lines))
    logger.info(f"Deleted scenario '{scenario_name}' from {file_path}")

    return f"Successfully deleted scenario '{scenario_name}' from {file_path}"


# ---------------------------------------------------------------------------
# Audit Trail Tools
# ---------------------------------------------------------------------------
def log_deletion_to_audit(
    request_id: str,
    approval: TestDeletionApproval,
    deleted_file_path: str,
    backup_created: bool = False,
    backup_path: Optional[str] = None,
) -> str:
    """Log deletion to audit trail.

    Args:
        request_id: Unique identifier for the deletion request
        approval: Approval details
        deleted_file_path: Path to the deleted file
        backup_created: Whether a backup was created
        backup_path: Path to backup file if created

    Returns:
        Status message
    """
    audit = TestDeletionAudit(
        request_id=request_id,
        approval=approval,
        deleted_file_path=deleted_file_path,
        deletion_timestamp=datetime.utcnow(),
        deletion_method="curator",
        backup_created=backup_created,
        backup_path=backup_path,
    )

    # In a real implementation, this would save to a database or file
    logger.info(f"Audit entry created for deletion request {request_id}")
    logger.info(f"Deleted file: {deleted_file_path}")
    logger.info(f"Backup created: {backup_created}")
    logger.info(f"Approval status: {approval.status.value}")

    return f"Audit entry created for deletion request {request_id}"


# ---------------------------------------------------------------------------
# Maintenance Report Tools
# ---------------------------------------------------------------------------
def generate_maintenance_report(watch_path: str = "automation") -> str:
    """Generate a comprehensive maintenance report for the regression suite.

    Args:
        watch_path: Path to the automation directory

    Returns:
        Status message with report ID
    """
    # Use Librarian's obsolescence detection tools
    from agents.librarian.tools import generate_obsolescence_report

    report_result = generate_obsolescence_report(watch_path)
    logger.info(f"Generated maintenance report: {report_result}")

    return report_result
