"""
Tests for logging infrastructure.

Tests cover:
- Logger setup and configuration
- Colored formatter
- File and console handlers
- Log rotation
"""

import pytest
import logging
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.logger import (
    setup_logger,
    get_logger,
    ColoredFormatter
)


class TestColoredFormatter:
    """Test ColoredFormatter functionality."""

    def test_colored_formatter_initialization(self):
        """Test formatter can be created."""
        formatter = ColoredFormatter(
            fmt='%(levelname)s: %(message)s',
            datefmt='%Y-%m-%d'
        )
        assert formatter is not None

    def test_format_debug(self):
        """Test formatting DEBUG level log."""
        formatter = ColoredFormatter(fmt='%(levelname)s: %(message)s')
        record = logging.LogRecord(
            name='test',
            level=logging.DEBUG,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        assert 'Test message' in formatted
        assert 'DEBUG' in formatted

    def test_format_info(self):
        """Test formatting INFO level log."""
        formatter = ColoredFormatter(fmt='%(levelname)s: %(message)s')
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Info message',
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        assert 'Info message' in formatted
        assert 'INFO' in formatted

    def test_format_warning(self):
        """Test formatting WARNING level log."""
        formatter = ColoredFormatter(fmt='%(levelname)s: %(message)s')
        record = logging.LogRecord(
            name='test',
            level=logging.WARNING,
            pathname='test.py',
            lineno=1,
            msg='Warning message',
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        assert 'Warning message' in formatted
        assert 'WARNING' in formatted

    def test_format_error(self):
        """Test formatting ERROR level log."""
        formatter = ColoredFormatter(fmt='%(levelname)s: %(message)s')
        record = logging.LogRecord(
            name='test',
            level=logging.ERROR,
            pathname='test.py',
            lineno=1,
            msg='Error message',
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        assert 'Error message' in formatted
        assert 'ERROR' in formatted

    def test_format_critical(self):
        """Test formatting CRITICAL level log."""
        formatter = ColoredFormatter(fmt='%(levelname)s: %(message)s')
        record = logging.LogRecord(
            name='test',
            level=logging.CRITICAL,
            pathname='test.py',
            lineno=1,
            msg='Critical message',
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        assert 'Critical message' in formatted
        assert 'CRITICAL' in formatted


class TestSetupLogger:
    """Test setup_logger function."""

    def test_setup_logger_default(self):
        """Test logger setup with default parameters."""
        logger = setup_logger('test_logger')
        assert logger is not None
        assert logger.name == 'test_logger'
        assert logger.level == logging.INFO

    def test_setup_logger_custom_level(self):
        """Test logger setup with custom log level."""
        logger = setup_logger('test_logger', log_level='DEBUG')
        assert logger.level == logging.DEBUG

        logger = setup_logger('test_logger2', log_level='WARNING')
        assert logger.level == logging.WARNING

    def test_setup_logger_console_only(self):
        """Test logger setup with console output only."""
        logger = setup_logger(
            'test_logger',
            console_output=True,
            file_output=False
        )
        assert logger is not None
        # Should have console handler
        assert any(
            isinstance(h, logging.StreamHandler)
            for h in logger.handlers
        )

    def test_setup_logger_file_only(self, tmp_path):
        """Test logger setup with file output only."""
        log_dir = tmp_path / 'logs'
        logger = setup_logger(
            'test_logger',
            log_dir=log_dir,
            console_output=False,
            file_output=True
        )
        assert logger is not None
        # Should have file handler
        assert any(
            isinstance(h, logging.handlers.RotatingFileHandler)
            for h in logger.handlers
        )

    def test_setup_logger_both_outputs(self, tmp_path):
        """Test logger setup with both console and file output."""
        log_dir = tmp_path / 'logs'
        logger = setup_logger(
            'test_logger',
            log_dir=log_dir,
            console_output=True,
            file_output=True
        )
        assert logger is not None
        assert len(logger.handlers) >= 2

    def test_setup_logger_custom_log_dir(self, tmp_path):
        """Test logger setup with custom log directory."""
        log_dir = tmp_path / 'custom_logs'
        logger = setup_logger(
            'test_logger',
            log_dir=log_dir,
            file_output=True
        )
        assert log_dir.exists()

    def test_setup_logger_no_propagation(self):
        """Test logger does not propagate to root logger."""
        logger = setup_logger('test_logger')
        assert logger.propagate is False

    def test_setup_logger_removes_existing_handlers(self):
        """Test that setup_logger removes existing handlers."""
        logger = setup_logger('test_logger')
        initial_handler_count = len(logger.handlers)

        # Setup again - should remove old handlers
        logger2 = setup_logger('test_logger')
        # Should have same number of handlers (not doubled)
        assert len(logger2.handlers) == initial_handler_count

    def test_setup_logger_invalid_level(self):
        """Test logger setup with invalid log level."""
        # Should default to INFO for invalid level
        logger = setup_logger('test_logger', log_level='INVALID')
        assert logger.level == logging.INFO


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_new(self):
        """Test getting a new logger."""
        logger = get_logger('new_logger')
        assert logger is not None
        assert logger.name == 'new_logger'

    def test_get_logger_existing(self):
        """Test getting an existing logger."""
        logger1 = get_logger('existing_logger')
        logger2 = get_logger('existing_logger')
        # Should return the same logger instance
        assert logger1 is logger2

    def test_get_logger_sets_up_if_no_handlers(self):
        """Test that get_logger sets up logger if no handlers."""
        # Create a logger without handlers
        test_logger = logging.getLogger('test_no_handlers')
        test_logger.handlers = []

        # get_logger should set it up
        logger = get_logger('test_no_handlers')
        assert len(logger.handlers) > 0

    def test_get_logger_preserves_existing_handlers(self):
        """Test that get_logger preserves existing handlers."""
        # Create logger with handler
        test_logger = logging.getLogger('test_with_handlers')
        handler = logging.StreamHandler(sys.stdout)
        test_logger.addHandler(handler)
        initial_count = len(test_logger.handlers)

        # get_logger should not add more handlers
        logger = get_logger('test_with_handlers')
        assert len(logger.handlers) == initial_count


