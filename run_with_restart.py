"""
Auto-restart wrapper for AI Translator.
Monitors the main app and restarts it if it crashes.

Usage: python run_with_restart.py
"""
import subprocess
import sys
import time
import os
import logging
from datetime import datetime

# Setup logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'restart_wrapper_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configuration
MAX_RESTARTS = 5          # Max restarts within reset window
RESTART_WINDOW = 3600     # Reset restart count after 1 hour of stable running
MIN_RUN_TIME = 60         # Consider crash if app runs less than 60 seconds
RESTART_DELAY = 5         # Seconds to wait before restarting

def get_script_path():
    """Get the path to translator.py"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'translator.py')

def run_translator():
    """Run the translator and return exit code."""
    script_path = get_script_path()
    python_exe = sys.executable

    logging.info(f"Starting AI Translator: {script_path}")
    start_time = time.time()

    try:
        process = subprocess.Popen(
            [python_exe, script_path],
            cwd=os.path.dirname(script_path)
        )
        process.wait()
        run_duration = time.time() - start_time
        return process.returncode, run_duration
    except Exception as e:
        logging.error(f"Failed to start translator: {e}")
        return -1, 0

def main():
    logging.info("=" * 50)
    logging.info("AI Translator Auto-Restart Wrapper Started")
    logging.info("=" * 50)

    restart_count = 0
    last_stable_time = time.time()

    while True:
        exit_code, run_duration = run_translator()

        logging.info(f"Translator exited with code {exit_code} after {run_duration:.0f} seconds")

        # Check if it was a clean exit (user quit)
        if exit_code == 0:
            logging.info("Clean exit detected. Not restarting.")
            break

        # Reset restart count if app ran for a while (stable)
        if run_duration > RESTART_WINDOW:
            restart_count = 0
            last_stable_time = time.time()
            logging.info("App ran stable. Reset restart count.")

        # Check if we've exceeded max restarts
        restart_count += 1
        if restart_count > MAX_RESTARTS:
            logging.error(f"Max restarts ({MAX_RESTARTS}) exceeded. Giving up.")
            logging.error("Please check the logs for errors and restart manually.")
            break

        # Check if crash was too quick (possible config/startup issue)
        if run_duration < MIN_RUN_TIME:
            logging.warning(f"App crashed quickly ({run_duration:.0f}s). Possible startup issue.")

        # Wait before restarting
        logging.info(f"Restarting in {RESTART_DELAY} seconds... (attempt {restart_count}/{MAX_RESTARTS})")
        time.sleep(RESTART_DELAY)

    logging.info("Auto-restart wrapper stopped.")

if __name__ == "__main__":
    main()
