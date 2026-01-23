"""
AI API Manager for AI Translator.
Handles communication with various AI providers (Google, OpenAI, Anthropic, Groq, etc.)
"""
import json
import urllib.request
import urllib.error
import logging
from typing import Optional

import google.generativeai as genai

from src.constants import MODEL_PROVIDER_MAP, API_KEY_PATTERNS


class AIAPIManager:
    """
    Manages AI API with primary/backup key fallback.
    Uses AI model for fast translations.
    Supports: Google Gemini, OpenAI, Anthropic, Groq, xAI, DeepSeek, Mistral, Perplexity,
              Cerebras, SambaNova, Together, SiliconFlow, OpenRouter.
    """

    MODEL_NAME = ''

    def __init__(self):
        self.api_configs = []
        self.notification_callback = None

    def configure(self, api_configs: list, notification_callback=None):
        """Configure the API with list of {model_name, api_key}."""
        self.api_configs = api_configs
        self.notification_callback = notification_callback

    def _identify_provider(self, model_name: str, api_key: str = "") -> str:
        """
        Identify API provider based on model name and API key format.

        Priority:
        1. Exact match in MODEL_PROVIDER_MAP (case-insensitive)
        2. Explicit provider prefix (openrouter/, together/, etc.)
        3. API key pattern (gsk_, sk-ant-, etc.)
        4. Model name pattern matching
        5. Default fallback
        """
        model = model_name.strip()
        model_lower = model.lower()
        key = api_key.strip()

        # 1. HIGHEST PRIORITY: Exact match in MODEL_PROVIDER_MAP
        for provider, models in MODEL_PROVIDER_MAP.items():
            for m in models:
                if m.lower() == model_lower:
                    return provider

        # 2. Check for explicit provider prefixes
        if model_lower.startswith('openrouter/'): return 'openrouter'
        if model_lower.startswith('together/') or model_lower.startswith('meta-llama/'): return 'together'
        if model_lower.startswith('silicon/') or model_lower.startswith('sf/'): return 'siliconflow'

        # 3. Model name contains "/" - likely Together or SiliconFlow format
        if '/' in model:
            # SiliconFlow patterns
            if any(model.startswith(p) for p in ['Qwen/', 'deepseek-ai/', 'THUDM/', '01-ai/', 'internlm/', 'Pro/']):
                return 'siliconflow'
            # Together patterns
            if any(model.startswith(p) for p in ['meta-llama/', 'mistralai/', 'google/']):
                return 'together'

        # 4. API Key Patterns
        for pattern, provider in API_KEY_PATTERNS.items():
            if key.startswith(pattern):
                return provider

        # 5. Proprietary Models
        if 'gemini' in model_lower:
            return 'google'
        if 'claude' in model_lower:
            return 'anthropic'
        if 'gpt' in model_lower or model_lower.startswith('o1') or model_lower.startswith('o3') or 'dall-e' in model_lower:
            return 'openai'
        if 'grok' in model_lower:
            return 'xai'

        # 6. Official Provider Models
        if model_lower.startswith('deepseek-'):
            return 'deepseek'

        if any(model_lower.startswith(p) for p in ['mistral-', 'codestral-', 'pixtral-', 'ministral-', 'open-mistral', 'open-mixtral']):
            return 'mistral'

        if 'sonar' in model_lower:
            return 'perplexity'

        # 7. Groq-specific model signatures
        groq_suffixes = ['-32768', '-8192', '-versatile', '-instant', '-preview', '-specdec']
        if any(model_lower.endswith(s) for s in groq_suffixes):
            return 'groq'

        if '/' not in model and any(model_lower.startswith(p) for p in ['llama3-', 'llama-3', 'gemma-', 'gemma2-', 'mixtral-', 'whisper-', 'distil-']):
            return 'groq'

        # 8. SambaNova: Meta-Llama-xxx format
        if model.startswith('Meta-Llama-'):
            return 'sambanova'

        # 9. Cerebras: llama3.1-xxx format (with dot)
        if model_lower.startswith('llama3.'):
            return 'cerebras'

        # 10. Generic fallback
        if 'qwen' in model_lower or model_lower.startswith('yi-'):
            return 'siliconflow'

        if any(x in model_lower for x in ['llama', 'mixtral', 'gemma', 'whisper']):
            return 'groq'

        return 'google'  # Ultimate fallback

    def _call_generic_openai_style(self, api_key: str, model_name: str, prompt: str, base_url: str) -> str:
        """Helper for OpenAI-compatible APIs."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }

        req = urllib.request.Request(
            base_url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content'].strip()

    def _call_anthropic(self, api_key: str, model_name: str, prompt: str) -> str:
        """Helper for Anthropic Claude API."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        data = {
            "model": model_name,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['content'][0]['text'].strip()

    def _generate_content(self, provider: str, api_key: str, model_name: str, prompt: str) -> str:
        """Route the request to the correct provider."""

        # --- Google (SDK) ---
        if provider == 'google':
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text.strip()

        # --- Anthropic ---
        elif provider == 'anthropic':
            return self._call_anthropic(api_key, model_name, prompt)

        # --- OpenAI Compatible APIs ---
        base_urls = {
            'openai': "https://api.openai.com/v1/chat/completions",
            'groq': "https://api.groq.com/openai/v1/chat/completions",
            'deepseek': "https://api.deepseek.com/chat/completions",
            'mistral': "https://api.mistral.ai/v1/chat/completions",
            'xai': "https://api.x.ai/v1/chat/completions",
            'perplexity': "https://api.perplexity.ai/chat/completions",
            'cerebras': "https://api.cerebras.ai/v1/chat/completions",
            'sambanova': "https://api.sambanova.ai/v1/chat/completions",
            'together': "https://api.together.xyz/v1/chat/completions",
            'siliconflow': "https://api.siliconflow.cn/v1/chat/completions",
            'openrouter': "https://openrouter.ai/api/v1/chat/completions",
        }

        if provider in base_urls:
            return self._call_generic_openai_style(api_key, model_name, prompt, base_urls[provider])

        raise Exception(f"Unknown provider: {provider}")

    def get_display_name(self, provider_code: str) -> str:
        """Get nice display name for provider."""
        display_map = {
            'google': 'Google (Gemini)',
            'openai': 'OpenAI',
            'anthropic': 'Anthropic (Claude)',
            'groq': 'Groq',
            'xai': 'xAI (Grok)',
            'deepseek': 'DeepSeek',
            'mistral': 'Mistral AI',
            'perplexity': 'Perplexity',
            'cerebras': 'Cerebras',
            'sambanova': 'SambaNova',
            'together': 'Together AI',
            'siliconflow': 'SiliconFlow',
            'openrouter': 'OpenRouter'
        }
        return display_map.get(provider_code.lower(), provider_code.title())

    def test_connection(self, model_name: str, api_key: str, provider: str = 'Auto') -> bool:
        """Test connection with a specific model and key."""
        try:
            target_provider = self._identify_provider(model_name, api_key) if provider == 'Auto' else provider.lower()
            self._generate_content(target_provider, api_key, model_name, "Say OK")
            return True
        except Exception as e:
            raise e

    def translate(self, prompt: str) -> str:
        """Translate text using configured keys with failover."""
        if not self.api_configs:
            raise Exception("API not configured. Please set your API key in Settings.")

        errors = []
        has_valid_key = False

        for i, config in enumerate(self.api_configs):
            api_key = config.get('api_key', '').strip()
            model_name = config.get('model_name', '').strip()
            provider = config.get('provider', 'Auto')

            if not api_key:
                continue

            if not model_name:
                error_msg = f"Key #{i+1}: Model name not specified."
                errors.append(error_msg)
                logging.warning(f"[API] {error_msg}")
                continue

            has_valid_key = True

            try:
                target_provider = self._identify_provider(model_name, api_key) if provider == 'Auto' else provider.lower()
                return self._generate_content(target_provider, api_key, model_name, prompt)
            except Exception as e:
                logging.warning(f"[API] Failed with {model_name} (Key #{i+1}): {e}")
                errors.append(f"{model_name}: {str(e)}")
                continue

        if not has_valid_key:
            raise Exception("No valid API key configured. Please add an API key in Settings.")

        raise Exception("All API keys failed.\n" + "\n".join(errors))
