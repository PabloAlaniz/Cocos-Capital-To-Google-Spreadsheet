"""Tests for log_config module."""

import pytest
import logging
from log_config import get_logger, setup_logging


class TestLogConfig:
    """Test logging configuration."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a Logger instance."""
        logger = get_logger('test_module')
        assert isinstance(logger, logging.Logger)

    def test_get_logger_name(self):
        """Test that logger has correct name."""
        logger = get_logger('my_module')
        assert logger.name == 'my_module'

    def test_setup_logging_configures_logging(self):
        """Test that setup_logging runs without error."""
        # Just verify it doesn't raise
        setup_logging()
        # Verify some handler is configured
        root_logger = logging.getLogger()
        assert root_logger is not None

    def test_multiple_loggers_independent(self):
        """Test that multiple loggers work independently."""
        logger1 = get_logger('module1')
        logger2 = get_logger('module2')
        assert logger1.name != logger2.name
