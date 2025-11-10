"""Unit tests for configuration loader."""
import os
import pytest
from src.utils.config import load_config, ConfigError

def test_load_config_missing_file(tmp_path):
    """Test loading config from non-existent file."""
    with pytest.raises(ConfigError, match="Config file not found"):
        load_config(str(tmp_path / "nonexistent.yaml"))

def test_load_config_env_override(tmp_path, monkeypatch):
    """Test environment variable overrides config values."""
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text("test_key: original_value\n")
    
    # Debug: Print file content
    print(f"\nFile content:\n{config_path.read_text()}")
    
    # Set environment variable
    monkeypatch.setenv("BUDDHARAUER_test_key", "overridden_value")
    
    config = load_config(str(config_path))
    print(f"\nLoaded config: {config}")
    print(f"Environment: {os.environ.get('BUDDHARAUER_test_key')}")
    
    assert config["test_key"] == "overridden_value"

def test_load_config_basic(tmp_path):
    """Test basic config loading."""
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text("""
    test_key: test_value
    nested:
        key: value
    """)
    
    config = load_config(str(config_path))
    assert config["test_key"] == "test_value"
    assert config["nested"]["key"] == "value"