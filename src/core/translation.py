"""
Translation Service for AI Translator.
Handles text translation using AI APIs with clipboard integration.
"""
import time
import queue
import logging
from typing import Optional

import keyboard

from src.constants import COOLDOWN
from src.core.clipboard import ClipboardManager
from src.core.api_manager import AIAPIManager


class TranslationService:
    """Handles all translation-related operations."""

    def __init__(self, config, notification_callback=None):
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
        has_custom_prompt = custom_prompt and custom_prompt.strip()

        if has_custom_prompt:
            # Has custom prompt → follow custom prompt, more flexible
            base_prompt = f"""Translate the following text to {target_language}.
Only return the translation, no explanations or additional text.
If the text is already in {target_language}, still provide a natural rephrasing.

Additional instructions from user: {custom_prompt}"""
        else:
            # No custom prompt (quick hotkey translation) → enforce target language
            base_prompt = f"""Translate the following text to {target_language}.

IMPORTANT: Your response MUST be in {target_language} only.
- Return ONLY the translation, no explanations or additional text
- If text is already in {target_language}, return it as-is or rephrase naturally IN {target_language}
- NEVER output in any language other than {target_language}
"""

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
        original_clipboard = ClipboardManager.save_clipboard()

        for attempt in range(3):
            try:
                ClipboardManager.set_text("")
                time.sleep(0.05)

                keyboard.press_and_release('ctrl+c')
                time.sleep(0.15 + (attempt * 0.1))

                new_text = ClipboardManager.get_text()
                if new_text and new_text.strip():
                    return new_text

            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")

        ClipboardManager.restore_clipboard(original_clipboard)
        return None

    def do_translation(self, target_language: str, callback=None, custom_prompt: str = ""):
        """Perform translation and put result in queue."""
        current_time = time.time()
        if current_time - self.last_translation_time < COOLDOWN:
            logging.info("Cooldown active, please wait...")
            self.translation_queue.put(("", "Please wait a moment...", target_language))
            return

        self.last_translation_time = current_time
        logging.info(f"Translating to {target_language}...")

        try:
            if not self._configure_api():
                error_msg = "Error: No API key configured.\n\nPlease add your AI API key in Settings."
                logging.warning(error_msg)
                self.translation_queue.put(("", error_msg, target_language))
                return

            selected_text = self.get_selected_text()

            if selected_text:
                logging.info(f"Selected text: {selected_text[:50]}...")
                translated = self.translate_text(selected_text, target_language, custom_prompt)
                logging.info("Translation complete!")
                self.translation_queue.put((selected_text, translated, target_language))
            else:
                error_msg = "No text selected. Please select text and try again."
                logging.warning(error_msg)
                self.translation_queue.put(("", error_msg, target_language))
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logging.error(error_msg)
            self.translation_queue.put(("", error_msg, target_language))
