"""
AI Translator v1.5.0

DEPRECATED: This file is kept for backward compatibility only.
Please use main.py as the entry point instead.

All code has been refactored into the following modules:
- src/constants.py     - Constants and configuration values
- src/core/            - Core functionality (clipboard, API, translation, hotkey)
- src/ui/              - UI components (settings, dialogs)
- src/utils/           - Utilities (logging, single instance, updates)
- src/app.py           - Main application class
- main.py              - Entry point
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == "__main__":
    sys.exit(main())
