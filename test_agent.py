import logging
import pytest
from schemas import SystemInventory, SystemExtraction
from agent import validate_inventory

def test_validate_inventory_clears_notes_for_high_confidence(caplog):
    """Verify that validate_inventory clears inferred_notes for confidence >= 95 and logs details."""
    system = SystemExtraction(
        name="Salesforce",
        category="CRM",
        auth_method="OAuth2",
        criticality="High",
        confidence_score=97,
        inferred_notes="Should be cleared",
        source_reference="Doc A"
    )
    inventory = SystemInventory(systems=[system])
    
    with caplog.at_level(logging.WARNING, logger="discovery_agent"):
        validated = validate_inventory(inventory)
        
    assert len(validated.systems) == 1
    assert validated.systems[0].inferred_notes == ""
    # Verify warning log was triggered
    assert any("cleared inferred_notes" in record.message.lower() for record in caplog.records)

def test_validate_inventory_flags_low_confidence(caplog):
    """Verify that validate_inventory logs an explicit audit warning for confidence < 70."""
    system = SystemExtraction(
        name="Coupa",
        category="Procurement",
        auth_method="Unknown",
        criticality="Medium",
        confidence_score=50,
        inferred_notes="Mentioned once in passing; sandbox existence unclear.",
        source_reference="Chat logs"
    )
    inventory = SystemInventory(systems=[system])
    
    with caplog.at_level(logging.WARNING, logger="discovery_agent"):
        validated = validate_inventory(inventory)
        
    assert len(validated.systems) == 1
    # Verify low-confidence warning log was triggered
    warnings = [record.message for record in caplog.records if record.levelname == "WARNING"]
    assert any("LOW confidence" in msg for msg in warnings)
    assert any("Coupa" in msg for msg in warnings)

def test_validate_inventory_logs_medium_confidence(caplog):
    """Verify that medium confidence systems are logged with inference notes and no warning logs."""
    system = SystemExtraction(
        name="Jira",
        category="Project Management",
        auth_method="SAML",
        criticality="Medium",
        confidence_score=85,
        inferred_notes="Inferred SAML from SSO doc.",
        source_reference="Doc B"
    )
    inventory = SystemInventory(systems=[system])
    
    with caplog.at_level(logging.INFO, logger="discovery_agent"):
        validated = validate_inventory(inventory)
        
    assert len(validated.systems) == 1
    # Verify info level logs exist for SAML inference notes
    info_logs = [record.message for record in caplog.records if record.levelname == "INFO"]
    assert any("Inferred SAML from SSO doc." in msg for msg in info_logs)
    
    # Assert no warning logs were generated
    warning_logs = [record.message for record in caplog.records if record.levelname == "WARNING"]
    assert len(warning_logs) == 0
