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
from typing import Optional, Callable

from packaging import version

from src.constants import VERSION, GITHUB_REPO
from src.core.ssl_pinning import get_ssl_context_for_url


class AutoUpdater:
    """Handles checking, downloading and installing updates."""

    def __init__(self):
        self.latest_version: Optional[str] = None
        self.exe_url: Optional[str] = None
        self.release_notes: str = ""
        self.download_path: Optional[str] = None

    def check_update(self) -> dict:
        """Check GitHub for newer version.

        Returns:
            dict with keys:
            - has_update: bool
            - version: str (new version if available)
            - notes: str (release notes)
            - error: str (error message if failed)
        """
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'CrossTrans'
            })
            ctx = get_ssl_context_for_url(url)

            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = json.loads(resp.read().decode())

            latest = data['tag_name'].lstrip('v')

            if version.parse(latest) > version.parse(VERSION):
                # Find exe asset
                for asset in data.get('assets', []):
                    if asset['name'].lower().endswith('.exe'):
                        self.exe_url = asset['browser_download_url']
                        break

                self.latest_version = latest
                self.release_notes = data.get('body', '')

                return {
                    'has_update': True,
                    'version': latest,
                    'notes': self.release_notes
                }

            return {'has_update': False, 'version': VERSION}

        except Exception as e:
            logging.error(f"Update check failed: {e}")
            return {'has_update': False, 'error': str(e)}

    def download(self, progress_callback: Optional[Callable[[int], None]] = None) -> dict:
        """Download the new version.

        Args:
            progress_callback: Called with progress percentage (0-100)

        Returns:
            dict with keys:
            - success: bool
            - error: str (if failed)
        """
        if not self.exe_url or not self.latest_version:
            return {'success': False, 'error': 'No update available'}

        if not getattr(sys, 'frozen', False):
            return {'success': False, 'error': 'Auto-update only works with exe version'}

        try:
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix='crosstrans_update_')
            self.download_path = os.path.join(temp_dir, f'CrossTrans_v{self.latest_version}.exe')

            req = urllib.request.Request(self.exe_url, headers={'User-Agent': 'CrossTrans'})
            ctx = get_ssl_context_for_url(self.exe_url)

            with urllib.request.urlopen(req, timeout=120, context=ctx) as response:
                total = int(response.headers.get('Content-Length', 0))
                downloaded = 0

                with open(self.download_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total > 0:
                            progress_callback(int(downloaded * 100 / total))

            return {'success': True}

        except Exception as e:
            logging.error(f"Download failed: {e}")
            return {'success': False, 'error': str(e)}

    def install_and_restart(self) -> dict:
        """Install the update and restart app.

        Returns:
            dict with keys:
            - success: bool
            - error: str (if failed)
        """
        if not self.download_path or not os.path.exists(self.download_path):
            return {'success': False, 'error': 'No downloaded update found'}

        try:
            current_exe = sys.executable
            temp_dir = os.path.dirname(self.download_path)

            # Create update batch script
            batch_path = os.path.join(temp_dir, 'update.bat')
            batch_content = f'''@echo off
:wait
tasklist /FI "PID eq %1" 2>NUL | find /I "%1" >NUL
if not errorlevel 1 (timeout /t 1 /nobreak >NUL & goto wait)

timeout /t 2 /nobreak >NUL
del /F /Q "{current_exe}.bak" >NUL 2>&1
move /Y "{current_exe}" "{current_exe}.bak" >NUL 2>&1
if errorlevel 1 (timeout /t 2 /nobreak >NUL & move /Y "{current_exe}" "{current_exe}.bak" >NUL 2>&1)

copy /Y "{self.download_path}" "{current_exe}" >NUL 2>&1
if errorlevel 1 (move /Y "{current_exe}.bak" "{current_exe}" >NUL 2>&1 & goto end)

start "" "{current_exe}"
timeout /t 3 /nobreak >NUL
rmdir /S /Q "{temp_dir}" >NUL 2>&1
:end
del /F /Q "%~f0" >NUL 2>&1
'''
            with open(batch_path, 'w') as f:
                f.write(batch_content)

            # Execute update script
            subprocess.Popen(
                ['cmd', '/c', batch_path, str(os.getpid())],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                close_fds=True
            )

            # Exit current app
            sys.exit(0)

        except Exception as e:
            logging.error(f"Install failed: {e}")
            return {'success': False, 'error': str(e)}
