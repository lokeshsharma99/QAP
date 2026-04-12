"""
Gherkin Spec Contract
======================

Pydantic models for the Scribe Agent's output.
The GherkinSpec represents a BDD specification in Gherkin format,
including scenarios, data requirements, and traceability to the source ticket.
"""

from enum import Enum

from pydantic import BaseModel, Field


class DataType(str, Enum):
    """Supported data types for test data."""

    STRING = "string"
    NUMBER = "number"
    EMAIL = "email"
    URL = "url"
    DATE = "date"
    BOOLEAN = "boolean"
    ENUM = "enum"


class DataRequirement(BaseModel):
    """A data requirement for a test scenario."""

    field_name: str = Field(description="Name of the data field (e.g., 'username', 'email')")
    data_type: DataType = Field(description="Data type of the field")
    example_value: str = Field(description="Example value for this field")
    source: str = Field(
        default="",
        description="Source of this data requirement (e.g., 'ticket description', 'Page Object field')"
    )
    is_required: bool = Field(
        default=True,
        description="Whether this data field is required for the test"
    )


class StepType(str, Enum):
    """Gherkin step types."""

    GIVEN = "Given"
    WHEN = "When"
    THEN = "Then"
    AND = "And"
    BUT = "But"


class GherkinStep(BaseModel):
    """A single Gherkin step."""

    step_type: StepType = Field(description="Step type (Given, When, Then, And, But)")
    text: str = Field(description="Step text in natural language")
    is_reusable: bool = Field(
        default=True,
        description="Whether this step is reusable across scenarios"
    )


class GherkinScenario(BaseModel):
    """A single Gherkin scenario."""

    name: str = Field(description="Scenario name")
    description: str = Field(default="", description="Optional scenario description")
    steps: list[GherkinStep] = Field(
        default_factory=list,
        description="List of Gherkin steps in this scenario"
    )
    data_requirements: list[DataRequirement] = Field(
        default_factory=list,
        description="Data requirements specific to this scenario"
    )


class GherkinSpec(BaseModel):
    """Complete BDD specification in Gherkin format.

    Produced by the Scribe Agent from a RequirementContext.
    Used by the Engineer Agent to generate test code.
    """

    feature_name: str = Field(description="Feature name (e.g., 'User Authentication')")
    feature_description: str = Field(description="Feature description in business language")
    scenarios: list[GherkinScenario] = Field(
        default_factory=list,
        description="List of scenarios in this feature"
    )
    data_requirements: list[DataRequirement] = Field(
        default_factory=list,
        description="Global data requirements for this feature"
    )
    traceability: dict[str, str] = Field(
        default_factory=dict,
        description="Traceability mapping (e.g., {'ticket_id': 'QA-123', 'requirement_context_id': '...'})"
    )
    file_path: str = Field(
        default="",
        description="Target file path for the .feature file (e.g., 'automation/features/user-authentication.feature')"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Gherkin tags for this feature (e.g., ['@smoke', '@regression'])"
    )
