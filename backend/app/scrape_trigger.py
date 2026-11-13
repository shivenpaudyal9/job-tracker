"""
Run the job scrape from inside the backend.

The scrape used to run only from a GitHub Actions cron job. When that
workflow is disabled or its secrets go stale, no jobs are scraped at all.
This lets the backend start the same scrape itself, in a background thread,
whenever the public job endpoints are hit and the last run is old enough.

A lock file (shared by all gunicorn workers on the instance) makes sure
only one scrape runs at a time and that runs are at least SCRAPE_INTERVAL
apart.
"""

import logging
import os
import tempfile
import threading
import time

logger = logging.getLogger(__name__)

SCRAPE_INTERVAL_SECONDS = int(os.getenv("SCRAPE_INTERVAL_SECONDS", str(4 * 3600)))
_LOCK_PATH = os.path.join(tempfile.gettempdir(), "jobtracker_scrape.lock")
_thread_guard = threading.Lock()


def _claim_run() -> bool:
    """Atomically claim the next run. Returns False if one ran recently."""
    now = time.time()
    try:
        age = now - os.path.getmtime(_LOCK_PATH)
        if age < SCRAPE_INTERVAL_SECONDS:
            return False
        os.remove(_LOCK_PATH)
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning("Scrape lock check failed: %s", e)
        return False

    try:
        fd = os.open(_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(now).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False  # another worker claimed it first
    except OSError as e:
        logger.warning("Could not create scrape lock: %s", e)
        return False


def _run():
    try:
        from jobs.daily_scrape import run
        run()
    except Exception as e:
        logger.exception("Background scrape failed: %s", e)


def maybe_start_scrape() -> str:
    """Start a background scrape if none ran within the interval.

    Returns "started" or "skipped". Never raises.
    """
    if os.getenv("DISABLE_BACKGROUND_SCRAPE") == "1":
        return "skipped"
    try:
        with _thread_guard:
            if not _claim_run():
                return "skipped"
        threading.Thread(target=_run, name="job-scrape", daemon=True).start()
        logger.info("Background job scrape started")
        return "started"
    except Exception as e:
        logger.warning("Could not start background scrape: %s", e)
        return "skipped"
