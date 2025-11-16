"""
Tests for configuration management.
"""

import pytest
from pathlib import Path
from src.core.config import Config, ConfigError


class TestConfig:
    """Test configuration loading and validation."""

    def test_config_loads_successfully(self):
        """Test that config loads without errors."""
        config = Config()
        assert config is not None
        assert config.assistant_name == "ZERO"

    def test_get_with_dot_notation(self):
        """Test getting config values with dot notation."""
        config = Config()

        # Test nested value
        assert config.get('general.name') == "ZERO"
        assert config.get('general.personality') == "jarvis"

        # Test with default
        assert config.get('nonexistent.key', 'default') == 'default'

    def test_get_all_returns_dict(self):
        """Test that get_all returns complete config dict."""
        config = Config()
        all_config = config.get_all()

        assert isinstance(all_config, dict)
        assert 'general' in all_config
        assert 'wake_word' in all_config

    def test_set_config_value(self):
        """Test setting config values."""
        config = Config()

        config.set('test.value', 123)
        assert config.get('test.value') == 123

    def test_log_level_property(self):
        """Test log_level property."""
        config = Config()
        assert config.log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    def test_debug_mode_property(self):
        """Test debug_mode property."""
        config = Config()
        assert isinstance(config.debug_mode, bool)
