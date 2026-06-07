import pytest
from pydantic import ValidationError
from schemas import SystemExtraction, SystemInventory

def test_valid_system_extraction_high_confidence():
    """Verify that a valid system extraction with high confidence is parsed successfully."""
    system = SystemExtraction(
        name="Salesforce",
        category="CRM",
        auth_method="OAuth2",
        key_entities=["Customer", "Lead"],
        business_processes=["Lead-to-Cash"],
        criticality="High",
        confidence_score=98,
        inferred_notes="",
        source_reference="Wiki page 1"
    )
    assert system.name == "Salesforce"
    assert system.criticality == "High"
    assert system.confidence_score == 98
    assert system.inferred_notes == ""

def test_valid_system_extraction_low_confidence():
    """Verify that a valid system extraction with lower confidence and inferred notes succeeds."""
    system = SystemExtraction(
        name="Jira",
        category="Project Management",
        auth_method="SAML",
        key_entities=["Ticket"],
        business_processes=["SDLC"],
        criticality="Medium",
        confidence_score=80,
        inferred_notes="Inferred SAML from SSO wiki page.",
        source_reference="Dev onboarding doc"
    )
    assert system.confidence_score == 80
    assert system.inferred_notes == "Inferred SAML from SSO wiki page."

def test_invalid_confidence_score_range():
    """Verify that confidence score must be between 0 and 100."""
    with pytest.raises(ValidationError) as excinfo:
        SystemExtraction(
            name="Jira",
            category="Project Management",
            auth_method="SAML",
            criticality="Medium",
            confidence_score=150,  # Invalid (>100)
            inferred_notes="Too high",
            source_reference="Dev onboarding doc"
        )
    assert "Confidence score must be an integer between 0 and 100" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        SystemExtraction(
            name="Jira",
            category="Project Management",
            auth_method="SAML",
            criticality="Medium",
            confidence_score=-10,  # Invalid (<0)
            inferred_notes="Too low",
            source_reference="Dev onboarding doc"
        )
    assert "Confidence score must be an integer between 0 and 100" in str(excinfo.value)

def test_missing_inferred_notes_for_low_confidence():
    """Verify that a system with confidence < 95 must have non-empty inferred_notes."""
    with pytest.raises(ValidationError) as excinfo:
        SystemExtraction(
            name="Jira",
            category="Project Management",
            auth_method="SAML",
            criticality="Medium",
            confidence_score=85,  # <95 requires inferred_notes
            inferred_notes="",    # Invalid (empty)
            source_reference="Dev onboarding doc"
        )
    assert "inferred_notes is required" in str(excinfo.value)

def test_criticality_normalization_and_validation():
    """Verify that criticality is normalized and validates only valid choices."""
    # Test valid choice lowercase normalization
    system = SystemExtraction(
        name="Salesforce",
        category="CRM",
        auth_method="OAuth2",
        criticality="medium",  # lowercase
        confidence_score=98,
        inferred_notes="",
        source_reference="Doc"
    )
    assert system.criticality == "Medium"  # Capitalized by validator

    # Test invalid choice
    with pytest.raises(ValidationError) as excinfo:
        SystemExtraction(
            name="Salesforce",
            category="CRM",
            auth_method="OAuth2",
            criticality="Crucial",  # Invalid choice
            confidence_score=98,
            inferred_notes="",
            source_reference="Doc"
        )
    assert "Criticality must be one of: High, Medium, Low" in str(excinfo.value)

def test_empty_string_fields():
    """Verify that required string fields cannot be empty or only whitespace."""
    with pytest.raises(ValidationError) as excinfo:
        SystemExtraction(
            name="   ",  # Whitespace only
            category="CRM",
            auth_method="OAuth2",
            criticality="High",
            confidence_score=98,
            inferred_notes="",
            source_reference="Doc"
        )
    assert "String fields must not be empty or whitespace only" in str(excinfo.value)

def test_system_inventory_container():
    """Verify the SystemInventory container schema parsing."""
    inventory = SystemInventory(systems=[
        SystemExtraction(
            name="Salesforce",
            category="CRM",
            auth_method="OAuth2",
            criticality="High",
            confidence_score=98,
            inferred_notes="",
            source_reference="Doc"
        )
    ])
    assert len(inventory.systems) == 1
    assert inventory.systems[0].name == "Salesforce"
