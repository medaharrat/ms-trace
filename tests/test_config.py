"""Tests for configuration management."""

import pytest
import yaml
import tempfile
from pathlib import Path
from trace.config import Config


def test_config_defaults():
    """Test that defaults are set when no config file exists."""
    config = Config(config_path=None)
    
    assert config.get_sourcegraph_endpoint() == "https://sourcegraph.example.com/.api/graphql"
    assert config.get_afs_root_path() == "/afs/project"
    assert config.get_log_level() == "INFO"


def test_config_from_file():
    """Test loading configuration from file."""
    config_data = {
        "sourcegraph": {
            "endpoint": "https://custom.sourcegraph.com/.api/graphql",
        },
        "afs": {
            "root_path": "/custom/afs/path",
        },
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        config = Config(config_path=config_path)
        assert config.get_sourcegraph_endpoint() == "https://custom.sourcegraph.com/.api/graphql"
        assert config.get_afs_root_path() == "/custom/afs/path"
    finally:
        Path(config_path).unlink()


def test_config_nested_get():
    """Test getting nested configuration values."""
    config = Config()
    
    # Test nested key access
    assert config.get("sourcegraph.endpoint") is not None
    assert config.get("nonexistent.key", "default") == "default"

