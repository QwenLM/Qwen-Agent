#!/usr/bin/env python3
"""
Run locale translation + validation in parallel batches.

This is the "max agents" entrypoint for localization content generation.
You can set --max-agents to control parallel locale workers.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ALL_LOCALES = [
    "ja-JP", "zh-CN", "zh-TW", "zh-HK", "zh-SG", "ko-KR",
    "es-US", "es-ES", "fr-FR", "de-DE", "it-IT", "hu-HU",
]
CORE_LOCALES = ["ja-JP", "zh-CN", "zh-TW", "zh-HK", "zh-SG", "ko-KR"]


def run_cmd(cmd: list[str], timeout_sec: int) -> tuple[int, str]:
    start = time.time()
    try:
        p = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start
        out = (e.stdout or "") + ("\n" + e.stderr if e.stderr else "")
        out = (
            f"[TIMEOUT] cmd exceeded {timeout_sec}s (elapsed={elapsed:.1f}s)\n"
            f"{' '.join(cmd)}\n{out}"
        )
        return 124, out
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    return p.returncode, out


def worker(
    locale: str,
    do_translate: bool,
    do_validate: bool,
    timeout_sec: int,
) -> tuple[str, int, str]:
    logs: list[str] = []
    rc = 0
    if do_translate:
        c, o = run_cmd(
            [
                sys.executable,
                "scripts/localization/translate_atoms_all_locales.py",
                "--locale",
                locale,
            ],
            timeout_sec=timeout_sec,
        )
        logs.append(f"[translate:{locale}] rc={c}\n{o}")
        rc = max(rc, c)
    if do_validate:
        c, o = run_cmd(
            [
                sys.executable,
                "scripts/localization/validate_translations.py",
                "--locale",
                locale,
                "--report",
            ],
            timeout_sec=timeout_sec,
        )
        logs.append(f"[validate:{locale}] rc={c}\n{o}")
        rc = max(rc, c)
    return locale, rc, "\n".join(logs)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run locale translation/validation with max-agent parallelism")
    ap.add_argument("--max-agents", type=int, default=2, help="Max parallel locale workers (safe default: 2)")
    ap.add_argument("--locales", nargs="*", default=ALL_LOCALES, help="Locales to process")
    ap.add_argument("--core-locales", action="store_true", help="Run only core production locales (6)")
    ap.add_argument("--translate-only", action="store_true")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--log-dir", default="artifacts/localization/batch_runs")
    ap.add_argument("--timeout-sec", type=int, default=420, help="Per-locale subprocess timeout (seconds)")
    ap.add_argument("--heartbeat-sec", type=int, default=30, help="Progress heartbeat interval (seconds)")
    args = ap.parse_args()

    do_translate = not args.validate_only
    do_validate = not args.translate_only
    locales = CORE_LOCALES if args.core_locales else args.locales

    log_dir = REPO_ROOT / args.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    print(
        "starting locale batches: "
        f"locales={len(locales)} max_agents={max(1, args.max_agents)} "
        f"timeout_sec={args.timeout_sec} heartbeat_sec={args.heartbeat_sec} "
        f"translate={do_translate} validate={do_validate}"
    )

    failures = 0
    started = time.time()
    pending = {}
    with ThreadPoolExecutor(max_workers=max(1, args.max_agents)) as ex:
        for loc in locales:
            fut = ex.submit(worker, loc, do_translate, do_validate, args.timeout_sec)
            pending[fut] = (loc, time.time())

        while pending:
            done, _ = wait(
                set(pending.keys()),
                timeout=max(1, args.heartbeat_sec),
                return_when=FIRST_COMPLETED,
            )
            if not done:
                now = time.time()
                in_progress = ", ".join(
                    f"{loc}:{int(now - st)}s" for _, (loc, st) in list(pending.items())[:8]
                )
                print(
                    f"[heartbeat] running={len(pending)} elapsed={int(now - started)}s "
                    f"in_progress={in_progress}"
                )
                continue

            for fut in done:
                locale, _st = pending.pop(fut)
                locale_result, rc, out = fut.result()
                (log_dir / f"{locale_result}.log").write_text(out, encoding="utf-8")
                print(f"[{locale_result}] rc={rc}")
                if rc != 0:
                    failures += 1

    print(f"done: locales={len(locales)} failures={failures} max_agents={max(1, args.max_agents)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
