"""
Workflow Status Contract
=========================

Pydantic models for workflow orchestration status tracking.
The WorkflowStatus represents the current state of a workflow execution,
including step completion, errors, and overall progress.
"""

from enum import Enum

from pydantic import BaseModel, Field


class WorkflowStepStatus(str, Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepStatus(BaseModel):
    """Status of a single workflow step."""

    step_name: str = Field(description="Name of the workflow step")
    status: WorkflowStepStatus = Field(description="Current status of the step")
    agent_id: str = Field(default="", description="ID of the agent executing this step")
    team_id: str = Field(default="", description="ID of the team executing this step")
    started_at: str = Field(default="", description="ISO 8601 timestamp when step started")
    completed_at: str = Field(default="", description="ISO 8601 timestamp when step completed")
    duration_ms: int = Field(default=0, description="Execution time in milliseconds")
    error_message: str = Field(default="", description="Error message if failed")
    output_contract: str = Field(default="", description="Contract type of step output")


class WorkflowStatus(BaseModel):
    """Complete status of a workflow execution.

    Used for tracking workflow progress and debugging failures.
    Provides visibility into step-by-step execution and hand-offs.
    """

    workflow_id: str = Field(description="ID of the workflow being executed")
    workflow_name: str = Field(description="Name of the workflow")
    run_id: str = Field(description="Unique identifier for this workflow run")
    status: WorkflowStepStatus = Field(description="Overall workflow status")
    started_at: str = Field(description="ISO 8601 timestamp when workflow started")
    completed_at: str = Field(default="", description="ISO 8601 timestamp when workflow completed")
    duration_ms: int = Field(default=0, description="Total execution time in milliseconds")
    steps: list[StepStatus] = Field(
        default_factory=list,
        description="Status of each workflow step"
    )
    current_step_index: int = Field(default=0, description="Index of currently executing step")
    total_steps: int = Field(default=0, description="Total number of steps in workflow")
    input_contract: str = Field(default="", description="Contract type of workflow input")
    output_contract: str = Field(default="", description="Contract type of workflow output")
    error_message: str = Field(default="", description="Error message if workflow failed")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata for the workflow run"
    )

    def get_progress(self) -> float:
        """Calculate progress as percentage (0-100)."""
        if self.total_steps == 0:
            return 0.0
        completed = sum(1 for step in self.steps if step.status == WorkflowStepStatus.COMPLETED)
        return (completed / self.total_steps) * 100
