from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class SystemExtraction(BaseModel):
    """
    Represents a single software system extracted from corporate documentation.
    """
    name: str = Field(
        ..., 
        description="The formal or recognized name of the software system (e.g., Salesforce, NetSuite, Coupa)."
    )
    category: str = Field(
        ..., 
        description="The functional category of the system (e.g., CRM, ERP, HRIS, Database, Billing, Procurement)."
    )
    auth_method: str = Field(
        ..., 
        description="The authentication method used by the system (e.g., OAuth2, API Key, Basic Auth, SAML, Unknown)."
    )
    key_entities: List[str] = Field(
        default_factory=list,
        description="List of key data entities or objects stored/processed in this system (e.g., Customer, Invoice, Ledger, Lead)."
    )
    business_processes: List[str] = Field(
        default_factory=list,
        description="List of business processes or workflows supported by this system (e.g., Lead-to-Cash, Procure-to-Pay, Financial Reporting)."
    )
    criticality: str = Field(
        ..., 
        description="The operational criticality of the system. Must be one of: High, Medium, Low."
    )
    confidence_score: int = Field(
        ..., 
        description="Self-assessed confidence score (0-100). Rules: 95+ for explicit mentions with solid evidence; 70-90 for inferred systems with missing details; <70 for uncertain mentions requiring human review."
    )
    inferred_notes: str = Field(
        default="",
        description="Mandatory explanation of what details are missing and what assumptions were made if confidence_score is below 95. Empty string if 95+."
    )
    source_reference: str = Field(
        ..., 
        description="A direct quote, page number, file name, or section reference from the document supporting the existence of this system."
    )

    @field_validator("name", "category", "auth_method", "criticality", "source_reference")
    @classmethod
    def check_non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("String fields must not be empty or whitespace only")
        return v.strip()

    @field_validator("confidence_score")
    @classmethod
    def check_confidence_range(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError("Confidence score must be an integer between 0 and 100")
        return v

    @field_validator("criticality")
    @classmethod
    def validate_criticality(cls, v: str) -> str:
        valid_criticality = {"high", "medium", "low"}
        if v.lower() not in valid_criticality:
            raise ValueError("Criticality must be one of: High, Medium, Low")
        return v.capitalize()

    @model_validator(mode="after")
    def validate_confidence_notes(self) -> "SystemExtraction":
        if self.confidence_score < 95 and not self.inferred_notes.strip():
            raise ValueError(
                f"For confidence score {self.confidence_score} (< 95), inferred_notes is required "
                f"to explain what was inferred and what evidence was missing."
            )
        return self


class SystemInventory(BaseModel):
    """
    Container for list of extracted systems.
    """
    systems: List[SystemExtraction] = Field(
        default_factory=list,
        description="A list of all extracted software systems from the documents."
    )
