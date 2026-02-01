"""
Main Settings Window - Composes all tab mixins into the final SettingsWindow class.
"""
import tkinter as tk
from tkinter import BOTH, X, RIGHT

try:
    import ttkbootstrap as ttk
    HAS_TTKBOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    HAS_TTKBOOTSTRAP = False

from src.utils.updates import AutoUpdater
from src.ui.settings.widgets import set_dark_title_bar
from src.ui.settings.api_tab import APITabMixin
from src.ui.settings.hotkey_tab import HotkeyTabMixin
from src.ui.settings.general_tab import GeneralTabMixin
from src.ui.settings.dictionary_tab import DictionaryTabMixin
from src.ui.settings.guide_tab import GuideTabMixin
from src.ui.settings.update_manager import UpdateManagerMixin


class SettingsWindow(
    APITabMixin,
    HotkeyTabMixin,
    GeneralTabMixin,
    DictionaryTabMixin,
    GuideTabMixin,
    UpdateManagerMixin
):
    """Settings dialog for configuring the application.

    This class uses mixins to organize functionality by tab:
    - APITabMixin: API Key tab with provider management and testing
    - HotkeyTabMixin: Hotkeys tab with keyboard shortcut configuration
    - GeneralTabMixin: General settings tab with autostart and updates
    - DictionaryTabMixin: Dictionary/NLP tab with language pack management
    - GuideTabMixin: User guide tab with help documentation
    - UpdateManagerMixin: Update checking and downloading functionality
    """

    def __init__(self, parent, config, on_save_callback=None, on_api_change_callback=None):
        """Initialize the Settings window.

        Args:
            parent: Parent tkinter window
            config: Configuration object for reading/writing settings
            on_save_callback: Optional callback when settings are saved
            on_api_change_callback: Optional callback when API keys change (for trial mode)
        """
        self.config = config
        self.on_save_callback = on_save_callback
        self.on_api_change_callback = on_api_change_callback
        self.hotkey_entries = {}
        self.custom_rows = []
        self.api_rows = []
        self.recording_language = None
        self.updater = AutoUpdater()

        # Use tk.Toplevel for better compatibility
        self.window = tk.Toplevel(parent)
        self.window.title("Settings - CrossTrans")
        self.window.geometry("1400x650")
        self.window.resizable(True, True)
        self.window.configure(bg='#2b2b2b')

        # Center on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 1400) // 2
        y = (self.window.winfo_screenheight() - 650) // 2
        self.window.geometry(f"+{x}+{y}")

        # Apply dark title bar (Windows 10/11)
        set_dark_title_bar(self.window)

        # Make window modal and handle close properly
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        self.window.focus_force()

        try:
            self._create_widgets()
        except Exception as e:
            print(f"Error creating settings widgets: {e}")
            import traceback
            traceback.print_exc()

    def _create_widgets(self):
        """Create settings UI with all tabs."""
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

        # Tab 4: Dictionary (NLP Language Packs)
        dict_frame = ttk.Frame(notebook, padding=20) if HAS_TTKBOOTSTRAP else ttk.Frame(notebook)
        notebook.add(dict_frame, text="  Dictionary  ")
        self._create_dictionary_tab(dict_frame)

        # Store notebook reference for opening specific tabs
        self.notebook = notebook

        # Tab 5: Guide
        guide_frame = ttk.Frame(notebook, padding=20) if HAS_TTKBOOTSTRAP else ttk.Frame(notebook)
        notebook.add(guide_frame, text="  Guide  ")
        self._create_guide_tab(guide_frame)

        # Close button only (auto-save handles all saves)
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill=X, padx=10, pady=(0, 10))

        if HAS_TTKBOOTSTRAP:
            ttk.Button(btn_frame, text="Close", command=self.window.destroy,
                       bootstyle="secondary", width=15).pack(side=RIGHT)
        else:
            ttk.Button(btn_frame, text="Close", command=self.window.destroy,
                       width=15).pack(side=RIGHT)
