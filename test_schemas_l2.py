import pytest
from pydantic import ValidationError
from schemas_l2 import DataFlow, IntegrationGap, UseCaseMapping, GapAnalysisReport

def test_valid_data_flow():
    """Verify that a valid DataFlow parses correctly."""
    flow = DataFlow(
        source_system="Salesforce",
        destination_system="NetSuite",
        entity_type="Invoice",
        trigger_event="Opportunity Closed Won"
    )
    assert flow.source_system == "Salesforce"
    assert flow.destination_system == "NetSuite"
    assert flow.entity_type == "Invoice"
    assert flow.trigger_event == "Opportunity Closed Won"

def test_invalid_data_flow_empty_string():
    """Verify that empty strings raise ValidationError in DataFlow."""
    with pytest.raises(ValidationError) as excinfo:
        DataFlow(
            source_system="  ",  # empty
            destination_system="NetSuite",
            entity_type="Invoice",
            trigger_event="Opportunity Closed Won"
        )
    assert "String fields must not be empty or whitespace only" in str(excinfo.value)

def test_valid_integration_gap():
    """Verify that a valid IntegrationGap parses and normalizes correctly."""
    gap = IntegrationGap(
        source_system="Salesforce",
        destination_system="NetSuite",
        status="missing",             # lower case status
        estimated_effort="high",      # lower case effort
        dependency_note="Required for Opportunity sync"
    )
    assert gap.status == "Missing"           # normalized to Capitalized
    assert gap.estimated_effort == "High"    # normalized to Capitalized

def test_invalid_integration_gap_status():
    """Verify that status must be Available or Missing."""
    with pytest.raises(ValidationError) as excinfo:
        IntegrationGap(
            source_system="Salesforce",
            destination_system="NetSuite",
            status="UnknownStatus",  # invalid
            estimated_effort="High",
            dependency_note="Required"
        )
    assert "Status must be one of: Available, Missing" in str(excinfo.value)

def test_invalid_integration_gap_effort():
    """Verify that estimated_effort must be Low, Medium, High, or Complex."""
    with pytest.raises(ValidationError) as excinfo:
        IntegrationGap(
            source_system="Salesforce",
            destination_system="NetSuite",
            status="Missing",
            estimated_effort="Very Hard",  # invalid
            dependency_note="Required"
        )
    assert "Estimated effort must be one of: Low, Medium, High, Complex" in str(excinfo.value)

def test_valid_use_case_mapping():
    """Verify that a valid UseCaseMapping parses successfully."""
    mapping = UseCaseMapping(
        use_case_name="Opportunity sync",
        involved_systems=["Salesforce", "NetSuite"],
        data_flows=[
            DataFlow(
                source_system="Salesforce",
                destination_system="NetSuite",
                entity_type="Invoice",
                trigger_event="Closed Won"
            )
        ],
        business_impact_score=9
    )
    assert mapping.use_case_name == "Opportunity sync"
    assert len(mapping.involved_systems) == 2
    assert mapping.business_impact_score == 9

def test_invalid_use_case_mapping_impact_range():
    """Verify that business_impact_score must be between 1 and 10."""
    # Test above range
    with pytest.raises(ValidationError) as excinfo:
        UseCaseMapping(
            use_case_name="Opportunity sync",
            involved_systems=["Salesforce"],
            business_impact_score=11
        )
    assert "business_impact_score must be an integer between 1 and 10" in str(excinfo.value)

    # Test below range
    with pytest.raises(ValidationError) as excinfo:
        UseCaseMapping(
            use_case_name="Opportunity sync",
            involved_systems=["Salesforce"],
            business_impact_score=0
        )
    assert "business_impact_score must be an integer between 1 and 10" in str(excinfo.value)

def test_invalid_use_case_mapping_empty_systems():
    """Verify that involved_systems cannot be empty."""
    with pytest.raises(ValidationError) as excinfo:
        UseCaseMapping(
            use_case_name="Opportunity sync",
            involved_systems=[],
            business_impact_score=5
        )
    assert "At least one involved system must be specified" in str(excinfo.value)
