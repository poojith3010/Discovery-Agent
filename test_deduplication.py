import pytest
from schemas import SystemInventory, SystemExtraction
from main import deduplicate_inventory

def test_deduplicate_inventory_merging():
    """Verify that multiple occurrences of the same system are correctly merged."""
    # 1. AWS and aws (case-insensitive deduplication)
    sys1 = SystemExtraction(
        name="AWS",
        category="Infrastructure",
        auth_method="Unknown",
        key_entities=["Server", "S3 Bucket"],
        business_processes=["Hosting", "Data Storage"],
        criticality="Medium",
        confidence_score=80,
        inferred_notes="Inferred hosting from infrastructure talk.",
        source_reference="Doc A"
    )
    
    sys2 = SystemExtraction(
        name="aws",
        category="Cloud Infrastructure",
        auth_method="IAM Role",
        key_entities=["S3 Bucket", "Lambda"],
        business_processes=["Serverless Compute"],
        criticality="High",
        confidence_score=96,
        inferred_notes="Should be cleared because confidence is 96",
        source_reference="Doc B"
    )
    
    inventory = SystemInventory(systems=[sys1, sys2])
    merged_inventory = deduplicate_inventory(inventory)
    
    assert len(merged_inventory.systems) == 1
    merged = merged_inventory.systems[0]
    
    # Keeping highest confidence
    assert merged.confidence_score == 96
    
    # Since confidence is >= 95, inferred_notes should be cleared
    assert merged.inferred_notes == ""
    
    # Keeping most definitive auth_method (IAM Role is not "Unknown")
    assert merged.auth_method == "IAM Role"
    
    # Highest criticality: High > Medium
    assert merged.criticality == "High"
    
    # Deduplicated entities: "Server", "S3 Bucket", "Lambda"
    assert set(merged.key_entities) == {"Server", "S3 Bucket", "Lambda"}
    
    # Deduplicated business processes: "Hosting", "Data Storage", "Serverless Compute"
    assert set(merged.business_processes) == {"Hosting", "Data Storage", "Serverless Compute"}
    
    # Concatenated source reference
    assert merged.source_reference == "Doc A; Doc B"


def test_deduplicate_inventory_keep_inferred_notes_below_95():
    """Verify that if merged confidence score is below 95, inferred_notes are merged and retained."""
    sys1 = SystemExtraction(
        name="CustomDB",
        category="Database",
        auth_method="Unknown",
        key_entities=["User"],
        business_processes=["Authentication"],
        criticality="Medium",
        confidence_score=70,
        inferred_notes="No auth method mentioned.",
        source_reference="Doc A"
    )
    
    sys2 = SystemExtraction(
        name="customdb",
        category="Database",
        auth_method="Unknown",
        key_entities=["Profile"],
        business_processes=["User registration"],
        criticality="Low",
        confidence_score=85,
        inferred_notes="No schema info available.",
        source_reference="Doc B"
    )
    
    inventory = SystemInventory(systems=[sys1, sys2])
    merged_inventory = deduplicate_inventory(inventory)
    
    assert len(merged_inventory.systems) == 1
    merged = merged_inventory.systems[0]
    
    assert merged.confidence_score == 85
    # Notes should be merged and separated by "; "
    assert "No auth method mentioned." in merged.inferred_notes
    assert "No schema info available." in merged.inferred_notes
    assert ";" in merged.inferred_notes
