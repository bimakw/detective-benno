"""Tests for configuration loading."""

import tempfile
from pathlib import Path

from detective_benno.config import load_config


class TestLoadConfig:
    """Tests for config loading."""

    def test_default_config(self):
        config = load_config()
        assert config.level == "standard"
        assert config.max_comments == 10

    def test_load_from_yaml_file(self):
        yaml_content = """
version: "1"
investigation:
  level: detailed
  max_findings: 20
guidelines:
  - "Check for SQL injection"
model:
  name: gpt-4o-mini
  temperature: 0.5
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()

            config = load_config(f.name)

            assert config.level == "detailed"
            assert config.max_comments == 20
            assert config.model == "gpt-4o-mini"
            assert config.temperature == 0.5
            assert "Check for SQL injection" in config.guidelines

        Path(f.name).unlink()

    def test_load_with_ignore_patterns(self):
        yaml_content = """
investigation:
  level: minimal
ignore:
  files:
    - "*.md"
    - "vendor/**"
  patterns:
    - "TODO:"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()

            config = load_config(f.name)

            assert "*.md" in config.ignore_files
            assert "vendor/**" in config.ignore_files
            assert "TODO:" in config.ignore_patterns

        Path(f.name).unlink()
