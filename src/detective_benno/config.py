"""Configuration loader for Detective Benno."""

import os
from pathlib import Path
from typing import Optional

import yaml

from detective_benno.models import ReviewConfig


def load_config(config_path: Optional[str] = None) -> ReviewConfig:
    """Load configuration from file or defaults.

    Args:
        config_path: Path to config file. If not provided, searches default locations.

    Returns:
        ReviewConfig instance.
    """
    if config_path:
        return _load_from_file(config_path)

    # Search for config in default locations
    search_paths = [
        Path(".benno.yaml"),
        Path(".benno.yml"),
        Path(".detective-benno.yaml"),
        Path(".detective-benno.yml"),
        Path.home() / ".config" / "detective-benno" / "config.yaml",
    ]

    for path in search_paths:
        if path.exists():
            return _load_from_file(str(path))

    # Check environment variable
    env_config = os.environ.get("BENNO_CONFIG")
    if env_config and Path(env_config).exists():
        return _load_from_file(env_config)

    return ReviewConfig()


def _load_from_file(path: str) -> ReviewConfig:
    """Load configuration from a YAML file.

    Args:
        path: Path to the config file.

    Returns:
        ReviewConfig instance.
    """
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    # Extract nested config values
    investigation = data.get("investigation", data.get("review", {}))
    model_config = data.get("model", {})
    ignore = data.get("ignore", {})

    return ReviewConfig(
        level=investigation.get("level", "standard"),
        max_comments=investigation.get("max_findings", investigation.get("max_comments", 10)),
        guidelines=data.get("guidelines", []),
        ignore_files=ignore.get("files", []),
        ignore_patterns=ignore.get("patterns", []),
        model=model_config.get("name", "gpt-4o"),
        temperature=model_config.get("temperature", 0.3),
    )
