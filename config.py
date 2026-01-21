"""
Configuration management for Gemini Translator v1.2.0
Handles API key, hotkeys, auto-start settings, and other preferences.
"""
import os
import sys
import json
import winreg
from typing import Optional, Dict, Any


class Config:
    """Manages application configuration stored in %APPDATA%/GeminiTranslator/config.json"""

    APP_NAME = "GeminiTranslator"
    CONFIG_DIR = os.path.join(os.environ.get('APPDATA', '.'), APP_NAME)
    CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

    DEFAULT_HOTKEYS = {
        "Vietnamese": "win+alt+v",
        "English": "win+alt+e",
        "Japanese": "win+alt+j",
        "Chinese Simplified": "win+alt+c"
    }

    DEFAULT_CONFIG = {
        "api_key": "",
        "hotkeys": DEFAULT_HOTKEYS.copy(),
        "autostart": False,
        "check_updates": True,
        "theme": "darkly"
    }

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        if not os.path.exists(self.CONFIG_DIR):
            os.makedirs(self.CONFIG_DIR)

    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._config = self.DEFAULT_CONFIG.copy()
        else:
            self._config = self.DEFAULT_CONFIG.copy()

        # Merge with defaults for any missing keys
        for key, value in self.DEFAULT_CONFIG.items():
            if key not in self._config:
                self._config[key] = value

        return self._config

    def save(self):
        """Save configuration to file."""
        self._ensure_config_dir()
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    # API Key management
    def get_api_key(self) -> str:
        """Get API key from config, environment variable, or .env file."""
        # Priority 1: Config file
        if self._config.get('api_key'):
            return self._config['api_key']

        # Priority 2: Environment variable
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            return api_key

        # Priority 3: .env file in app directory
        env_path = os.path.join(self._get_app_dir(), '.env')
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('GEMINI_API_KEY='):
                            return line.split('=', 1)[1].strip().strip('"\'')
            except IOError:
                pass

        return ""

    def set_api_key(self, api_key: str):
        """Set API key in config."""
        self._config['api_key'] = api_key
        self.save()

    def _get_app_dir(self) -> str:
        """Get the directory where the exe/script is located."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    # Hotkeys management
    def get_hotkeys(self) -> Dict[str, str]:
        """Get hotkey configuration."""
        return self._config.get('hotkeys', self.DEFAULT_HOTKEYS.copy())

    def set_hotkeys(self, hotkeys: Dict[str, str]):
        """Set hotkey configuration."""
        self._config['hotkeys'] = hotkeys
        self.save()

    def set_hotkey(self, language: str, hotkey: str):
        """Set hotkey for a specific language."""
        if 'hotkeys' not in self._config:
            self._config['hotkeys'] = self.DEFAULT_HOTKEYS.copy()
        self._config['hotkeys'][language] = hotkey
        self.save()

    def remove_hotkey(self, language: str):
        """Remove hotkey for a specific language."""
        if 'hotkeys' in self._config and language in self._config['hotkeys']:
            del self._config['hotkeys'][language]
            self.save()

    # Auto-start management
    def get_autostart(self) -> bool:
        """Get auto-start setting."""
        return self._config.get('autostart', False)

    def set_autostart(self, enable: bool):
        """Set auto-start with Windows."""
        self._config['autostart'] = enable
        self._update_registry_autostart(enable)
        self.save()

    def _update_registry_autostart(self, enable: bool):
        """Update Windows registry for auto-start."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                               winreg.KEY_SET_VALUE | winreg.KEY_READ) as key:
                if enable:
                    exe_path = self._get_exe_path()
                    winreg.SetValueEx(key, self.APP_NAME, 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(key, self.APP_NAME)
                    except FileNotFoundError:
                        pass
        except WindowsError as e:
            print(f"Failed to update registry: {e}")

    def _get_exe_path(self) -> str:
        """Get the path to use for auto-start."""
        if getattr(sys, 'frozen', False):
            return sys.executable
        return f'pythonw.exe "{os.path.abspath(__file__.replace("config.py", "translator.py"))}"'

    def is_autostart_enabled(self) -> bool:
        """Check if auto-start is currently enabled in registry."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                               winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, self.APP_NAME)
                return True
        except (FileNotFoundError, WindowsError):
            return False

    # Update settings
    def get_check_updates(self) -> bool:
        """Get check for updates setting."""
        return self._config.get('check_updates', True)

    def set_check_updates(self, enable: bool):
        """Set check for updates setting."""
        self._config['check_updates'] = enable
        self.save()

    # Theme settings
    def get_theme(self) -> str:
        """Get UI theme."""
        return self._config.get('theme', 'darkly')

    def set_theme(self, theme: str):
        """Set UI theme."""
        self._config['theme'] = theme
        self.save()

    # Generic getter/setter
    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Set a config value."""
        self._config[key] = value
        self.save()
