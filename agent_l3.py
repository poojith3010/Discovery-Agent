import os
import logging
from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from agent import get_llm
from schemas_l3 import GeneratedIntegration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("discovery_agent_l3")

def generate_mock_integration(source_system: str, destination_system: str) -> GeneratedIntegration:
    """
    Generates realistic, runnable Python connector code, YAML agent definitions, 
    README guides, requirements.txt, and unit test files deterministically when API keys are not provided.
    """
    src = source_system.lower().strip()
    dst = destination_system.lower().strip()
    
    logger.info(f"Generating deterministic mock integration for {source_system} -> {destination_system}...")
    
    filename_py = f"{src}_to_{dst}.py"
    filename_yaml = f"{src}_{dst}_agent.yaml"
    filename_test = f"test_{src}_to_{dst}.py"
    
    # Generic, production-grade Python code skeleton customized for the systems
    connector_code = f'''"""
Production-grade Integration Connector: {source_system} to {destination_system}
Generated autonomously by Discovery Agent Level 3.
"""

import os
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("{src}_to_{dst}")

class {source_system}To{destination_system}Connector:
    """
    Connector module handling authentication, pagination, rate limiting, and retries.
    """
    def __init__(self, base_url: str, auth_token: str, client_id: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.client_id = client_id
        self.session = requests.Session()
        self.session.headers.update({{
            "Authorization": f"Bearer {{self.auth_token}}",
            "Content-Type": "application/json",
            "User-Agent": "Aivar-DiscoveryAgent/1.0"
        }})

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        reraise=True
    )
    def call_api_with_retry(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Wrapper to perform API requests with automatic exponential backoff retries on failures.
        """
        url = f"{{self.base_url}}{{endpoint}}"
        logger.info(f"Executing {{method}} request to {{url}}...")
        response = self.session.request(method, url, timeout=10, **kwargs)
        
        # Handle API Rate Limiting (HTTP 429)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            logger.warning(f"Rate limited (429). Sleeping for {{retry_after}} seconds...")
            time.sleep(retry_after)
            raise requests.exceptions.RequestException("Rate limited, retrying...")
            
        response.raise_for_status()
        return response

    def fetch_records_paginated(self, endpoint: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches records using cursor-based pagination to handle real-world API scale.
        """
        all_records = []
        next_cursor = None
        has_more = True

        while has_more:
            params: Dict[str, Any] = {{"limit": limit}}
            if next_cursor:
                params["starting_after"] = next_cursor

            try:
                response = self.call_api_with_retry("GET", endpoint, params=params)
                data = response.json()
                
                # Assume standard JSON response envelope
                records = data.get("data", [])
                all_records.extend(records)
                
                # Check for cursor paging tokens
                next_cursor = data.get("paging", {{}}).get("cursors", {{}}).get("after", None)
                has_more = bool(next_cursor) and len(records) > 0
                logger.info(f"Fetched {{len(records)}} records. Has more pages: {{has_more}}.")
            except Exception as e:
                logger.error(f"Failed to fetch paginated records: {{e}}")
                raise

        return all_records

    def create_entity(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs a CRUD creation operation.
        """
        try:
            response = self.call_api_with_retry("POST", endpoint, json=payload)
            logger.info("Successfully created entity.")
            return response.json()
        except Exception as e:
            logger.error(f"Error creating entity: {{e}}")
            raise

# Local verification block
if __name__ == "__main__":
    logger.info("Initializing connector validation dry-run...")
    # Instantiate dry run class
    connector = {source_system}To{destination_system}Connector(
        base_url="https://api.{src}.com/v1",
        auth_token="dummy_token_123"
    )
    logger.info("Connector validation dry-run successful.")
'''

    yaml_content = f'''# Agent Definition YAML for {source_system} to {destination_system} Integration
# Generated autonomously by Discovery Agent Level 3

agent:
  name: {source_system}To{destination_system}SyncAgent
  version: 1.0.0
  description: Autonomous sync agent managing data flows between {source_system} and {destination_system}.
  system_prompt: |
    You are an integration agent designed to safely sync data between {source_system} and {destination_system}.
    Your primary goal is to fetch entities, format payloads, handle authentication, and write updates correctly.
    You must always inspect API schemas, enforce rate limiting, handle rate limit errors gracefully, and log detailed exception details.

tools:
  - name: call_api_with_retry
    description: Executes REST API calls to {source_system} or {destination_system} endpoints with transient error retry policies.
  - name: fetch_records_paginated
    description: Cursor-based page extraction tool.
  - name: create_entity
    description: Writes new records to the target system.

workflow_steps:
  - step: 1
    description: Authenticate and retrieve active session.
  - step: 2
    description: Scan source system for recent triggers or record changes.
  - step: 3
    description: Extract entity details via cursor pagination if data size is large.
  - step: 4
    description: Translate fields from {source_system} format to {destination_system} schema mapping.
  - step: 5
    description: Perform creation write operations on target system.
  - step: 6
    description: Log status and commit pagination offset sync bookmarks.

test_scenarios:
  - scenario: "Normal Opportunity Sync Workflow"
    input_trigger: "Opportunity Closed"
    expected_action: "Call POST endpoint on {destination_system} to create customer record"
  - scenario: "Handling HTTP 429 Rate Limiting"
    input_trigger: "API Rate limit hit"
    expected_action: "Sleep for duration specified in Retry-After header and retry request"
  - scenario: "Authentication Expired Scenario"
    input_trigger: "HTTP 401 Unauthorized"
    expected_action: "Trigger session re-auth token cycle and replay transaction"
'''

    readme_content = f'''# Setup Guide: {source_system} to {destination_system} Connector

This directory contains the integration scripts generated autonomously to close the identified gap between **{source_system}** and **{destination_system}**.

## Prerequisites
* Python 3.10 or higher
* Required dependencies listed in `requirements.txt`.

## Installation
Install dependencies via pip:
```bash
pip install -r requirements.txt
```

## Running the Connector
Ensure you have configured your environment credentials, then run the validation dry run:
```bash
python {filename_py}
```

## Running the Automated Tests
Run unit tests inside this folder:
```bash
python -m unittest {filename_test}
```
'''

    requirements_content = "requests>=2.31.0\ntenacity>=8.2.0\n"

    # Automating Mock Unit Tests code
    tests_code = f'''"""
Unit tests for {source_system}To{destination_system}Connector.
Generated autonomously by Discovery Agent Level 3.
"""

import unittest
from unittest.mock import patch, MagicMock
import requests
from {src}_to_{dst} import {source_system}To{destination_system}Connector

class Test{source_system}To{destination_system}Connector(unittest.TestCase):
    def setUp(self):
        self.connector = {source_system}To{destination_system}Connector(
            base_url="https://api.{src}.com/v1",
            auth_token="dummy_token_123"
        )

    @patch("requests.Session.request")
    def test_call_api_success(self, mock_request):
        """Test standard successful API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {{"status": "success"}}
        mock_request.return_value = mock_response

        res = self.connector.call_api_with_retry("GET", "/test")
        self.assertEqual(res.json(), {{"status": "success"}})

    @patch("requests.Session.request")
    def test_call_api_rate_limiting_retry(self, mock_request):
        """Test that connector handles HTTP 429 Rate Limiting by waiting and retrying."""
        # 1st call: rate limit. 2nd call: success
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {{"Retry-After": "0"}} # Instant wait for tests fast run
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {{"status": "success"}}
        
        mock_request.side_effect = [mock_response_429, mock_response_200]

        res = self.connector.call_api_with_retry("GET", "/test")
        self.assertEqual(res.json(), {{"status": "success"}})
        self.assertEqual(mock_request.call_count, 2)

    @patch("requests.Session.request")
    def test_fetch_records_paginated(self, mock_request):
        """Test cursor-based pagination logic fetches all records."""
        # Page 1 response
        mock_resp_1 = MagicMock()
        mock_resp_1.status_code = 200
        mock_resp_1.json.return_value = {{
            "data": [{{"id": "1", "name": "Item 1"}}],
            "paging": {{"cursors": {{"after": "cursor_token_123"}}}}
        }}
        
        # Page 2 response (last page)
        mock_resp_2 = MagicMock()
        mock_resp_2.status_code = 200
        mock_resp_2.json.return_value = {{
            "data": [{{"id": "2", "name": "Item 2"}}],
            "paging": {{}}
        }}

        mock_request.side_effect = [mock_resp_1, mock_resp_2]

        records = self.connector.fetch_records_paginated("/items", limit=1)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["id"], "1")
        self.assertEqual(records[1]["id"], "2")

if __name__ == "__main__":
    unittest.main()
'''

    return GeneratedIntegration(
        connector_filename=filename_py,
        connector_code=connector_code.strip(),
        yaml_filename=filename_yaml,
        yaml_content=yaml_content.strip(),
        readme_content=readme_content.strip(),
        requirements_content=requirements_content.strip(),
        tests_filename=filename_test,
        tests_code=tests_code.strip()
    )

def run_code_generation_agent(source_system: str, destination_system: str, dependency_note: str) -> GeneratedIntegration:
    """
    Generates working Python connector modules and agent YAML templates.
    Falls back to local deterministic generation if LLM API keys are not set.
    """
    try:
        llm = get_llm()
    except ValueError as e:
        logger.warning(
            "API keys are not configured. Running Level 3 agent in Local Mock Simulation Mode..."
        )
        return generate_mock_integration(source_system, destination_system)

    structured_llm = llm.with_structured_output(GeneratedIntegration)

    system_prompt = (
        "You are an expert Senior Integration Engineer.\n"
        "Your task is to generate actual, runnable, and production-ready Python connector code, "
        "YAML agent definitions, a requirements.txt manifest, and a mock test script for the given integration gap.\n\n"
        "Follow these rules precisely:\n"
        "1. PYTHON CONNECTOR CODE:\n"
        "   - Create a clean class implementation (e.g., class SalesforceToNetSuiteConnector).\n"
        "   - NO pseudocode, placeholders, or stubs. The code must be complete, importable, and runnable.\n"
        "   - Implement authentication (OAuth2 token exchanges, API keys, or basic auth headers).\n"
        "   - Include a robust HTTP request helper that uses the 'requests' session class and incorporates 'tenacity' retry policies (exponential backoffs for connection failures and 429 rate limit statuses).\n"
        "   - Implement cursor-based pagination logic using an iterative paging loop (e.g. tracking after/cursor parameters).\n"
        "   - Add basic mock implementation of CRUD endpoints (fetching and creating entities) and a local main dry run block at the bottom so the file is runnable.\n"
        "2. YAML AGENT DEFINITION:\n"
        "   - Must provide a valid YAML configuration containing 'agent', 'tools', 'workflow_steps', and 'test_scenarios'.\n"
        "   - Detail the system prompt guiding the agent on safety rules, authentication errors, and pagination limits.\n"
        "3. SETUP GUIDE (README):\n"
        "   - Provide clean markdown text on how to install dependencies and execute the script.\n"
        "4. REQUIREMENTS MANIFEST (requirements_content):\n"
        "   - Provide a list of Python packages required for the script (e.g., requests, tenacity).\n"
        "5. AUTOMATED UNIT TESTS (tests_filename & tests_code):\n"
        "   - Generate a valid Python unit test file (using unittest) that mocks API request responses to test:\n"
        "     a) standard successful query,\n"
        "     b) rate limit HTTP 429 backoff retries, and\n"
        "     c) cursor-based pagination loop execution.\n\n"
        "Ensure all fields are fully populated and the code is structured cleanly."
    )

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", (
            "Generate the integration code and YAML agent definition for:\n"
            "Source System: {source_system}\n"
            "Destination System: {destination_system}\n"
            "Dependency Context: {dependency_note}"
        ))
    ])

    chain = prompt_template | structured_llm

    logger.info(f"Generating integration gap solution for {source_system} -> {destination_system}...")
    result = chain.invoke({
        "source_system": source_system,
        "destination_system": destination_system,
        "dependency_note": dependency_note
    })

    if not isinstance(result, GeneratedIntegration):
        raise TypeError(f"Expected GeneratedIntegration response from model, got: {type(result)}")

    return result
