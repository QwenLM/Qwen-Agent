#!/usr/bin/env python3
"""
LM Studio job lock with size-aware coexistence.

Ensures heavy LLM jobs don't stomp on each other when sharing a single
local LM Studio instance.  Jobs declare their "weight" — a rough estimate
of how many concurrent LLM calls they'll make and for how long.

Rules:
  - A new job checks the lock.  If no job is running → acquire.
  - If a job IS running, the new job estimates its own weight.
    * weight == "light"  → allowed to run alongside (e.g. validate-only,
      dry-run, single-teacher shard, smoke probe)
    * weight == "heavy"  → blocked, with a clear message explaining why.
  - The running job also records its weight, so a second heavy job can
    see "the holder is heavy, I'm heavy → blocked" while a light job
    can see "the holder is heavy, I'm light → proceed".

Weight heuristics (callers pass shards/timeout hints):
  shards <= 3  AND  timeout <= 60   → light
  everything else                    → heavy

Usage:
    from scripts.lm_studio_lock import lm_studio_lock

    # Heavy job (full locale batches)
    with lm_studio_lock("locale-batches", shards=318, timeout_sec=120):
        ...

    # Light job (validate-only, no LLM calls)
    with lm_studio_lock("locale-validate", shards=0, timeout_sec=60):
        ...

If blocked, prints a clear message and exits(1).
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

# ─── Weight thresholds ──────────────────────────────────────────────────────
LIGHT_MAX_SHARDS = 3
LIGHT_MAX_TIMEOUT = 60


def classify_weight(shards: int, timeout_sec: int) -> str:
    """Classify a job as 'light' or 'heavy' based on its size."""
    if shards <= LIGHT_MAX_SHARDS and timeout_sec <= LIGHT_MAX_TIMEOUT:
        return "light"
    return "heavy"


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


def _acquire(job_name: str, weight: str, shards: int, timeout_sec: int) -> bool:
    """
    Try to acquire the lock.

    Returns True if:
      - No lock exists (we take it)
      - Lock exists but owner is dead / stale (we reclaim)
      - Lock exists, owner is alive, but OUR job is light (coexist)

    Returns False if:
      - Lock exists, owner is alive, and OUR job is heavy (blocked)
    """
    existing = _read_lock()

    if existing:
        owner_pid = existing.get("pid", -1)
        owner_name = existing.get("job", "unknown")
        owner_weight = existing.get("weight", "heavy")
        owner_shards = existing.get("shards", "?")
        started = existing.get("started", 0)
        age_sec = time.time() - started

        # Check if the owning process is still alive
        if _is_process_alive(owner_pid) and age_sec < STALE_THRESHOLD_SEC:
            age_min = int(age_sec / 60)

            # Light jobs can coexist with any running job
            if weight == "light":
                print(
                    f"[LOCK] Another job running: {owner_name} ({owner_weight}, "
                    f"{owner_shards} shards, {age_min}m ago)\n"
                    f"  This job '{job_name}' is light ({shards} shards) — proceeding alongside."
                )
                return True

            # Heavy job trying to run alongside another job → blocked
            print(
                f"\n[LOCK] LM Studio is busy — job too big to run alongside.\n"
                f"  Running:  {owner_name} ({owner_weight}, {owner_shards} shards, "
                f"pid={owner_pid}, {age_min}m ago)\n"
                f"  Blocked:  {job_name} ({weight}, {shards} shards)\n"
                f"  Lock file: {LOCK_FILE}\n\n"
                f"  Options:\n"
                f"    1. Wait for '{owner_name}' to finish, then re-run\n"
                f"    2. Cancel that job, then:  rm {LOCK_FILE}\n"
                f"    3. If the lock is stale:   rm {LOCK_FILE}\n"
            )
            return False

        # Stale lock or dead process — reclaim
        print(f"[LOCK] Reclaiming stale lock (previous: {owner_name}, pid={owner_pid})")

    # Write our lock (only heavy jobs write — light jobs don't need to block others)
    if weight == "heavy":
        LOCK_FILE.write_text(json.dumps({
            "job": job_name,
            "pid": os.getpid(),
            "weight": weight,
            "shards": shards,
            "timeout_sec": timeout_sec,
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
def lm_studio_lock(
    job_name: str,
    shards: int = 999,
    timeout_sec: int = 120,
):
    """
    Context manager: acquire LM Studio lock or exit(1).

    Args:
        job_name:    Human-readable job identifier (e.g. "locale-batches")
        shards:      Number of LLM call units this job will make.
                     0 = no LLM calls (validate-only). <=3 with short timeout = light.
        timeout_sec: Per-shard timeout. Used for weight classification.

    Light jobs (<=3 shards, <=60s timeout) are allowed to coexist with
    a running heavy job. Heavy jobs block if another job is running.
    """
    weight = classify_weight(shards, timeout_sec)

    if not _acquire(job_name, weight, shards, timeout_sec):
        sys.exit(1)

    # Only register cleanup for heavy jobs (they wrote the lock file)
    if weight == "heavy":
        atexit.register(_release)

    try:
        yield
    finally:
        if weight == "heavy":
            _release()
