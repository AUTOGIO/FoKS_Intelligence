"""Tests for M3 optimizations module."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from app.utils.m3_optimizations import (
    check_neural_engine_available,
    get_system_info,
    optimize_for_m3,
    recommend_model_config,
)


class TestOptimizeForM3:
    """Tests for optimize_for_m3 function."""

    @patch("app.utils.m3_optimizations.settings")
    def test_optimize_for_m3_when_not_m3(self, mock_settings):
        """Test optimize_for_m3 when not running on M3."""
        mock_settings.is_m3 = False
        result = optimize_for_m3()
        assert result == {}

    @patch("app.utils.m3_optimizations.settings")
    @patch("app.utils.m3_optimizations.os.environ")
    def test_optimize_for_m3_when_m3(self, mock_environ, mock_settings):
        """Test optimize_for_m3 when running on M3."""
        mock_settings.is_m3 = True
        mock_settings.is_apple_silicon = True
        mock_settings.enable_neural_engine = True
        mock_settings.optimal_workers = 4
        mock_settings.max_concurrent_tasks = 120
        mock_settings.memory_gb = 16

        result = optimize_for_m3()

        assert "max_workers" in result
        assert "thread_pool_size" in result
        assert "max_memory_mb" in result
        assert "max_concurrent_tasks" in result
        assert result["max_workers"] == 4
        assert result["max_concurrent_tasks"] == 120

    @patch("app.utils.m3_optimizations.settings")
    @patch("app.utils.m3_optimizations.os.environ")
    def test_optimize_for_m3_sets_environment_variables(self, mock_environ, mock_settings):
        """Test optimize_for_m3 sets environment variables."""
        mock_settings.is_m3 = True
        mock_settings.is_apple_silicon = True

        optimize_for_m3()

        # Verify environment variables are set
        assert mock_environ.setdefault.called


class TestGetSystemInfo:
    """Tests for get_system_info function."""

    @patch("app.utils.m3_optimizations.settings")
    @patch("app.utils.m3_optimizations.platform")
    def test_get_system_info(self, mock_platform, mock_settings):
        """Test get_system_info returns correct structure."""
        mock_settings.hardware_model = "arm64"
        mock_settings.is_apple_silicon = True
        mock_settings.is_m3 = True
        mock_settings.cpu_cores = 8
        mock_settings.memory_gb = 16
        mock_settings.optimal_workers = 4
        mock_settings.max_concurrent_tasks = 120
        mock_settings.enable_neural_engine = True
        mock_settings.max_request_size_mb = 10
        mock_platform.platform.return_value = "macOS-14.0-arm64"
        mock_platform.processor.return_value = "arm"

        result = get_system_info()

        assert "hardware" in result
        assert "optimizations" in result
        assert result["hardware"]["is_m3"] is True
        assert result["hardware"]["cpu_cores"] == 8
        assert result["optimizations"]["optimal_workers"] == 4


class TestCheckNeuralEngineAvailable:
    """Tests for check_neural_engine_available function."""

    @patch("app.utils.m3_optimizations.settings")
    def test_check_neural_engine_not_apple_silicon(self, mock_settings):
        """Test check_neural_engine_available when not Apple Silicon."""
        mock_settings.is_apple_silicon = False
        assert check_neural_engine_available() is False

    @patch("app.utils.m3_optimizations.settings")
    @patch("app.utils.m3_optimizations.subprocess.run")
    def test_check_neural_engine_available_success(self, mock_run, mock_settings):
        """Test check_neural_engine_available when available."""
        mock_settings.is_apple_silicon = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1\n"
        mock_run.return_value = mock_result

        assert check_neural_engine_available() is True

    @patch("app.utils.m3_optimizations.settings")
    @patch("app.utils.m3_optimizations.subprocess.run")
    def test_check_neural_engine_available_failure(self, mock_run, mock_settings):
        """Test check_neural_engine_available when not available."""
        mock_settings.is_apple_silicon = True
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        assert check_neural_engine_available() is False

    @patch("app.utils.m3_optimizations.settings")
    @patch("app.utils.m3_optimizations.subprocess.run")
    def test_check_neural_engine_available_exception(self, mock_run, mock_settings):
        """Test check_neural_engine_available when exception occurs."""
        mock_settings.is_apple_silicon = True
        mock_run.side_effect = Exception("Error")

        assert check_neural_engine_available() is False


class TestRecommendModelConfig:
    """Tests for recommend_model_config function."""

    @patch("app.utils.m3_optimizations.settings")
    @patch("app.utils.m3_optimizations.check_neural_engine_available")
    def test_recommend_model_config_m3(self, mock_check_ane, mock_settings):
        """Test recommend_model_config for M3."""
        mock_settings.is_m3 = True
        mock_settings.is_apple_silicon = True
        mock_settings.memory_gb = 16
        mock_settings.enable_neural_engine = True
        mock_check_ane.return_value = True

        result = recommend_model_config()

        assert "preferred_format" in result
        assert "quantization" in result
        assert "max_model_size_gb" in result
        assert "use_neural_engine" in result
        assert result["preferred_format"] == "MLX"
        assert result["use_neural_engine"] is True
        assert "optimal_batch_size" in result
        assert "preferred_models" in result

    @patch("app.utils.m3_optimizations.settings")
    @patch("app.utils.m3_optimizations.check_neural_engine_available")
    def test_recommend_model_config_non_m3(self, mock_check_ane, mock_settings):
        """Test recommend_model_config for non-M3."""
        mock_settings.is_m3 = False
        mock_settings.is_apple_silicon = False
        mock_settings.memory_gb = 8
        mock_check_ane.return_value = False

        result = recommend_model_config()

        assert result["preferred_format"] == "GGUF"
        assert result["use_neural_engine"] is False
        assert "optimal_batch_size" not in result

    @patch("app.utils.m3_optimizations.settings")
    @patch("app.utils.m3_optimizations.check_neural_engine_available")
    def test_recommend_model_config_low_memory(self, mock_check_ane, mock_settings):
        """Test recommend_model_config for low memory."""
        mock_settings.is_m3 = False
        mock_settings.is_apple_silicon = True
        mock_settings.memory_gb = 8
        mock_check_ane.return_value = False

        result = recommend_model_config()

        assert result["quantization"] == "8-bit"

