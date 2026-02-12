"""
Trial mode management for CrossTrans.

Handles trial mode status, quota checking, API key re-validation,
and trial-related dialogs.
"""
import logging
from typing import Optional, Callable


class TrialManager:
    """Manages trial mode status, quota checking, and API key re-validation.

    Responsibilities:
    - Schedule periodic API key re-checks when in forced trial mode
    - Re-test API keys and disable trial mode if any becomes valid
    - Show trial exhausted and feature blocked dialogs
    """

    def __init__(self, root, config, translation_service, toast_manager):
        """Initialize the trial manager.

        Args:
            root: Root Tk window
            config: Config object
            translation_service: TranslationService instance
            toast_manager: ToastManager for notifications
        """
        self.root = root
        self.config = config
        self.translation_service = translation_service
        self.toast = toast_manager

        # Callback for showing settings tab
        self._on_show_settings_tab: Optional[Callable[[str], None]] = None

    def configure_callbacks(self, on_show_settings_tab: Optional[Callable[[str], None]] = None):
        """Configure callback functions.

        Args:
            on_show_settings_tab: Callback to open settings and navigate to a specific tab
        """
        self._on_show_settings_tab = on_show_settings_tab

    def schedule_recheck(self) -> None:
        """Schedule re-check of API keys when in forced trial mode."""
        if not self.config.get_trial_mode_forced():
            return

        # Check if we need to re-test (24h since last check)
        last_check = self.config.get_trial_last_api_check()
        if last_check:
            try:
                from datetime import datetime, timedelta
                last_dt = datetime.fromisoformat(last_check)
                if datetime.now() - last_dt >= timedelta(hours=24):
                    # Time to re-check
                    self.root.after(5000, self._recheck_api_keys)
            except Exception as e:
                logging.warning(f"Failed to parse last API check time: {e}")

        # Schedule next check in 1 hour
        self.root.after(3600000, self.schedule_recheck)  # 1 hour

    def is_trial_mode(self) -> bool:
        """Check if currently in trial mode.

        Returns:
            True if in trial mode, False otherwise
        """
        return self.translation_service.is_trial_mode()

    def show_trial_exhausted(self) -> None:
        """Show trial quota exhausted dialog."""
        from src.ui.dialogs import TrialExhaustedDialog
        TrialExhaustedDialog(self.root, on_open_settings_tab=self._on_show_settings_tab)

    def show_feature_blocked(self, feature_name: str) -> None:
        """Show dialog when user tries to use a feature disabled in trial mode.

        Args:
            feature_name: Name of the blocked feature (e.g., "File/Image translation")
        """
        from src.ui.dialogs import TrialFeatureDialog
        TrialFeatureDialog(self.root, feature_name=feature_name, on_open_settings_tab=self._on_show_settings_tab)

    def _recheck_api_keys(self) -> None:
        """Re-check API keys and disable trial mode if any works."""
        from datetime import datetime
        from src.core.api_manager import AIAPIManager

        logging.info("Re-checking API keys for trial mode...")

        api_keys = self.config.get_api_keys()
        if not api_keys:
            return

        manager = AIAPIManager()
        any_working = False

        for key_config in api_keys:
            key = key_config.get('api_key', '').strip()
            if not key:
                continue

            model = key_config.get('model_name', '').strip() or 'Auto'
            provider = key_config.get('provider', 'Auto')

            try:
                if manager.test_connection(model, key, provider):
                    any_working = True
                    self.config.api_status_cache[key] = True
                    logging.info(f"API key now working: {key[:8]}...")
                    break
            except Exception:
                self.config.api_status_cache[key] = False

        # Update last check time
        self.config.set_trial_last_api_check(datetime.now().isoformat())

        if any_working:
            # Disable trial mode
            self.config.set_trial_mode_forced(False)
            logging.info("API key now working - disabled forced trial mode")

            # Show toast notification
            self.toast.show(
                "API Key Restored",
                "Your API key is now working. Trial mode disabled.",
                duration=5000
            )
