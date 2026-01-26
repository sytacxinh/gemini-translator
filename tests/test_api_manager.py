"""
Unit tests for api_manager.py - AI API communication.
"""
import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.api_manager import AIAPIManager


class TestProviderIdentification:
    """Tests for _identify_provider method."""

    def test_identify_google_gemini_model(self):
        """Test Google provider detection for Gemini models."""
        manager = AIAPIManager()

        assert manager._identify_provider('gemini-2.0-flash', '') == 'google'
        assert manager._identify_provider('gemini-1.5-pro', '') == 'google'
        assert manager._identify_provider('gemini-pro-vision', '') == 'google'

    def test_identify_openai_models(self):
        """Test OpenAI provider detection."""
        manager = AIAPIManager()

        assert manager._identify_provider('gpt-4', '') == 'openai'
        assert manager._identify_provider('gpt-4o', '') == 'openai'
        assert manager._identify_provider('gpt-3.5-turbo', '') == 'openai'
        assert manager._identify_provider('o1-preview', '') == 'openai'

    def test_identify_anthropic_claude(self):
        """Test Anthropic provider detection for Claude models."""
        manager = AIAPIManager()

        assert manager._identify_provider('claude-3-opus', '') == 'anthropic'
        assert manager._identify_provider('claude-3.5-sonnet', '') == 'anthropic'

    def test_identify_by_api_key_pattern(self):
        """Test provider detection via API key prefix."""
        manager = AIAPIManager()

        # Groq key pattern
        assert manager._identify_provider('unknown-model', 'gsk_abc123') == 'groq'

        # Anthropic key pattern
        assert manager._identify_provider('unknown-model', 'sk-ant-abc123') == 'anthropic'

    def test_identify_groq_models(self):
        """Test Groq provider detection."""
        manager = AIAPIManager()

        assert manager._identify_provider('llama3-8b-8192', '') == 'groq'
        assert manager._identify_provider('mixtral-8x7b-32768', '') == 'groq'
        assert manager._identify_provider('gemma-7b-it', '') == 'groq'

    def test_identify_deepseek(self):
        """Test DeepSeek provider detection."""
        manager = AIAPIManager()

        assert manager._identify_provider('deepseek-chat', '') == 'deepseek'
        assert manager._identify_provider('deepseek-coder', '') == 'deepseek'

    def test_identify_mistral(self):
        """Test Mistral provider detection."""
        manager = AIAPIManager()

        assert manager._identify_provider('mistral-large', '') == 'mistral'
        assert manager._identify_provider('mistral-small', '') == 'mistral'
        assert manager._identify_provider('codestral-latest', '') == 'mistral'

    def test_identify_xai_grok(self):
        """Test xAI Grok provider detection."""
        manager = AIAPIManager()

        assert manager._identify_provider('grok-beta', '') == 'xai'
        assert manager._identify_provider('grok-2', '') == 'xai'

    def test_identify_openrouter_prefix(self):
        """Test OpenRouter explicit prefix."""
        manager = AIAPIManager()

        assert manager._identify_provider('openrouter/gpt-4', '') == 'openrouter'
        assert manager._identify_provider('openrouter/claude-3', '') == 'openrouter'

    def test_identify_together_prefix(self):
        """Test Together AI prefix."""
        manager = AIAPIManager()

        assert manager._identify_provider('together/llama-3', '') == 'together'
        assert manager._identify_provider('meta-llama/Meta-Llama-3', '') == 'together'

    def test_identify_siliconflow(self):
        """Test SiliconFlow provider detection."""
        manager = AIAPIManager()

        assert manager._identify_provider('Qwen/Qwen2-7B', '') == 'siliconflow'
        assert manager._identify_provider('deepseek-ai/DeepSeek-V2', '') == 'siliconflow'

    def test_identify_cerebras(self):
        """Test Cerebras provider detection."""
        manager = AIAPIManager()

        assert manager._identify_provider('llama3.1-8b', '') == 'cerebras'
        assert manager._identify_provider('llama3.2-70b', '') == 'cerebras'

    def test_identify_sambanova(self):
        """Test SambaNova provider detection."""
        manager = AIAPIManager()

        assert manager._identify_provider('Meta-Llama-3.1-8B', '') == 'sambanova'

    def test_identify_perplexity(self):
        """Test Perplexity provider detection."""
        manager = AIAPIManager()

        assert manager._identify_provider('sonar-small-online', '') == 'perplexity'
        assert manager._identify_provider('llama-3.1-sonar-large', '') == 'perplexity'

    def test_fallback_to_google(self):
        """Test that unknown models fallback to Google."""
        manager = AIAPIManager()

        # Completely unknown model should default to google
        assert manager._identify_provider('some-random-model', '') == 'google'


class TestConfiguration:
    """Tests for API configuration."""

    def test_configure_with_api_configs(self):
        """Test configuring manager with API configs."""
        manager = AIAPIManager()

        configs = [
            {'model_name': 'gpt-4', 'api_key': 'test-key', 'provider': 'openai'}
        ]
        callback = MagicMock()

        manager.configure(configs, callback)

        assert manager.api_configs == configs
        assert manager.notification_callback == callback

    def test_configure_empty(self):
        """Test configuring with empty list."""
        manager = AIAPIManager()
        manager.configure([])

        assert manager.api_configs == []


class TestTranslation:
    """Tests for translation methods."""

    def test_translate_no_config_raises(self):
        """Test that translate raises when not configured."""
        manager = AIAPIManager()

        with pytest.raises(Exception) as exc:
            manager.translate("Hello")

        assert "API not configured" in str(exc.value)

    def test_translate_no_valid_key_raises(self):
        """Test that translate raises when no valid key."""
        manager = AIAPIManager()
        manager.configure([{'model_name': '', 'api_key': ''}])

        with pytest.raises(Exception) as exc:
            manager.translate("Hello")

        assert "No valid API key" in str(exc.value)

    @patch('src.core.api_manager.genai')
    def test_translate_google_success(self, mock_genai):
        """Test successful Google translation."""
        manager = AIAPIManager()
        manager.configure([
            {'model_name': 'gemini-2.0-flash', 'api_key': 'test-key', 'provider': 'Auto'}
        ])

        # Mock Gemini response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Translated text"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = manager.translate("Hello world")

        assert result == "Translated text"
        mock_genai.configure.assert_called_once_with(api_key='test-key')

    @patch('urllib.request.urlopen')
    def test_translate_openai_style(self, mock_urlopen, mock_openai_response):
        """Test OpenAI-style API translation."""
        manager = AIAPIManager()
        manager.configure([
            {'model_name': 'gpt-4', 'api_key': 'sk-test', 'provider': 'Auto'}
        ])

        mock_urlopen.return_value = mock_openai_response

        result = manager.translate("Hello world")

        assert result == "Translated text here"


class TestRateLimitHandling:
    """Tests for rate limit and retry logic."""

    @patch('urllib.request.urlopen')
    @patch('time.sleep')
    def test_rate_limit_retry(self, mock_sleep, mock_urlopen, mock_openai_response):
        """Test exponential backoff on rate limit."""
        manager = AIAPIManager()
        manager.configure([
            {'model_name': 'gpt-4', 'api_key': 'sk-test', 'provider': 'Auto'}
        ])

        # First call: rate limit, second call: success
        rate_limit_error = MagicMock()
        rate_limit_error.code = 429
        rate_limit_error.__enter__ = MagicMock(side_effect=Exception("rate limit"))

        import urllib.error
        mock_urlopen.side_effect = [
            urllib.error.HTTPError(None, 429, "Rate Limited", {}, None),
            mock_openai_response
        ]

        result = manager.translate("Hello")

        assert result == "Translated text here"
        # Should have slept once (exponential backoff)
        mock_sleep.assert_called()


class TestMultimodal:
    """Tests for multimodal translation."""

    def test_translate_multimodal_no_config(self):
        """Test multimodal raises when not configured."""
        manager = AIAPIManager()

        with pytest.raises(Exception) as exc:
            manager.translate_multimodal("Test prompt")

        assert "API not configured" in str(exc.value)

    @patch('src.core.api_manager.genai')
    @patch('PIL.Image.open')
    def test_translate_multimodal_with_images(self, mock_pil, mock_genai):
        """Test multimodal translation with images."""
        import tempfile
        import os

        manager = AIAPIManager()
        manager.configure([
            {'model_name': 'gemini-2.0-flash', 'api_key': 'test-key', 'provider': 'Auto'}
        ])

        # Create a temp file to simulate image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name

        try:
            # Mock response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Image analysis result"
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            mock_image = MagicMock()
            mock_pil.return_value = mock_image

            result = manager.translate_multimodal(
                "Analyze this image",
                image_paths=[temp_path],
                file_contents={}
            )

            assert result == "Image analysis result"
        finally:
            os.unlink(temp_path)

    @patch('src.core.api_manager.genai')
    def test_translate_multimodal_with_file_contents(self, mock_genai):
        """Test multimodal translation with file contents."""
        manager = AIAPIManager()
        manager.configure([
            {'model_name': 'gemini-2.0-flash', 'api_key': 'test-key', 'provider': 'Auto'}
        ])

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "File translation result"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = manager.translate_multimodal(
            "Translate this file",
            image_paths=[],
            file_contents={'test.txt': 'Hello world'}
        )

        assert result == "File translation result"


class TestDisplayName:
    """Tests for provider display names."""

    def test_get_display_name(self):
        """Test getting display names for providers."""
        manager = AIAPIManager()

        assert manager.get_display_name('google') == 'Google (Gemini)'
        assert manager.get_display_name('openai') == 'OpenAI'
        assert manager.get_display_name('anthropic') == 'Anthropic (Claude)'
        assert manager.get_display_name('groq') == 'Groq'
        assert manager.get_display_name('unknown') == 'Unknown'


class TestConnectionTest:
    """Tests for connection testing."""

    @patch('src.core.api_manager.genai')
    def test_connection_success(self, mock_genai):
        """Test successful connection test."""
        manager = AIAPIManager()

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = manager.test_connection('gemini-2.0-flash', 'test-key')

        assert result == True

    @patch('src.core.api_manager.genai')
    def test_connection_failure(self, mock_genai):
        """Test failed connection test."""
        manager = AIAPIManager()

        mock_genai.configure.side_effect = Exception("Invalid API key")

        with pytest.raises(Exception):
            manager.test_connection('gemini-2.0-flash', 'invalid-key')
