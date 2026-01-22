"""
AI Translator v1.4.0
A Windows desktop application for instant text translation using AI models.
"""
import os
import sys
import time
import json
import queue
import socket
import threading
import webbrowser
import urllib.request
import urllib.error
from typing import Optional, Dict, Tuple, Any

import pyperclip
import keyboard
import google.generativeai as genai
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw
from packaging import version

import tkinter as tk
from tkinter import BOTH, X, Y, LEFT, RIGHT, W, NW, VERTICAL, END

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    HAS_TTKBOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    from tkinter import messagebox as Messagebox
    HAS_TTKBOOTSTRAP = False

# Windows-specific imports
try:
    import win32clipboard
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from config import Config

# ============== VERSION ==============
VERSION = "1.4.0"
GITHUB_REPO = "sytacxinh/ai-translator"

# ============== SINGLE INSTANCE LOCK ==============
LOCK_PORT = 47823

def is_already_running() -> Tuple[bool, Optional[socket.socket]]:
    """Check if another instance is already running using socket lock."""
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.bind(('127.0.0.1', LOCK_PORT))
        lock_socket.listen(1)
        return False, lock_socket
    except socket.error:
        return True, None

# ============== AVAILABLE LANGUAGES ==============
LANGUAGES = [
    ("Vietnamese", "vi", "Tiếng Việt"),
    ("English", "en", "English"),
    ("Japanese", "ja", "日本語"),
    ("Chinese Simplified", "zh-CN", "中文简体"),
    ("Chinese Traditional", "zh-TW", "中文繁體"),
    ("Korean", "ko", "한국어"),
    ("French", "fr", "Français"),
    ("German", "de", "Deutsch"),
    ("Spanish", "es", "Español"),
    ("Italian", "it", "Italiano"),
    ("Portuguese", "pt", "Português"),
    ("Russian", "ru", "Русский"),
    ("Thai", "th", "ไทย"),
    ("Indonesian", "id", "Bahasa Indonesia"),
    ("Malay", "ms", "Bahasa Melayu"),
    ("Hindi", "hi", "हिन्दी"),
    ("Arabic", "ar", "العربية"),
    ("Dutch", "nl", "Nederlands"),
    ("Polish", "pl", "Polski"),
    ("Turkish", "tr", "Türkçe"),
    ("Swedish", "sv", "Svenska"),
    ("Danish", "da", "Dansk"),
    ("Norwegian", "no", "Norsk"),
    ("Finnish", "fi", "Suomi"),
    ("Greek", "el", "Ελληνικά"),
    ("Czech", "cs", "Čeština"),
    ("Romanian", "ro", "Română"),
    ("Hungarian", "hu", "Magyar"),
    ("Ukrainian", "uk", "Українська"),
    ("Afrikaans", "af", "Afrikaans"),
    ("Albanian", "sq", "Shqip"),
    ("Amharic", "am", "አማርኛ"),
    ("Armenian", "hy", "Հայերեն"),
    ("Azerbaijani", "az", "Azərbaycan"),
    ("Basque", "eu", "Euskara"),
    ("Belarusian", "be", "Беларуская"),
    ("Bengali", "bn", "বাংলা"),
    ("Bosnian", "bs", "Bosanski"),
    ("Bulgarian", "bg", "Български"),
    ("Catalan", "ca", "Català"),
    ("Cebuano", "ceb", "Cebuano"),
    ("Chichewa", "ny", "Chichewa"),
    ("Corsican", "co", "Corsu"),
    ("Croatian", "hr", "Hrvatski"),
    ("Esperanto", "eo", "Esperanto"),
    ("Estonian", "et", "Eesti"),
    ("Filipino", "tl", "Filipino"),
    ("Frisian", "fy", "Frysk"),
    ("Galician", "gl", "Galego"),
    ("Georgian", "ka", "ქարთული"),
    ("Gujarati", "gu", "ગુજરાતી"),
    ("Haitian Creole", "ht", "Kreyòl Ayisyen"),
    ("Hausa", "ha", "Hausa"),
    ("Hawaiian", "haw", "Ōlelo Hawaiʻi"),
    ("Hebrew", "iw", "עברית"),
    ("Hmong", "hmn", "Hmoob"),
    ("Icelandic", "is", "Íslenska"),
    ("Igbo", "ig", "Igbo"),
    ("Irish", "ga", "Gaeilge"),
    ("Javanese", "jw", "Jawa"),
    ("Kannada", "kn", "ಕನ್ನಡ"),
    ("Kazakh", "kk", "Қазақ"),
    ("Khmer", "km", "ខ្მែរ"),
    ("Kurdish (Kurmanji)", "ku", "Kurdî"),
    ("Kyrgyz", "ky", "Кыргызча"),
    ("Lao", "lo", "ລາວ"),
    ("Latin", "la", "Latina"),
    ("Latvian", "lv", "Latviešu"),
    ("Lithuanian", "lt", "Lietuvių"),
    ("Luxembourgish", "lb", "Lëtzebuergesch"),
    ("Macedonian", "mk", "Македонски"),
    ("Malagasy", "mg", "Malagasy"),
    ("Malayalam", "ml", "മലയാളം"),
    ("Maltese", "mt", "Malti"),
    ("Maori", "mi", "Māori"),
    ("Marathi", "mr", "मराठी"),
    ("Mongolian", "mn", "Монгол"),
    ("Myanmar (Burmese)", "my", "မြန်မာ"),
    ("Nepali", "ne", "नेपाली"),
    ("Pashto", "ps", "پښتو"),
    ("Persian", "fa", "فارسی"),
    ("Punjabi", "pa", "ਪੰਜਾਬੀ"),
    ("Samoan", "sm", "Gagana faʻa Sāmoa"),
    ("Scots Gaelic", "gd", "Gàidhlig"),
    ("Serbian", "sr", "Српски"),
    ("Sesotho", "st", "Sesotho"),
    ("Shona", "sn", "chiShona"),
    ("Sindhi", "sd", "سنڌي"),
    ("Sinhala", "si", "සිංහල"),
    ("Slovak", "sk", "Slovenčina"),
    ("Slovenian", "sl", "Slovenščina"),
    ("Somali", "so", "Soomaali"),
    ("Sundanese", "su", "Basa Sunda"),
    ("Swahili", "sw", "Kiswahili"),
    ("Tajik", "tg", "Тоҷикӣ"),
    ("Tamil", "ta", "தமிழ்"),
    ("Telugu", "te", "తెలుగు"),
    ("Urdu", "ur", "اردو"),
    ("Uzbek", "uz", "Oʻzbek"),
    ("Welsh", "cy", "Cymraeg"),
    ("Xhosa", "xh", "isiXhosa"),
    ("Yiddish", "yi", "ייִדיש"),
    ("Yoruba", "yo", "Yorùbá"),
    ("Zulu", "zu", "isiZulu"),
]

COOLDOWN = 2.0

PROVIDERS_LIST = [
    "Auto", "Google", "OpenAI", "Anthropic", "DeepSeek",
    "Groq", "xAI", "Mistral", "Perplexity", "Cerebras",
    "SambaNova", "Together", "SiliconFlow", "OpenRouter"
]

# ============== MODEL DATABASE FOR ACCURATE PROVIDER DETECTION ==============
# Maps specific model patterns to their native providers
MODEL_PROVIDER_MAP = {
    # === GROQ (có suffix context window như -32768, -8192, hoặc -versatile, -instant) ===
    'groq': [
        'llama-3.1-70b-versatile', 'llama-3.1-8b-instant', 'llama-3.2-1b-preview',
        'llama-3.2-3b-preview', 'llama-3.2-11b-vision-preview', 'llama-3.2-90b-vision-preview',
        'llama-3.3-70b-versatile', 'llama-3.3-70b-specdec',
        'llama3-70b-8192', 'llama3-8b-8192', 'llama-guard-3-8b',
        'mixtral-8x7b-32768', 'gemma-7b-it', 'gemma2-9b-it',
        'whisper-large-v3', 'whisper-large-v3-turbo', 'distil-whisper-large-v3-en',
    ],
    # === MISTRAL AI (Official - tên có dạng mistral-xxx-latest hoặc codestral) ===
    'mistral': [
        'mistral-large-latest', 'mistral-large-2411', 'mistral-large-2407',
        'mistral-medium-latest', 'mistral-small-latest', 'mistral-small-2409',
        'ministral-8b-latest', 'ministral-3b-latest',
        'open-mistral-nemo', 'open-mistral-7b', 'open-mixtral-8x7b', 'open-mixtral-8x22b',
        'codestral-latest', 'codestral-mamba-latest',
        'pixtral-large-latest', 'pixtral-12b-latest',
    ],
    # === DEEPSEEK (Official) ===
    'deepseek': [
        'deepseek-chat', 'deepseek-coder', 'deepseek-reasoner',
    ],
    # === XAI (Grok) ===
    'xai': [
        'grok-beta', 'grok-vision-beta', 'grok-2', 'grok-2-vision', 'grok-2-1212',
    ],
    # === PERPLEXITY (có prefix sonar hoặc llama-3.1-sonar) ===
    'perplexity': [
        'sonar', 'sonar-pro', 'sonar-reasoning', 'sonar-reasoning-pro',
        'llama-3.1-sonar-small-128k-online', 'llama-3.1-sonar-large-128k-online',
        'llama-3.1-sonar-huge-128k-online',
    ],
    # === CEREBRAS (Llama cực nhanh) ===
    'cerebras': [
        'llama3.1-8b', 'llama3.1-70b', 'llama-3.3-70b',
    ],
    # === SAMBANOVA (Llama 405B full precision miễn phí) ===
    'sambanova': [
        'Meta-Llama-3.1-8B-Instruct', 'Meta-Llama-3.1-70B-Instruct',
        'Meta-Llama-3.1-405B-Instruct', 'Meta-Llama-3.2-1B-Instruct',
        'Meta-Llama-3.2-3B-Instruct', 'Meta-Llama-3.3-70B-Instruct',
    ],
    # === TOGETHER (format: owner/model-name) ===
    'together': [
        'meta-llama/Llama-3.2-3B-Instruct-Turbo', 'meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo',
        'meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo', 'meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo',
        'meta-llama/Llama-3.3-70B-Instruct-Turbo',
        'mistralai/Mixtral-8x7B-Instruct-v0.1', 'mistralai/Mistral-7B-Instruct-v0.3',
        'Qwen/Qwen2.5-7B-Instruct-Turbo', 'Qwen/Qwen2.5-72B-Instruct-Turbo',
        'google/gemma-2-9b-it', 'google/gemma-2-27b-it',
        'deepseek-ai/deepseek-llm-67b-chat',
    ],
    # === SILICONFLOW (format: owner/model-name, server TQ) ===
    'siliconflow': [
        'Qwen/Qwen2.5-7B-Instruct', 'Qwen/Qwen2.5-14B-Instruct', 'Qwen/Qwen2.5-32B-Instruct',
        'Qwen/Qwen2.5-72B-Instruct', 'Qwen/Qwen2.5-Coder-7B-Instruct',
        'Qwen/QwQ-32B-Preview', 'Qwen/Qwen2-VL-72B-Instruct',
        'deepseek-ai/DeepSeek-V3', 'deepseek-ai/DeepSeek-V2.5', 'deepseek-ai/DeepSeek-Coder-V2-Instruct',
        'THUDM/glm-4-9b-chat', 'internlm/internlm2_5-7b-chat',
        '01-ai/Yi-1.5-9B-Chat', '01-ai/Yi-1.5-34B-Chat',
        'Pro/Qwen/Qwen2.5-7B-Instruct', 'Pro/deepseek-ai/DeepSeek-V3',
    ],
}

# API Key Patterns (chính xác nhất)
API_KEY_PATTERNS = {
    'gsk_': 'groq',           # Groq keys start with gsk_
    'sk-ant-': 'anthropic',   # Anthropic keys start with sk-ant-
    'xai-': 'xai',            # xAI keys start with xai-
    'sk-or-v1-': 'openrouter', # OpenRouter keys
    'pplx-': 'perplexity',    # Perplexity keys
    # Note: sk- is used by OpenAI, DeepSeek, Together, SiliconFlow - cần dựa vào model name
}


# ============== CLIPBOARD MANAGER ==============
class ClipboardManager:
    """Manages clipboard operations with proper preservation of content."""

    @staticmethod
    def save_clipboard() -> Optional[Dict[int, Any]]:
        """Save current clipboard content including files/images."""
        if not HAS_WIN32:
            try:
                return {'text': pyperclip.paste()}
            except:
                return None

        try:
            win32clipboard.OpenClipboard()
            formats = []
            fmt = win32clipboard.EnumClipboardFormats(0)
            while fmt:
                formats.append(fmt)
                fmt = win32clipboard.EnumClipboardFormats(fmt)

            saved = {}
            for fmt in formats:
                try:
                    saved[fmt] = win32clipboard.GetClipboardData(fmt)
                except:
                    pass
            return saved
        except:
            return None
        finally:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass

    @staticmethod
    def restore_clipboard(saved: Optional[Dict[int, Any]]):
        """Restore saved clipboard content."""
        if not saved:
            return

        if not HAS_WIN32:
            if 'text' in saved:
                try:
                    pyperclip.copy(saved['text'])
                except:
                    pass
            return

        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            for fmt, data in saved.items():
                try:
                    win32clipboard.SetClipboardData(fmt, data)
                except:
                    pass
        except:
            pass
        finally:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass

    @staticmethod
    def set_text(text: str):
        """Set clipboard to text."""
        if HAS_WIN32:
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
            except:
                pyperclip.copy(text)
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except:
                    pass
        else:
            pyperclip.copy(text)

    @staticmethod
    def get_text() -> str:
        """Get text from clipboard."""
        try:
            return pyperclip.paste()
        except:
            return ""


# ============== AI API MANAGER ==============
class AIAPIManager:
    """
    Manages AI API with primary/backup key fallback.
    Uses AI model for fast translations.
    Supports: Google Gemini, OpenAI, Anthropic, Groq, xAI, DeepSeek, Mistral, Perplexity.
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
        Updated 2026: Uses MODEL_PROVIDER_MAP for accurate detection.

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

        # 2. Check for explicit provider prefixes (Recommended usage: 'provider/model')
        if model_lower.startswith('openrouter/'): return 'openrouter'
        if model_lower.startswith('together/') or model_lower.startswith('meta-llama/'): return 'together'
        if model_lower.startswith('silicon/') or model_lower.startswith('sf/'): return 'siliconflow'

        # 3. Model name contains "/" - likely Together or SiliconFlow format
        if '/' in model:
            # SiliconFlow patterns: Qwen/, deepseek-ai/, THUDM/, 01-ai/, Pro/
            if any(model.startswith(p) for p in ['Qwen/', 'deepseek-ai/', 'THUDM/', '01-ai/', 'internlm/', 'Pro/']):
                return 'siliconflow'
            # Together patterns: meta-llama/, mistralai/, google/
            if any(model.startswith(p) for p in ['meta-llama/', 'mistralai/', 'google/']):
                return 'together'
            # OpenRouter catches most with sk-or key or openrouter/ prefix

        # 4. API Key Patterns (chính xác cho những provider có key đặc biệt)
        for pattern, provider in API_KEY_PATTERNS.items():
            if key.startswith(pattern):
                return provider

        # 5. Proprietary Models (Specific SDK or Unique API)
        if 'gemini' in model_lower:
            return 'google'
        if 'claude' in model_lower:
            return 'anthropic'
        if 'gpt' in model_lower or model_lower.startswith('o1') or model_lower.startswith('o3') or 'dall-e' in model_lower:
            return 'openai'
        if 'grok' in model_lower:
            return 'xai'

        # 6. Official Provider Models (based on model naming conventions)
        # DeepSeek Official: deepseek-chat, deepseek-coder, deepseek-reasoner
        if model_lower.startswith('deepseek-'):
            return 'deepseek'

        # Mistral AI Official: mistral-xxx-latest, codestral-xxx, pixtral-xxx, ministral-xxx
        if any(model_lower.startswith(p) for p in ['mistral-', 'codestral-', 'pixtral-', 'ministral-', 'open-mistral', 'open-mixtral']):
            return 'mistral'

        # Perplexity: sonar models
        if 'sonar' in model_lower:
            return 'perplexity'

        # 7. Groq-specific model signatures (suffix -32768, -8192, -versatile, -instant, -preview, -specdec)
        groq_suffixes = ['-32768', '-8192', '-versatile', '-instant', '-preview', '-specdec']
        if any(model_lower.endswith(s) for s in groq_suffixes):
            return 'groq'

        # Groq model patterns: llama3-xxx, gemma-xxx, gemma2-xxx (without /)
        if '/' not in model and any(model_lower.startswith(p) for p in ['llama3-', 'llama-3', 'gemma-', 'gemma2-', 'mixtral-', 'whisper-', 'distil-']):
            return 'groq'

        # 8. SambaNova: Meta-Llama-xxx format (PascalCase)
        if model.startswith('Meta-Llama-'):
            return 'sambanova'

        # 9. Cerebras: llama3.1-xxx format (with dot)
        if model_lower.startswith('llama3.'):
            return 'cerebras'

        # 10. Generic fallback for remaining cases
        # If model contains 'qwen' or 'yi' without '/', assume user wants official API
        if 'qwen' in model_lower or model_lower.startswith('yi-'):
            return 'siliconflow'

        # If nothing matches and it's a generic name, default to Groq (fast & free)
        if any(x in model_lower for x in ['llama', 'mixtral', 'gemma', 'whisper']):
            return 'groq'

        return 'google'  # Ultimate fallback

    def _call_generic_openai_style(self, api_key: str, model_name: str, prompt: str, base_url: str) -> str:
        """Helper for OpenAI-compatible APIs (OpenAI, Groq, xAI)."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
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
        """Route the request to the correct provider with updated Base URLs."""
        
        # --- Google (SDK) ---
        if provider == 'google':
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text.strip()
            
        # --- Anthropic (SDK/Custom REST) ---
        elif provider == 'anthropic':
            return self._call_anthropic(api_key, model_name, prompt)
            
        # --- OpenAI Compatible APIs (Standard Format) ---
        base_url = ""
        
        if provider == 'openai':
            base_url = "https://api.openai.com/v1/chat/completions"
            
        elif provider == 'groq':
            base_url = "https://api.groq.com/openai/v1/chat/completions"
            
        elif provider == 'deepseek':
            base_url = "https://api.deepseek.com/chat/completions"
            
        elif provider == 'mistral':
            base_url = "https://api.mistral.ai/v1/chat/completions"
            
        elif provider == 'xai':
            base_url = "https://api.x.ai/v1/chat/completions"
            
        elif provider == 'perplexity':
            base_url = "https://api.perplexity.ai/chat/completions"
            
        # --- NEW PROVIDERS (2026) ---
        
        elif provider == 'cerebras':
            # Nhanh nhất thế giới cho Llama. Key lấy tại: cloud.cerebras.ai
            base_url = "https://api.cerebras.ai/v1/chat/completions"
            
        elif provider == 'sambanova':
            # Chạy Llama 3.1 405B miễn phí. Key tại: cloud.sambanova.ai
            base_url = "https://api.sambanova.ai/v1/chat/completions"
            
        elif provider == 'together':
            # Rất nhiều model lạ. Key tại: api.together.xyz
            base_url = "https://api.together.xyz/v1/chat/completions"
            
        elif provider == 'siliconflow':
            # Tốt nhất cho Qwen 2.5, Yi, DeepSeek V3 (Server TQ). Key tại: siliconflow.cn
            base_url = "https://api.siliconflow.cn/v1/chat/completions"
            
        elif provider == 'openrouter':
            # Aggregator (Dùng 1 key cho tất cả). Key tại: openrouter.ai
            base_url = "https://openrouter.ai/api/v1/chat/completions"
            # Lưu ý: OpenRouter thường cần thêm header HTTP-Referer, 
            # nhưng hàm _call_generic_openai_style cơ bản vẫn chạy được.

        else:
            raise Exception(f"Unknown provider: {provider}")

        # Gọi hàm chung cho nhóm OpenAI-style
        return self._call_generic_openai_style(api_key, model_name, prompt, base_url)

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
        """
        Translate text using configured keys with failover.
        """
        if not self.api_configs:
            raise Exception("API not configured. Please set your API key in Settings.")

        errors = []
        has_valid_key = False
        
        for i, config in enumerate(self.api_configs):
            api_key = config.get('api_key', '').strip()
            model_name = config.get('model_name', '').strip()
            provider = config.get('provider', 'Auto')
            
            # Skip if no API key
            if not api_key:
                continue
            
            # Check if model name is provided by user
            if not model_name:
                error_msg = f"Key #{i+1}: Model name not specified. Please enter a model name in Settings."
                errors.append(error_msg)
                print(f"[API] {error_msg}")
                continue
            
            has_valid_key = True
                
            try:
                target_provider = self._identify_provider(model_name, api_key) if provider == 'Auto' else provider.lower()
                return self._generate_content(target_provider, api_key, model_name, prompt)
            except Exception as e:
                print(f"[API] Failed with {model_name} (Key #{i+1}): {e}")
                errors.append(f"{model_name}: {str(e)}")
                continue
        
        # If no valid key was found
        if not has_valid_key:
            raise Exception("No valid API key configured. Please add an API key in Settings.")
        
        raise Exception("All API keys failed.\n" + "\n".join(errors))


# ============== TRANSLATION SERVICE ==============
class TranslationService:
    """Handles all translation-related operations."""

    def __init__(self, config: Config, notification_callback=None):
        self.config = config
        self.api_manager = AIAPIManager()
        self.last_translation_time = 0
        self.translation_queue = queue.Queue()
        self.notification_callback = notification_callback
        self._configure_api()

    def _configure_api(self) -> bool:
        """Configure the AI API with all keys."""
        api_keys = self.config.get_api_keys()
        self.api_manager.configure(api_keys, self.notification_callback)
        
        # Check if there's at least one valid (non-empty) API key
        has_valid_key = False
        for config in api_keys:
            if config.get('api_key', '').strip():
                has_valid_key = True
                break
        
        return has_valid_key

    def reconfigure(self):
        """Reconfigure API (call after API key change)."""
        self._configure_api()

    def translate_text(self, text: str, target_language: str,
                       custom_prompt: Optional[str] = None) -> str:
        """Translate text to target language using AI API."""
        base_prompt = f"""Translate the following text to {target_language}.
Only return the translation, no explanations or additional text.
If the text is already in {target_language}, still provide a natural rephrasing.

If currency amounts are mentioned (like $, €, £, ¥, ₫, etc.), add the approximate
equivalent in the target language's local currency in parentheses after each amount.
Example: $100 (*~2,500,000 VND) or ¥1000 (*~$7)"""

        if custom_prompt and custom_prompt.strip():
            base_prompt += f"\n\nAdditional instructions from user: {custom_prompt}"

        prompt = f"{base_prompt}\n\nText to translate:\n{text}"

        try:
            return self.api_manager.translate(prompt)
        except Exception as e:
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
                return "Error: Invalid API key. Please check your API key in Settings."
            return f"Error: {error_msg}"

    def get_selected_text(self) -> Optional[str]:
        """Get currently selected text by simulating Ctrl+C."""
        # Save original clipboard
        original_clipboard = ClipboardManager.save_clipboard()

        # Try multiple times
        for attempt in range(3):
            try:
                # Clear clipboard
                ClipboardManager.set_text("")
                time.sleep(0.05)

                # Simulate Ctrl+C using keyboard library
                keyboard.press_and_release('ctrl+c')

                # Wait for clipboard
                time.sleep(0.15 + (attempt * 0.1))

                new_text = ClipboardManager.get_text()
                if new_text and new_text.strip():
                    return new_text

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")

        # Restore original clipboard if nothing was copied
        ClipboardManager.restore_clipboard(original_clipboard)
        return None

    def do_translation(self, target_language: str, callback=None, custom_prompt: str = ""):
        """Perform translation and put result in queue."""
        current_time = time.time()
        if current_time - self.last_translation_time < COOLDOWN:
            print(f"[{time.strftime('%H:%M:%S')}] Cooldown active, please wait...")
            self.translation_queue.put(("", "Please wait a moment...", target_language))
            return

        self.last_translation_time = current_time
        print(f"[{time.strftime('%H:%M:%S')}] Translating to {target_language}...")

        try:
            # Check if API is configured first
            if not self._configure_api():
                error_msg = "Error: No API key configured.\n\nPlease add your AI API key in Settings."
                print(f"[{time.strftime('%H:%M:%S')}] {error_msg}")
                self.translation_queue.put(("", error_msg, target_language))
                return
            
            selected_text = self.get_selected_text()

            if selected_text:
                print(f"[{time.strftime('%H:%M:%S')}] Selected text: {selected_text[:50]}...")
                translated = self.translate_text(selected_text, target_language, custom_prompt)
                print(f"[{time.strftime('%H:%M:%S')}] Translation complete!")
                self.translation_queue.put((selected_text, translated, target_language))
            else:
                error_msg = "No text selected. Please select text and try again."
                print(f"[{time.strftime('%H:%M:%S')}] {error_msg}")
                self.translation_queue.put(("", error_msg, target_language))
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[{time.strftime('%H:%M:%S')}] {error_msg}")
            self.translation_queue.put(("", error_msg, target_language))


# ============== HOTKEY MANAGER ==============
class HotkeyManager:
    """Manages global hotkeys using keyboard library."""

    def __init__(self, config: Config, callback):
        self.config = config
        self.callback = callback
        self.registered_hotkeys = []

    def register_hotkeys(self):
        """Register all configured hotkeys."""
        self.unregister_all()
        hotkeys = self.config.get_hotkeys()

        for language, combo in hotkeys.items():
            if combo:
                try:
                    keyboard.add_hotkey(
                        combo,
                        lambda l=language: self._on_hotkey(l),
                        suppress=True  # Suppress event to override other apps
                    )
                    self.registered_hotkeys.append(combo)
                    print(f"Registered hotkey: {combo} -> {language}")
                except Exception as e:
                    print(f"Failed to register hotkey {combo}: {e}")

    def _on_hotkey(self, language: str):
        """Handle hotkey press."""
        threading.Thread(target=lambda: self.callback(language), daemon=True).start()

    def unregister_all(self):
        """Unregister all hotkeys."""
        for combo in self.registered_hotkeys:
            try:
                keyboard.remove_hotkey(combo)
            except:
                pass
        self.registered_hotkeys.clear()


# ============== UPDATE CHECKER ==============
def check_for_updates() -> Dict[str, Any]:
    """Check GitHub for newer releases."""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'AITranslator'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        latest_version = data['tag_name'].lstrip('v')
        if version.parse(latest_version) > version.parse(VERSION):
            return {
                'available': True,
                'version': latest_version,
                'url': data['html_url'],
                'notes': data.get('body', '')
            }
    except Exception as e:
        print(f"Update check failed: {e}")

    return {'available': False}


# ============== SETTINGS WINDOW ==============
class SettingsWindow:
    """Settings dialog for configuring the application."""

    def __init__(self, parent, config: Config, on_save_callback=None):
        self.config = config
        self.on_save_callback = on_save_callback
        self.hotkey_entries = {}
        self.custom_rows = []
        self.api_rows = []
        self.recording_language = None

        # Use tk.Toplevel for better compatibility
        self.window = tk.Toplevel(parent)
        self.window.title("Settings - AI Translator")
        self.window.geometry("1400x650")
        self.window.resizable(True, True)
        self.window.configure(bg='#2b2b2b')

        # Center on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 1400) // 2
        y = (self.window.winfo_screenheight() - 650) // 2
        self.window.geometry(f"+{x}+{y}")

        # Make window modal and handle close properly
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        self.window.grab_set()
        self.window.focus_force()

        try:
            self._create_widgets()
        except Exception as e:
            print(f"Error creating settings widgets: {e}")
            import traceback
            traceback.print_exc()

    def _create_widgets(self):
        """Create settings UI."""
        if HAS_TTKBOOTSTRAP:
            notebook = ttk.Notebook(self.window, bootstyle="dark")
        else:
            notebook = ttk.Notebook(self.window)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Tab 1: General (moved to first position)
        general_frame = ttk.Frame(notebook, padding=20) if HAS_TTKBOOTSTRAP else ttk.Frame(notebook)
        notebook.add(general_frame, text="  General  ")
        self._create_general_tab(general_frame)

        # Tab 2: Hotkeys
        hotkey_frame = ttk.Frame(notebook, padding=20) if HAS_TTKBOOTSTRAP else ttk.Frame(notebook)
        notebook.add(hotkey_frame, text="  Hotkeys  ")
        self._create_hotkey_tab(hotkey_frame)

        # Tab 3: API Key
        api_frame = ttk.Frame(notebook, padding=20) if HAS_TTKBOOTSTRAP else ttk.Frame(notebook)
        notebook.add(api_frame, text="  API Key  ")
        self._create_api_tab(api_frame)

        # Buttons
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill=X, padx=10, pady=(0, 10))

        if HAS_TTKBOOTSTRAP:
            ttk.Button(btn_frame, text="Save", command=self._save,
                       bootstyle="success", width=15).pack(side=RIGHT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=self.window.destroy,
                       bootstyle="secondary", width=15).pack(side=RIGHT)
        else:
            ttk.Button(btn_frame, text="Save", command=self._save,
                       width=15).pack(side=RIGHT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=self.window.destroy,
                       width=15).pack(side=RIGHT)

    def _create_api_tab(self, parent):
        """Create API key settings tab."""
        self.api_rows = []
        self.api_canvas = None
        self.api_container = None

        ttk.Label(parent, text="API Configuration", font=('Segoe UI', 12, 'bold')).pack(anchor=W)
        ttk.Label(parent, text="Configure multiple models and keys for failover redundancy.",
                  font=('Segoe UI', 9)).pack(anchor=W, pady=(5, 10))

        # Scrollable container for API keys (no visible scrollbar)
        canvas = tk.Canvas(parent, highlightthickness=0, height=380)
        api_container = ttk.Frame(canvas)

        canvas.pack(fill=BOTH, expand=True)
        self.api_canvas = canvas
        self.api_container = api_container

        window_id = canvas.create_window((0, 0), window=api_container, anchor=NW)

        def _configure_canvas(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind('<Configure>', _configure_canvas)

        # Mousewheel scrolling only
        def _on_mousewheel(event):
            if canvas.winfo_exists() and canvas.winfo_ismapped():
                try:
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                except:
                    pass
        canvas.bind("<MouseWheel>", _on_mousewheel)
        api_container.bind("<MouseWheel>", _on_mousewheel)

        # Container for API rows (to keep them separate from buttons/footer)
        self.api_list_frame = ttk.Frame(api_container)
        self.api_list_frame.pack(fill=X, expand=True)

        # Load existing keys (Primary row always exists, empty by default)
        saved_keys = self.config.get_api_keys()
        if not saved_keys:
            saved_keys = [{'model_name': '', 'api_key': ''}]

        # Render rows
        for i, config in enumerate(saved_keys):
            is_primary = (i == 0)
            self._add_api_row(self.api_list_frame, config.get('model_name', ''), config.get('api_key', ''), config.get('provider', 'Auto'), is_primary)

        # Buttons frame: Delete All (left) + Add Backup (right)
        btn_frame = ttk.Frame(api_container)
        btn_frame.pack(fill=X, pady=15)

        if HAS_TTKBOOTSTRAP:
            ttk.Button(btn_frame, text="Delete All API Keys",
                       command=self._delete_all_keys,
                       bootstyle="danger", width=18).pack(side=LEFT)
            self.add_api_btn = ttk.Button(btn_frame, text="+ Add Backup Key",
                                        command=lambda: self._add_new_api_row(self.api_list_frame, canvas),
                                        bootstyle="success-outline", width=18)
        else:
            ttk.Button(btn_frame, text="Delete All API Keys",
                       command=self._delete_all_keys, width=18).pack(side=LEFT)
            self.add_api_btn = ttk.Button(btn_frame, text="+ Add Backup Key",
                                        command=lambda: self._add_new_api_row(self.api_list_frame, canvas), width=18)
        self.add_api_btn.pack(side=LEFT, padx=10)

        ttk.Label(api_container, text="Delete All: Removes all API keys from storage permanently.",
                  font=('Segoe UI', 8), foreground='#888888').pack(anchor=W, pady=(5, 0))

        # Supported Providers Table
        ttk.Separator(api_container).pack(fill=X, pady=15)
        ttk.Label(api_container, text="Supported Providers & Models:", font=('Segoe UI', 10, 'bold')).pack(anchor=W)
        
        providers_text = (
            "• Google: Gemini models\n"
            "• OpenAI: GPT-4, o1, o3\n"
            "• Anthropic: Claude models\n"
            "• DeepSeek: DeepSeek-V3, R1\n"
            "• Groq: Llama, Mixtral\n"
            "• xAI: Grok models\n"
            "• Mistral AI: Mistral models\n"
            "• Perplexity: Sonar models\n"
            "• Cerebras: Llama models\n"
            "• SambaNova: Llama 405B\n"
            "• Together AI: Open source models\n"
            "• SiliconFlow: Qwen, Yi models\n"
            "• OpenRouter: All models"
        )
        
        ttk.Label(api_container, text=providers_text, font=('Segoe UI', 9), 
                 foreground='#aaaaaa', justify=LEFT).pack(anchor=W, pady=(5, 10))

        # Update scroll region
        def update_scroll():
            api_container.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))
        self.window.after(100, update_scroll)

    def _add_api_row(self, parent, model, key, provider="Auto", is_primary=False):
        """Add a single API configuration row.

        Row format: Label + Model + API Key + Show + Test + Delete
        """
        row = ttk.Frame(parent)
        row.pack(fill=X, pady=5)

        # Row label (Primary or Backup #N)
        row_num = len(self.api_rows) + 1
        if is_primary:
            label_text = "Primary:"
        else:
            label_text = f"Backup {row_num - 1}:"
        ttk.Label(row, text=label_text, font=('Segoe UI', 9, 'bold'), width=10).pack(side=LEFT)

        # Provider Combobox
        provider_var = tk.StringVar(value=provider)
        ttk.Label(row, text="Provider:", font=('Segoe UI', 9)).pack(side=LEFT)
        provider_cb = ttk.Combobox(row, textvariable=provider_var, values=PROVIDERS_LIST, width=10, state="readonly")
        provider_cb.pack(side=LEFT, padx=(3, 8))

        # Model Name with placeholder
        model_var = tk.StringVar(value=model)
        ttk.Label(row, text="Model:", font=('Segoe UI', 9)).pack(side=LEFT)
        model_entry = ttk.Entry(row, textvariable=model_var, width=25)
        model_entry.pack(side=LEFT, padx=(3, 8))

        # Add placeholder for model entry
        model_placeholder = "gemini-2.0-flash"
        if not model:
            model_entry.insert(0, model_placeholder)
            model_entry.config(foreground='#888888')

        def on_model_focus_in(e):
            if model_entry.get() == model_placeholder:
                model_entry.delete(0, END)
                model_entry.config(foreground='white' if HAS_TTKBOOTSTRAP else 'black')

        def on_model_focus_out(e):
            if not model_entry.get():
                model_entry.insert(0, model_placeholder)
                model_entry.config(foreground='#888888')

        model_entry.bind('<FocusIn>', on_model_focus_in)
        model_entry.bind('<FocusOut>', on_model_focus_out)

        # API Key with placeholder
        key_var = tk.StringVar(value=key)
        ttk.Label(row, text="API Key:", font=('Segoe UI', 9)).pack(side=LEFT)

        key_entry = ttk.Entry(row, textvariable=key_var, width=80, show="*")
        key_entry.pack(side=LEFT, padx=(3, 5))

        # Store show state for this row
        show_state = {'showing': False}

        # Show button (per-row)
        def toggle_show_key():
            if show_state['showing']:
                key_entry.config(show="*")
                show_btn.config(text="Show")
                show_state['showing'] = False
            else:
                key_entry.config(show="")
                show_btn.config(text="Hide")
                show_state['showing'] = True

        if HAS_TTKBOOTSTRAP:
            show_btn = ttk.Button(row, text="Show", command=toggle_show_key,
                                  bootstyle="secondary-outline", width=5)
        else:
            show_btn = ttk.Button(row, text="Show", command=toggle_show_key, width=5)
        show_btn.pack(side=LEFT, padx=2)

        # Test Button
        test_label = ttk.Label(row, text="", width=15)

        if HAS_TTKBOOTSTRAP:
            ttk.Button(row, text="Test",
                       command=lambda: self._test_single_api(model_var.get(), key_var.get(), provider_var.get(), test_label, model_placeholder),
                       bootstyle="info-outline", width=5).pack(side=LEFT, padx=2)
        else:
            ttk.Button(row, text="Test",
                       command=lambda: self._test_single_api(model_var.get(), key_var.get(), provider_var.get(), test_label, model_placeholder),
                       width=5).pack(side=LEFT, padx=2)

        # Delete Button (only for backups)
        if not is_primary:
            if HAS_TTKBOOTSTRAP:
                ttk.Button(row, text="Delete",
                           command=lambda r=row, kv=key_var: self._delete_api_row(r, kv),
                           bootstyle="danger-outline", width=6).pack(side=LEFT, padx=2)
            else:
                ttk.Button(row, text="Delete",
                           command=lambda r=row, kv=key_var: self._delete_api_row(r, kv),
                           width=6).pack(side=LEFT, padx=2)

        test_label.pack(side=LEFT, padx=3)

        self.api_rows.append({
            'frame': row,
            'model_var': model_var,
            'provider_var': provider_var,
            'model_entry': model_entry,
            'model_placeholder': model_placeholder,
            'key_var': key_var,
            'key_entry': key_entry,
            'is_primary': is_primary
        })
        # Only update button if it exists (button is created after initial rows)
        if hasattr(self, 'add_api_btn'):
            self._update_api_add_button()

    def _add_new_api_row(self, container, canvas):
        """Add a new backup API row."""
        if len(self.api_rows) < 6: # 1 Primary + 5 Backups
            self._add_api_row(container, "", "")  # Empty model and key for new rows
            container.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))

    def _delete_api_row(self, row_frame, key_var):
        """Delete an API row from UI."""
        row_frame.destroy()
        self.api_rows = [r for r in self.api_rows if r['key_var'] != key_var]
        self._update_api_add_button()

    def _delete_all_keys(self):
        """Clear all API keys but keep models, and save immediately."""
        msg = "Are you sure you want to clear all API keys?\nThis will keep your model names but remove the keys.\nChanges will be saved immediately."
        if HAS_TTKBOOTSTRAP:
            result = Messagebox.yesno(msg, title="Confirm Clear", parent=self.window)
            if result != "Yes": return
        else:
            from tkinter import messagebox
            if not messagebox.askyesno("Confirm Clear", msg, parent=self.window): return

        # Clear keys in all rows
        for row in self.api_rows:
            row['key_var'].set("")
        
        # Save immediately as requested
        self._save_api_keys_to_config()
        
        if HAS_TTKBOOTSTRAP:
            Messagebox.show_info("All API keys have been cleared and saved.", title="Keys Cleared", parent=self.window)
        else:
            from tkinter import messagebox
            messagebox.showinfo("Keys Cleared", "All API keys have been cleared and saved.", parent=self.window)

    def _save_api_keys_to_config(self):
        """Save current API keys to config."""
        try:
            api_keys_list = []
            for row in self.api_rows:
                model = row['model_var'].get().strip()
                key = row['key_var'].get().strip()
                provider = row['provider_var'].get()
                # Don't save placeholder as model name
                if model == row.get('model_placeholder', ''):
                    model = ''
                if model or key:  # Only save if there's actual data
                    api_keys_list.append({'model_name': model, 'api_key': key, 'provider': provider})
            self.config.set_api_keys(api_keys_list)
        except Exception as e:
            print(f"Error saving API keys to config: {e}")
            import traceback
            traceback.print_exc()

    def _update_api_add_button(self):
        """Enable/disable add button based on limit."""
        if len(self.api_rows) >= 6:
            self.add_api_btn.configure(state='disabled')
        else:
            self.add_api_btn.configure(state='normal')

    def _test_single_api(self, model_name, api_key, provider, result_label, model_placeholder="gemini-2.0-flash"):
        """Test API connection."""
        model_name = model_name.strip()
        # Use placeholder as default if model is empty or is the placeholder text
        if not model_name or model_name == model_placeholder:
            model_name = model_placeholder
        api_key = api_key.strip()
        
        if HAS_TTKBOOTSTRAP:
            result_label.config(text="Testing...", bootstyle="warning")
        else:
            result_label.config(text="Testing...", foreground="orange")
        self.window.update()

        if not api_key:
            if HAS_TTKBOOTSTRAP:
                result_label.config(text="No API key", bootstyle="danger")
            else:
                result_label.config(text="No API key", foreground="red")
            return

        try:
            # Use the AIAPIManager to test, which now supports multi-provider logic
            api_manager = AIAPIManager()
            target_provider = api_manager._identify_provider(model_name, api_key) if provider == 'Auto' else provider.lower()
            api_manager.test_connection(model_name, api_key, provider)
            display_name = api_manager.get_display_name(target_provider)
            
            if HAS_TTKBOOTSTRAP:
                result_label.config(text="OK!", bootstyle="success")
                Messagebox.show_info(f"Connection Verified!\n\nProvider: {display_name}\nModel: {model_name}\nStatus: OK", title="Test Result", parent=self.window)
            else:
                result_label.config(text="OK!", foreground="green")
                from tkinter import messagebox
                messagebox.showinfo("Test Result", f"Connection Verified!\n\nProvider: {display_name}\nModel: {model_name}\nStatus: OK", parent=self.window)
        except Exception as e:
            error = str(e)
            
            # Try to identify provider for error message
            provider_name = "UNKNOWN"
            try:
                code = (AIAPIManager()._identify_provider(model_name, api_key) if provider == 'Auto' else provider)
                provider_name = AIAPIManager().get_display_name(code)
            except: pass
            
            if "API_KEY_INVALID" in error:
                if HAS_TTKBOOTSTRAP:
                    result_label.config(text="Invalid Key", bootstyle="danger")
                    Messagebox.show_error(f"Invalid API Key!\n\nProvider: {provider_name}\nModel: {model_name}\nError: {error}", title="Test Failed", parent=self.window)
                else:
                    result_label.config(text="Invalid Key", foreground="red")
                    from tkinter import messagebox
                    messagebox.showerror("Test Failed", f"Invalid API Key!\n\nProvider: {provider_name}\nModel: {model_name}\nError: {error}", parent=self.window)
            else:
                if HAS_TTKBOOTSTRAP:
                    result_label.config(text="Error", bootstyle="danger")
                    Messagebox.show_error(f"Connection Failed!\n\nProvider: {provider_name}\nModel: {model_name}\nError: {error}", title="Test Error", parent=self.window)
                else:
                    result_label.config(text="Error", foreground="red")
                    from tkinter import messagebox
                    messagebox.showerror("Test Error", f"Connection Failed!\n\nProvider: {provider_name}\nModel: {model_name}\nError: {error}", parent=self.window)

    def _create_hotkey_tab(self, parent):
        """Create hotkey settings tab."""
        # Clear previous entries
        self.hotkey_entries = {}
        self.custom_rows = []

        ttk.Label(parent, text="Keyboard Shortcuts", font=('Segoe UI', 12, 'bold')).pack(anchor=W)
        ttk.Label(parent, text="Click 'Edit' and press your desired key combination.",
                  font=('Segoe UI', 9)).pack(anchor=W, pady=(5, 15))

        # Scrollable frame for hotkeys
        canvas = tk.Canvas(parent, highlightthickness=0)
        hotkey_container = ttk.Frame(canvas)

        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        window_id = canvas.create_window((0, 0), window=hotkey_container, anchor=NW)

        def _configure_canvas(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind('<Configure>', _configure_canvas)

        def _on_mousewheel(event):
            if canvas.winfo_exists() and canvas.winfo_ismapped():
                try:
                    x, y = canvas.winfo_pointerxy()
                    cx, cy = canvas.winfo_rootx(), canvas.winfo_rooty()
                    cw, ch = canvas.winfo_width(), canvas.winfo_height()
                    if cx <= x <= cx+cw and cy <= y <= cy+ch:
                        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                except:
                    pass
        
        self.window.bind("<MouseWheel>", _on_mousewheel, add="+")

        # 1. Main Languages
        self.default_langs = ["Vietnamese", "English", "Japanese", "Chinese Simplified"]
        ttk.Label(hotkey_container, text="Main Languages", font=('Segoe UI', 10, 'bold')).pack(anchor=W, pady=(0, 10))

        saved_hotkeys = self.config.get_hotkeys()

        for lang in self.default_langs:
            current_key = saved_hotkeys.get(lang, self.config.DEFAULT_HOTKEYS.get(lang, ""))
            self._add_default_hotkey_row(hotkey_container, lang, current_key)

        ttk.Separator(hotkey_container).pack(fill=X, pady=20)

        # 2. Custom Languages
        ttk.Label(hotkey_container, text="Custom Languages", font=('Segoe UI', 10, 'bold')).pack(anchor=W, pady=(0, 10))

        self.custom_rows_frame = ttk.Frame(hotkey_container)
        self.custom_rows_frame.pack(fill=X)

        # Load existing custom hotkeys
        for lang, key in saved_hotkeys.items():
            if lang not in self.default_langs:
                self._add_custom_hotkey_row(self.custom_rows_frame, lang, key)

        # Add Button
        self.add_btn_frame = ttk.Frame(hotkey_container)
        self.add_btn_frame.pack(fill=X, pady=15)

        if HAS_TTKBOOTSTRAP:
            self.add_btn = ttk.Button(self.add_btn_frame, text="+ Add Language",
                                    command=lambda: self._add_new_custom_row(canvas, hotkey_container),
                                    bootstyle="success-outline")
        else:
            self.add_btn = ttk.Button(self.add_btn_frame, text="+ Add Language",
                                    command=lambda: self._add_new_custom_row(canvas, hotkey_container))
        self.add_btn.pack(side=LEFT)

        self._update_add_button_state()
        
        # Update scroll
        hotkey_container.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def _add_default_hotkey_row(self, parent, language, hotkey):
        """Add a row for default languages with Restore button."""
        row = ttk.Frame(parent)
        row.pack(fill=X, pady=5, padx=5)

        ttk.Label(row, text=f"{language}:", width=22, anchor=W).pack(side=LEFT)

        entry_var = tk.StringVar(value=hotkey)
        entry = ttk.Entry(row, textvariable=entry_var, width=22, state='readonly')
        entry.pack(side=LEFT, padx=5)
        self.hotkey_entries[language] = entry_var

        if HAS_TTKBOOTSTRAP:
            ttk.Button(row, text="Edit", command=lambda: self._start_record(entry, entry_var),
                       bootstyle="info-outline", width=8).pack(side=LEFT, padx=2)
            ttk.Button(row, text="Restore", 
                       command=lambda: entry_var.set(self.config.DEFAULT_HOTKEYS.get(language, "")),
                       bootstyle="secondary-outline", width=8).pack(side=LEFT, padx=2)
        else:
            ttk.Button(row, text="Edit", command=lambda: self._start_record(entry, entry_var), 
                       width=8).pack(side=LEFT, padx=2)
            ttk.Button(row, text="Restore", 
                       command=lambda: entry_var.set(self.config.DEFAULT_HOTKEYS.get(language, "")),
                       width=8).pack(side=LEFT, padx=2)

    def _add_custom_hotkey_row(self, parent, language, hotkey, is_new=False):
        """Add a row for custom languages with Delete button."""
        row = ttk.Frame(parent)
        row.pack(fill=X, pady=5, padx=5)

        lang_var = tk.StringVar(value=language)
        
        if is_new:
            # Filter available languages
            used_langs = self.default_langs + [r['lang_var'].get() for r in self.custom_rows]
            available = [l[0] for l in LANGUAGES if l[0] not in used_langs]
            all_langs = [l[0] for l in LANGUAGES]
            
            combo = ttk.Combobox(row, textvariable=lang_var, values=all_langs, width=20)
            combo.pack(side=LEFT)
            if available:
                combo.set(available[0])
        else:
            ttk.Label(row, text=f"{language}:", width=22, anchor=W).pack(side=LEFT)

        entry_var = tk.StringVar(value=hotkey)
        entry = ttk.Entry(row, textvariable=entry_var, width=22, state='readonly')
        entry.pack(side=LEFT, padx=5)

        if HAS_TTKBOOTSTRAP:
            ttk.Button(row, text="Edit", command=lambda: self._start_record(entry, entry_var),
                       bootstyle="info-outline", width=8).pack(side=LEFT, padx=2)
            ttk.Button(row, text="Delete", 
                       command=lambda: self._delete_custom_row(row, lang_var),
                       bootstyle="danger-outline", width=8).pack(side=LEFT, padx=2)
        else:
            ttk.Button(row, text="Edit", command=lambda: self._start_record(entry, entry_var),
                       width=8).pack(side=LEFT, padx=2)
            ttk.Button(row, text="Delete", 
                       command=lambda: self._delete_custom_row(row, lang_var),
                       width=8).pack(side=LEFT, padx=2)

        self.custom_rows.append({
            'frame': row,
            'lang_var': lang_var,
            'hotkey_var': entry_var
        })
        # Only update button if it exists (button is created after initial rows)
        if hasattr(self, 'add_btn'):
            self._update_add_button_state()

    def _add_new_custom_row(self, canvas, container):
        """Handle adding a new custom row."""
        if len(self.custom_rows) < 4:
            self._add_custom_hotkey_row(self.custom_rows_frame, "", "", is_new=True)
            container.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))

    def _delete_custom_row(self, row_frame, lang_var):
        """Delete a custom row."""
        row_frame.destroy()
        self.custom_rows = [r for r in self.custom_rows if r['lang_var'] != lang_var]
        self._update_add_button_state()

    def _update_add_button_state(self):
        """Enable/disable add button based on count."""
        if len(self.custom_rows) >= 4:
            self.add_btn.configure(state='disabled')
        else:
            self.add_btn.configure(state='normal')

    def _start_record(self, entry, entry_var):
        """Start recording hotkey."""
        entry.config(state='normal')
        entry.delete(0, END)
        entry.insert(0, "Press keys...")
        
        # Unhook any existing
        try:
            keyboard.unhook_all()
        except:
            pass
            
        # Hook with specific callback for this entry
        keyboard.hook(lambda e: self._on_key_record(e, entry_var, entry))

    def _on_key_record(self, event, entry_var, entry=None):
        """Handle key press during recording."""
        if event.event_type == 'down':
            name = keyboard.get_hotkey_name()
            entry_var.set(name)
            
            # Check if it's a modifier key
            modifiers = getattr(keyboard, 'all_modifiers', 
                              {'alt', 'alt gr', 'ctrl', 'left alt', 'left ctrl', 
                               'left shift', 'left windows', 'right alt', 'right ctrl', 
                               'right shift', 'right windows', 'shift', 'windows', 'cmd'})
            is_modifier = event.name in modifiers
            
            # If not a modifier, we assume the combo is complete
            if not is_modifier:
                keyboard.unhook_all()
                if entry:
                    entry.config(state='readonly')

    def _create_general_tab(self, parent):
        """Create general settings tab."""
        ttk.Label(parent, text="General Settings", font=('Segoe UI', 12, 'bold')).pack(anchor=W)

        # Auto-start
        ttk.Separator(parent).pack(fill=X, pady=15)
        self.autostart_var = tk.BooleanVar(value=self.config.is_autostart_enabled())
        if HAS_TTKBOOTSTRAP:
            ttk.Checkbutton(parent, text="Start AI Translator with Windows",
                            variable=self.autostart_var,
                            bootstyle="round-toggle-success").pack(anchor=W, pady=5)
        else:
            ttk.Checkbutton(parent, text="Start AI Translator with Windows",
                            variable=self.autostart_var).pack(anchor=W, pady=5)

        # Check for updates
        self.updates_var = tk.BooleanVar(value=self.config.get_check_updates())
        if HAS_TTKBOOTSTRAP:
            ttk.Checkbutton(parent, text="Check for updates on startup",
                            variable=self.updates_var,
                            bootstyle="round-toggle-success").pack(anchor=W, pady=5)
        else:
            ttk.Checkbutton(parent, text="Check for updates on startup",
                            variable=self.updates_var).pack(anchor=W, pady=5)

        # Restore Defaults button
        ttk.Separator(parent).pack(fill=X, pady=15)
        if HAS_TTKBOOTSTRAP:
            ttk.Button(parent, text="Restore Defaults", command=self._restore_defaults,
                       bootstyle="warning-outline", width=15).pack(anchor=W)
        else:
            ttk.Button(parent, text="Restore Defaults", command=self._restore_defaults,
                       width=15).pack(anchor=W)
        ttk.Label(parent, text="Reset hotkeys and settings to default values (keeps API keys)",
                  font=('Segoe UI', 8)).pack(anchor=W, pady=(2, 0))

        # About section
        ttk.Separator(parent).pack(fill=X, pady=20)
        ttk.Label(parent, text="About", font=('Segoe UI', 11, 'bold')).pack(anchor=W)
        ttk.Label(parent, text=f"AI Translator v{VERSION}").pack(anchor=W, pady=(5, 0))
        ttk.Label(parent, text="Supports multiple AI models with failover").pack(anchor=W)

        if HAS_TTKBOOTSTRAP:
            link_btn = ttk.Button(parent, text="View on GitHub",
                                  command=lambda: webbrowser.open(f"https://github.com/{GITHUB_REPO}"),
                                  bootstyle="link")
        else:
            link_btn = ttk.Button(parent, text="View on GitHub",
                                  command=lambda: webbrowser.open(f"https://github.com/{GITHUB_REPO}"))
        link_btn.pack(anchor=W, pady=5)

    def _save(self):
        """Save all settings."""
        # Save API keys list
        api_keys_list = []
        for row in self.api_rows:
            model = row['model_var'].get().strip()
            key = row['key_var'].get().strip()
            # Don't save placeholder as model name
            model_placeholder = row.get('model_placeholder', 'gemini-2.0-flash')
            if model == model_placeholder:
                model = ''
            api_keys_list.append({'model_name': model, 'api_key': key})
        self.config.set_api_keys(api_keys_list)

        # Save all hotkeys
        hotkeys = {}
        
        # 1. Default languages
        for lang, entry_var in self.hotkey_entries.items():
            value = entry_var.get().strip()
            if value and value != "Press keys...":
                hotkeys[lang] = value
                
        # 2. Custom languages
        for row in self.custom_rows:
            lang = row['lang_var'].get().strip()
            value = row['hotkey_var'].get().strip()
            if lang and value and value != "Press keys...":
                hotkeys[lang] = value
                
        self.config.set_hotkeys(hotkeys)

        # Save general settings
        self.config.set_autostart(self.autostart_var.get())
        self.config.set_check_updates(self.updates_var.get())

        if self.on_save_callback:
            self.on_save_callback()

    def _restore_defaults(self):
        """Restore all settings to defaults (except API keys)."""
        # Restore default hotkeys
        # Only for default languages
        for lang, entry_var in self.hotkey_entries.items():
            default_hotkey = self.config.DEFAULT_HOTKEYS.get(lang, "")
            entry_var.set(default_hotkey)
        
        # Note: We don't delete custom rows here to avoid data loss, 
        # but user can delete them manually.

        # Restore general settings
        self.autostart_var.set(False)
        self.updates_var.set(False)


# ============== API ERROR DIALOG ==============
class APIErrorDialog:
    """Professional error dialog for API key issues."""

    def __init__(self, parent, error_message: str = "", on_open_settings=None):
        self.on_open_settings = on_open_settings

        self.window = tk.Toplevel(parent)
        self.window.title("API Key Error - AI Translator")
        self.window.geometry("500x400")
        self.window.resizable(False, False)
        self.window.grab_set()

        # Center
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 500) // 2
        y = (self.window.winfo_screenheight() - 400) // 2
        self.window.geometry(f"+{x}+{y}")

        self._create_widgets(error_message)

    def _create_widgets(self, error_message: str):
        """Create error dialog UI."""
        main = ttk.Frame(self.window, padding=25) if HAS_TTKBOOTSTRAP else ttk.Frame(self.window)
        main.pack(fill=BOTH, expand=True)

        # Warning icon and title
        if HAS_TTKBOOTSTRAP:
            ttk.Label(main, text="API Key Error", font=('Segoe UI', 16, 'bold'),
                      bootstyle="danger").pack(anchor=W)
        else:
            lbl = ttk.Label(main, text="API Key Error", font=('Segoe UI', 16, 'bold'))
            lbl.pack(anchor=W)

        ttk.Label(main, text="Your AI API key is not working or not configured.",
                  font=('Segoe UI', 10), wraplength=450).pack(anchor=W, pady=(10, 20))

        # Instructions
        ttk.Label(main, text="How to fix:", font=('Segoe UI', 11, 'bold')).pack(anchor=W)

        instructions = ttk.Frame(main)
        instructions.pack(fill=X, pady=10)

        ttk.Label(instructions, text="1. Get a free API key at:",
                  font=('Segoe UI', 10)).pack(anchor=W)
        if HAS_TTKBOOTSTRAP:
            ttk.Button(instructions, text="https://aistudio.google.com/app/apikey",
                       command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
                       bootstyle="link").pack(anchor=W, padx=(15, 0))
        else:
            ttk.Button(instructions, text="https://aistudio.google.com/app/apikey",
                       command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey")).pack(anchor=W, padx=(15, 0))

        ttk.Label(instructions, text="\n2. Open Settings and enter your API key.",
                  font=('Segoe UI', 10)).pack(anchor=W)

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=X, pady=20)

        if self.on_open_settings:
            if HAS_TTKBOOTSTRAP:
                ttk.Button(btn_frame, text="Open Settings",
                           command=self._open_settings,
                           bootstyle="success", width=15).pack(side=LEFT)
            else:
                ttk.Button(btn_frame, text="Open Settings",
                           command=self._open_settings,
                           width=15).pack(side=LEFT)

        if HAS_TTKBOOTSTRAP:
            ttk.Button(btn_frame, text="Close", command=self.window.destroy,
                       bootstyle="secondary", width=15).pack(side=RIGHT)
        else:
            ttk.Button(btn_frame, text="Close", command=self.window.destroy,
                       width=15).pack(side=RIGHT)

    def _open_settings(self):
        """Open settings and close this dialog."""
        self.window.destroy()
        if self.on_open_settings:
            self.on_open_settings()


# ============== MAIN APP ==============
class TranslatorApp:
    """Main application class."""

    def __init__(self):
        # Initialize configuration
        self.config = Config()

        # Create root window
        if HAS_TTKBOOTSTRAP:
            self.root = ttk.Window(themename="darkly")
        else:
            self.root = tk.Tk()
        self.root.withdraw()

        # Handle root window close
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        # Initialize services
        self.translation_service = TranslationService(self.config)
        self.hotkey_manager = HotkeyManager(self.config, self._on_hotkey_translate)

        # UI state
        self.popup = None
        self.tooltip = None
        self.tray_icon = None
        self.running = True
        self.selected_language = "Vietnamese"
        self.filtered_languages = LANGUAGES.copy()

        # Current translation data
        self.current_original = ""
        self.current_translated = ""
        self.current_target_lang = ""
        self.settings_window = None
        
        # Dragging state
        self._drag_x = 0
        self._drag_y = 0

    def _on_hotkey_translate(self, language: str):
        """Handle hotkey translation request."""
        self.root.after(0, lambda: self.show_loading_tooltip(language))
        self.translation_service.do_translation(language)

    def show_loading_tooltip(self, target_lang: str):
        """Show loading indicator."""
        if self.tooltip:
            try:
                self.tooltip.destroy()
            except:
                pass
        
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.overrideredirect(True)
        self.tooltip.configure(bg='#2b2b2b')
        self.tooltip.attributes('-topmost', True)
        
        frame = ttk.Frame(self.tooltip, padding=10)
        frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(frame, text=f"⏳ Translating to {target_lang}...", 
                 font=('Segoe UI', 10), foreground='#ffffff', background='#2b2b2b').pack()
        
        mouse_x = self.root.winfo_pointerx()
        mouse_y = self.root.winfo_pointery()
        self.tooltip.geometry(f"+{mouse_x + 15}+{mouse_y + 20}")

    def calculate_tooltip_size(self, text: str) -> Tuple[int, int]:
        """Calculate optimal tooltip dimensions based on text content."""
        MAX_WIDTH = 800
        MAX_HEIGHT = self.root.winfo_screenheight() - 100
        MIN_WIDTH = 280
        MIN_HEIGHT = 100
        CHAR_WIDTH = 9
        LINE_HEIGHT = 26
        PADDING = 80

        char_count = len(text)
        line_count = text.count('\n') + 1

        # Width calculation
        if char_count < 35:
            width = max(char_count * CHAR_WIDTH + 60, MIN_WIDTH)
        elif char_count < 100:
            width = min(450, MAX_WIDTH)
        elif char_count < 300:
            width = min(600, MAX_WIDTH)
        else:
            width = MAX_WIDTH

        # Height calculation (add 1 extra line for better readability)
        chars_per_line = max((width - 50) // CHAR_WIDTH, 1)
        wrapped_lines = max(line_count, (char_count // chars_per_line) + 1) + 1  # +1 extra line
        height = min(wrapped_lines * LINE_HEIGHT + PADDING, MAX_HEIGHT)

        return int(width), int(max(height, MIN_HEIGHT))

    def show_tooltip(self, original: str, translated: str, target_lang: str):
        """Show compact tooltip near mouse cursor with translation result."""
        self.current_original = original
        self.current_translated = translated
        self.current_target_lang = target_lang

        # Close existing tooltip
        if self.tooltip:
            try:
                self.tooltip.destroy()
            except:
                pass

        # Check if this is an error message
        is_error = translated.startswith("Error:") or translated.startswith("No text")
        
        # Calculate size
        width, height = self.calculate_tooltip_size(translated)
        if is_error:
            height = max(height, 120)  # Ensure error messages have enough space

        # Create tooltip window
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.overrideredirect(True)
        
        # Handle close properly
        def on_tooltip_close():
            self.close_tooltip()
        
        self.tooltip.protocol("WM_DELETE_WINDOW", on_tooltip_close)
        
        # Color based on error status
        if is_error:
            self.tooltip.configure(bg='#3d1f1f')  # Dark red background for errors
        else:
            self.tooltip.configure(bg='#2b2b2b')

        # Set topmost initially, then remove so it can go behind other windows
        self.tooltip.attributes('-topmost', True)
        self.tooltip.after(100, lambda: self.tooltip.attributes('-topmost', False) if self.tooltip else None)

        # Bind dragging events to the window itself
        self.tooltip.bind("<Button-1>", self._start_move)
        self.tooltip.bind("<B1-Motion>", self._on_drag)

        # Main frame
        main_frame = ttk.Frame(self.tooltip, padding=15)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Bind dragging events to the main frame
        main_frame.bind("<Button-1>", self._start_move)
        main_frame.bind("<B1-Motion>", self._on_drag)

        # Translation text with color for errors
        text_height = max(1, (height - 80) // 26)
        text_fg = '#ff6b6b' if is_error else '#ffffff'  # Light red for errors
        
        self.tooltip_text = tk.Text(main_frame, wrap=tk.WORD, 
                                    bg='#3d1f1f' if is_error else '#2b2b2b', 
                                    fg=text_fg,
                                    font=('Segoe UI', 11), relief='flat',
                                    width=width // 9, height=text_height,
                                    borderwidth=0, highlightthickness=0)
        self.tooltip_text.insert('1.0', translated)
        self.tooltip_text.config(state='disabled')
        self.tooltip_text.pack(fill=BOTH, expand=True)

        # Mouse wheel scroll
        self.tooltip_text.bind('<MouseWheel>',
            lambda e: self.tooltip_text.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Button frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(12, 0))
        
        # Bind dragging events to the button frame
        btn_frame.bind("<Button-1>", self._start_move)
        btn_frame.bind("<B1-Motion>", self._on_drag)

        if not is_error:
            # Copy button (only show for success)
            copy_btn_kwargs = {"text": "Copy", "command": self.copy_from_tooltip, "width": 8}
            if HAS_TTKBOOTSTRAP:
                copy_btn_kwargs["bootstyle"] = "primary"
            self.tooltip_copy_btn = ttk.Button(btn_frame, **copy_btn_kwargs)
            self.tooltip_copy_btn.pack(side=LEFT)

            # Open Translator button (only show for success)
            open_btn_kwargs = {"text": "Open Translator", "command": self.open_full_translator, "width": 14}
            if HAS_TTKBOOTSTRAP:
                open_btn_kwargs["bootstyle"] = "success"
            ttk.Button(btn_frame, **open_btn_kwargs).pack(side=LEFT, padx=8)
        else:
            # For errors, show "Open Settings" button
            settings_btn_kwargs = {"text": "Open Settings", "command": self._open_settings_from_error, "width": 14}
            if HAS_TTKBOOTSTRAP:
                settings_btn_kwargs["bootstyle"] = "warning"
            ttk.Button(btn_frame, **settings_btn_kwargs).pack(side=LEFT, padx=8)

        # Close button
        close_btn_kwargs = {"text": "✕", "command": self.close_tooltip, "width": 3}
        if HAS_TTKBOOTSTRAP:
            close_btn_kwargs["bootstyle"] = "secondary"
        ttk.Button(btn_frame, **close_btn_kwargs).pack(side=RIGHT)

        # Position near mouse
        mouse_x = self.root.winfo_pointerx()
        mouse_y = self.root.winfo_pointery()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = mouse_x + 15
        y = mouse_y + 20

        if x + width > screen_width:
            x = mouse_x - width - 15
        if y + height > screen_height:
            y = mouse_y - height - 20

        self.tooltip.geometry(f"{width}x{height}+{x}+{y}")

        # Bindings
        self.tooltip.bind('<Escape>', lambda e: on_tooltip_close())

    def _start_move(self, event):
        """Record start position for dragging."""
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        """Handle dragging of the tooltip."""
        if not self.tooltip:
            return
        
        deltax = event.x - self._drag_x
        deltay = event.y - self._drag_y
        x = self.tooltip.winfo_x() + deltax
        y = self.tooltip.winfo_y() + deltay
        self.tooltip.geometry(f"+{x}+{y}")

    def _on_tooltip_focus_out(self, event):
        """Handle tooltip losing focus."""
        if self.tooltip:
            # Immediately close instead of using after()
            self.close_tooltip()

    def close_tooltip(self):
        """Close the tooltip."""
        if self.tooltip:
            try:
                if self.tooltip.winfo_exists():
                    self.tooltip.destroy()
            except:
                pass
            self.tooltip = None

    def copy_from_tooltip(self):
        """Copy translation from tooltip to clipboard."""
        pyperclip.copy(self.current_translated)
        self.tooltip_copy_btn.configure(text="Copied!")
        if self.tooltip:
            self.tooltip.after(1000, lambda: self._reset_copy_btn())

    def _reset_copy_btn(self):
        """Reset copy button text."""
        if self.tooltip and self.tooltip_copy_btn:
            try:
                self.tooltip_copy_btn.configure(text="Copy")
            except:
                pass

    def open_full_translator(self):
        """Close tooltip and open full translator window."""
        self.close_tooltip()
        self.show_popup(self.current_original, self.current_translated, self.current_target_lang)

    def show_main_window(self, icon=None, item=None):
        """Show main translator window from tray."""
        # Ensure runs on main thread
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda: self.show_main_window(icon, item))
            return

        # Prevent double-calling by checking if popup is being shown
        if hasattr(self, '_showing_popup') and self._showing_popup:
            return
        self._showing_popup = True
        try:
            self.show_popup("", "", self.selected_language)
        finally:
            # Reset after a short delay
            self.root.after(500, lambda: setattr(self, '_showing_popup', False))

    def show_popup(self, original: str, translated: str, target_lang: str):
        """Show the full translator popup window."""
        if self.popup:
            try:
                self.popup.destroy()
            except:
                pass
            self.popup = None

        # Use tk.Toplevel for better compatibility
        self.popup = tk.Toplevel(self.root)
        self.popup.title("AI Translator")
        self.popup.configure(bg='#2b2b2b')

        # Focus handlers for topmost behavior
        def on_popup_focus_in(e):
            self.popup.attributes('-topmost', True)
            self.popup.after(100, lambda: self.popup.attributes('-topmost', False) if self.popup else None)

        self.popup.bind('<FocusIn>', on_popup_focus_in)

        # Handle close button properly
        def on_popup_close():
            try:
                if self.popup and self.popup.winfo_exists():
                    self.popup.destroy()
            except:
                pass
            self.popup = None

        self.popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        self.popup.bind('<Escape>', lambda e: on_popup_close())

        # Window size and position
        screen_width = self.popup.winfo_screenwidth()
        screen_height = self.popup.winfo_screenheight()
        window_width = 1400
        window_height = 850
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.popup.geometry(f"{window_width}x{window_height}+{x}+{y}")

        if HAS_TTKBOOTSTRAP:
            main_frame = ttk.Frame(self.popup, padding=20)
        else:
            main_frame = ttk.Frame(self.popup)
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # ===== ORIGINAL TEXT =====
        ttk.Label(main_frame, text="Original:", font=('Segoe UI', 10)).pack(anchor=W)

        self.original_text = tk.Text(main_frame, height=6, wrap=tk.WORD,
                                     bg='#2b2b2b', fg='#cccccc',
                                     font=('Segoe UI', 11), relief='flat',
                                     padx=10, pady=10, insertbackground='white',
                                     undo=True, maxundo=-1)
        self.original_text.insert('1.0', original)
        self.original_text.pack(fill=X, pady=(5, 15))
        self.original_text.bind('<MouseWheel>',
            lambda e: self.original_text.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Undo/Redo bindings
        self.original_text.bind('<Control-z>', lambda e: self.original_text.edit_undo() or "break")
        self.original_text.bind('<Control-Z>', lambda e: self.original_text.edit_undo() or "break")
        self.original_text.bind('<Control-Shift-z>', lambda e: self.original_text.edit_redo() or "break")
        self.original_text.bind('<Control-Shift-Z>', lambda e: self.original_text.edit_redo() or "break")

        # ===== LANGUAGE SELECTOR =====
        ttk.Label(main_frame, text="Translate to:", font=('Segoe UI', 10)).pack(anchor=W)

        # Search box
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(main_frame, textvariable=self.search_var,
                                      font=('Segoe UI', 10))
        self.search_entry.pack(fill=X, pady=(5, 5))
        self.search_entry.insert(0, "Search language...")
        self.search_entry.bind('<FocusIn>', self._on_search_focus_in)
        self.search_entry.bind('<FocusOut>', self._on_search_focus_out)
        self.search_var.trace_add('write', self._filter_languages)

        # Language listbox (no visible scrollbar)
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=X, pady=(0, 15))

        self.lang_listbox = tk.Listbox(list_frame, height=3, bg='#2b2b2b', fg='#ffffff',
                                       font=('Segoe UI', 10), relief='flat',
                                       selectbackground='#0d6efd', selectforeground='white',
                                       activestyle='none', highlightthickness=0,
                                       borderwidth=0)
        self.lang_listbox.pack(fill=X)
        self.lang_listbox.bind('<MouseWheel>',
            lambda e: self.lang_listbox.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._populate_language_list()
        self.lang_listbox.bind('<<ListboxSelect>>', self._on_language_select)
        self._select_language_in_list(target_lang)

        # ===== CUSTOM PROMPT =====
        ttk.Label(main_frame, text="Custom prompt (optional):",
                  font=('Segoe UI', 10)).pack(anchor=W)

        self.custom_prompt_text = tk.Text(main_frame, height=4, wrap=tk.WORD,
                                          bg='#2b2b2b', fg='#cccccc',
                                          font=('Segoe UI', 10), relief='flat',
                                          padx=10, pady=10, insertbackground='white',
                                          undo=True, maxundo=-1)
        self.custom_prompt_text.pack(fill=X, pady=(5, 15))
        self.custom_prompt_text.bind('<MouseWheel>',
            lambda e: self.custom_prompt_text.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Undo/Redo bindings for custom prompt
        self.custom_prompt_text.bind('<Control-z>', lambda e: self.custom_prompt_text.edit_undo() or "break")
        self.custom_prompt_text.bind('<Control-Z>', lambda e: self.custom_prompt_text.edit_undo() or "break")
        self.custom_prompt_text.bind('<Control-Shift-z>', lambda e: self.custom_prompt_text.edit_redo() or "break")
        self.custom_prompt_text.bind('<Control-Shift-Z>', lambda e: self.custom_prompt_text.edit_redo() or "break")

        # Placeholder for custom prompt
        placeholder = "E.g., 'Make it formal' or 'Use casual tone'"
        self.custom_prompt_text.insert('1.0', placeholder)
        self.custom_prompt_text.config(fg='#666666')

        def on_custom_focus_in(e):
            if self.custom_prompt_text.get('1.0', 'end-1c') == placeholder:
                self.custom_prompt_text.delete('1.0', tk.END)
                self.custom_prompt_text.config(fg='#cccccc')

        def on_custom_focus_out(e):
            if not self.custom_prompt_text.get('1.0', 'end-1c').strip():
                self.custom_prompt_text.insert('1.0', placeholder)
                self.custom_prompt_text.config(fg='#666666')

        self.custom_prompt_text.bind('<FocusIn>', on_custom_focus_in)
        self.custom_prompt_text.bind('<FocusOut>', on_custom_focus_out)

        # ===== TRANSLATION OUTPUT =====
        ttk.Label(main_frame, text="Translation:", font=('Segoe UI', 10)).pack(anchor=W)

        self.trans_text = tk.Text(main_frame, height=10, wrap=tk.WORD,
                                  bg='#2b2b2b', fg='#ffffff',
                                  font=('Segoe UI', 12), relief='flat',
                                  padx=10, pady=10)
        self.trans_text.insert('1.0', translated)
        self.trans_text.config(state='disabled')  # Make read-only
        self.trans_text.pack(fill=BOTH, expand=True, pady=(5, 15))
        self.trans_text.bind('<MouseWheel>',
            lambda e: self.trans_text.yview_scroll(int(-1*(e.delta/120)), "units"))

        # ===== BUTTONS =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X)

        # Translate button
        if HAS_TTKBOOTSTRAP:
            self.translate_btn = ttk.Button(btn_frame,
                                            text=f"Translate → {self.selected_language}",
                                            command=self._do_retranslate,
                                            bootstyle="success", width=25)
        else:
            self.translate_btn = ttk.Button(btn_frame,
                                            text=f"Translate → {self.selected_language}",
                                            command=self._do_retranslate, width=25)
        self.translate_btn.pack(side=LEFT)

        # Copy button
        if HAS_TTKBOOTSTRAP:
            self.copy_btn = ttk.Button(btn_frame, text="Copy",
                                       command=self._copy_translation,
                                       bootstyle="primary", width=12)
        else:
            self.copy_btn = ttk.Button(btn_frame, text="Copy",
                                       command=self._copy_translation, width=12)
        self.copy_btn.pack(side=LEFT, padx=10)

        # Open Gemini button
        if HAS_TTKBOOTSTRAP:
            self.gemini_btn = ttk.Button(btn_frame, text="✦ Open Gemini",
                                         command=self._open_in_gemini,
                                         bootstyle="info", width=15)
        else:
            self.gemini_btn = ttk.Button(btn_frame, text="✦ Open Gemini",
                                         command=self._open_in_gemini, width=15)
        self.gemini_btn.pack(side=LEFT)

        # Close button
        if HAS_TTKBOOTSTRAP:
            ttk.Button(btn_frame, text="Close", command=on_popup_close,
                       bootstyle="secondary", width=12).pack(side=RIGHT)
        else:
            ttk.Button(btn_frame, text="Close", command=on_popup_close,
                       width=12).pack(side=RIGHT)

        self.popup.focus_force()

    def _populate_language_list(self):
        """Populate language listbox."""
        if not hasattr(self, 'lang_listbox'):
            return
        self.lang_listbox.delete(0, tk.END)
        for lang_name, lang_code, _ in self.filtered_languages:
            self.lang_listbox.insert(tk.END, f"{lang_name} ({lang_code})")

    def _filter_languages(self, *args):
        """Filter language list based on search."""
        if not hasattr(self, 'lang_listbox'):
            return

        search_term = self.search_var.get().lower()
        if search_term in ("", "search language..."):
            self.filtered_languages = LANGUAGES.copy()
        else:
            self.filtered_languages = []
            for lang_name, lang_code, lang_aliases in LANGUAGES:
                searchable = f"{lang_name} {lang_code} {lang_aliases}".lower()
                if search_term in searchable:
                    self.filtered_languages.append((lang_name, lang_code, lang_aliases))

        self._populate_language_list()

        if self.filtered_languages:
            self.lang_listbox.selection_set(0)
            self.selected_language = self.filtered_languages[0][0]
            self._update_translate_button()

    def _on_search_focus_in(self, event):
        """Handle search box focus in."""
        if self.search_entry.get() == "Search language...":
            self.search_entry.delete(0, tk.END)

    def _on_search_focus_out(self, event):
        """Handle search box focus out."""
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search language...")

    def _on_language_select(self, event):
        """Handle language selection."""
        selection = self.lang_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.filtered_languages):
                self.selected_language = self.filtered_languages[index][0]
                self._update_translate_button()

    def _select_language_in_list(self, lang_name: str):
        """Select a language in the listbox."""
        if not hasattr(self, 'lang_listbox'):
            return
        for i, (name, _, _) in enumerate(self.filtered_languages):
            if name == lang_name:
                self.lang_listbox.selection_clear(0, tk.END)
                self.lang_listbox.selection_set(i)
                self.lang_listbox.see(i)
                self.selected_language = name
                break
        self._update_translate_button()

    def _update_translate_button(self):
        """Update translate button text."""
        if hasattr(self, 'translate_btn'):
            self.translate_btn.configure(text=f"Translate → {self.selected_language}")

    def _do_retranslate(self):
        """Perform translation from popup."""
        original = self.original_text.get('1.0', tk.END).strip()
        if not original:
            return

        # Get custom prompt
        custom_prompt = self.custom_prompt_text.get('1.0', tk.END).strip()
        placeholder = "E.g., 'Make it formal' or 'Use casual tone'"
        if custom_prompt == placeholder:
            custom_prompt = ""

        self.translate_btn.configure(text="⏳ Translating...", state='disabled')
        self.popup.update()

        def translate_thread():
            translated = self.translation_service.translate_text(
                original, self.selected_language, custom_prompt)
            if self.popup:
                self.popup.after(0, lambda: self._update_translation(translated))

        threading.Thread(target=translate_thread, daemon=True).start()

    def _update_translation(self, translated: str):
        """Update translation result in popup."""
        self.trans_text.config(state='normal')  # Enable to update
        self.trans_text.delete('1.0', tk.END)
        self.trans_text.insert('1.0', translated)
        self.trans_text.config(state='disabled')  # Make read-only again
        self.translate_btn.configure(text=f"Translate → {self.selected_language}",
                                     state='normal')

    def _copy_translation(self):
        """Copy translation to clipboard."""
        translated = self.trans_text.get('1.0', tk.END).strip()
        pyperclip.copy(translated)
        self.copy_btn.configure(text="Copied!")
        self.popup.after(1000, lambda: self.copy_btn.configure(text="Copy"))

    def _open_in_gemini(self):
        """Open Gemini web with translation prompt."""
        original = self.original_text.get('1.0', tk.END).strip()
        if not original:
            return

        prompt = f"Translate the following text to {self.selected_language}:\n\n{original}"
        pyperclip.copy(prompt)
        self.gemini_btn.configure(text="Copied! Opening...")
        webbrowser.open("https://gemini.google.com/app")
        self.popup.after(2000, lambda: self.gemini_btn.configure(text="✦ Open Gemini"))

    def show_settings(self, icon=None, item=None):
        """Show settings window."""
        # Ensure runs on main thread
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda: self.show_settings(icon, item))
            return

        # Check if already open
        if self.settings_window and self.settings_window.window.winfo_exists():
            self.settings_window.window.lift()
            self.settings_window.window.focus_force()
            return

        def on_settings_save():
            self.translation_service.reconfigure()
            self.hotkey_manager.register_hotkeys()
            self._refresh_tray_menu()
            
            if HAS_TTKBOOTSTRAP:
                Messagebox.show_info("Settings saved successfully!", title="Saved", parent=self.settings_window.window)
            else:
                from tkinter import messagebox
                messagebox.showinfo("Saved", "Settings saved successfully!", parent=self.settings_window.window)

        self.settings_window = SettingsWindow(self.root, self.config, on_settings_save)

    def _open_settings_from_error(self):
        """Open settings from error tooltip."""
        self.close_tooltip()
        self.show_settings()

    def _refresh_tray_menu(self):
        """Refresh tray menu to reflect updated hotkeys."""
        if self.tray_icon:
            # Build new menu items
            menu_items = [
                MenuItem('Open Translator', self.show_main_window, default=True),
                MenuItem('─────────────', lambda: None, enabled=False),
            ]

            # Add all hotkeys (default + custom) from config
            all_hotkeys = self.config.get_all_hotkeys()
            for language, hotkey in all_hotkeys.items():
                display_hotkey = '+'.join(part.capitalize() for part in hotkey.split('+'))
                menu_items.append(
                    MenuItem(f'{display_hotkey} → {language}', lambda: None, enabled=False)
                )

            menu_items.extend([
                MenuItem('─────────────', lambda: None, enabled=False),
                MenuItem('Settings', self.show_settings),
                MenuItem('Quit', self.quit_app)
            ])

            self.tray_icon.menu = Menu(*menu_items)

    def _create_tray_icon(self):
        """Create system tray icon."""
        # Create icon image
        image = Image.new('RGB', (64, 64), color='#0d6efd')
        draw = ImageDraw.Draw(image)
        draw.text((18, 18), "T", fill='white')

        # Build menu items dynamically from config
        menu_items = [
            MenuItem('Open Translator', self.show_main_window, default=True),
            MenuItem('─────────────', lambda: None, enabled=False),
        ]

        # Add all hotkeys (default + custom) from config
        all_hotkeys = self.config.get_all_hotkeys()
        for language, hotkey in all_hotkeys.items():
            # Format hotkey for display (e.g., "win+alt+v" → "Win+Alt+V")
            display_hotkey = '+'.join(part.capitalize() for part in hotkey.split('+'))
            menu_items.append(
                MenuItem(f'{display_hotkey} → {language}', lambda: None, enabled=False)
            )

        menu_items.extend([
            MenuItem('─────────────', lambda: None, enabled=False),
            MenuItem('Settings', self.show_settings),
            MenuItem('Quit', self.quit_app)
        ])

        menu = Menu(*menu_items)

        self.tray_icon = Icon("AI Translator", image,
                             f"AI Translator v{VERSION}", menu)
        return self.tray_icon

    def quit_app(self, icon=None, item=None):
        """Quit the application."""
        self.running = False
        self.hotkey_manager.unregister_all()
        self.close_tooltip()
        if self.popup:
            try:
                if self.popup.winfo_exists():
                    self.popup.destroy()
            except:
                pass
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        try:
            if self.root.winfo_exists():
                self.root.quit()
        except:
            pass
        os._exit(0)

    def _check_queue(self):
        """Check translation queue for results."""
        try:
            while True:
                original, translated, target_lang = self.translation_service.translation_queue.get_nowait()
                if self.running:  # Check if still running
                    self.show_tooltip(original, translated, target_lang)
        except queue.Empty:
            pass

        if self.running and self.root.winfo_exists():
            self.root.after(100, self._check_queue)

    def _check_updates_async(self):
        """Check for updates asynchronously."""
        if not self.config.get_check_updates():
            return

        update_info = check_for_updates()
        if update_info['available']:
            self.root.after(0, lambda: self._show_update_notification(update_info))

    def _show_update_notification(self, update_info: Dict):
        """Show update notification."""
        if HAS_TTKBOOTSTRAP:
            result = Messagebox.yesno(
                f"A new version ({update_info['version']}) is available!\n\n"
                f"Current version: {VERSION}\n\n"
                "Would you like to download it?",
                title="Update Available",
                parent=self.root
            )
            if result == "Yes":
                webbrowser.open(update_info['url'])
        else:
            from tkinter import messagebox
            result = messagebox.askyesno(
                "Update Available",
                f"A new version ({update_info['version']}) is available!\n\n"
                f"Current version: {VERSION}\n\n"
                "Would you like to download it?"
            )
            if result:
                webbrowser.open(update_info['url'])

    def _show_api_error(self):
        """Show API error dialog."""
        APIErrorDialog(self.root, on_open_settings=self.show_settings)

    def run(self):
        """Run the application."""
        print("=" * 50)
        print(f"AI Translator v{VERSION}")
        print("=" * 50)
        print()
        print("Hotkeys:")
        for lang, hotkey in self.config.get_hotkeys().items():
            print(f"  {hotkey} → {lang}")
        print()
        print("Select any text, then press a hotkey to translate!")
        print()
        print("Listening...")
        print("-" * 50)

        # Check API key
        if not self.config.get_api_key():
            self.root.after(500, self._show_api_error)

        # Register hotkeys
        self.hotkey_manager.register_hotkeys()

        # Setup tray icon - use non-blocking approach
        self._create_tray_icon()
        # Run tray icon on separate thread with proper exception handling
        def run_tray_safe():
            try:
                self.tray_icon.run()
            except Exception as e:
                print(f"Tray icon error: {e}")
        
        tray_thread = threading.Thread(target=run_tray_safe, daemon=True)
        tray_thread.daemon = True
        tray_thread.start()

        # Check for updates
        threading.Thread(target=self._check_updates_async, daemon=True).start()

        # Start queue checker
        self.root.after(100, self._check_queue)

        # Run main loop (should now be responsive)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Main loop error: {e}")
        finally:
            self.quit_app()


# ============== MAIN ==============
if __name__ == "__main__":
    already_running, lock_socket = is_already_running()

    if already_running:
        root = tk.Tk()
        root.withdraw()
        if HAS_TTKBOOTSTRAP:
            Messagebox.show_warning(
                "AI Translator is already running!\n\n"
                "Check the system tray (bottom-right corner).",
                title="AI Translator"
            )
        else:
            from tkinter import messagebox
            messagebox.showwarning(
                "AI Translator",
                "AI Translator is already running!\n\n"
                "Check the system tray (bottom-right corner)."
            )
        root.destroy()
        sys.exit(0)

    app = TranslatorApp()
    app.run()
