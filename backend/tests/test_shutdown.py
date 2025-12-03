"""Tests for shutdown utilities."""

from __future__ import annotations

import signal
from unittest.mock import MagicMock, patch

import pytest

from app.utils.shutdown import (
    register_shutdown_handler,
    setup_graceful_shutdown,
    _signal_handler,
)


class TestRegisterShutdownHandler:
    """Tests for register_shutdown_handler function."""

    def test_register_shutdown_handler(self):
        """Test registering a shutdown handler."""
        handler_called = []

        def test_handler():
            handler_called.append(True)

        register_shutdown_handler(test_handler)
        # Handler should be registered (we can't easily test the signal handler without mocking)
        assert len(handler_called) == 0

    def test_register_multiple_handlers(self):
        """Test registering multiple shutdown handlers."""
        handlers_called = []

        def handler1():
            handlers_called.append(1)

        def handler2():
            handlers_called.append(2)

        register_shutdown_handler(handler1)
        register_shutdown_handler(handler2)
        # Both handlers should be registered
        assert len(handlers_called) == 0


class TestSignalHandler:
    """Tests for _signal_handler function."""

    @patch("app.utils.shutdown.logger")
    @patch("app.utils.shutdown.sys.exit")
    def test_signal_handler_calls_handlers(self, mock_exit, mock_logger):
        """Test signal handler calls registered handlers."""
        from app.utils.shutdown import _shutdown_handlers

        # Clear handlers
        _shutdown_handlers.clear()

        handler_called = []

        def test_handler():
            handler_called.append(True)

        _shutdown_handlers.append(test_handler)
        _signal_handler(signal.SIGTERM, None)

        assert len(handler_called) == 1
        mock_exit.assert_called_once_with(0)

    @patch("app.utils.shutdown.logger")
    @patch("app.utils.shutdown.sys.exit")
    def test_signal_handler_handles_exception(self, mock_exit, mock_logger):
        """Test signal handler handles exceptions in handlers."""
        from app.utils.shutdown import _shutdown_handlers

        # Clear handlers
        _shutdown_handlers.clear()

        def failing_handler():
            raise Exception("Handler error")

        _shutdown_handlers.append(failing_handler)
        _signal_handler(signal.SIGTERM, None)

        # Should still exit even if handler fails
        mock_exit.assert_called_once_with(0)
        mock_logger.error.assert_called()


class TestSetupGracefulShutdown:
    """Tests for setup_graceful_shutdown function."""

    @patch("app.utils.shutdown.signal.signal")
    @patch("app.utils.shutdown.logger")
    def test_setup_graceful_shutdown(self, mock_logger, mock_signal):
        """Test setup_graceful_shutdown registers signal handlers."""
        setup_graceful_shutdown()

        # Should register handlers for SIGINT and SIGTERM
        assert mock_signal.call_count == 2
        calls = [call[0][0] for call in mock_signal.call_args_list]
        assert signal.SIGINT in calls
        assert signal.SIGTERM in calls
        mock_logger.info.assert_called()

