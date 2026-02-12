"""
Update status checking and UI management for CrossTrans.

Handles checking previous update status, showing update dialogs,
and startup update checks.
"""
import os
import sys
import logging
import threading
from typing import Optional

from src.constants import VERSION
from src.ui.toast import ToastType
from src.utils.updates import (
    AutoUpdater,
    STARTUP_UPDATE_DELAY,
    UPDATE_TOAST_DURATION,
    THREAD_NAMES
)


class UpdateUIManager:
    """Manages update status checking and UI feedback.

    Responsibilities:
    - Check status files from previous update attempts
    - Show success/failure dialogs after UI initialization
    - Perform silent startup update checks
    - Show update available notifications
    """

    def __init__(self, root, config, toast_manager):
        """Initialize the update UI manager.

        Args:
            root: Root Tk window
            config: Config object
            toast_manager: ToastManager instance for notifications
        """
        self.root = root
        self.config = config
        self.toast = toast_manager

        # Pending update info (set during check, shown later)
        self._pending_update_success_version: Optional[str] = None
        self._pending_update_error: Optional[str] = None
        self._pending_update_path: Optional[str] = None

    def check_update_status(self) -> None:
        """Check if previous update succeeded or failed.

        Reads status files created by the update batch script:
        - crosstrans_update_error.txt: Update failed, shows error dialog
        - crosstrans_update_success.txt: Update completed
        - crosstrans_update_expected.txt: Expected version number
        - crosstrans_update_pending.txt: Path to pending update file (for reboot fallback)

        Shows appropriate feedback to user and offers MoveFileEx fallback if update failed.
        """
        temp = os.environ.get('TEMP', os.environ.get('TMP', ''))
        if not temp:
            return

        error_file = os.path.join(temp, 'crosstrans_update_error.txt')
        success_file = os.path.join(temp, 'crosstrans_update_success.txt')
        expected_file = os.path.join(temp, 'crosstrans_update_expected.txt')
        pending_file = os.path.join(temp, 'crosstrans_update_pending.txt')

        status_files = [error_file, success_file, expected_file, pending_file]

        try:
            if os.path.exists(error_file):
                # Update failed - offer reboot fallback
                error_msg = ""
                pending_path = None

                try:
                    with open(error_file, 'r') as f:
                        error_msg = f.read().strip()
                except Exception:
                    error_msg = "Unknown error"

                if os.path.exists(pending_file):
                    try:
                        with open(pending_file, 'r') as f:
                            pending_path = f.read().strip()
                    except Exception:
                        pass

                logging.warning(f"Previous update failed: {error_msg}")

                # Schedule dialog to show after UI is initialized
                self._pending_update_error = error_msg
                self._pending_update_path = pending_path

                # Cleanup status files (but keep pending for MoveFileEx if needed)
                for f in [error_file, success_file, expected_file]:
                    if os.path.exists(f):
                        try:
                            os.remove(f)
                        except Exception:
                            pass

            elif os.path.exists(success_file):
                # Check if version matches expected
                expected_ver = None
                if os.path.exists(expected_file):
                    try:
                        with open(expected_file, 'r') as f:
                            expected_ver = f.read().strip()
                    except Exception:
                        pass

                if expected_ver:
                    if VERSION == expected_ver:
                        # Success! Schedule toast after UI initialized
                        logging.info(f"Update to v{expected_ver} successful!")
                        self._pending_update_success_version = expected_ver
                    else:
                        # Version mismatch - update failed silently
                        logging.error(f"Update verification failed: Expected v{expected_ver} but running v{VERSION}")
                        self._pending_update_error = f"Expected v{expected_ver} but running v{VERSION}"
                        self._pending_update_path = None

                # Cleanup all status files
                for f in status_files:
                    if os.path.exists(f):
                        try:
                            os.remove(f)
                        except Exception:
                            pass

        except Exception as e:
            logging.warning(f"Error checking update status: {e}")

    def show_pending_dialogs(self) -> None:
        """Show any pending update dialogs after main window is ready.

        Called after the main UI components are initialized.
        """
        # Show update success toast
        if self._pending_update_success_version:
            version = self._pending_update_success_version
            self._pending_update_success_version = None
            self.root.after(2000, lambda: self._show_update_success_toast(version))

        # Show update failed dialog
        if self._pending_update_error:
            error_msg = self._pending_update_error
            pending_path = self._pending_update_path
            self._pending_update_error = None
            self._pending_update_path = None
            self.root.after(1000, lambda: self._show_update_failed_dialog(error_msg, pending_path))

    def startup_update_check(self) -> None:
        """Silent update check on startup (non-intrusive).

        Checks for updates in background thread after app initialization.
        Shows toast notification if update available.
        """
        def check_updates():
            import time
            time.sleep(STARTUP_UPDATE_DELAY)  # Wait for app to fully load

            logging.info("Auto-checking for updates on startup...")
            updater = AutoUpdater()
            result = updater.check_update()

            if result.get('has_update'):
                new_version = result['version']
                logging.info(f"Update available: {new_version}")
                # Show non-intrusive toast notification
                self.root.after(0, lambda: self._show_update_toast(new_version))
            else:
                logging.info("No update available on startup check")

        threading.Thread(
            target=check_updates,
            daemon=True,
            name=THREAD_NAMES['startup']
        ).start()

    def _show_update_success_toast(self, version: str) -> None:
        """Show success toast after update.

        Args:
            version: The version that was successfully installed
        """
        self.toast.show(
            "Update Successful",
            f"CrossTrans has been updated to v{version}",
            duration=5000
        )

    def _show_update_failed_dialog(self, error_msg: str, pending_path: str = None) -> None:
        """Show dialog when update failed, offering reboot fallback.

        Args:
            error_msg: Error message from the failed update
            pending_path: Path to the pending update file (for MoveFileEx fallback)
        """
        from src.ui.dialogs import UpdateFailedDialog

        dialog = UpdateFailedDialog(
            self.root,
            error_msg,
            pending_path,
            current_exe=sys.executable
        )

        if dialog.result == 'reboot' and pending_path:
            # User chose to schedule update for reboot
            updater = AutoUpdater()
            result = updater.schedule_update_on_reboot(pending_path, sys.executable)

            if result['success']:
                self.toast.show(
                    "Update Scheduled",
                    "Update will be applied when you restart Windows.",
                    duration=5000
                )
                # Clean up pending file marker
                pending_file = os.path.join(
                    os.environ.get('TEMP', ''),
                    'crosstrans_update_pending.txt'
                )
                if os.path.exists(pending_file):
                    try:
                        os.remove(pending_file)
                    except Exception:
                        pass
            else:
                self.toast.show(
                    "Scheduling Failed",
                    result.get('message', 'Could not schedule update'),
                    duration=5000,
                    toast_type=ToastType.ERROR
                )

        elif dialog.result == 'manual':
            # Open GitHub releases page
            import webbrowser
            from src.constants import GITHUB_REPO
            webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases/latest")

    def _show_update_toast(self, new_version: str) -> None:
        """Show non-intrusive update notification as toast.

        Args:
            new_version: Version number of the available update (e.g., "1.9.7")
        """
        from src.ui.toast import show_toast
        show_toast(
            self.root,
            "Update Available",
            f"CrossTrans v{new_version} is available!\nOpen Settings to update.",
            duration=UPDATE_TOAST_DURATION
        )
