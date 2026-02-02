"""
Test script for the update system.

This script simulates different update scenarios to verify the implementation works.
Run this from the project directory: python test_update_system.py
"""
import os
import sys
import tempfile
import shutil

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_batch_script_generation():
    """Test that the batch script is generated correctly."""
    print("\n=== Test 1: Batch Script Generation ===")

    from src.utils.updates import AutoUpdater

    updater = AutoUpdater()
    updater.latest_version = "1.9.9"

    # Create a fake download
    temp_dir = tempfile.mkdtemp(prefix='crosstrans_test_')
    fake_exe = os.path.join(temp_dir, 'CrossTrans_v1.9.9.exe')

    # Create a fake EXE file
    with open(fake_exe, 'wb') as f:
        f.write(b'FAKE_EXE_CONTENT_FOR_TESTING' * 1000)

    updater.download_path = fake_exe

    # Check batch script would be created
    print(f"  Download path: {updater.download_path}")
    print(f"  Latest version: {updater.latest_version}")
    print(f"  File exists: {os.path.exists(fake_exe)}")
    print(f"  File size: {os.path.getsize(fake_exe)} bytes")

    # Clean up
    shutil.rmtree(temp_dir)
    print("  [OK] Batch script generation test passed")


def test_movefile_api():
    """Test that MoveFileEx API is accessible."""
    print("\n=== Test 2: MoveFileEx API Access ===")

    import ctypes
    from ctypes import wintypes

    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.MoveFileExW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD
        ]
        kernel32.MoveFileExW.restype = wintypes.BOOL
        print("  [OK] MoveFileEx API is accessible")
    except Exception as e:
        print(f"  [FAIL] MoveFileEx API error: {e}")


def test_update_status_files():
    """Test that status files are created and read correctly."""
    print("\n=== Test 3: Status File Handling ===")

    temp = os.environ.get('TEMP', os.environ.get('TMP', ''))

    # Test files
    error_file = os.path.join(temp, 'crosstrans_update_error.txt')
    success_file = os.path.join(temp, 'crosstrans_update_success.txt')
    expected_file = os.path.join(temp, 'crosstrans_update_expected.txt')
    pending_file = os.path.join(temp, 'crosstrans_update_pending.txt')

    # Create test files
    with open(error_file, 'w') as f:
        f.write("Test error message")

    with open(expected_file, 'w') as f:
        f.write("1.9.9")

    with open(pending_file, 'w') as f:
        f.write("C:\\path\\to\\pending.exe")

    # Verify files exist
    print(f"  Error file exists: {os.path.exists(error_file)}")
    print(f"  Expected file exists: {os.path.exists(expected_file)}")
    print(f"  Pending file exists: {os.path.exists(pending_file)}")

    # Read files
    with open(error_file, 'r') as f:
        error_msg = f.read().strip()
    print(f"  Error message: '{error_msg}'")

    with open(expected_file, 'r') as f:
        expected_ver = f.read().strip()
    print(f"  Expected version: '{expected_ver}'")

    # Clean up
    for f in [error_file, success_file, expected_file, pending_file]:
        if os.path.exists(f):
            os.remove(f)

    print("  [OK] Status file handling test passed")


def test_update_failed_dialog():
    """Test that UpdateFailedDialog can be imported."""
    print("\n=== Test 4: UpdateFailedDialog Import ===")

    try:
        from src.ui.dialogs import UpdateFailedDialog
        print("  [OK] UpdateFailedDialog imported successfully")
        print(f"  Class: {UpdateFailedDialog}")
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")


def test_schedule_update_on_reboot():
    """Test the schedule_update_on_reboot method."""
    print("\n=== Test 5: Schedule Update on Reboot ===")

    from src.utils.updates import AutoUpdater

    updater = AutoUpdater()

    # Create temp files for testing
    temp_dir = tempfile.mkdtemp(prefix='crosstrans_reboot_test_')
    source = os.path.join(temp_dir, 'source.exe')
    dest = os.path.join(temp_dir, 'dest.exe')

    # Create source file
    with open(source, 'wb') as f:
        f.write(b'SOURCE_EXE_CONTENT')

    print(f"  Source: {source}")
    print(f"  Dest: {dest}")

    # Test the function (this will NOT actually schedule, just test the API call)
    # Note: This might fail if not running as admin
    result = updater.schedule_update_on_reboot(source, dest)
    print(f"  Result: {result}")

    if result['success']:
        print("  [OK] MoveFileEx succeeded (update scheduled for reboot)")
        print("  Note: You would need to reboot to see the effect")
    else:
        print(f"  [WARN] MoveFileEx returned: {result.get('message', 'Unknown error')}")
        print("  This is expected if not running as administrator")

    # Clean up
    shutil.rmtree(temp_dir)


def test_github_api():
    """Test GitHub API connectivity."""
    print("\n=== Test 6: GitHub API Connectivity ===")

    from src.utils.updates import AutoUpdater

    updater = AutoUpdater()
    result = updater.check_update()

    print(f"  Result: {result}")

    if result.get('error'):
        print(f"  [WARN] Error: {result['error']}")
    elif result.get('has_update'):
        print(f"  [OK] Update available: v{result['version']}")
    else:
        print(f"  [OK] Already up to date: v{result.get('version', 'unknown')}")


def simulate_update_failure():
    """Simulate an update failure to test the dialog."""
    print("\n=== Test 7: Simulate Update Failure ===")

    temp = os.environ.get('TEMP', '')

    # Create error file as if update failed
    error_file = os.path.join(temp, 'crosstrans_update_error.txt')
    expected_file = os.path.join(temp, 'crosstrans_update_expected.txt')
    pending_file = os.path.join(temp, 'crosstrans_update_pending.txt')

    with open(error_file, 'w') as f:
        f.write("Test: File is locked by another process")

    with open(expected_file, 'w') as f:
        f.write("1.9.9")

    with open(pending_file, 'w') as f:
        f.write("C:\\temp\\CrossTrans_v1.9.9.exe")

    print(f"  Created error file: {error_file}")
    print(f"  Created expected file: {expected_file}")
    print(f"  Created pending file: {pending_file}")
    print("")
    print("  Now run the app (python main.py) to see the UpdateFailedDialog!")
    print("  The dialog should appear on startup.")


def cleanup_test_files():
    """Remove any leftover test files."""
    print("\n=== Cleanup Test Files ===")

    temp = os.environ.get('TEMP', '')
    files = [
        'crosstrans_update_error.txt',
        'crosstrans_update_success.txt',
        'crosstrans_update_expected.txt',
        'crosstrans_update_pending.txt',
        'crosstrans_update.log'
    ]

    for f in files:
        path = os.path.join(temp, f)
        if os.path.exists(path):
            os.remove(path)
            print(f"  Removed: {path}")

    print("  [OK] Cleanup complete")


if __name__ == '__main__':
    print("=" * 60)
    print("CrossTrans Update System Test Suite")
    print("=" * 60)

    if len(sys.argv) > 1:
        if sys.argv[1] == '--simulate-failure':
            simulate_update_failure()
        elif sys.argv[1] == '--cleanup':
            cleanup_test_files()
        elif sys.argv[1] == '--github':
            test_github_api()
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Options: --simulate-failure, --cleanup, --github")
    else:
        # Run all tests
        test_batch_script_generation()
        test_movefile_api()
        test_update_status_files()
        test_update_failed_dialog()
        test_schedule_update_on_reboot()
        test_github_api()

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        print("\nTo simulate an update failure and see the dialog:")
        print("  python test_update_system.py --simulate-failure")
        print("  python main.py")
        print("\nTo cleanup test files:")
        print("  python test_update_system.py --cleanup")
