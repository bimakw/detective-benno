"""Shared test fixtures for Detective Benno."""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from detective_benno.models import (
    FileChange,
    ProviderConfig,
    ReviewComment,
    ReviewConfig,
    ReviewResult,
    Severity,
)

# =============================================================================
# Sample Code Fixtures
# =============================================================================


@pytest.fixture
def sample_python_code() -> str:
    """Sample Python code with known issues."""
    return '''def unsafe_query(user_input):
    """Execute a database query."""
    query = f"SELECT * FROM users WHERE id = {user_input}"
    return execute(query)


def process_data(data):
    password = "secret123"
    for item in data:
        print(item)
    return data
'''


@pytest.fixture
def sample_python_file(sample_python_code: str) -> FileChange:
    """Sample Python FileChange with known issues."""
    return FileChange(
        path="src/database.py",
        content=sample_python_code,
        language="python",
    )


@pytest.fixture
def sample_go_code() -> str:
    """Sample Go code with known issues."""
    return '''package main

import "fmt"

func main() {
    password := "admin123"
    fmt.Println(password)
}
'''


@pytest.fixture
def sample_diff() -> str:
    """Sample git diff."""
    return '''diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,5 @@
+import os
+
 def main():
-    pass
+    password = os.environ.get("PASSWORD", "default123")
+    print(password)
'''


# =============================================================================
# Mock LLM Response Fixtures
# =============================================================================


@pytest.fixture
def mock_review_response_critical() -> dict[str, Any]:
    """Mock LLM response with critical findings."""
    return {
        "comments": [
            {
                "line_start": 3,
                "line_end": 3,
                "severity": "critical",
                "category": "security",
                "message": "SQL injection vulnerability detected",
                "suggestion": "Use parameterized queries instead",
                "suggested_code": 'query = "SELECT * FROM users WHERE id = %s"\ncursor.execute(query, (user_input,))',
            },
            {
                "line_start": 9,
                "severity": "critical",
                "category": "security",
                "message": "Hardcoded password detected",
                "suggestion": "Use environment variables for secrets",
            },
        ]
    }


@pytest.fixture
def mock_review_response_warnings() -> dict[str, Any]:
    """Mock LLM response with warnings only."""
    return {
        "comments": [
            {
                "line_start": 10,
                "severity": "warning",
                "category": "best-practice",
                "message": "Consider using logging instead of print",
                "suggestion": "Use logging.info() for production code",
            },
        ]
    }


@pytest.fixture
def mock_review_response_empty() -> dict[str, Any]:
    """Mock LLM response with no issues."""
    return {"comments": []}


# =============================================================================
# Config Fixtures
# =============================================================================


@pytest.fixture
def default_config() -> ReviewConfig:
    """Default ReviewConfig."""
    return ReviewConfig()


@pytest.fixture
def openai_config() -> ReviewConfig:
    """ReviewConfig with OpenAI provider."""
    return ReviewConfig(
        level="standard",
        max_comments=10,
        provider=ProviderConfig(
            name="openai",
            model="gpt-4o",
            api_key="test-api-key",
        ),
    )


@pytest.fixture
def ollama_config() -> ReviewConfig:
    """ReviewConfig with Ollama provider."""
    return ReviewConfig(
        level="standard",
        max_comments=10,
        provider=ProviderConfig(
            name="ollama",
            model="codellama",
            base_url="http://localhost:11434",
        ),
    )


@pytest.fixture
def anthropic_config() -> ReviewConfig:
    """ReviewConfig with Anthropic provider."""
    return ReviewConfig(
        level="standard",
        max_comments=10,
        provider=ProviderConfig(
            name="anthropic",
            model="claude-sonnet-4-20250514",
            api_key="test-api-key",
        ),
    )


# =============================================================================
# Mock Client Fixtures
# =============================================================================


@pytest.fixture
def mock_openai_client(mock_review_response_critical: dict[str, Any]) -> MagicMock:
    """Mock OpenAI client with realistic response."""
    mock_client = MagicMock()

    # Mock response structure
    mock_message = MagicMock()
    mock_message.content = json.dumps(mock_review_response_critical)

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_usage = MagicMock()
    mock_usage.total_tokens = 500

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_ollama_response(mock_review_response_critical: dict[str, Any]) -> dict[str, Any]:
    """Mock Ollama API response."""
    return {
        "model": "codellama",
        "response": json.dumps(mock_review_response_critical),
        "done": True,
        "eval_count": 300,
        "prompt_eval_count": 200,
    }


@pytest.fixture
def mock_anthropic_client(mock_review_response_critical: dict[str, Any]) -> MagicMock:
    """Mock Anthropic client with realistic response."""
    mock_client = MagicMock()

    # Mock response structure for Anthropic
    mock_content_block = MagicMock()
    mock_content_block.text = json.dumps(mock_review_response_critical)

    mock_usage = MagicMock()
    mock_usage.input_tokens = 200
    mock_usage.output_tokens = 300

    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_response.usage = mock_usage

    mock_client.messages.create.return_value = mock_response

    return mock_client


# =============================================================================
# Result Fixtures
# =============================================================================


@pytest.fixture
def sample_review_result() -> ReviewResult:
    """Sample ReviewResult with mixed findings."""
    return ReviewResult(
        files_reviewed=2,
        comments=[
            ReviewComment(
                file_path="src/main.py",
                line_start=10,
                severity=Severity.CRITICAL,
                category="security",
                message="SQL injection vulnerability",
            ),
            ReviewComment(
                file_path="src/main.py",
                line_start=20,
                severity=Severity.WARNING,
                category="performance",
                message="Inefficient loop detected",
            ),
            ReviewComment(
                file_path="src/utils.py",
                line_start=5,
                severity=Severity.SUGGESTION,
                category="best-practice",
                message="Consider adding type hints",
            ),
        ],
        model_used="gpt-4o",
        tokens_used=1000,
    )


# =============================================================================
# Temporary File Fixtures
# =============================================================================


@pytest.fixture
def temp_python_file(tmp_path, sample_python_code: str):
    """Create a temporary Python file for testing."""
    file_path = tmp_path / "test_file.py"
    file_path.write_text(sample_python_code)
    return file_path


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config_content = """
version: "1"

investigation:
  level: detailed
  max_findings: 5

provider:
  name: openai
  model: gpt-4o-mini
  temperature: 0.5

guidelines:
  - "Check for security issues"
  - "Look for performance problems"

ignore:
  files:
    - "*.md"
    - "test_*.py"
"""
    config_path = tmp_path / ".benno.yaml"
    config_path.write_text(config_content)
    return config_path
