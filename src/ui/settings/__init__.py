"""
Settings module for CrossTrans.

This module contains the Settings window split into multiple files for maintainability:
- widgets.py: Custom widgets (AutocompleteCombobox) and helper functions
- base.py: SettingsWindow base class with initialization and common methods
- api_tab.py: API Key tab functionality
- hotkey_tab.py: Hotkeys tab functionality
- general_tab.py: General settings tab functionality
- dictionary_tab.py: Dictionary/NLP tab functionality
- guide_tab.py: User guide tab functionality
- update_manager.py: Update checking and downloading functionality
"""

from src.ui.settings.main import SettingsWindow

__all__ = ['SettingsWindow']
