"""
Configuration module for JARVIS-MK2.
Handles loading and accessing configuration settings.
"""

import yaml
import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union


class Config:
    """Configuration manager for JARVIS-MK2."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._config: dict = {}
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self._loaded = True
            self._load_defaults()
            self._load_from_file()
            self._load_from_env()

    def _load_defaults(self) -> None:
        """Load default configuration values."""
        self._config = {
            "system": {
                "name": "JARVIS-MK2",
                "version": "0.1.0",
                "debug": False,
                "log_level": "INFO",
            },
            "modules": {
                "auto_load": True,
                "paths": ["modules"],
            },
            "memory": {
                "short_term": {
                    "max_size": 1000,
                },
                "long_term": {
                    "type": "json",  # or sqlite, redis, etc.
                    "path": "data/memory.json",
                },
            },
            "tasks": {
                "max_workers": 4,
                "retry_attempts": 3,
            },
        }

    def _load_from_file(self) -> None:
        """Load configuration from file."""
        logger = logging.getLogger(__name__)
        config_paths = [
            Path("config.yaml"),
            Path("config.yml"),
            Path("config.json"),
            Path("/etc/jarvis-mk2/config.yaml"),
            Path.home() / ".jarvis-mk2" / "config.yaml",
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        if config_path.suffix in ['.yaml', '.yml']:
                            config_data = yaml.safe_load(f)
                        else:  # JSON
                            import json
                            config_data = json.load(f)

                    if config_data:
                        self._deep_update(self._config, config_data)
                    logger.info(f"Loaded configuration from {config_path}")
                    break
                except Exception as e:
                    logger.error(f"Error loading configuration from {config_path}: {e}")

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        logger = logging.getLogger(__name__)
        # Override configuration with environment variables
        # Format: JARVIS_MK2_SECTION_KEY=value
        for key, value in os.environ.items():
            if key.startswith("JARVIS_MK2_"):
                # Remove prefix and split by underscore
                config_key = key[11:].lower()  # Remove 'JARVIS_MK2_'
                parts = config_key.split('_')
                if len(parts) >= 2:
                    section = '_'.join(parts[:-1])
                    option = parts[-1]
                    # Convert value to appropriate type
                    typed_value = self._convert_env_value(value)
                    self._set_nested(section, option, typed_value)

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        # Return as string
        return value

    def _set_nested(self, section: str, option: str, value: Any) -> None:
        """Set a nested configuration value."""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][option] = value

    def _deep_update(self, target: dict, source: dict) -> None:
        """Deep update a dictionary."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Dot-separated key (e.g., 'system.debug')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Dot-separated key (e.g., 'system.debug')
            value: Value to set
        """
        keys = key.split('.')
        target = self._config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def to_dict(self) -> dict:
        """Return a copy of the configuration as a dictionary."""
        return self._config.copy()


# Global configuration instance
config = Config()