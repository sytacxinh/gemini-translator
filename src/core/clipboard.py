"""
Clipboard management for AI Translator.
Handles saving, restoring, and manipulating clipboard content.
"""
import logging
from typing import Optional, Dict, Any

import pyperclip

# Windows-specific imports
try:
    import win32clipboard
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


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
        except Exception as e:
            logging.warning(f"Failed to save clipboard: {e}")
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
        except Exception as e:
            logging.warning(f"Failed to restore clipboard: {e}")
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
