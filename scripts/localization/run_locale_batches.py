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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ALL_LOCALES = [
    "ja-JP", "zh-CN", "zh-TW", "zh-HK", "zh-SG", "ko-KR",
    "es-US", "es-ES", "fr-FR", "de-DE", "it-IT", "hu-HU",
]


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    return p.returncode, out


def worker(locale: str, do_translate: bool, do_validate: bool) -> tuple[str, int, str]:
    logs: list[str] = []
    rc = 0
    if do_translate:
        c, o = run_cmd([
            sys.executable,
            "scripts/localization/translate_atoms_all_locales.py",
            "--locale", locale,
        ])
        logs.append(f"[translate:{locale}] rc={c}\n{o}")
        rc = max(rc, c)
    if do_validate:
        c, o = run_cmd([
            sys.executable,
            "scripts/localization/validate_translations.py",
            "--locale", locale,
            "--report",
        ])
        logs.append(f"[validate:{locale}] rc={c}\n{o}")
        rc = max(rc, c)
    return locale, rc, "\n".join(logs)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run locale translation/validation with max-agent parallelism")
    ap.add_argument("--max-agents", type=int, default=3, help="Max parallel locale workers")
    ap.add_argument("--locales", nargs="*", default=ALL_LOCALES, help="Locales to process")
    ap.add_argument("--translate-only", action="store_true")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--log-dir", default="artifacts/localization/batch_runs")
    args = ap.parse_args()

    do_translate = not args.validate_only
    do_validate = not args.translate_only

    log_dir = REPO_ROOT / args.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    with ThreadPoolExecutor(max_workers=max(1, args.max_agents)) as ex:
        futs = [ex.submit(worker, loc, do_translate, do_validate) for loc in args.locales]
        for fut in as_completed(futs):
            locale, rc, out = fut.result()
            (log_dir / f"{locale}.log").write_text(out, encoding="utf-8")
            print(f"[{locale}] rc={rc}")
            if rc != 0:
                failures += 1

    print(f"done: locales={len(args.locales)} failures={failures} max_agents={args.max_agents}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
