# contracts/__init__.py
"""Pydantic contracts for all agent hand-offs."""

from contracts.automation_scaffold import AutomationScaffold
from contracts.execution_result import ExecutionResult, ScenarioResult
from contracts.gherkin_spec import DataRequirement, GherkinSpec
from contracts.grooming_assessment import CriterionScore, GroomingAssessment
from contracts.healing_patch import HealingPatch
from contracts.impact_report import ImpactReport, TestGap
from contracts.judge_verdict import JudgeVerdict
from contracts.pipeline_rca_report import FailedJob, PipelineRCAReport, RemediationStep
from contracts.rca_report import RCAReport
from contracts.requirement_context import AcceptanceCriterion, LinkedRequirement, RequirementContext
from contracts.run_context import RunContext, TestUser
from contracts.site_manifesto import PageEntry, SiteManifesto, UIComponent
from contracts.squad_handoff import SquadHandoff
from contracts.test_deletion_approval import ObsolescenceReport, TestDeletionApproval, TestDeletionAudit, TestDeletionRequest
from contracts.workflow_inputs import DiscoveryInput, ImpactAssessmentInput, JiraTicketInput, PipelineFailureInput, TriageInput
from contracts.workflow_status import StepStatus, WorkflowStatus

__all__ = [
    # Phase 0.5
    "SiteManifesto",
    "PageEntry",
    "UIComponent",
    # Phase 2
    "AcceptanceCriterion",
    "LinkedRequirement",
    "RequirementContext",
    "DataRequirement",
    "GherkinSpec",
    "JudgeVerdict",
    # Phase 3
    "RunContext",
    "TestUser",
    "ExecutionResult",
    "ScenarioResult",
    "AutomationScaffold",
    # Phase 4
    "RCAReport",
    "HealingPatch",
    # Phase 5 — Impact Analysis
    "ImpactReport",
    "TestGap",
    # Phase 5 — Pipeline RCA
    "PipelineRCAReport",
    "RemediationStep",
    "FailedJob",
    # Phase 5 — Grooming
    "CriterionScore",
    "GroomingAssessment",
    # Curator — Test Deletion
    "TestDeletionRequest",
    "TestDeletionApproval",
    "TestDeletionAudit",
    "ObsolescenceReport",
    # Workflow orchestration
    "JiraTicketInput",
    "TriageInput",
    "DiscoveryInput",
    "ImpactAssessmentInput",
    "PipelineFailureInput",
    "StepStatus",
    "WorkflowStatus",
    # Inter-squad
    "SquadHandoff",
]
