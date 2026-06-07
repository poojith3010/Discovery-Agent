from pydantic import BaseModel, Field, field_validator

class GeneratedIntegration(BaseModel):
    """
    Represents the complete generated integration artifacts for a single missing integration gap.
    """
    connector_filename: str = Field(
        ...,
        description="The filename for the Python connector module (e.g., salesforce_to_netsuite.py)."
    )
    connector_code: str = Field(
        ...,
        description="The actual runnable Python integration code implementing authentication, CRUD, rate limiting, retries, and pagination."
    )
    yaml_filename: str = Field(
        ...,
        description="The filename for the agent configuration YAML file (e.g., salesforce_netsuite_agent.yaml)."
    )
    yaml_content: str = Field(
        ...,
        description="The YAML configuration string containing system prompt, tool bindings, workflow steps, and test scenarios."
    )
    readme_content: str = Field(
        ...,
        description="A Markdown-formatted setup guide explaining dependencies, installation, usage, and local run instructions."
    )
    requirements_content: str = Field(
        ...,
        description="The content for the requirements.txt manifest file listing all required dependencies (e.g., requests, tenacity)."
    )
    tests_filename: str = Field(
        ...,
        description="The filename for the unit test script (e.g., test_salesforce_to_netsuite.py)."
    )
    tests_code: str = Field(
        ...,
        description="The Python source code containing unit tests for the connector using mock objects."
    )

    @field_validator(
        "connector_filename", "connector_code", "yaml_filename", 
        "yaml_content", "readme_content", "requirements_content", 
        "tests_filename", "tests_code"
    )
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Fields must not be empty or whitespace only")
        return v.strip()

    @field_validator("connector_filename", "tests_filename")
    @classmethod
    def validate_python_filename(cls, v: str) -> str:
        if not v.strip().endswith(".py"):
            raise ValueError("Python filenames must end with '.py'")
        return v.strip()

    @field_validator("yaml_filename")
    @classmethod
    def validate_yaml_filename(cls, v: str) -> str:
        if not (v.strip().endswith(".yaml") or v.strip().endswith(".yml")):
            raise ValueError("yaml_filename must end with '.yaml' or '.yml'")
        return v.strip()
