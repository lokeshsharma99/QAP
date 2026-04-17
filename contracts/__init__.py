"""
Contracts Package
=================

Pydantic models for agent hand-off protocols.
Every transition between agents uses a structured contract defined here.
"""

from contracts.judge_verdict import JudgeVerdict
from contracts.grooming_assessment import GroomingAssessment
from contracts.gherkin_spec import GherkinSpec
from contracts.requirement_context import RequirementContext
from contracts.run_context import RunContext, TestUser
from contracts.site_manifesto import SiteManifesto
from contracts.test_deletion_approval import (
    TestDeletionRequest,
    TestDeletionApproval,
    TestDeletionAudit,
    ObsolescenceReport,
    DeletionReason,
    ApprovalStatus,
)

__all__ = [
    "GherkinSpec",
    "GroomingAssessment",
    "JudgeVerdict",
    "RequirementContext",
    "RunContext",
    "TestUser",
    "SiteManifesto",
    "TestDeletionRequest",
    "TestDeletionApproval",
    "TestDeletionAudit",
    "ObsolescenceReport",
    "DeletionReason",
    "ApprovalStatus",
]
