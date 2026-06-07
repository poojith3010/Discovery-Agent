from typing import List
from pydantic import BaseModel, Field, field_validator, model_validator

class DataFlow(BaseModel):
    """
    Represents a specific directional data transfer between two systems for a use case.
    """
    source_system: str = Field(
        ...,
        description="The system from which the data originates (e.g., Salesforce)."
    )
    destination_system: str = Field(
        ...,
        description="The system where the data is being sent or processed (e.g., NetSuite)."
    )
    entity_type: str = Field(
        ...,
        description="The business object or entity type being transferred (e.g., Customer, Invoice, Alert Log)."
    )
    trigger_event: str = Field(
        ...,
        description="The event that initiates this data flow (e.g., Opportunity Won, High Priority Alert Raised)."
    )

    @field_validator("source_system", "destination_system", "entity_type", "trigger_event")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("String fields must not be empty or whitespace only")
        return v.strip()


class IntegrationGap(BaseModel):
    """
    Identifies a required integration connection between a source and a destination system.
    """
    source_system: str = Field(
        ...,
        description="The source system of the integration link."
    )
    destination_system: str = Field(
        ...,
        description="The destination system of the integration link."
    )
    status: str = Field(
        ...,
        description="Status of the integration. Must be 'Available' or 'Missing'."
    )
    estimated_effort: str = Field(
        ...,
        description="Rough order of magnitude effort to build/enable this integration. Must be: Low, Medium, High, Complex."
    )
    dependency_note: str = Field(
        ...,
        description="Detailed note explaining which use cases rely on this integration and any sequencing dependencies."
    )

    @field_validator("source_system", "destination_system", "dependency_note")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("String fields must not be empty or whitespace only")
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_status = {"available", "missing"}
        if v.lower() not in valid_status:
            raise ValueError("Status must be one of: Available, Missing")
        return v.capitalize()

    @field_validator("estimated_effort")
    @classmethod
    def validate_effort(cls, v: str) -> str:
        valid_efforts = {"low", "medium", "high", "complex"}
        if v.lower() not in valid_efforts:
            raise ValueError("Estimated effort must be one of: Low, Medium, High, Complex")
        return v.capitalize()


class UseCaseMapping(BaseModel):
    """
    Maps an automation use case to involved systems, data flows, and business impact.
    """
    use_case_name: str = Field(
        ...,
        description="The name or description of the automation use case."
    )
    involved_systems: List[str] = Field(
        ...,
        description="List of all software systems involved in executing this use case."
    )
    data_flows: List[DataFlow] = Field(
        default_factory=list,
        description="Step-by-step data flows required to satisfy the use case."
    )
    business_impact_score: int = Field(
        ...,
        description="Business impact score from 1 (lowest) to 10 (highest), based on frequency and criticality."
    )

    @field_validator("use_case_name")
    @classmethod
    def check_name_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("use_case_name must not be empty")
        return v.strip()

    @field_validator("involved_systems")
    @classmethod
    def check_involved_systems(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one involved system must be specified")
        cleaned = [item.strip() for item in v if item.strip()]
        if not cleaned:
            raise ValueError("involved_systems list cannot contain only empty values")
        return cleaned

    @field_validator("business_impact_score")
    @classmethod
    def check_impact_score(cls, v: int) -> int:
        if not (1 <= v <= 10):
            raise ValueError("business_impact_score must be an integer between 1 and 10")
        return v


class GapAnalysisReport(BaseModel):
    """
    Container for the final prioritized gap analysis report.
    """
    use_case_mappings: List[UseCaseMapping] = Field(
        default_factory=list,
        description="List of mapped use cases, systems, and data flows."
    )
    prioritized_gaps: List[IntegrationGap] = Field(
        default_factory=list,
        description="Prioritized list of identified integration gaps (both missing and available) sorted by business priority."
    )
