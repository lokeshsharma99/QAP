"""
Squad Handoff Contract
======================

Pydantic models for inter-squad communication and hand-offs.
The SquadHandoff represents the structured data passed between squads
during workflow execution, ensuring clear contract-based communication.
"""

from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


class SquadName(str, Enum):
    """Names of the squads in Quality Autopilot."""

    STRATEGY = "strategy"
    CONTEXT = "context"
    ENGINEERING = "engineering"
    OPERATIONS = "operations"
    GROOMING = "grooming"


class HandoffStatus(str, Enum):
    """Status of a hand-off between squads."""

    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"


class SquadHandoff(BaseModel):
    """Structured hand-off data passed between squads.

    Used for inter-squad communication in workflows.
    Ensures contract-based data passing with clear traceability.
    """

    handoff_id: str = Field(description="Unique identifier for this hand-off")
    from_squad: SquadName = Field(description="Squad sending the hand-off")
    to_squad: SquadName = Field(description="Squad receiving the hand-off")
    workflow_id: str = Field(description="ID of the workflow this hand-off belongs to")
    workflow_run_id: str = Field(description="ID of the workflow run")
    status: HandoffStatus = Field(default=HandoffStatus.PENDING, description="Status of the hand-off")
    
    # Contract information
    contract_type: str = Field(description="Type of contract being handed off (e.g., 'RequirementContext', 'GherkinSpec')")
    contract_data: dict = Field(
        default_factory=dict,
        description="The contract data being handed off (serialized contract)"
    )
    contract_version: str = Field(default="1.0", description="Version of the contract schema")
    
    # Timing
    created_at: str = Field(description="ISO 8601 timestamp when hand-off was created")
    sent_at: str = Field(default="", description="ISO 8601 timestamp when hand-off was sent")
    received_at: str = Field(default="", description="ISO 8601 timestamp when hand-off was received")
    completed_at: str = Field(default="", description="ISO 8601 timestamp when hand-off was completed")
    
    # Validation
    validation_passed: bool = Field(default=True, description="Whether contract validation passed")
    validation_errors: list[str] = Field(
        default_factory=list,
        description="List of validation errors if validation failed"
    )
    
    # Metadata
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata for the hand-off"
    )
    notes: str = Field(default="", description="Additional notes for the receiving squad")

    class Config:
        json_schema_extra = {
            "example": {
                "handoff_id": "handoff-001",
                "from_squad": "strategy",
                "to_squad": "engineering",
                "workflow_id": "full_lifecycle",
                "workflow_run_id": "run-123",
                "status": "in_transit",
                "contract_type": "GherkinSpec",
                "contract_data": {
                    "feature_name": "User Authentication",
                    "scenarios": [...]
                },
                "contract_version": "1.0",
                "created_at": "2025-04-13T10:00:00Z",
                "sent_at": "2025-04-13T10:00:05Z",
                "received_at": "",
                "completed_at": "",
                "validation_passed": True,
                "validation_errors": [],
                "metadata": {},
                "notes": "Gherkin spec ready for implementation"
            }
        }
