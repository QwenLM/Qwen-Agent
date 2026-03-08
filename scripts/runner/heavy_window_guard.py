#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import yaml


def _in_range(now_hour: int, start: int, end: int) -> bool:
    # Inclusive start, exclusive end. Supports overnight ranges.
    if start < end:
        return start <= now_hour < end
    return now_hour >= start or now_hour < end


def _is_allowed(window_cfg: dict, now_hour: int) -> bool:
    if "ranges" in window_cfg:
        for rng in window_cfg["ranges"]:
            if _in_range(now_hour, int(rng["start_hour_utc"]), int(rng["end_hour_utc"])):
                return True
        return False
    return _in_range(now_hour, int(window_cfg["start_hour_utc"]), int(window_cfg["end_hour_utc"]))


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail fast if heavy job is outside allowed UTC window.")
    ap.add_argument("--job-class", required=True, choices=["regression", "localization", "scheduled_comparator"])
    ap.add_argument("--config", default=str(Path("config/runner/heavy_windows.yaml")))
    ap.add_argument("--allow-override-env", default="HEAVY_WINDOW_BYPASS")
    args = ap.parse_args()

    if Path(args.config).exists() is False:
        print(f"[window-guard] missing config: {args.config}")
        return 2

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
    bypass = bool(os.environ.get(args.allow_override_env, "").strip())
    if bypass:
        print(f"[window-guard] bypass enabled via {args.allow_override_env}")
        return 0

    policy = cfg.get("policy", {})
    if not policy.get("enforce_windows", True):
        print("[window-guard] window enforcement disabled in config")
        return 0

    windows = cfg.get("windows", {})
    job = windows.get(args.job_class)
    if not job:
        print(f"[window-guard] no window for job class: {args.job_class}")
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    hour = now.hour
    allowed = _is_allowed(job, hour)
    print(f"[window-guard] now_utc={now.isoformat()} hour={hour} job_class={args.job_class} allowed={allowed}")
    if allowed:
        return 0

    print(
        f"[window-guard] BLOCKED: '{args.job_class}' outside allowed UTC window.\n"
        f"Edit config/runner/heavy_windows.yaml or wait for the next window."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
