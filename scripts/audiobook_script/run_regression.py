#!/usr/bin/env python3
"""
Audiobook Golden Regression Suite — run_regression.py

Runs the full comparator loop against the golden regression set
(config/audiobook_script/golden_regression_set/) and fails if any
required locale drops below its expected quality floor.

Requirements:
  - LM Studio running at http://127.0.0.1:1234 with Qwen model loaded
  - prompts/audiobook/draft_{content_type}_v2.txt present
  - prompts/audiobook/judge_audiobook_v2.txt present
  - All golden sample files present (see golden_set/index.json)

Usage:
  # Run all required locales
  python scripts/audiobook_script/run_regression.py

  # Run specific locale
  python scripts/audiobook_script/run_regression.py --locale zh-TW

  # Dry run (validate setup, no API calls)
  python scripts/audiobook_script/run_regression.py --dry-run

  # Verbose output
  python scripts/audiobook_script/run_regression.py --verbose

Exit codes:
  0 = All regressions pass
  1 = One or more regressions failed
  2 = Setup/config error (missing files, LM Studio unreachable)

Config: config/audiobook_script/comparator_config.yaml
Golden set: config/audiobook_script/golden_regression_set/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("regression")


@dataclass
class RegressionResult:
    section_id: str
    locale: str
    content_type: str
    golden_file: str
    expect_pass: bool
    min_aggregate_score: float
    actual_decision: str
    actual_aggregate_score: float
    loops_attempted: int
    hard_gate_failures: int
    regression_pass: bool
    failure_reason: str | None


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        raise RuntimeError("pyyaml required: pip install pyyaml --break-system-packages")
    except Exception as e:
        raise RuntimeError(f"Failed to load {path}: {e}")


def _check_lm_studio(base_url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Check if LM Studio is reachable."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{base_url}/models")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            models = data.get("data", [])
            if models:
                return True, f"LM Studio reachable — {len(models)} model(s) loaded: {[m.get('id','?') for m in models[:3]]}"
            return True, "LM Studio reachable — no models currently loaded"
    except Exception as e:
        return False, f"LM Studio not reachable at {base_url}: {e}"


def _load_golden_index(golden_dir: Path) -> list[dict]:
    idx_path = golden_dir / "index.json"
    if not idx_path.exists():
        raise RuntimeError(f"Golden index missing: {idx_path}")
    return json.loads(idx_path.read_text(encoding="utf-8")).get("samples", [])


def _validate_setup(repo: Path, cfg: dict, golden_dir: Path, verbose: bool = False) -> list[str]:
    """Check all prerequisites. Returns list of errors (empty = OK)."""
    errors = []

    # Check LM Studio
    base_url = cfg.get("draft_model", {}).get("base_url", "http://127.0.0.1:1234/v1")
    reachable, msg = _check_lm_studio(base_url)
    if reachable:
        if verbose: print(f"  ✓ {msg}")
    else:
        errors.append(msg)

    # Check prompts
    routing = cfg.get("draft_model", {}).get("prompt_routing", {})
    judge_id = cfg.get("judge_model", {}).get("system_prompt_id", "judge_audiobook_v2")
    for prompt_id in list(routing.values()) + [judge_id]:
        for subdir in ["prompts/audiobook", "prompts"]:
            p = repo / subdir / f"{prompt_id}.txt"
            if p.exists():
                if verbose: print(f"  ✓ prompt: {p.relative_to(repo)}")
                break
        else:
            errors.append(f"Prompt not found: {prompt_id}.txt (searched prompts/audiobook/ and prompts/)")

    # Check golden files
    samples = _load_golden_index(golden_dir)
    for sample in samples:
        gp = golden_dir / sample["file"]
        if not gp.exists():
            errors.append(f"Golden sample missing: {gp.relative_to(repo)}")
        elif verbose:
            print(f"  ✓ golden: {sample['file']}")

    return errors


async def _run_one_golden(
    repo: Path,
    golden_dir: Path,
    sample: dict,
    cfg: dict,
    checklist: dict,
    result_schema: dict,
    verbose: bool,
) -> RegressionResult:
    """Run one golden sample through the comparator loop."""
    from scripts.audiobook_script.run_comparator_loop import run_section_loop, _load_prompt, _resolve_draft_prompt_id

    golden_cfg = _load_yaml(golden_dir / sample["file"])
    section_id  = golden_cfg["section_id"]
    locale      = golden_cfg["locale"]
    content_type = golden_cfg.get("content_type", "pearl_prime")
    source_text  = golden_cfg["source_text"]
    expect_pass  = golden_cfg.get("expect_pass", True)
    min_score    = float(golden_cfg.get("min_aggregate_score", 0.75))

    draft_prompt_id = _resolve_draft_prompt_id(cfg, content_type)
    judge_prompt_id = cfg.get("judge_model", {}).get("system_prompt_id", "judge_audiobook_v2")
    draft_prompt = _load_prompt(repo, draft_prompt_id)
    judge_prompt = _load_prompt(repo, judge_prompt_id)

    if verbose:
        print(f"  → Running: {section_id} [{locale}/{content_type}]")

    t0 = time.time()
    result = await run_section_loop(
        section_id=section_id,
        locale=locale,
        english_source=source_text,
        book_id="regression",
        batch_id=f"regression_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
        cfg=cfg,
        checklist=checklist,
        result_schema=result_schema,
        repo=repo,
        draft_system_prompt=draft_prompt,
        judge_system_prompt=judge_prompt,
    )
    elapsed = time.time() - t0

    # Assess regression pass
    regression_pass = True
    failure_reason = None

    if expect_pass and result.decision != "pass":
        regression_pass = False
        failure_reason = f"Expected pass but got {result.decision} (hard_gate_failures={result.hard_gate_failures})"
    elif result.best_aggregate_score < min_score:
        regression_pass = False
        failure_reason = f"Score {result.best_aggregate_score:.3f} < required {min_score}"

    status = "✓ PASS" if regression_pass else "✗ FAIL"
    if verbose:
        print(f"    {status} — decision={result.decision} score={result.best_aggregate_score:.3f} "
              f"loops={result.loops_attempted} [{elapsed:.1f}s]")
        if failure_reason:
            print(f"    Reason: {failure_reason}")

    return RegressionResult(
        section_id=section_id,
        locale=locale,
        content_type=content_type,
        golden_file=sample["file"],
        expect_pass=expect_pass,
        min_aggregate_score=min_score,
        actual_decision=result.decision,
        actual_aggregate_score=result.best_aggregate_score,
        loops_attempted=result.loops_attempted,
        hard_gate_failures=result.hard_gate_failures,
        regression_pass=regression_pass,
        failure_reason=failure_reason,
    )


async def _run_regression(
    repo: Path,
    locale_filter: str | None,
    verbose: bool,
    dry_run: bool,
) -> int:
    from scripts.audiobook_script.run_comparator_loop import _load_config, _load_checklist, _load_result_schema

    cfg = _load_config(repo)
    checklist = _load_checklist(repo)
    result_schema = _load_result_schema(repo)
    golden_dir = repo / cfg.get("regression", {}).get("golden_set_path", "config/audiobook_script/golden_regression_set/")

    print(f"\n{'='*60}")
    print("AUDIOBOOK GOLDEN REGRESSION SUITE")
    print(f"LM Studio: {cfg.get('draft_model', {}).get('base_url', 'http://127.0.0.1:1234/v1')}")
    print(f"{'='*60}\n")

    # Setup validation
    print("Checking setup...")
    errors = _validate_setup(repo, cfg, golden_dir, verbose=verbose)
    if errors:
        print("\n❌ SETUP ERRORS — cannot proceed:")
        for e in errors:
            print(f"  ✗ {e}")
        return 2

    print("  ✓ Setup OK\n")

    if dry_run:
        print("Dry run complete — all checks passed. No API calls made.")
        return 0

    # Load samples
    all_samples = _load_golden_index(golden_dir)
    samples = [s for s in all_samples
               if not locale_filter or s.get("locale") == locale_filter]

    if not samples:
        print(f"No golden samples found{' for locale ' + locale_filter if locale_filter else ''}.")
        return 2

    required_locales = set(cfg.get("regression", {}).get("required_locales", ["zh-TW", "zh-HK", "zh-SG", "zh-CN"]))
    tested_locales = {s["locale"] for s in samples}

    print(f"Running {len(samples)} golden sample(s)...\n")
    t_start = time.time()

    results: list[RegressionResult] = []
    for sample in samples:
        try:
            r = await _run_one_golden(repo, golden_dir, sample, cfg, checklist, result_schema, verbose)
            results.append(r)
        except Exception as e:
            logger.error("Golden sample %s failed with exception: %s", sample["file"], e)
            results.append(RegressionResult(
                section_id=sample.get("section_id", "?"),
                locale=sample.get("locale", "?"),
                content_type=sample.get("content_type", "?"),
                golden_file=sample["file"],
                expect_pass=True,
                min_aggregate_score=0.75,
                actual_decision="error",
                actual_aggregate_score=0.0,
                loops_attempted=0,
                hard_gate_failures=9,
                regression_pass=False,
                failure_reason=f"Exception: {e}",
            ))

    total_elapsed = time.time() - t_start

    # Summary
    passed = [r for r in results if r.regression_pass]
    failed = [r for r in results if not r.regression_pass]

    print(f"\n{'='*60}")
    print(f"REGRESSION RESULTS  [{total_elapsed:.1f}s]")
    print(f"{'='*60}")
    print(f"  Passed: {len(passed)}/{len(results)}")
    if failed:
        print(f"\n  FAILURES:")
        for r in failed:
            print(f"    ✗ {r.section_id} [{r.locale}/{r.content_type}]")
            print(f"      {r.failure_reason}")

    # Check required locale coverage
    if not locale_filter:
        missing_required = required_locales - tested_locales
        if missing_required:
            print(f"\n  ⚠ Missing required locales: {sorted(missing_required)}")
            print("  Add golden samples for these locales before go-live.")

    # Write regression report
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "pass_rate": round(len(passed) / len(results), 4) if results else 0.0,
        "elapsed_seconds": round(total_elapsed, 1),
        "results": [
            {
                "section_id": r.section_id,
                "locale": r.locale,
                "content_type": r.content_type,
                "golden_file": r.golden_file,
                "regression_pass": r.regression_pass,
                "actual_decision": r.actual_decision,
                "actual_aggregate_score": r.actual_aggregate_score,
                "loops_attempted": r.loops_attempted,
                "hard_gate_failures": r.hard_gate_failures,
                "failure_reason": r.failure_reason,
            }
            for r in results
        ],
    }
    report_path = repo / "artifacts/audiobook/regression_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Report written: {report_path.relative_to(repo)}")

    if failed:
        print(f"\n❌ REGRESSION FAILED — {len(failed)} sample(s) did not meet quality floor\n")
        return 1

    print(f"\n✅ ALL REGRESSIONS PASS\n")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Audiobook Golden Regression Suite")
    ap.add_argument("--locale", help="Run only this locale (e.g. zh-TW)")
    ap.add_argument("--repo", help="Repo root path (default: auto-detected)")
    ap.add_argument("--dry-run", action="store_true", help="Validate setup only; no API calls")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = ap.parse_args()

    repo = Path(args.repo) if args.repo else REPO_ROOT
    return asyncio.run(_run_regression(
        repo=repo,
        locale_filter=args.locale,
        verbose=args.verbose,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    sys.exit(main())
