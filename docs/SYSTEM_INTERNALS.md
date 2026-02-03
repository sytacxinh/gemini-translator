# CrossTrans - System Internals Documentation

> **Purpose**: This document is a comprehensive technical reference for AI assistants and developers. It explains in detail how CrossTrans's **Auto-Update System** and **Auto-Start with Windows** mechanisms work, traced directly from source code.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Auto-Start with Windows](#2-auto-start-with-windows)
3. [Application Startup Flow](#3-application-startup-flow)
4. [Single Instance Prevention](#4-single-instance-prevention)
5. [Auto-Update System](#5-auto-update-system)
6. [Version Upgrade Detection](#6-version-upgrade-detection)
7. [Trial Mode Auto-Recheck](#7-trial-mode-auto-recheck)
8. [File Paths & Storage Locations](#8-file-paths--storage-locations)
9. [Thread Architecture](#9-thread-architecture)
10. [Constants & Timing Reference](#10-constants--timing-reference)

---

## 1. Architecture Overview

```
CrossTrans Application Architecture (Startup & Update related)

Windows Boot
    │
    ▼
Registry: HKCU\...\Run\AITranslator
    │
    ▼
main.py (Entry Point)
    ├── setup_logging()
    ├── is_already_running()  ──→ TCP socket lock on 127.0.0.1:47823
    │       │ (if locked)
    │       └── Show warning → Exit
    │
    └── TranslatorApp()
            ├── Config.load()  ──→ %APPDATA%/AITranslator/config.json
            ├── _check_version_upgrade()
            │       │ (if version changed)
            │       └── Clear __pycache__ → os.execl() restart
            ├── _check_update_status()  ──→ Read %TEMP%/crosstrans_update_*.txt
            ├── Create Root Window (hidden)
            ├── Init Services (Translation, Hotkey, FileProcessor)
            ├── Init UI (Toast, Tooltip, Tray)
            ├── _startup_update_check()  ──→ Background thread (3s delay)
            ├── _schedule_trial_recheck()  ──→ Every 24h
            └── run()
                    ├── Start HotkeyManager thread
                    ├── Start TrayIcon thread (daemon)
                    ├── Pre-warm NLP (daemon thread)
                    └── root.mainloop()
```

### Key Source Files

| File | Role |
|------|------|
| `main.py` | Entry point, single instance check |
| `config.py` | Configuration management, registry auto-start, API key encryption |
| `src/app.py` | Main application class, initialization orchestrator |
| `src/utils/updates.py` | Auto-update logic (check, download, install, fallback) |
| `src/utils/single_instance.py` | TCP socket lock for single instance |
| `src/ui/settings/general_tab.py` | Auto-start toggle UI |
| `src/ui/settings/update_manager.py` | Update check/download UI |
| `src/ui/toast.py` | Toast notification system |
| `src/ui/tray.py` | System tray icon and menu |
| `src/core/quota_manager.py` | Trial mode quota tracking |
| `src/constants.py` | VERSION, GITHUB_REPO, LOCK_PORT |

---

## 2. Auto-Start with Windows

### 2.1 Registry Mechanism

CrossTrans uses the **Windows Registry** to register itself for auto-start.

**Registry Location:**
```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
```

**Registry Key Name:** `AITranslator` (kept for backward compatibility, defined as `APP_NAME` in `config.py` line 22)

**Registry Value (depends on deployment type):**
- **EXE build:** Direct path to `CrossTrans.exe`
  - Example: `C:\Program Files\CrossTrans\CrossTrans.exe`
- **Source code:** Path to `pythonw.exe` with `main.py` argument
  - Example: `"C:\Python310\pythonw.exe" "C:\path\to\main.py"`
  - Uses `pythonw.exe` (not `python.exe`) to avoid console window
  - Falls back to `python.exe` if `pythonw.exe` not found

### 2.2 Enabling/Disabling Auto-Start

**Source: `config.py` lines 328-374**

```
User toggles checkbox in Settings > General tab
    │
    ▼
_on_autostart_toggle()  [general_tab.py line 104]
    │  (500ms debounce to avoid rapid saves)
    ▼
_save_autostart()  [general_tab.py line 112]
    │
    ▼
config.set_autostart(enable)  [config.py line 328]
    ├── Save to config.json: _config['autostart'] = enable
    ├── _update_registry_autostart(enable)  [config.py line 334]
    │       │
    │       ├── If enable=True:
    │       │       exe_path = _get_exe_path()
    │       │       winreg.SetValueEx(key, "AITranslator", 0, REG_SZ, exe_path)
    │       │
    │       └── If enable=False:
    │               winreg.DeleteValue(key, "AITranslator")
    │
    └── config.save()
```

### 2.3 Checking Current Auto-Start Status

**Source: `config.py` lines 365-374**

`is_autostart_enabled()` queries the registry directly (not config.json) to verify the actual state:

```python
# Opens HKCU\Software\Microsoft\Windows\CurrentVersion\Run
# Tries to read "AITranslator" value
# Returns True if value exists, False if FileNotFoundError
```

This ensures the UI checkbox reflects reality even if the registry was modified externally.

### 2.4 EXE Path Detection

**Source: `config.py` lines 351-363**

```python
def _get_exe_path(self) -> str:
    if getattr(sys, 'frozen', False):
        # PyInstaller EXE: return sys.executable directly
        return sys.executable
    else:
        # Source code: find pythonw.exe, construct command
        python_dir = os.path.dirname(sys.executable)
        pythonw = os.path.join(python_dir, 'pythonw.exe')
        script_path = os.path.abspath('main.py')
        return f'"{pythonw}" "{script_path}"'
```

---

## 3. Application Startup Flow

### 3.1 Phase 1: Entry Point (`main.py` lines 28-72)

```
1. setup_logging()
2. is_already_running() → check TCP socket on 127.0.0.1:47823
   ├── If already running: show warning dialog → exit with code 0
   └── If not running: hold socket lock → continue
3. from src.app import TranslatorApp
4. app = TranslatorApp()
5. app.run()
6. finally: lock_socket.close()
```

### 3.2 Phase 2: TranslatorApp.__init__() (`src/app.py` lines 145-238)

```
Step 1: self.config = Config()
        → Loads %APPDATA%/AITranslator/config.json
        → Merges with defaults for missing keys
        → Migrates plaintext API keys to DPAPI encryption

Step 2: self._check_version_upgrade()
        → Compare config.get_last_run_version() with current VERSION
        → If different: clear __pycache__ dirs → restart via os.execl()
        → If same: continue

Step 3: self._check_update_status()
        → Read status files from %TEMP%:
          - crosstrans_update_error.txt    → set self._pending_update_error
          - crosstrans_update_success.txt  → set self._pending_update_success_version
          - crosstrans_update_expected.txt → verify expected version
          - crosstrans_update_pending.txt  → set self._pending_update_path
        → Clean up status files after reading

Step 4: Create Root Window
        → ttkbootstrap with "darkly" theme (or plain Tkinter fallback)
        → TkinterDnD support for drag-and-drop
        → root.withdraw() → window hidden initially

Step 5: Initialize Core Services
        → TranslationService(config)
        → HotkeyManager(config, callback)
        → FileProcessor(api_manager)

Step 6: Initialize UI Components
        → ToastManager(root)
        → TooltipManager(root)
        → TrayManager(config) with callbacks for show/settings/quit

Step 7: Schedule Startup Tasks
        → If auto_check_updates enabled: _startup_update_check()
        → _schedule_trial_recheck()
        → _show_pending_update_dialogs()
```

### 3.3 Phase 3: TranslatorApp.run() (`src/app.py` lines 2456-2530)

```
1. Print version and hotkey info to console/log
2. self.hotkey_manager.start()
   → Registers global hotkeys in a dedicated thread
   → Waits up to 2s for ready event
3. self._create_tray_icon()
   → Creates pystray Icon with menu
   → Runs on daemon thread (blocking Icon.run() call)
4. Pre-warm NLP manager (daemon thread)
   → Loads installed language packs for Dictionary mode
5. self.root.after(100, self._check_queue)
   → Starts queue polling for cross-thread communication
6. self.root.after(60000, self._watchdog_check)
   → Starts watchdog timer
7. self.root.mainloop()
   → Enters Tkinter event loop (blocks until quit)
```

---

## 4. Single Instance Prevention

**Source: `src/utils/single_instance.py`**

### Mechanism: TCP Socket Lock

```python
LOCK_PORT = 47823  # From src/constants.py line 12

def is_already_running() -> Tuple[bool, Optional[socket.socket]]:
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lock_socket.bind(('127.0.0.1', LOCK_PORT))
    lock_socket.listen(1)
    return False, lock_socket   # Success: first instance
    # If socket.error → return True, None  # Already running
```

### How It Works

1. App tries to bind TCP socket to `127.0.0.1:47823`
2. **First instance:** Bind succeeds → socket kept open as lock → app continues
3. **Second instance:** Bind fails (address already in use) → shows warning → exits
4. **Cleanup:** Socket closed in `main.py` finally block when app exits

### Warning Dialog (when duplicate detected)

Shows: "CrossTrans is already running! Check the system tray (bottom-right corner)."

---

## 5. Auto-Update System

### 5.1 Overview

```
Update Flow:

[Startup or Manual Check]
        │
        ▼
    Check GitHub API ──→ GET /repos/Masaru-urasaM/CrossTrans/releases/latest
        │
        ├── No update → done
        │
        └── Update available
                │
                ├── Source build → "Open GitHub Releases?" dialog → browser
                │
                └── EXE build → "Download and install?" dialog
                        │
                        ▼
                    Download EXE (with progress bar)
                        │
                        ▼
                    SHA256 verification (if checksum in release notes)
                        │
                        ▼
                    Create update.bat script
                        │
                        ▼
                    Launch batch script → exit app
                        │
                        ▼
                    Batch script:
                        ├── Wait for app to close (30s timeout)
                        ├── Backup current EXE → .bak
                        ├── Copy new EXE (5 retries, 2s delay)
                        ├── Verify file size
                        ├── Write status files to %TEMP%
                        ├── Launch new version
                        └── Clean up temp files
                                │
                                ├── Success → crosstrans_update_success.txt
                                │
                                └── Failure → crosstrans_update_error.txt
                                        │
                                        ▼
                                    Next app launch reads status files
                                        │
                                        ├── Show success toast
                                        └── Show failure dialog
                                                │
                                                ├── Option 1: Schedule for next Windows restart
                                                │       → MoveFileEx() API
                                                │
                                                └── Option 2: Download manually from GitHub
```

### 5.2 Update Check (`src/utils/updates.py` lines 146-350)

**GitHub API Call:**
```
GET https://api.github.com/repos/Masaru-urasaM/CrossTrans/releases/latest
Headers:
  Accept: application/vnd.github.v3+json
  User-Agent: CrossTrans
Timeout: 30 seconds
SSL: Custom pinning via get_ssl_context_for_url()
```

**Retry Logic:**
- Max 3 retries with exponential backoff: 1s, 2s, 4s
- HTTP 403 (rate limit): retry
- HTTP 404: no retry, return error
- HTTP 5xx: retry
- Network/SSL errors: retry

**Version Comparison:**
```python
from packaging.version import Version
latest_ver = Version(tag_name.lstrip('v'))
current_ver = Version(VERSION)
if latest_ver > current_ver:
    # Update available
```

**Data Extracted from Release:**
- `tag_name` → version number (strip 'v' prefix)
- `body` → release notes (truncated to 300 chars for UI)
- `assets` → search for `.exe` file → download URL
- Release notes regex `SHA256:\s*([0-9a-fA-F]{64})` → checksum

### 5.3 Auto-Check on Startup (`src/app.py` lines 542-568)

```
Condition: config.get_auto_check_updates() == True

Flow:
1. Launch background thread "StartupUpdateCheck" (non-daemon)
2. Wait 3 seconds (STARTUP_UPDATE_DELAY)
3. Call AutoUpdater().check_update()
4. If update found: show toast notification
   → "Update Available - CrossTrans v{X.X.X} is available! Open Settings to update."
   → Toast duration: 5000ms
5. No blocking dialogs (silent check)
```

### 5.4 Download Process (`src/utils/updates.py` lines 359-434)

```
Timeout: 180 seconds (3 minutes)
Chunk size: 8192 bytes
Download path: %TEMP%/crosstrans_update_{random}/CrossTrans_v{version}.exe

Progress:
  → progress_callback(percentage)  # 0-100
  → UI: Modal progress window with progress bar + cancel button

Verification:
  → If SHA256 checksum found in release notes:
    → Calculate SHA256 of downloaded file
    → Compare with expected
    → Delete file and return error if mismatch

Cancellation:
  → Thread-safe threading.Event() flag
  → Cancel button sets event → download loop checks each iteration
```

### 5.5 Installation Process (`src/utils/updates.py` lines 453-659)

The app creates a **Windows batch script** (`update.bat`) that performs the actual update:

```batch
# Pseudocode of update.bat logic:

1. LOG "Starting update..."
2. Write status marker files to %TEMP%

3. WAIT for app process to close:
   - Check every 1 second using "tasklist /PID {pid}"
   - Timeout after 30 seconds
   - If timeout: launch OLD exe and abort

4. BACKUP current EXE:
   - Copy current.exe → current.exe.bak
   - Retry up to 5 times with 2-second delays
   - If all retries fail: launch old exe and abort

5. COPY new EXE:
   - Copy downloaded.exe → current.exe
   - Retry up to 5 times with 2-second delays
   - Verify file size matches source
   - If copy fails: ROLLBACK from .bak file

6. On SUCCESS:
   - Write crosstrans_update_success.txt
   - Launch new exe
   - Clean up temp directory and batch script

7. On FAILURE:
   - Write crosstrans_update_error.txt
   - Restore from .bak if possible
   - Launch old exe
   - Clean up
```

**Batch script launched with:** `subprocess.Popen()` using `CREATE_NO_WINDOW` flag only (no visible console window).

> **Warning (v1.9.9 fix):** Do NOT combine `CREATE_NO_WINDOW` with `DETACHED_PROCESS` - they are mutually exclusive per Microsoft docs and cause undefined behavior (visible CMD window on some Windows versions).

### 5.5.1 v1.9.9 Update System Fixes

The following critical bugs were fixed in v1.9.9:

1. **`os._exit(0)` instead of `sys.exit(0)`**: `sys.exit()` raises `SystemExit` which Tkinter's `after()` callback handler silently catches, preventing the app from exiting. `os._exit(0)` terminates immediately.

2. **Removed `DETACHED_PROCESS` flag**: Was combined with `CREATE_NO_WINDOW`, causing a visible CMD window.

3. **EXE versioned rename**: After update, new EXE is named `CrossTrans_v{version}.exe` instead of overwriting the old file. Old EXE is backed up to `.bak`. Registry auto-start path is updated by the batch script.

4. **Batch script parenthesis fix**: `(` and `)` characters inside echo strings within `if` blocks break cmd.exe parsing. All parentheses removed from echo strings in if blocks.

5. **File descriptor redirect fix**: `echo 1.9.8>file` causes `8>` to be interpreted as file descriptor 8 redirect. Fixed by adding space before `>`.

6. **First-launch retry**: New EXE may fail on first launch due to Windows Defender scanning. Added 2s delay before launch + automatic retry if process doesn't start.

### 5.6 Reboot Fallback (`src/utils/updates.py` lines 665-734)

When the batch script fails (file locked, permissions, etc.), the app offers a **reboot fallback**:

```python
# Uses Windows API: MoveFileEx()
# Flag: MOVEFILE_DELAY_UNTIL_REBOOT

# This registers a pending file rename in Windows registry:
# HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\PendingFileRenameOperations
# Windows executes this BEFORE any user applications start on next boot
```

**Error codes handled:** 403 (access denied), 2 (file not found), 3 (path not found)

### 5.7 Post-Update Status Check (`src/app.py` lines 305-410)

On every app startup, `_check_update_status()` reads status files from `%TEMP%`:

| Status File | Meaning | App Response |
|-------------|---------|--------------|
| `crosstrans_update_success.txt` | Update succeeded | Show success toast (2s delay): "Update Successful - CrossTrans has been updated to v{X.X.X}" |
| `crosstrans_update_error.txt` | Update failed | Show failure dialog with options |
| `crosstrans_update_expected.txt` | Expected version | Used to verify success |
| `crosstrans_update_pending.txt` | Path to pending update | Offer MoveFileEx reboot fallback |

**Failure dialog options:**
1. "Schedule for next Windows restart" → calls `AutoUpdater.schedule_update_on_reboot()`
2. "Download manually from GitHub" → opens browser to releases page
3. Skip/dismiss

### 5.8 Source vs EXE Behavior

Detection: `getattr(sys, 'frozen', False)`

| Aspect | Source Code | Compiled EXE |
|--------|------------|--------------|
| Update check | Same GitHub API call | Same GitHub API call |
| Update action | "Open GitHub Releases?" → browser | "Download and install?" → auto-update |
| Auto-install | Not available | Full batch script flow |
| Reboot fallback | Not available | MoveFileEx API |

### 5.9 Update Settings in UI

**Settings > General tab** (`src/ui/settings/general_tab.py`):
- Checkbox: "Check for updates on startup" → `config.set_auto_check_updates(bool)`
- Auto-saves on toggle change

**Settings > General tab** (`src/ui/settings/update_manager.py`):
- Button: "Check for Updates" (or "Retry Update Check" after error)
- Status label with color coding
- Progress dialog during download
- Release notes display (first 300 characters)

### 5.10 Update Telemetry (Local Only)

**Source: `config.py` lines 504-558**

Stored in `config.json` only (no external transmission):
```json
{
    "update_stats": {
        "total": 15,
        "success": 12,
        "failed": 3,
        "last_check": "2024-01-15T10:30:00",
        "last_success": "2024-01-15T10:30:00",
        "error_types": {
            "network": 2,
            "rate_limit": 1,
            "ssl": 0,
            "timeout": 0,
            "parse_error": 0,
            "other": 0
        }
    }
}
```

---

## 6. Version Upgrade Detection

**Source: `src/app.py` lines 240-303**

### Mechanism

```
App startup
    │
    ▼
config.get_last_run_version()  ──→ Read from config.json
    │
    ▼
Compare with current VERSION (from src/constants.py)
    │
    ├── Same version → continue normally
    │
    └── Different version (upgrade detected)
            │
            ▼
        _clear_caches_and_restart()
            │
            ├── Delete __pycache__ directories:
            │     src/__pycache__/
            │     src/core/__pycache__/
            │     src/ui/__pycache__/
            │     src/ui/settings/__pycache__/
            │     src/utils/__pycache__/
            │     src/assets/__pycache__/
            │
            ├── config.set_last_run_version(VERSION)
            │     → Save new version to config.json
            │
            └── os.execl(sys.executable, sys.executable, *sys.argv)
                  → Restart the entire Python process
                  → __init__() returns True, run() is never called
                  → On restart: versions match → continue normally
```

### Why Cache Clearing?

Python's `__pycache__` contains compiled `.pyc` files. When the app is updated (especially from a batch script that replaces the EXE or source files), stale `.pyc` files can cause:
- ImportError from changed module structures
- Old behavior persisting despite code changes
- AttributeError from renamed/removed functions

The cache clear + restart ensures the new code runs cleanly.

---

## 7. Trial Mode Auto-Recheck

**Source: `src/app.py` lines 476-540**

### Purpose

When a user's API key stops working (expired, quota exceeded, etc.), CrossTrans forces trial mode (100 free translations/day). The auto-recheck periodically tests if the API key is working again, and automatically disables trial mode if so.

### Mechanism

```
App startup
    │
    ▼
_schedule_trial_recheck()
    │
    ├── If trial_mode_forced == False → skip (no recheck needed)
    │
    └── If trial_mode_forced == True:
            │
            ├── Read config.trial_last_api_check (ISO datetime)
            │
            ├── If 24+ hours since last check:
            │       │
            │       ▼
            │   Schedule _recheck_api_keys_for_trial() after 5 seconds
            │       │
            │       ▼
            │   For each saved API key:
            │       → Test connection via AIAPIManager.test_connection()
            │       → If ANY key works:
            │           ├── config.set_trial_mode_forced(False)
            │           └── Show toast: "API Key Restored - Your API key is now working."
            │       → Update config.trial_last_api_check to now
            │
            └── Schedule next _schedule_trial_recheck() after 1 hour
                (keeps checking every hour while app is running)
```

### Key Timing
- First check: 5 seconds after startup (if 24h elapsed)
- Recurring: Every 1 hour (`self.root.after(3600000, ...)`)
- API check interval: Only actually tests keys if 24+ hours since last test

---

## 8. File Paths & Storage Locations

| Component | Path | Purpose |
|-----------|------|---------|
| Config | `%APPDATA%/AITranslator/config.json` | All app settings, API keys (encrypted), update stats |
| App Logs | `logs/` (relative to app dir) | Application log files |
| Download Temp | `%TEMP%/crosstrans_update_{random}/` | Downloaded update EXE |
| Update Log | `%TEMP%/crosstrans_update.log` | Batch script log |
| Update Error | `%TEMP%/crosstrans_update_error.txt` | Error message from failed update |
| Update Success | `%TEMP%/crosstrans_update_success.txt` | Success marker from update |
| Expected Version | `%TEMP%/crosstrans_update_expected.txt` | Expected version number |
| Pending Update | `%TEMP%/crosstrans_update_pending.txt` | Path to pending update file |
| Backup EXE | `{current_exe}.bak` | Backup before update |
| Registry | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\AITranslator` | Auto-start entry |
| Socket Lock | `127.0.0.1:47823` | Single instance prevention |

---

## 9. Thread Architecture

| Thread Name | Type | Purpose | Daemon? |
|-------------|------|---------|---------|
| `MainThread` | Main | Tkinter event loop (`root.mainloop()`) | N/A |
| `StartupUpdateCheck` | Background | Silent update check on startup | No |
| `UpdateCheckThread` | Background | Manual update check from Settings | No |
| `DownloadThread` | Background | Download update EXE | No |
| `UpdateMonitor` | Background | Monitor download thread for timeout | No |
| `HotkeyThread` | Background | Listen for global hotkeys | Yes |
| `TrayThread` | Background | Run system tray icon | Yes |
| `NLPPrewarm` | Background | Pre-load NLP language packs | Yes |

### Thread Safety Patterns Used
- `threading.Event()` for download cancellation
- `self.root.after()` for UI updates from background threads
- `queue.Queue()` for cross-thread communication
- Dictionary container for exception passing between threads

---

## 10. Constants & Timing Reference

**Source: `src/utils/updates.py` lines 32-45, `src/constants.py`**

| Constant | Value | Purpose |
|----------|-------|---------|
| `VERSION` | `"1.9.9"` | Current app version |
| `GITHUB_REPO` | `"Masaru-urasaM/CrossTrans"` | GitHub repository |
| `LOCK_PORT` | `47823` | Single instance TCP port |
| `UPDATE_CHECK_TIMEOUT` | 30s | HTTP request timeout |
| `UPDATE_DOWNLOAD_TIMEOUT` | 180s | Download timeout |
| `UPDATE_CHECK_MAX_RETRIES` | 3 | Retry attempts for check |
| `UPDATE_THREAD_TIMEOUT` | 60s | Thread join timeout |
| `RELEASE_NOTES_MAX_LENGTH` | 300 chars | Truncation limit for UI |
| `PROGRESS_WINDOW_SIZE` | `"350x120"` | Progress dialog size |
| `UPDATE_TOAST_DURATION` | 5000ms | Toast notification display time |
| `STARTUP_UPDATE_DELAY` | 3s | Delay before auto-check |
| `AUTOSTART_DEBOUNCE` | 500ms | Debounce for auto-start toggle |
| `TRIAL_RECHECK_INTERVAL` | 1 hour | How often to check trial status |
| `TRIAL_API_CHECK_INTERVAL` | 24 hours | Min time between actual API tests |
| Batch script process wait | 30s | Timeout waiting for app to close |
| Batch script file copy retry | 5 attempts, 2s delay | Retry for file operations |

---

## Appendix: Config.json Schema (Update & Startup Related)

```json
{
    "autostart": false,
    "auto_check_updates": false,
    "last_run_version": "1.9.8.2",
    "trial_mode_forced": false,
    "trial_last_api_check": "2024-01-15T10:30:00",
    "update_stats": {
        "total": 0,
        "success": 0,
        "failed": 0,
        "last_check": "",
        "last_success": "",
        "error_types": {
            "network": 0,
            "rate_limit": 0,
            "ssl": 0,
            "parse_error": 0,
            "timeout": 0,
            "other": 0
        }
    }
}
```
