"""
Configuration management for ZERO assistant.

This module handles loading and validating configuration from YAML files
and environment variables.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when there's a configuration error."""
    pass


class Config:
    """
    Configuration manager for ZERO assistant.

    Loads configuration from YAML files and environment variables,
    validates required settings, and provides type-safe access to config values.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config YAML file. If None, uses default location.
        """
        # Load environment variables from .env file
        load_dotenv()

        # Determine config file path
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        # Load YAML configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

        # Substitute environment variables
        self._config = self._substitute_env_vars(self._config)

        # Validate required configuration
        self._validate()

    def _substitute_env_vars(self, config: Any) -> Any:
        """
        Recursively substitute environment variables in config.

        Variables in format ${VAR_NAME} will be replaced with environment values.

        Args:
            config: Configuration dictionary or value

        Returns:
            Configuration with environment variables substituted
        """
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Match ${VAR_NAME} pattern
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, config)

            for var_name in matches:
                env_value = os.getenv(var_name, '')
                config = config.replace(f'${{{var_name}}}', env_value)

            return config
        else:
            return config

    def _validate(self):
        """Validate that required configuration is present."""
        required_keys = [
            'general',
            'wake_word',
            'stt',
            'tts',
            'nlu',
            'skills',
            'ui',
            'audio',
        ]

        for key in required_keys:
            if key not in self._config:
                raise ConfigError(f"Missing required configuration section: {key}")

        # Check for required API keys (only if not in mock mode)
        if not self.get('development.mock_apis', False):
            required_api_keys = [
                ('wake_word.access_key', 'Picovoice access key'),
                ('stt.api_key', 'Deepgram API key'),
                ('nlu.cloud.api_key', 'OpenAI API key'),
                ('skills.weather.api_key', 'OpenWeatherMap API key'),
            ]

            missing_keys = []
            for key_path, description in required_api_keys:
                value = self.get(key_path)
                if not value or value.startswith('your_') or value == '':
                    missing_keys.append(f"{description} ({key_path})")

            if missing_keys:
                raise ConfigError(
                    f"Missing required API keys:\n"
                    f"{'  - ' + chr(10).join(missing_keys)}\n"
                    f"Please set them in your .env file or config.yaml"
                )

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Configuration key path (e.g., 'general.name')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get('general.name')
            'ZERO'
            >>> config.get('skills.weather.enabled')
            True
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation.

        Args:
            key_path: Configuration key path (e.g., 'general.log_level')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def get_all(self) -> Dict[str, Any]:
        """
        Get entire configuration dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()

    def reload(self):
        """Reload configuration from file."""
        self.__init__()

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.get('general.log_level', 'INFO')

    @property
    def debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get('development.debug_mode', False)

    @property
    def assistant_name(self) -> str:
        """Get assistant name."""
        return self.get('general.name', 'ZERO')


# Global config instance
_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global configuration instance.

    Args:
        config_path: Path to config file (only used on first call)

    Returns:
        Global Config instance
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = Config(config_path)

    return _config_instance


def reload_config():
    """Reload global configuration."""
    global _config_instance
    if _config_instance is not None:
        _config_instance.reload()
