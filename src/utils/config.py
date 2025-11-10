"""Configuration loader for Buddharauer.

Loads YAML config and environment variables. Provides access to all configuration parameters.
"""
import os
import yaml
from typing import Any, Dict
from dotenv import load_dotenv

CONFIG_PATH = os.getenv("CONFIG_PATH", "fastagent.config.yaml")

load_dotenv()

class ConfigError(Exception):
    """Custom exception for config errors."""
    pass

def load_config(path: str = CONFIG_PATH) -> Dict[str, Any]:
    """Load configuration from YAML file and environment variables.

    Args:
        path: Path to YAML config file.
    Returns:
        Dictionary of config parameters.
    Raises:
        ConfigError: If config file is missing or invalid.
    """
    if not os.path.exists(path):
        raise ConfigError(f"Config file not found: {path}")
    
    # Load YAML config
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    
    # Overlay environment variables
    for key, value in os.environ.items():
        if key.startswith("BUDDHARAUER_"):
            # Convert environment variable key to match YAML key format
            config_key = key[12:].lower()  # Remove prefix and convert to lowercase
            config[config_key] = value
    
    return config

# Example usage
if __name__ == "__main__":
    cfg = load_config()
    print(cfg)
