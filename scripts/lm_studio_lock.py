#!/usr/bin/env python3
"""
LM Studio job lock with three-tier coexistence.

Jobs declare their weight (light / medium / heavy) based on shard count
and timeout.  The lock uses a compatibility matrix to decide whether a
new job can run alongside an existing one.

Compatibility matrix:
    holder ↓ / new →   light   medium   heavy
    light               ✓        ✓        ✓
    medium              ✓        ✓        ✗
    heavy               ✓        ✗        ✗

Stale-lock recovery: if the PID that wrote the lock is dead, or the
lock is older than STALE_THRESHOLD_SEC, it is reclaimed automatically.

Usage:
    from scripts.lm_studio_lock import lm_studio_lock

    with lm_studio_lock("locale-batches", shards=318, timeout_sec=120):
        ...  # heavy — blocks if another heavy/medium is running

    with lm_studio_lock("marketing-briefs", shards=12, timeout_sec=90):
        ...  # medium — blocks only if heavy is running

    with lm_studio_lock("smoke-probe", shards=1, timeout_sec=30):
        ...  # light — always proceeds
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

# ─── Weight thresholds (config-driven) ──────────────────────────────────────
# Override these via environment variables if needed:
#   LM_LOCK_LIGHT_MAX_SHARDS=5 LM_LOCK_MEDIUM_MAX_SHARDS=50 ...
LIGHT_MAX_SHARDS = int(os.environ.get("LM_LOCK_LIGHT_MAX_SHARDS", 3))
LIGHT_MAX_TIMEOUT = int(os.environ.get("LM_LOCK_LIGHT_MAX_TIMEOUT", 60))
MEDIUM_MAX_SHARDS = int(os.environ.get("LM_LOCK_MEDIUM_MAX_SHARDS", 30))
MEDIUM_MAX_TIMEOUT = int(os.environ.get("LM_LOCK_MEDIUM_MAX_TIMEOUT", 180))

# Compatibility: can NEW weight run alongside HOLDER weight?
# Read as: COMPAT[holder_weight][new_weight] → bool
COMPAT = {
    "light":  {"light": True,  "medium": True,  "heavy": True},
    "medium": {"light": True,  "medium": True,  "heavy": False},
    "heavy":  {"light": True,  "medium": False, "heavy": False},
}


def classify_weight(shards: int, timeout_sec: int) -> str:
    """Classify a job as light / medium / heavy."""
    if shards <= LIGHT_MAX_SHARDS and timeout_sec <= LIGHT_MAX_TIMEOUT:
        return "light"
    if shards <= MEDIUM_MAX_SHARDS and timeout_sec <= MEDIUM_MAX_TIMEOUT:
        return "medium"
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
      - Lock exists, owner is alive, and compatibility matrix allows coexistence

    Returns False if:
      - Lock exists, owner is alive, and compatibility matrix blocks us
    """
    existing = _read_lock()

    if existing:
        owner_pid = existing.get("pid", -1)
        owner_name = existing.get("job", "unknown")
        owner_weight = existing.get("weight", "heavy")
        owner_shards = existing.get("shards", "?")
        started = existing.get("started", 0)
        age_sec = time.time() - started

        # Stale-lock recovery: dead process or too old
        if not _is_process_alive(owner_pid):
            print(f"[LOCK] Reclaiming lock — owner process (pid={owner_pid}) is dead")
        elif age_sec >= STALE_THRESHOLD_SEC:
            age_hr = age_sec / 3600
            print(f"[LOCK] Reclaiming lock — stale ({age_hr:.1f}h old, threshold={STALE_THRESHOLD_SEC/3600:.0f}h)")
        else:
            # Owner is alive and lock is fresh — check compatibility
            age_min = int(age_sec / 60)
            allowed = COMPAT.get(owner_weight, {}).get(weight, False)

            if allowed:
                print(
                    f"[LOCK] {owner_name} ({owner_weight}, {owner_shards} shards) running for {age_min}m.\n"
                    f"  This job '{job_name}' is {weight} ({shards} shards) — compatible, proceeding."
                )
                return True

            # Blocked
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

    # Write lock (only medium/heavy — light jobs don't need to block others)
    if weight in ("medium", "heavy"):
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
        job_name:    Human-readable job identifier
        shards:      Number of LLM call units (0 = no LLM calls)
        timeout_sec: Per-shard timeout

    Weight classification:
        light:   ≤3 shards, ≤60s   → always proceeds
        medium:  4-30 shards, ≤180s → blocked by heavy, not by medium/light
        heavy:   >30 shards or >180s → blocked by heavy or medium
    """
    weight = classify_weight(shards, timeout_sec)

    if not _acquire(job_name, weight, shards, timeout_sec):
        sys.exit(1)

    # Only register cleanup for medium/heavy (they wrote the lock file)
    if weight in ("medium", "heavy"):
        atexit.register(_release)

    try:
        yield
    finally:
        if weight in ("medium", "heavy"):
            _release()
