"""
Progress Dialog for long-running translation operations.
Provides visual feedback when processing large files or multiple attachments.
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

try:
    import ttkbootstrap
    HAS_TTKBOOTSTRAP = True
except ImportError:
    HAS_TTKBOOTSTRAP = False


class ProgressDialog:
    """Modal progress dialog for file translations.

    Features:
    - Shows current file being processed
    - Progress bar with percentage
    - Cancel button (optional)
    - Thread-safe updates via window.after()

    Usage:
        dialog = ProgressDialog(parent_window, "Translating Files")
        dialog.update(1, 5, "Processing file1.txt...")
        dialog.close()
    """

    def __init__(self, parent: tk.Tk, title: str = "Processing",
                 show_cancel: bool = False,
                 on_cancel: Optional[Callable[[], None]] = None) -> None:
        """Initialize progress dialog.

        Args:
            parent: Parent Tk window
            title: Dialog title
            show_cancel: Whether to show cancel button
            on_cancel: Callback when cancel is clicked
        """
        self.parent = parent
        self.cancelled = False
        self.on_cancel = on_cancel

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("420x140")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)

        # Make modal
        self.dialog.grab_set()

        # Prevent closing via X button
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        # Center on parent
        self._center_on_parent()

        # Create UI
        self._create_widgets(show_cancel)

    def _center_on_parent(self) -> None:
        """Center dialog on parent window."""
        self.dialog.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        dialog_width = 420
        dialog_height = 140

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

    def _create_widgets(self, show_cancel: bool) -> None:
        """Create dialog widgets."""
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Status label
        self.status_label = ttk.Label(frame, text="Initializing...",
                                       font=('Segoe UI', 10))
        self.status_label.pack(anchor='w')

        # Progress bar
        if HAS_TTKBOOTSTRAP:
            self.progress_bar = ttk.Progressbar(frame, length=380,
                                                 mode='determinate',
                                                 bootstyle="info-striped")
        else:
            self.progress_bar = ttk.Progressbar(frame, length=380,
                                                 mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=10)

        # Bottom frame for percentage and cancel button
        bottom_frame = ttk.Frame(frame)
        bottom_frame.pack(fill=tk.X)

        # Percentage label
        self.percent_label = ttk.Label(bottom_frame, text="0%",
                                        font=('Segoe UI', 9))
        self.percent_label.pack(side=tk.LEFT)

        # Cancel button (optional)
        if show_cancel:
            cancel_btn = ttk.Button(bottom_frame, text="Cancel",
                                    command=self._on_cancel)
            cancel_btn.pack(side=tk.RIGHT)

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.cancelled = True
        self.status_label.config(text="Cancelling...")
        if self.on_cancel:
            self.on_cancel()

    def _on_close_attempt(self) -> None:
        """Handle close button click - treat as cancel."""
        self._on_cancel()

    def update(self, current: int, total: int, message: Optional[str] = None) -> None:
        """Update progress (thread-safe).

        Call this from any thread - it will safely update on main thread.

        Args:
            current: Current item number (0-based or 1-based)
            total: Total number of items
            message: Optional status message
        """
        if self.cancelled:
            return

        try:
            # Calculate percentage
            percent = int((current / total) * 100) if total > 0 else 0
            percent = min(100, max(0, percent))  # Clamp to 0-100

            # Update widgets
            self.progress_bar['value'] = percent
            self.percent_label.config(text=f"{percent}%")

            if message:
                self.status_label.config(text=message)

            # Force UI update
            self.dialog.update()
        except tk.TclError:
            # Dialog was destroyed
            pass

    def set_indeterminate(self, message: str = "Processing...") -> None:
        """Switch to indeterminate mode (bouncing bar).

        Use when total is unknown.
        """
        try:
            self.progress_bar.config(mode='indeterminate')
            self.progress_bar.start(10)  # Animation speed
            self.status_label.config(text=message)
            self.percent_label.config(text="")
        except tk.TclError:
            pass

    def close(self) -> None:
        """Close the dialog."""
        try:
            self.progress_bar.stop()  # Stop animation if running
            self.dialog.grab_release()
            self.dialog.destroy()
        except tk.TclError:
            # Already destroyed
            pass

    def is_cancelled(self) -> bool:
        """Check if user cancelled the operation."""
        return self.cancelled


def show_quick_progress(parent: tk.Tk, message: str, duration_ms: int = 2000) -> None:
    """Show a brief progress indicator that auto-closes.

    Args:
        parent: Parent window
        message: Message to display
        duration_ms: How long to show (milliseconds)
    """
    dialog = ProgressDialog(parent, "Processing")
    dialog.set_indeterminate(message)
    parent.after(duration_ms, dialog.close)
