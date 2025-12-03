"""Tests for monitoring service."""

from __future__ import annotations

import time

import pytest

from app.services.monitoring import MonitoringService, RequestMetrics, TaskMetrics


class TestMonitoringService:
    """Test suite for MonitoringService."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.monitoring = MonitoringService()

    def test_record_request_success(self) -> None:
        """Test recording successful request."""
        self.monitoring.record_request(success=True, response_time_ms=100.0)
        stats = self.monitoring.get_stats()
        assert stats["requests"]["total"] == 1
        assert stats["requests"]["success"] == 1

    def test_record_request_failure(self) -> None:
        """Test recording failed request."""
        self.monitoring.record_request(success=False, response_time_ms=100.0)
        stats = self.monitoring.get_stats()
        assert stats["requests"]["total"] == 1
        assert stats["requests"]["failures"] == 1

    def test_record_task_success(self) -> None:
        """Test recording successful task."""
        initial_total = self.monitoring.stats["tasks"]["total"]
        self.monitoring.record_task("say", True, 0.05)
        stats = self.monitoring.get_stats()
        assert stats["tasks"]["total"] == initial_total + 1
        assert stats["tasks"]["success"] >= 1

    def test_record_task_failure(self) -> None:
        """Test recording failed task."""
        initial_total = self.monitoring.stats["tasks"]["total"]
        initial_failures = self.monitoring.stats["tasks"]["failures"]
        self.monitoring.record_task("invalid_task", False, 0.01)
        stats = self.monitoring.get_stats()
        assert stats["tasks"]["total"] == initial_total + 1
        assert stats["tasks"]["failures"] == initial_failures + 1

    def test_get_stats(self) -> None:
        """Test getting statistics."""
        # Reset stats for this test
        initial_requests = self.monitoring.stats["requests"]["total"]
        initial_tasks = self.monitoring.stats["tasks"]["total"]

        self.monitoring.record_request(success=True, response_time_ms=100.0)
        self.monitoring.record_task("say", True, 0.05)

        stats = self.monitoring.get_stats()

        assert "uptime_seconds" in stats
        assert "uptime_formatted" in stats
        assert "requests" in stats
        assert "tasks" in stats
        assert stats["requests"]["total"] == initial_requests + 1
        assert stats["tasks"]["total"] == initial_tasks + 1

    def test_format_uptime(self) -> None:
        """Test uptime formatting."""
        # Test seconds
        assert "s" in MonitoringService._format_uptime(45)
        # Test minutes
        assert "m" in MonitoringService._format_uptime(125)
        # Test hours
        assert "h" in MonitoringService._format_uptime(3700)
        # Test days
        assert "d" in MonitoringService._format_uptime(90000)

