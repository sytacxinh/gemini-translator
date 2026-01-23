"""
Dialog windows for AI Translator.
"""
import webbrowser

import tkinter as tk
from tkinter import BOTH, X, LEFT, RIGHT, W

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    HAS_TTKBOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    HAS_TTKBOOTSTRAP = False


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
