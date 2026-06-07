import pytest
from pydantic import ValidationError
from schemas_l3 import GeneratedIntegration

def test_valid_generated_integration():
    """Verify that a valid GeneratedIntegration is successfully parsed."""
    integration = GeneratedIntegration(
        connector_filename="salesforce_to_netsuite.py",
        connector_code="print('running')",
        yaml_filename="salesforce_netsuite_agent.yaml",
        yaml_content="agent:\n  name: Test",
        readme_content="# Readme Guide",
        requirements_content="requests>=2.31.0",
        tests_filename="test_salesforce_to_netsuite.py",
        tests_code="import unittest"
    )
    assert integration.connector_filename == "salesforce_to_netsuite.py"
    assert integration.yaml_filename == "salesforce_netsuite_agent.yaml"
    assert integration.connector_code == "print('running')"
    assert integration.requirements_content == "requests>=2.31.0"
    assert integration.tests_filename == "test_salesforce_to_netsuite.py"

def test_invalid_connector_filename_extension():
    """Verify that connector_filename must end with '.py'."""
    with pytest.raises(ValidationError) as excinfo:
        GeneratedIntegration(
            connector_filename="salesforce_to_netsuite.txt",  # invalid
            connector_code="print('running')",
            yaml_filename="salesforce_netsuite_agent.yaml",
            yaml_content="agent:\n  name: Test",
            readme_content="# Readme Guide",
            requirements_content="requests>=2.31.0",
            tests_filename="test_salesforce_to_netsuite.py",
            tests_code="import unittest"
        )
    assert "Python filenames must end with '.py'" in str(excinfo.value)

def test_invalid_tests_filename_extension():
    """Verify that tests_filename must end with '.py'."""
    with pytest.raises(ValidationError) as excinfo:
        GeneratedIntegration(
            connector_filename="salesforce_to_netsuite.py",
            connector_code="print('running')",
            yaml_filename="salesforce_netsuite_agent.yaml",
            yaml_content="agent:\n  name: Test",
            readme_content="# Readme Guide",
            requirements_content="requests>=2.31.0",
            tests_filename="test_salesforce_to_netsuite.txt",  # invalid
            tests_code="import unittest"
        )
    assert "Python filenames must end with '.py'" in str(excinfo.value)

def test_invalid_yaml_filename_extension():
    """Verify that yaml_filename must end with '.yaml' or '.yml'."""
    with pytest.raises(ValidationError) as excinfo:
        GeneratedIntegration(
            connector_filename="salesforce_to_netsuite.py",
            connector_code="print('running')",
            yaml_filename="salesforce_netsuite_agent.json",  # invalid
            yaml_content="agent:\n  name: Test",
            readme_content="# Readme Guide",
            requirements_content="requests>=2.31.0",
            tests_filename="test_salesforce_to_netsuite.py",
            tests_code="import unittest"
        )
    assert "yaml_filename must end with '.yaml' or '.yml'" in str(excinfo.value)

def test_empty_fields():
    """Verify that empty fields raise ValidationError."""
    with pytest.raises(ValidationError) as excinfo:
        GeneratedIntegration(
            connector_filename="salesforce_to_netsuite.py",
            connector_code="   ",  # whitespace only
            yaml_filename="salesforce_netsuite_agent.yaml",
            yaml_content="agent:\n  name: Test",
            readme_content="# Readme Guide",
            requirements_content="requests>=2.31.0",
            tests_filename="test_salesforce_to_netsuite.py",
            tests_code="import unittest"
        )
    assert "Fields must not be empty or whitespace only" in str(excinfo.value)
