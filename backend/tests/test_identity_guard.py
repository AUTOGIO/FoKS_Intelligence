"""Tests for the Local Identity Guard module.

Tests cover:
1. System prompt injection behavior
2. Cloud leakage detection patterns
3. Response sanitization
4. Toggleable guard functionality
"""

from __future__ import annotations

import pytest
from unittest.mock import patch


class TestIdentityGuard:
    """Test suite for IdentityGuard class."""

    def test_identity_guard_enabled_by_default(self):
        """Verify identity guard is enabled by default."""
        # Import fresh to test default state
        from app.services.identity_guard import identity_guard

        assert identity_guard.enabled is True

    def test_system_prompt_not_empty(self):
        """Verify system prompt is configured and not empty."""
        from app.services.identity_guard import identity_guard

        prompt = identity_guard.system_prompt
        assert prompt is not None
        assert len(prompt) > 50
        assert "local" in prompt.lower()

    def test_build_system_message_format(self):
        """Verify system message is correctly formatted."""
        from app.services.identity_guard import identity_guard

        message = identity_guard.build_system_message()
        assert message["role"] == "system"
        assert "content" in message
        assert len(message["content"]) > 0

    def test_should_inject_when_enabled(self):
        """Verify should_inject_system_prompt returns True when enabled."""
        from app.services.identity_guard import identity_guard

        # Since default is enabled, should return True
        assert identity_guard.should_inject_system_prompt() is True

    def test_cloud_patterns_compiled(self):
        """Verify cloud leakage patterns compile successfully."""
        from app.services.identity_guard import identity_guard

        patterns = identity_guard.get_compiled_patterns()
        assert len(patterns) > 0
        # Should have at least OpenAI, Anthropic, Google patterns
        assert len(patterns) >= 10


class TestLeakageDetection:
    """Test suite for cloud leakage detection."""

    def test_safe_response_passes(self):
        """Verify safe responses are not flagged."""
        from app.services.identity_guard import scan_for_leakage

        safe_responses = [
            "I am a helpful local AI assistant.",
            "Here is the Python code you requested.",
            "The weather today is sunny.",
            "Let me help you with that task.",
        ]

        for response in safe_responses:
            result = scan_for_leakage(response)
            assert result.is_safe is True
            assert len(result.detected_patterns) == 0

    def test_openai_reference_detected(self):
        """Verify OpenAI references are detected."""
        from app.services.identity_guard import scan_for_leakage

        response = "I am ChatGPT, developed by OpenAI."
        result = scan_for_leakage(response)
        assert result.is_safe is False
        assert len(result.detected_patterns) > 0

    def test_anthropic_reference_detected(self):
        """Verify Anthropic references are detected."""
        from app.services.identity_guard import scan_for_leakage

        response = "As Claude, an AI made by Anthropic, I can help."
        result = scan_for_leakage(response)
        assert result.is_safe is False
        assert len(result.detected_patterns) > 0

    def test_google_reference_detected(self):
        """Verify Google AI references are detected."""
        from app.services.identity_guard import scan_for_leakage

        response = "I am Gemini, Google AI here to assist."
        result = scan_for_leakage(response)
        assert result.is_safe is False
        assert len(result.detected_patterns) > 0

    def test_microsoft_reference_detected(self):
        """Verify Microsoft references are detected."""
        from app.services.identity_guard import scan_for_leakage

        response = "I am Copilot, powered by Microsoft."
        result = scan_for_leakage(response)
        assert result.is_safe is False
        assert len(result.detected_patterns) > 0


class TestResponseSanitization:
    """Test suite for response sanitization."""

    def test_safe_response_unchanged(self):
        """Verify safe responses are returned unchanged."""
        from app.services.identity_guard import sanitize_response

        original = "I am a helpful local AI assistant."
        sanitized = sanitize_response(original)
        assert sanitized == original

    def test_unsafe_response_replaced(self):
        """Verify unsafe responses are replaced with fallback."""
        from app.services.identity_guard import sanitize_response
        from app.config import settings

        unsafe = "I am ChatGPT, developed by OpenAI."
        sanitized = sanitize_response(unsafe)
        assert sanitized != unsafe
        assert sanitized == settings.local_fallback_response


class TestLockedModels:
    """Test suite for locked model configuration."""

    def test_locked_models_from_settings(self):
        """Verify locked models are read from settings."""
        from app.config import settings

        assert settings.locked_chat_model is not None
        assert settings.locked_reasoning_model is not None
        assert settings.locked_embedding_model is not None
        assert settings.locked_vision_model is not None
        assert settings.locked_scientific_model is not None

    def test_default_models_match_locked(self):
        """Verify DEFAULT_MODELS matches locked settings."""
        from app.services.model_registry import DEFAULT_MODELS
        from app.config import settings

        assert DEFAULT_MODELS["chat"] == settings.locked_chat_model
        assert DEFAULT_MODELS["reasoning"] == settings.locked_reasoning_model
        assert DEFAULT_MODELS["embeddings"] == settings.locked_embedding_model
        assert DEFAULT_MODELS["vision"] == settings.locked_vision_model
        assert DEFAULT_MODELS["scientific"] == settings.locked_scientific_model


class TestToggleableBehavior:
    """Test suite for toggleable guard behavior."""

    def test_disabled_guard_skips_sanitization(self):
        """Verify disabled guard returns response unchanged."""
        from app.services.identity_guard import IdentityGuard

        # Create a disabled guard instance
        with patch("app.services.identity_guard.settings") as mock_settings:
            mock_settings.local_identity_guard = False
            mock_settings.cloud_leakage_patterns = []

            guard = IdentityGuard()
            guard._enabled = False

            unsafe = "I am ChatGPT, developed by OpenAI."
            result = guard.sanitize_response(unsafe)
            assert result == unsafe

    def test_disabled_guard_skips_system_prompt(self):
        """Verify disabled guard does not inject system prompt."""
        from app.services.identity_guard import IdentityGuard

        with patch("app.services.identity_guard.settings") as mock_settings:
            mock_settings.local_identity_guard = False

            guard = IdentityGuard()
            guard._enabled = False

            assert guard.should_inject_system_prompt() is False

