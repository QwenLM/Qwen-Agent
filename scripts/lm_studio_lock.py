#!/usr/bin/env python3
"""
LM Studio single-job lock.

Ensures only one heavy LLM job (regression, locale batches, etc.) runs
at a time against the local LM Studio instance. Uses a file lock in
/tmp so it works across processes without extra dependencies.

Usage:
    from scripts.lm_studio_lock import lm_studio_lock

    with lm_studio_lock("locale-batches"):
        # ... your LLM work here ...

If another job holds the lock, this will print a clear message and exit(1).
"""
from __future__ import annotations

import atexit
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

LOCK_FILE = Path("/tmp/lm_studio_job.lock")
STALE_THRESHOLD_SEC = 7200  # 2 hours — assume stale if older


def _read_lock() -> dict | None:
    """Read existing lock file. Returns None if missing or corrupt."""
    try:
        if not LOCK_FILE.exists():
            return None
        data = json.loads(LOCK_FILE.read_text())
        return data
    except Exception:
        return None


def _is_process_alive(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _acquire(job_name: str) -> bool:
    """Try to acquire the lock. Returns True if acquired."""
    existing = _read_lock()

    if existing:
        owner_pid = existing.get("pid", -1)
        owner_name = existing.get("job", "unknown")
        started = existing.get("started", 0)
        age_sec = time.time() - started

        # Check if the owning process is still alive
        if _is_process_alive(owner_pid) and age_sec < STALE_THRESHOLD_SEC:
            age_min = int(age_sec / 60)
            print(
                f"\n[LOCK] LM Studio is busy.\n"
                f"  Another job is running: {owner_name} (pid={owner_pid}, {age_min}m ago)\n"
                f"  Lock file: {LOCK_FILE}\n\n"
                f"  Options:\n"
                f"    1. Wait for '{owner_name}' to finish\n"
                f"    2. Cancel that job, then: rm {LOCK_FILE}\n"
                f"    3. If the lock is stale: rm {LOCK_FILE}\n"
            )
            return False

        # Stale lock or dead process — reclaim
        print(f"[LOCK] Reclaiming stale lock (previous: {owner_name}, pid={owner_pid})")

    # Write our lock
    LOCK_FILE.write_text(json.dumps({
        "job": job_name,
        "pid": os.getpid(),
        "started": time.time(),
    }))
    return True


def _release():
    """Release the lock if we own it."""
    existing = _read_lock()
    if existing and existing.get("pid") == os.getpid():
        try:
            LOCK_FILE.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def lm_studio_lock(job_name: str):
    """Context manager: acquire LM Studio lock or exit(1)."""
    if not _acquire(job_name):
        sys.exit(1)

    # Auto-release on exit (normal or crash)
    atexit.register(_release)
    try:
        yield
    finally:
        _release()
