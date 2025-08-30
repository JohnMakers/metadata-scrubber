# app/utils/cleanup.py
"""
Periodic cleanup of old files in UPLOAD_DIR and OUTPUT_DIR.
We scan on every upload, and also schedule a periodic task.
"""

from datetime import datetime
from pathlib import Path
from app.settings import UPLOAD_DIR, OUTPUT_DIR, RETENTION
import os
import time
import threading

def _is_old(path: Path) -> bool:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return (datetime.now() - mtime) > RETENTION
    except FileNotFoundError:
        return False

def cleanup_once() -> None:
    for root in (UPLOAD_DIR, OUTPUT_DIR):
        for p in root.glob("*"):
            try:
                if p.is_file() and _is_old(p):
                    p.unlink(missing_ok=True)
            except Exception:
                # We intentionally swallow cleanup errors to avoid impacting user flow.
                pass

def start_background_cleanup(interval_seconds: int = 120) -> None:
    """
    Starts a background thread that periodically cleans old files.
    This is lightweight and fine for an MVP. For production,
    use a proper scheduler (e.g., Celery beat, APScheduler, or cron).
    """
    def _loop():
        while True:
            cleanup_once()
            time.sleep(interval_seconds)

    t = threading.Thread(target=_loop, name="cleanup-thread", daemon=True)
    t.start()
