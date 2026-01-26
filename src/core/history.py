"""
History Manager for AI Translator.
Handles saving, retrieving, and managing translation history.
"""
import time
import uuid
from typing import List, Dict, Any


class HistoryManager:
    """Manages translation history with a limit on entries."""
    
    MAX_HISTORY = 100

    def __init__(self, config):
        self.config = config

    def add_entry(self, original: str, translated: str, target_lang: str, 
                  source_type: str = "text", model_used: str = "Auto"):
        """Add a new translation entry to history."""
        if not self.config.get('history_enabled', True):
            return

        # Don't save if original text is empty or too short/trivial
        if not original or len(original.strip()) < 2:
            return

        entry = {
            'id': str(uuid.uuid4()),
            'timestamp': time.time(),
            'original': original,
            'translated': translated,
            'target_lang': target_lang,
            'source_type': source_type,
            'model_used': model_used
        }

        history = self.config.get('history', [])
        history.insert(0, entry)
        
        # Enforce limit
        if len(history) > self.MAX_HISTORY:
            history = history[:self.MAX_HISTORY]
            
        self.config.set('history', history)

    def get_history(self) -> List[Dict[str, Any]]:
        """Get full history list."""
        return self.config.get('history', [])

    def clear_history(self):
        """Clear all history."""
        self.config.set('history', [])

    def delete_entry(self, entry_id: str):
        """Delete a specific entry by ID."""
        history = self.config.get('history', [])
        history = [h for h in history if h.get('id') != entry_id]
        self.config.set('history', history)