"""
Auto-Update System for CrossTrans.
"""
import os
import sys
import json
import logging
import tempfile
import subprocess
import urllib.request
import time
import re
from typing import Optional, Callable

from packaging import version

from src.constants import VERSION, GITHUB_REPO
from src.core.ssl_pinning import get_ssl_context_for_url


class UpdateError(Exception):
    """Base exception for update-related errors."""
    pass


class DownloadCancelledException(UpdateError):
    """Exception raised when user cancels download."""
    pass


# Update System Constants
UPDATE_CHECK_TIMEOUT = 30  # seconds - GitHub API request timeout
UPDATE_DOWNLOAD_TIMEOUT = 180  # seconds - Download timeout
UPDATE_CHECK_MAX_RETRIES = 3  # Max retry attempts for update check
UPDATE_THREAD_TIMEOUT = 60  # seconds - Thread join timeout
RELEASE_NOTES_MAX_LENGTH = 300  # characters - Truncate release notes
PROGRESS_WINDOW_SIZE = "350x120"  # Progress dialog dimensions
UPDATE_TOAST_DURATION = 5000  # milliseconds - Toast notification duration
STARTUP_UPDATE_DELAY = 3  # seconds - Delay before auto-check on startup
THREAD_NAMES = {
    'check': 'UpdateCheckThread',
    'download': 'DownloadThread',
    'monitor': 'UpdateMonitor',
    'startup': 'StartupUpdateCheck'
}


# Valid error types for telemetry
VALID_ERROR_TYPES = {'network', 'rate_limit', 'ssl', 'parse_error', 'timeout', 'other'}

# Error detection patterns (for classifying error messages)
ERROR_PATTERNS = {
    'network': ['connect', 'connection', 'internet', 'network', 'unreachable', 'dns'],
    'rate_limit': ['rate limit', '403', 'too many requests'],
    'ssl': ['ssl', 'certificate', 'tls', 'secure connection'],
    'parse_error': ['parse', 'invalid json', 'malformed', 'invalid response'],
    'timeout': ['timeout', 'timed out', 'time out'],
}


def classify_error_type(error_message: str) -> str:
    """Classify error type based on error message content.

    Args:
        error_message: The error message to classify

    Returns:
        Error type string from VALID_ERROR_TYPES ('network', 'rate_limit', etc.)
        Returns 'other' if no pattern matches.
    """
    if not error_message:
        return 'other'

    error_lower = error_message.lower()

    for error_type, patterns in ERROR_PATTERNS.items():
        if any(pattern in error_lower for pattern in patterns):
            return error_type

    return 'other'


# User-friendly error messages
ERROR_MESSAGES = {
    'network': (
        "Cannot connect to GitHub.\n\n"
        "Possible solutions:\n"
        "• Check your internet connection\n"
        "• Disable VPN/proxy temporarily\n"
        "• Check firewall settings\n"
        "• Try again in a few moments"
    ),
    'rate_limit': (
        "GitHub rate limit reached.\n\n"
        "Please try again in a few minutes."
    ),
    'ssl': (
        "SSL/Security error.\n\n"
        "Possible solutions:\n"
        "• Update Windows to latest version\n"
        "• Check system date/time is correct\n"
        "• Disable antivirus temporarily\n"
        "• Contact support if issue persists"
    ),
    'parse_error': (
        "Invalid response from GitHub.\n\n"
        "GitHub may be experiencing issues.\n"
        "Please try again later."
    ),
    'timeout': (
        "Update check timed out.\n\n"
        "Your connection may be slow.\n"
        "Please try again."
    )
}


class AutoUpdater:
    """Handles checking, downloading and installing updates from GitHub releases.

    Provides comprehensive update functionality with:
    - GitHub API integration for checking latest releases
    - Automatic download with progress tracking
    - SHA256 integrity verification
    - Batch script-based installation with rollback support
    - Comprehensive error handling and logging
    """

    def __init__(self, test_mode: bool = False, mock_response: Optional[dict] = None):
        """Initialize AutoUpdater.

        Args:
            test_mode: If True, uses mock_response instead of real GitHub API calls.
                       Useful for testing without network access.
            mock_response: Mock response dict to return in test mode.
                           Should have same structure as check_update() return value.
        """
        self.latest_version: Optional[str] = None
        self.exe_url: Optional[str] = None
        self.release_notes: str = ""
        self.download_path: Optional[str] = None
        self.expected_sha256: Optional[str] = None
        self.test_mode = test_mode
        self.mock_response = mock_response

    def check_update(self, max_retries: int = 3) -> dict:
        """Check GitHub for newer version with retry logic and comprehensive logging.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            dict with keys:
            - has_update: bool
            - version: str (new version if available)
            - notes: str (release notes)
            - error: str (error message if failed)
        """
        # Test mode support
        if self.test_mode and self.mock_response:
            logging.info("TEST MODE: Using mock response")
            return self.mock_response

        logging.info("=" * 60)
        logging.info("UPDATE CHECK STARTED")
        logging.info(f"Current version: {VERSION}")
        logging.info(f"GitHub repo: {GITHUB_REPO}")

        for attempt in range(max_retries):
            try:
                logging.info(f"Update check attempt {attempt + 1}/{max_retries}")

                url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
                logging.info(f"Fetching: {url}")

                # Create request with headers
                req = urllib.request.Request(url, headers={
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'CrossTrans'
                })
                logging.debug(f"Request headers: {dict(req.headers)}")

                # Create SSL context with error handling
                try:
                    ctx = get_ssl_context_for_url(url)
                    logging.info("SSL context created successfully")
                except Exception as ssl_err:
                    logging.error(f"SSL context creation failed: {ssl_err}", exc_info=True)
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logging.warning(f"Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    return {
                        'has_update': False,
                        'error': ERROR_MESSAGES['ssl']
                    }

                # Make API request
                logging.info("Sending GitHub API request...")
                with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                    logging.info(f"Response status: {resp.status}")
                    logging.debug(f"Response headers: {dict(resp.headers)}")

                    data = json.loads(resp.read().decode())
                    logging.debug(f"Response data keys: {list(data.keys())}")

                # Validate and parse response
                latest = data.get('tag_name', '').lstrip('v')
                logging.info(f"Latest version from GitHub: {latest}")

                if not latest:
                    logging.error("No tag_name in GitHub response")
                    return {
                        'has_update': False,
                        'error': ERROR_MESSAGES['parse_error']
                    }

                # Version comparison
                try:
                    current_ver = version.parse(VERSION)
                    latest_ver = version.parse(latest)
                    logging.info(f"Version comparison: {VERSION} ({current_ver}) vs {latest} ({latest_ver})")

                    if latest_ver > current_ver:
                        logging.info(f"New version available: {latest}")

                        # Find exe asset
                        for asset in data.get('assets', []):
                            if asset['name'].lower().endswith('.exe'):
                                self.exe_url = asset['browser_download_url']
                                logging.info(f"Found EXE asset: {self.exe_url}")
                                break

                        if not self.exe_url:
                            logging.warning("No .exe asset found in release")
                            return {
                                'has_update': False,
                                'error': 'No executable file found in the release'
                            }

                        self.latest_version = latest
                        self.release_notes = data.get('body', '')

                        # Try to extract SHA256 from release notes
                        sha256_match = re.search(r'SHA256:?\s*([0-9a-fA-F]{64})', self.release_notes, re.IGNORECASE)
                        if sha256_match:
                            self.expected_sha256 = sha256_match.group(1)
                            logging.info(f"Found SHA256 checksum in release notes: {self.expected_sha256}")
                        else:
                            logging.warning("No SHA256 checksum found in release notes")
                            self.expected_sha256 = None

                        logging.info("Update check completed successfully - update available")
                        return {
                            'has_update': True,
                            'version': latest,
                            'notes': self.release_notes
                        }
                    else:
                        logging.info(f"No update available. Current version ({VERSION}) is up to date.")
                        return {'has_update': False, 'version': VERSION}

                except version.InvalidVersion as e:
                    logging.error(f"Invalid version format: {e}")
                    return {
                        'has_update': False,
                        'error': f'Version parsing error: {e}'
                    }

            except urllib.error.HTTPError as e:
                error_body = self._read_error_response(e)
                logging.error(f"HTTP {e.code}: {error_body}")

                if e.code == 403:
                    # GitHub rate limit
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logging.warning(f"GitHub rate limit (403), retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logging.error("GitHub rate limit exceeded after all retries")
                        return {
                            'has_update': False,
                            'error': ERROR_MESSAGES['rate_limit']
                        }

                elif e.code == 404:
                    # Repo not found - don't retry
                    logging.error("GitHub repository not found (404)")
                    return {
                        'has_update': False,
                        'error': 'Update service not available (repository not found)'
                    }

                elif e.code >= 500:
                    # Server error - retry
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logging.warning(f"GitHub server error {e.code}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logging.error(f"GitHub server error {e.code} persisted after all retries")
                        return {
                            'has_update': False,
                            'error': f'GitHub server error: HTTP {e.code}'
                        }

                # Other HTTP errors - don't retry
                logging.error(f"HTTP error {e.code}: {error_body}")
                return {
                    'has_update': False,
                    'error': f'GitHub API error: HTTP {e.code}'
                }

            except urllib.error.URLError as e:
                logging.error(f"Network error: {e.reason}")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logging.warning(f"Network error, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logging.error("Network error persisted after all retries")
                    return {
                        'has_update': False,
                        'error': ERROR_MESSAGES['network']
                    }

            except Exception as e:
                logging.error(f"Unexpected error in update check: {e}", exc_info=True)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logging.warning(f"Unexpected error, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        'has_update': False,
                        'error': f'Update check failed: {str(e)}'
                    }

        logging.error("Update check failed after all retry attempts")
        return {
            'has_update': False,
            'error': 'Update check failed after all retry attempts'
        }

    def _read_error_response(self, http_error) -> str:
        """Helper to safely read error response body."""
        try:
            return http_error.read().decode('utf-8')
        except Exception:
            return "(could not read error details)"

    def download(self, progress_callback: Optional[Callable[[int], None]] = None) -> dict:
        """Download the new version with SHA256 integrity verification.

        Args:
            progress_callback: Called with progress percentage (0-100)

        Returns:
            dict with keys:
            - success: bool
            - error: str (if failed)
        """
        if not self.exe_url or not self.latest_version:
            logging.error("Download attempted without update URL or version")
            return {'success': False, 'error': 'No update available'}

        if not getattr(sys, 'frozen', False):
            logging.warning("Download attempted from source (not frozen EXE)")
            return {'success': False, 'error': 'Auto-update only works with exe version'}

        try:
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix='crosstrans_update_')
            self.download_path = os.path.join(temp_dir, f'CrossTrans_v{self.latest_version}.exe')
            logging.info(f"Download path: {self.download_path}")

            req = urllib.request.Request(self.exe_url, headers={'User-Agent': 'CrossTrans'})
            ctx = get_ssl_context_for_url(self.exe_url)

            logging.info(f"Starting download from: {self.exe_url}")
            with urllib.request.urlopen(req, timeout=180, context=ctx) as response:
                total = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                logging.info(f"File size: {total} bytes ({total / 1024 / 1024:.1f} MB)")

                with open(self.download_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total > 0:
                            progress_callback(int(downloaded * 100 / total))

            logging.info(f"Download completed: {downloaded} bytes")

            # Verify SHA256 checksum if available
            if hasattr(self, 'expected_sha256') and self.expected_sha256:
                logging.info("Verifying download integrity with SHA256...")
                actual_sha256 = self._calculate_sha256(self.download_path)
                logging.info(f"Expected SHA256: {self.expected_sha256}")
                logging.info(f"Actual SHA256:   {actual_sha256}")

                if actual_sha256.lower() != self.expected_sha256.lower():
                    logging.error("SHA256 mismatch! Download may be corrupted.")
                    try:
                        os.unlink(self.download_path)
                        logging.info("Deleted corrupted download")
                    except Exception as del_err:
                        logging.warning(f"Could not delete corrupted file: {del_err}")

                    return {
                        'success': False,
                        'error': 'Downloaded file integrity check failed. Please try again.'
                    }

                logging.info("✓ Download integrity verified successfully!")
            else:
                logging.warning("No checksum available - skipping integrity verification")

            return {'success': True}

        except Exception as e:
            logging.error(f"Download failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash as hex string
        """
        import hashlib

        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def install_and_restart(self) -> dict:
        """Install the update and restart app with comprehensive error handling.

        Returns:
            dict with keys:
            - success: bool
            - error: str (if failed)
        """
        if not self.download_path or not os.path.exists(self.download_path):
            logging.error("Install attempted without valid download path")
            return {'success': False, 'error': 'No downloaded update found'}

        try:
            current_exe = sys.executable
            temp_dir = os.path.dirname(self.download_path)
            logging.info(f"Installing update from: {self.download_path}")
            logging.info(f"Current EXE: {current_exe}")

            # Create enhanced update batch script with logging and rollback
            batch_path = os.path.join(temp_dir, 'update.bat')
            batch_content = f'''@echo off
setlocal enabledelayedexpansion

:: Log file
set LOGFILE="%TEMP%\\crosstrans_update.log"
echo Update started at %DATE% %TIME% > %LOGFILE%

:: Wait for app to close
echo Waiting for CrossTrans to close... >> %LOGFILE%
:wait
tasklist /FI "PID eq %1" 2>NUL | find /I "%1" >NUL
if not errorlevel 1 (
    echo Still running... >> %LOGFILE%
    timeout /t 1 /nobreak >NUL
    goto wait
)

echo Process closed >> %LOGFILE%
timeout /t 2 /nobreak >NUL

:: Backup current version
echo Creating backup... >> %LOGFILE%
del /F /Q "{current_exe}.bak" >NUL 2>&1

move /Y "{current_exe}" "{current_exe}.bak" >NUL 2>&1
if errorlevel 1 (
    echo ERROR: Could not backup current version >> %LOGFILE%
    timeout /t 2 /nobreak >NUL
    move /Y "{current_exe}" "{current_exe}.bak" >NUL 2>&1
)

if not exist "{current_exe}.bak" (
    echo FATAL: Backup failed >> %LOGFILE%
    echo Update failed: Could not backup current version > "%TEMP%\\crosstrans_update_error.txt"
    goto end
)

echo Backup created successfully >> %LOGFILE%

:: Copy new version
echo Installing new version... >> %LOGFILE%
copy /Y "{self.download_path}" "{current_exe}" >NUL 2>&1

if errorlevel 1 (
    echo ERROR: Installation failed, restoring backup... >> %LOGFILE%
    move /Y "{current_exe}.bak" "{current_exe}" >NUL 2>&1
    echo Update failed: Could not install new version > "%TEMP%\\crosstrans_update_error.txt"
    goto end
)

if not exist "{current_exe}" (
    echo FATAL: New version not found, restoring backup... >> %LOGFILE%
    move /Y "{current_exe}.bak" "{current_exe}" >NUL 2>&1
    echo Update failed: Installation incomplete > "%TEMP%\\crosstrans_update_error.txt"
    goto end
)

echo Installation successful >> %LOGFILE%

:: Start new version
echo Starting new version... >> %LOGFILE%
start "" "{current_exe}"

:: Wait and cleanup
timeout /t 3 /nobreak >NUL
echo Cleaning up... >> %LOGFILE%
rmdir /S /Q "{temp_dir}" >NUL 2>&1

echo Update completed successfully >> %LOGFILE%
echo Update completed successfully > "%TEMP%\\crosstrans_update_success.txt"

:end
echo Cleaning up update script... >> %LOGFILE%
del /F /Q "%~f0" >NUL 2>&1
'''
            with open(batch_path, 'w') as f:
                f.write(batch_content)

            logging.info(f"Created update batch script: {batch_path}")

            # Execute update script
            subprocess.Popen(
                ['cmd', '/c', batch_path, str(os.getpid())],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                close_fds=True
            )

            logging.info("Update script launched, exiting application...")
            # Exit current app
            sys.exit(0)

        except Exception as e:
            logging.error(f"Install failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
