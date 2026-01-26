"""
Screenshot Capture Module for AI Translator.
"""
import tkinter as tk
import tempfile
import os
from PIL import ImageGrab


class ScreenshotCapture:
    """Handles screen capture for OCR."""

    def __init__(self, root=None):
        self.root = root
        self.top = None
        self.canvas = None
        self.original_image = None
        self.callback = None
        self.start_x = 0
        self.start_y = 0
        self.cur_x = 0
        self.cur_y = 0
        self.rect = None

    def capture_region(self, callback):
        """
        Opens an overlay to select a region.
        callback(image_path): function to call with captured image path.
        """
        self.callback = callback

        try:
            # Capture full screen (all monitors on Windows if supported by Pillow)
            self.original_image = ImageGrab.grab(all_screens=True)
        except Exception as e:
            print(f"Screenshot error: {e}")
            if callback:
                callback(None)
            return

        # Create overlay window with parent for proper event loop integration
        self.top = tk.Toplevel(self.root)
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-topmost', True)
        self.top.attributes('-alpha', 0.3)  # Semi-transparent overlay
        self.top.configure(bg='black', cursor="cross")
        
        # Bind events
        self.top.bind("<ButtonPress-1>", self._on_press)
        self.top.bind("<B1-Motion>", self._on_drag)
        self.top.bind("<ButtonRelease-1>", self._on_release)
        self.top.bind("<Escape>", lambda e: self._close(call_callback=True))
        
        # Create canvas for drawing selection rectangle
        self.canvas = tk.Canvas(self.top, highlightthickness=0, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.top.focus_force()

    def _on_press(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root

        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            0, 0, 0, 0, outline='red', width=2, fill='white', stipple='gray25'
        )

    def _on_drag(self, event):
        self.cur_x = event.x_root
        self.cur_y = event.y_root
        
        # Map global coords to canvas coords
        canvas_x = self.cur_x - self.top.winfo_rootx()
        canvas_y = self.cur_y - self.top.winfo_rooty()
        start_canvas_x = self.start_x - self.top.winfo_rootx()
        start_canvas_y = self.start_y - self.top.winfo_rooty()

        self.canvas.coords(self.rect, start_canvas_x, start_canvas_y, canvas_x, canvas_y)

    def _on_release(self, event):
        if not self.original_image:
            self._close()
            return

        x1 = min(self.start_x, self.cur_x)
        y1 = min(self.start_y, self.cur_y)
        x2 = max(self.start_x, self.cur_x)
        y2 = max(self.start_y, self.cur_y)

        # Save image reference BEFORE closing (close sets original_image = None)
        image = self.original_image

        self._close()

        # Ensure valid size
        if (x2 - x1) < 10 or (y2 - y1) < 10:
            if self.callback:
                self.callback(None)
            return

        try:
            # Crop image using saved reference
            # Note: This assumes simple coordinate mapping.
            # Multi-monitor setups with negative coordinates might need offset adjustment.
            cropped = image.crop((x1, y1, x2, y2))
            
            fd, path = tempfile.mkstemp(suffix='.png')
            os.close(fd)
            cropped.save(path)
            
            if self.callback:
                self.callback(path)
                
        except Exception as e:
            print(f"Crop failed: {e}")

    def _close(self, call_callback=False):
        if self.top:
            self.top.destroy()
        self.top = None
        self.original_image = None
        if call_callback and self.callback:
            self.callback(None)