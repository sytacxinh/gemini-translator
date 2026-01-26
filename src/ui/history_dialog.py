"""
History Dialog for AI Translator.
"""
import tkinter as tk
from tkinter import BOTH, X, Y, LEFT, RIGHT, TOP, BOTTOM, W, E, NW
from datetime import datetime

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    HAS_TTKBOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    HAS_TTKBOOTSTRAP = False


class HistoryDialog:
    """Dialog to view and manage translation history."""

    def __init__(self, parent, history_manager, on_load_callback):
        self.history_manager = history_manager
        self.on_load_callback = on_load_callback

        # Use tk.Toplevel
        self.window = tk.Toplevel(parent)
        self.window.title("Translation History")
        self.window.geometry("600x700")
        self.window.configure(bg='#2b2b2b')
        
        # Center
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 600) // 2
        y = (self.window.winfo_screenheight() - 700) // 2
        self.window.geometry(f"+{x}+{y}")

        self.window.transient(parent)
        self.window.grab_set()
        self.window.focus_force()

        self._create_widgets()
        self._refresh_list()

    def _create_widgets(self):
        """Create UI elements."""
        # Header
        header_frame = ttk.Frame(self.window, padding=15)
        header_frame.pack(fill=X)
        
        ttk.Label(header_frame, text="Recent Translations", font=('Segoe UI', 14, 'bold')).pack(side=LEFT)
        
        if HAS_TTKBOOTSTRAP:
            ttk.Button(header_frame, text="Clear All", command=self._clear_all,
                       bootstyle="danger-outline", width=10).pack(side=RIGHT)
        else:
            ttk.Button(header_frame, text="Clear All", command=self._clear_all,
                       width=10).pack(side=RIGHT)

        # List Container (Canvas + Scrollbar)
        list_container = ttk.Frame(self.window)
        list_container.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(list_container, bg='#2b2b2b', highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=560) # Fixed width approx
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Mousewheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.window.bind("<Destroy>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        # Resize handler for canvas width
        def _configure_canvas(event):
            self.canvas.itemconfig(self.canvas.find_withtag("all")[0], width=event.width)
        self.canvas.bind('<Configure>', _configure_canvas)

    def _refresh_list(self):
        """Populate the list with history items."""
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        history = self.history_manager.get_history()

        if not history:
            ttk.Label(self.scrollable_frame, text="No history yet.", 
                     foreground='#888888', font=('Segoe UI', 10)).pack(pady=20)
            return

        for item in history:
            self._create_history_item(item)

    def _create_history_item(self, item):
        """Create a single history row."""
        frame = ttk.Frame(self.scrollable_frame, padding=10)
        frame.pack(fill=X, pady=2)
        
        # Separator line at bottom
        ttk.Separator(self.scrollable_frame).pack(fill=X, padx=10)

        # Top row: Lang + Time
        top_row = ttk.Frame(frame)
        top_row.pack(fill=X, pady=(0, 5))
        
        lang = item.get('target_lang', 'Unknown')
        ts = item.get('timestamp', 0)
        time_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
        
        if HAS_TTKBOOTSTRAP:
            ttk.Label(top_row, text=lang, bootstyle="info", font=('Segoe UI', 9, 'bold')).pack(side=LEFT)
        else:
            ttk.Label(top_row, text=lang, foreground='#17a2b8', font=('Segoe UI', 9, 'bold')).pack(side=LEFT)
            
        ttk.Label(top_row, text=time_str, foreground='#888888', font=('Segoe UI', 8)).pack(side=RIGHT)

        # Content
        original = item.get('original', '').replace('\n', ' ')
        if len(original) > 60: original = original[:57] + "..."
        
        translated = item.get('translated', '').replace('\n', ' ')
        if len(translated) > 60: translated = translated[:57] + "..."

        ttk.Label(frame, text=original, font=('Segoe UI', 10), foreground='#cccccc').pack(anchor=W)
        ttk.Label(frame, text=f"→ {translated}", font=('Segoe UI', 10), foreground='#ffffff').pack(anchor=W, pady=(2, 0))

        # Click to load
        frame.bind("<Button-1>", lambda e, i=item: self._load_item(i))
        for child in frame.winfo_children():
            child.bind("<Button-1>", lambda e, i=item: self._load_item(i))

        # Delete button (small 'x' on right, but tricky with layout, let's put it in top row)
        del_btn = ttk.Label(top_row, text="✕", foreground='#dc3545', cursor="hand2")
        del_btn.pack(side=RIGHT, padx=(0, 10))
        del_btn.bind("<Button-1>", lambda e, i=item: self._delete_item(i))

    def _load_item(self, item):
        """Load item into main translator."""
        self.on_load_callback(item)
        self.window.destroy()

    def _delete_item(self, item):
        """Delete item."""
        self.history_manager.delete_entry(item.get('id'))
        self._refresh_list()

    def _clear_all(self):
        """Clear all history."""
        if HAS_TTKBOOTSTRAP:
            if Messagebox.yesno("Clear all history?", parent=self.window) != "Yes": return
        else:
            from tkinter import messagebox
            if not messagebox.askyesno("Confirm", "Clear all history?", parent=self.window): return
            
        self.history_manager.clear_history()
        self._refresh_list()