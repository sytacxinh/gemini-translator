"""
Gemini Translator v1.2.0
A Windows desktop application for instant text translation using Google's Gemini AI.
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
VERSION = "1.2.0"
GITHUB_REPO = "sytacxinh/gemini-translator"

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
    ("English", "en", "Anh"),
    ("Japanese", "ja", "日本語 Nihongo"),
    ("Chinese Simplified", "zh-CN", "中文简体 Trung Quốc"),
    ("Chinese Traditional", "zh-TW", "中文繁體 Đài Loan"),
    ("Korean", "ko", "한국어 Hàn Quốc"),
    ("French", "fr", "Français Pháp"),
    ("German", "de", "Deutsch Đức"),
    ("Spanish", "es", "Español Tây Ban Nha"),
    ("Italian", "it", "Italiano Ý"),
    ("Portuguese", "pt", "Português Bồ Đào Nha"),
    ("Russian", "ru", "Русский Nga"),
    ("Thai", "th", "ไทย Thái"),
    ("Indonesian", "id", "Bahasa Indonesia"),
    ("Malay", "ms", "Bahasa Melayu Mã Lai"),
    ("Hindi", "hi", "हिन्दी Ấn Độ"),
    ("Arabic", "ar", "العربية Ả Rập"),
    ("Dutch", "nl", "Nederlands Hà Lan"),
    ("Polish", "pl", "Polski Ba Lan"),
    ("Turkish", "tr", "Türkçe Thổ Nhĩ Kỳ"),
    ("Swedish", "sv", "Svenska Thụy Điển"),
    ("Danish", "da", "Dansk Đan Mạch"),
    ("Norwegian", "no", "Norsk Na Uy"),
    ("Finnish", "fi", "Suomi Phần Lan"),
    ("Greek", "el", "Ελληνικά Hy Lạp"),
    ("Czech", "cs", "Čeština Séc"),
    ("Romanian", "ro", "Română Rumani"),
    ("Hungarian", "hu", "Magyar Hungary"),
    ("Ukrainian", "uk", "Українська Ukraina"),
]

COOLDOWN = 2.0


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


# ============== TRANSLATION SERVICE ==============
class TranslationService:
    """Handles all translation-related operations."""

    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self.last_translation_time = 0
        self.translation_queue = queue.Queue()
        self._configure_api()

    def _configure_api(self) -> bool:
        """Configure the Gemini API with the current API key."""
        api_key = self.config.get_api_key()
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
                return True
            except Exception as e:
                print(f"Failed to configure API: {e}")
        return False

    def reconfigure(self):
        """Reconfigure API (call after API key change)."""
        self._configure_api()

    def translate_text(self, text: str, target_language: str,
                       custom_prompt: Optional[str] = None) -> str:
        """Translate text to target language using Gemini API."""
        if not self.model:
            return "Error: API not configured. Please set your API key in Settings."

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
            response = self.model.generate_content(prompt)
            return response.text.strip()
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
            return

        self.last_translation_time = current_time
        print(f"[{time.strftime('%H:%M:%S')}] Translating to {target_language}...")

        try:
            selected_text = self.get_selected_text()

            if selected_text:
                print(f"[{time.strftime('%H:%M:%S')}] Selected text: {selected_text[:50]}...")
                translated = self.translate_text(selected_text, target_language, custom_prompt)
                print(f"[{time.strftime('%H:%M:%S')}] Translation complete!")
                self.translation_queue.put((selected_text, translated, target_language))
            else:
                print(f"[{time.strftime('%H:%M:%S')}] No text selected!")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")


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
                        suppress=False  # Don't suppress other keyboard input
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
            'User-Agent': 'GeminiTranslator'
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
        self.recording_language = None

        # Use tk.Toplevel for better compatibility
        self.window = tk.Toplevel(parent)
        self.window.title("Settings - Gemini Translator")
        self.window.geometry("600x550")
        self.window.resizable(False, False)
        self.window.configure(bg='#2b2b2b')

        # Center on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 600) // 2
        y = (self.window.winfo_screenheight() - 550) // 2
        self.window.geometry(f"+{x}+{y}")

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

        # Tab 1: API Key
        api_frame = ttk.Frame(notebook, padding=20) if HAS_TTKBOOTSTRAP else ttk.Frame(notebook)
        notebook.add(api_frame, text="  API Key  ")
        self._create_api_tab(api_frame)

        # Tab 2: Hotkeys
        hotkey_frame = ttk.Frame(notebook, padding=20) if HAS_TTKBOOTSTRAP else ttk.Frame(notebook)
        notebook.add(hotkey_frame, text="  Hotkeys  ")
        self._create_hotkey_tab(hotkey_frame)

        # Tab 3: General
        general_frame = ttk.Frame(notebook, padding=20) if HAS_TTKBOOTSTRAP else ttk.Frame(notebook)
        notebook.add(general_frame, text="  General  ")
        self._create_general_tab(general_frame)

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
        ttk.Label(parent, text="Gemini API Key", font=('Segoe UI', 12, 'bold')).pack(anchor=W)
        ttk.Label(parent, text="Enter your Google Gemini API key below.",
                  font=('Segoe UI', 9)).pack(anchor=W, pady=(5, 10))

        # API Key entry
        self.api_key_var = tk.StringVar(value=self.config.get_api_key())
        api_entry = ttk.Entry(parent, textvariable=self.api_key_var, width=60, show="*")
        api_entry.pack(fill=X, pady=(0, 10))

        # Show/hide toggle
        self.show_key_var = tk.BooleanVar(value=False)
        def toggle_show():
            api_entry.config(show="" if self.show_key_var.get() else "*")
        if HAS_TTKBOOTSTRAP:
            ttk.Checkbutton(parent, text="Show API key", variable=self.show_key_var,
                            command=toggle_show, bootstyle="round-toggle").pack(anchor=W)
        else:
            ttk.Checkbutton(parent, text="Show API key", variable=self.show_key_var,
                            command=toggle_show).pack(anchor=W)

        # Get API key link
        link_frame = ttk.Frame(parent)
        link_frame.pack(fill=X, pady=20)
        ttk.Label(link_frame, text="Don't have an API key?").pack(side=LEFT)
        if HAS_TTKBOOTSTRAP:
            link_btn = ttk.Button(link_frame, text="Get free API key",
                                  command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
                                  bootstyle="link")
        else:
            link_btn = ttk.Button(link_frame, text="Get free API key",
                                  command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"))
        link_btn.pack(side=LEFT, padx=5)

        # Test connection
        ttk.Separator(parent).pack(fill=X, pady=10)
        test_frame = ttk.Frame(parent)
        test_frame.pack(fill=X)
        if HAS_TTKBOOTSTRAP:
            ttk.Button(test_frame, text="Test Connection", command=self._test_api,
                       bootstyle="info-outline").pack(side=LEFT)
        else:
            ttk.Button(test_frame, text="Test Connection", command=self._test_api).pack(side=LEFT)
        self.test_result_label = ttk.Label(test_frame, text="")
        self.test_result_label.pack(side=LEFT, padx=10)

    def _test_api(self):
        """Test API connection."""
        if HAS_TTKBOOTSTRAP:
            self.test_result_label.config(text="Testing...", bootstyle="warning")
        else:
            self.test_result_label.config(text="Testing...", foreground="orange")
        self.window.update()

        api_key = self.api_key_var.get().strip()
        if not api_key:
            if HAS_TTKBOOTSTRAP:
                self.test_result_label.config(text="Please enter an API key", bootstyle="danger")
            else:
                self.test_result_label.config(text="Please enter an API key", foreground="red")
            return

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            model.generate_content("Say 'OK'")
            if HAS_TTKBOOTSTRAP:
                self.test_result_label.config(text="Connection successful!", bootstyle="success")
            else:
                self.test_result_label.config(text="Connection successful!", foreground="green")
        except Exception as e:
            error = str(e)
            if "API_KEY_INVALID" in error:
                if HAS_TTKBOOTSTRAP:
                    self.test_result_label.config(text="Invalid API key", bootstyle="danger")
                else:
                    self.test_result_label.config(text="Invalid API key", foreground="red")
            else:
                if HAS_TTKBOOTSTRAP:
                    self.test_result_label.config(text=f"Error: {error[:30]}...", bootstyle="danger")
                else:
                    self.test_result_label.config(text=f"Error: {error[:30]}...", foreground="red")

    def _create_hotkey_tab(self, parent):
        """Create hotkey settings tab."""
        ttk.Label(parent, text="Keyboard Shortcuts", font=('Segoe UI', 12, 'bold')).pack(anchor=W)
        ttk.Label(parent, text="Click 'Record' and press your desired key combination.",
                  font=('Segoe UI', 9)).pack(anchor=W, pady=(5, 15))

        # Scrollable frame for hotkeys
        canvas = tk.Canvas(parent, highlightthickness=0, height=300)
        scrollbar = ttk.Scrollbar(parent, orient=VERTICAL, command=canvas.yview)
        hotkey_container = ttk.Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        canvas.create_window((0, 0), window=hotkey_container, anchor=NW)

        hotkeys = self.config.get_hotkeys()

        # Default languages to show
        default_languages = ["Vietnamese", "English", "Japanese", "Chinese Simplified"]
        all_languages = default_languages + [lang for lang, _, _ in LANGUAGES
                                              if lang not in default_languages and lang in hotkeys]

        for lang in all_languages:
            self._add_hotkey_row(hotkey_container, lang, hotkeys.get(lang, ""))

        hotkey_container.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # Add language button
        add_frame = ttk.Frame(parent)
        add_frame.pack(fill=X, pady=10)

        self.add_lang_var = tk.StringVar()
        lang_names = [lang for lang, _, _ in LANGUAGES if lang not in all_languages]
        if lang_names:
            lang_combo = ttk.Combobox(add_frame, textvariable=self.add_lang_var,
                                       values=lang_names, width=25, state="readonly")
            lang_combo.pack(side=LEFT)
            if HAS_TTKBOOTSTRAP:
                ttk.Button(add_frame, text="+ Add Language",
                           command=lambda: self._add_language(hotkey_container, canvas),
                           bootstyle="success-outline").pack(side=LEFT, padx=10)
            else:
                ttk.Button(add_frame, text="+ Add Language",
                           command=lambda: self._add_language(hotkey_container, canvas)).pack(side=LEFT, padx=10)

    def _add_hotkey_row(self, parent, language: str, hotkey: str):
        """Add a hotkey configuration row."""
        row = ttk.Frame(parent)
        row.pack(fill=X, pady=5)

        ttk.Label(row, text=f"{language}:", width=20, anchor=W).pack(side=LEFT)

        entry_var = tk.StringVar(value=hotkey)
        entry = ttk.Entry(row, textvariable=entry_var, width=25)
        entry.pack(side=LEFT, padx=5)
        self.hotkey_entries[language] = entry_var

        def start_record():
            entry_var.set("Press keys...")
            self.recording_language = language
            keyboard.hook(lambda e: self._on_key_record(e, entry_var))

        if HAS_TTKBOOTSTRAP:
            ttk.Button(row, text="Record", command=start_record,
                       bootstyle="info-outline", width=8).pack(side=LEFT, padx=5)
        else:
            ttk.Button(row, text="Record", command=start_record,
                       width=8).pack(side=LEFT, padx=5)

        def clear_hotkey():
            entry_var.set("")
        if HAS_TTKBOOTSTRAP:
            ttk.Button(row, text="Clear", command=clear_hotkey,
                       bootstyle="secondary-outline", width=8).pack(side=LEFT)
        else:
            ttk.Button(row, text="Clear", command=clear_hotkey,
                       width=8).pack(side=LEFT)

    def _on_key_record(self, event, entry_var):
        """Handle key press during recording."""
        if event.event_type == 'down' and self.recording_language:
            keyboard.unhook_all()
            hotkey = keyboard.get_hotkey_name()
            entry_var.set(hotkey)
            self.recording_language = None

    def _add_language(self, container, canvas):
        """Add a new language hotkey row."""
        lang = self.add_lang_var.get()
        if lang and lang not in self.hotkey_entries:
            self._add_hotkey_row(container, lang, "")
            container.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))

    def _create_general_tab(self, parent):
        """Create general settings tab."""
        ttk.Label(parent, text="General Settings", font=('Segoe UI', 12, 'bold')).pack(anchor=W)

        # Auto-start
        ttk.Separator(parent).pack(fill=X, pady=15)
        self.autostart_var = tk.BooleanVar(value=self.config.is_autostart_enabled())
        if HAS_TTKBOOTSTRAP:
            ttk.Checkbutton(parent, text="Start Gemini Translator with Windows",
                            variable=self.autostart_var,
                            bootstyle="round-toggle-success").pack(anchor=W, pady=5)
        else:
            ttk.Checkbutton(parent, text="Start Gemini Translator with Windows",
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

        # About section
        ttk.Separator(parent).pack(fill=X, pady=20)
        ttk.Label(parent, text="About", font=('Segoe UI', 11, 'bold')).pack(anchor=W)
        ttk.Label(parent, text=f"Gemini Translator v{VERSION}").pack(anchor=W, pady=(5, 0))
        ttk.Label(parent, text="Powered by Google Gemini AI").pack(anchor=W)

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
        # Save API key
        self.config.set_api_key(self.api_key_var.get().strip())

        # Save hotkeys
        hotkeys = {}
        for lang, var in self.hotkey_entries.items():
            value = var.get().strip()
            if value and value != "Press keys...":
                hotkeys[lang] = value
        self.config.set_hotkeys(hotkeys)

        # Save general settings
        self.config.set_autostart(self.autostart_var.get())
        self.config.set_check_updates(self.updates_var.get())

        if self.on_save_callback:
            self.on_save_callback()

        self.window.destroy()


# ============== API ERROR DIALOG ==============
class APIErrorDialog:
    """Professional error dialog for API key issues."""

    def __init__(self, parent, error_message: str = "", on_open_settings=None):
        self.on_open_settings = on_open_settings

        self.window = tk.Toplevel(parent)
        self.window.title("API Key Error - Gemini Translator")
        self.window.geometry("500x400")
        self.window.resizable(False, False)
        self.window.transient(parent)
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

        ttk.Label(main, text="Your Gemini API key is not working or not configured.",
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

        ttk.Label(instructions, text="\n2. Open Settings and enter your API key, OR",
                  font=('Segoe UI', 10)).pack(anchor=W)

        ttk.Label(instructions, text="\n3. Create a .env file in the app folder with:",
                  font=('Segoe UI', 10)).pack(anchor=W)

        code_frame = ttk.Frame(instructions)
        code_frame.pack(anchor=W, padx=(15, 0), pady=5)
        if HAS_TTKBOOTSTRAP:
            ttk.Label(code_frame, text="GEMINI_API_KEY=your_api_key_here",
                      font=('Consolas', 10), bootstyle="secondary").pack()
        else:
            ttk.Label(code_frame, text="GEMINI_API_KEY=your_api_key_here",
                      font=('Consolas', 10)).pack()

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

    def _on_hotkey_translate(self, language: str):
        """Handle hotkey translation request."""
        self.translation_service.do_translation(language)

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

        # Calculate size
        width, height = self.calculate_tooltip_size(translated)

        # Create tooltip window
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes('-topmost', True)
        self.tooltip.configure(bg='#2b2b2b')

        # Main frame
        main_frame = ttk.Frame(self.tooltip, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # Translation text
        text_height = max(1, (height - 80) // 26)
        self.tooltip_text = tk.Text(main_frame, wrap=tk.WORD, bg='#2b2b2b', fg='#ffffff',
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

        # Copy button
        copy_btn_kwargs = {"text": "Copy", "command": self.copy_from_tooltip, "width": 8}
        if HAS_TTKBOOTSTRAP:
            copy_btn_kwargs["bootstyle"] = "primary"
        self.tooltip_copy_btn = ttk.Button(btn_frame, **copy_btn_kwargs)
        self.tooltip_copy_btn.pack(side=LEFT)

        # Open Translator button
        open_btn_kwargs = {"text": "Open Translator", "command": self.open_full_translator, "width": 14}
        if HAS_TTKBOOTSTRAP:
            open_btn_kwargs["bootstyle"] = "success"
        ttk.Button(btn_frame, **open_btn_kwargs).pack(side=LEFT, padx=8)

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
        self.tooltip.bind('<Escape>', lambda e: self.close_tooltip())
        self.tooltip.bind('<FocusOut>', self._on_tooltip_focus_out)
        self.tooltip.focus_force()

    def _on_tooltip_focus_out(self, event):
        """Handle tooltip losing focus."""
        if self.tooltip:
            self.tooltip.after(150, self._check_tooltip_focus)

    def _check_tooltip_focus(self):
        """Check if tooltip should close."""
        if self.tooltip:
            try:
                focused = self.root.focus_get()
                if focused is None or not str(focused).startswith(str(self.tooltip)):
                    self.close_tooltip()
            except:
                pass

    def close_tooltip(self):
        """Close the tooltip."""
        if self.tooltip:
            try:
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
        self.popup.title("Gemini Translator")
        self.popup.attributes('-topmost', True)
        self.popup.configure(bg='#2b2b2b')

        # Window size and position
        screen_width = self.popup.winfo_screenwidth()
        screen_height = self.popup.winfo_screenheight()
        window_width = 1000
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
                                     padx=10, pady=10, insertbackground='white')
        self.original_text.insert('1.0', original)
        self.original_text.pack(fill=X, pady=(5, 15))
        self.original_text.bind('<MouseWheel>',
            lambda e: self.original_text.yview_scroll(int(-1*(e.delta/120)), "units"))

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
                                          padx=10, pady=10, insertbackground='white')
        self.custom_prompt_text.pack(fill=X, pady=(5, 15))
        self.custom_prompt_text.bind('<MouseWheel>',
            lambda e: self.custom_prompt_text.yview_scroll(int(-1*(e.delta/120)), "units"))

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
            ttk.Button(btn_frame, text="Close", command=self.popup.destroy,
                       bootstyle="secondary", width=12).pack(side=RIGHT)
        else:
            ttk.Button(btn_frame, text="Close", command=self.popup.destroy,
                       width=12).pack(side=RIGHT)

        self.popup.bind('<Escape>', lambda e: self.popup.destroy())
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

        self.translate_btn.configure(text="Translating...", state='disabled')
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
        def on_settings_save():
            self.translation_service.reconfigure()
            self.hotkey_manager.register_hotkeys()

        SettingsWindow(self.root, self.config, on_settings_save)

    def _create_tray_icon(self):
        """Create system tray icon."""
        # Create icon image
        image = Image.new('RGB', (64, 64), color='#0d6efd')
        draw = ImageDraw.Draw(image)
        draw.text((18, 18), "GT", fill='white')

        menu = Menu(
            MenuItem('Open Translator', self.show_main_window, default=True),
            MenuItem('─────────────', lambda: None, enabled=False),
            MenuItem('Win+Alt+V → Vietnamese', lambda: None, enabled=False),
            MenuItem('Win+Alt+E → English', lambda: None, enabled=False),
            MenuItem('Win+Alt+J → Japanese', lambda: None, enabled=False),
            MenuItem('Win+Alt+C → Chinese', lambda: None, enabled=False),
            MenuItem('─────────────', lambda: None, enabled=False),
            MenuItem('Settings', self.show_settings),
            MenuItem('Quit', self.quit_app)
        )

        self.tray_icon = Icon("Gemini Translator", image,
                             f"Gemini Translator v{VERSION}", menu)
        return self.tray_icon

    def quit_app(self, icon=None, item=None):
        """Quit the application."""
        self.running = False
        self.hotkey_manager.unregister_all()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        os._exit(0)

    def _check_queue(self):
        """Check translation queue for results."""
        try:
            while True:
                original, translated, target_lang = self.translation_service.translation_queue.get_nowait()
                self.show_tooltip(original, translated, target_lang)
        except queue.Empty:
            pass

        if self.running:
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
        print(f"Gemini Translator v{VERSION}")
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

        # Setup tray icon
        self._create_tray_icon()
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

        # Check for updates
        threading.Thread(target=self._check_updates_async, daemon=True).start()

        # Start queue checker
        self.root.after(100, self._check_queue)

        # Run main loop
        self.root.mainloop()


# ============== MAIN ==============
if __name__ == "__main__":
    already_running, lock_socket = is_already_running()

    if already_running:
        root = tk.Tk()
        root.withdraw()
        if HAS_TTKBOOTSTRAP:
            Messagebox.show_warning(
                "Gemini Translator is already running!\n\n"
                "Check the system tray (bottom-right corner).",
                title="Gemini Translator"
            )
        else:
            from tkinter import messagebox
            messagebox.showwarning(
                "Gemini Translator",
                "Gemini Translator is already running!\n\n"
                "Check the system tray (bottom-right corner)."
            )
        root.dSestroy()
        sys.exit(0)

    app = TranslatorApp()
    app.run()
