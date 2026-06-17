"""Validate travel planning query metadata against summarized constraints."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RANGE_RE = re.compile(
    r"between\s+(\d{1,2})(?::00)?\s*(AM|PM)?\s+and\s+(\d{1,2})(?::00)?\s*(AM|PM)?",
    re.IGNORECASE,
)


def _load_json(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path.name}: expected a list of query records")
    return data


def _hour(value: str, suffix: str | None) -> int:
    hour = int(value)
    if suffix:
        suffix = suffix.upper()
        if suffix == "PM" and hour != 12:
            hour += 12
        elif suffix == "AM" and hour == 12:
            hour = 0
    return hour


def _extract_en_hour_range(text: str) -> tuple[int, int] | None:
    match = RANGE_RE.search(text)
    if not match:
        return None
    return (
        _hour(match.group(1), match.group(2)),
        _hour(match.group(3), match.group(4)),
    )


def _record_label(path: Path, record: dict[str, Any]) -> str:
    return f"{path.name}: id={record.get('id', '<missing>')}"


def _validate_ids(path: Path, records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for record in records:
        record_id = str(record.get("id", ""))
        if not record_id:
            errors.append(f"{path.name}: record without id")
        elif record_id in seen:
            errors.append(f"{path.name}: duplicate id {record_id}")
        seen.add(record_id)
    return errors


def _validate_train_time_ranges(path: Path, records: list[dict[str, Any]], lang: str) -> list[str]:
    errors: list[str] = []
    for record in records:
        constraints = record.get("meta_info", {}).get("hard_constraints", {})
        train_range = constraints.get("train_departure_time_range")
        if not train_range:
            continue

        summary = record.get("query_with_constraints", "")
        if lang == "zh":
            expected = train_range.get("time_range")
            if expected and expected not in summary:
                errors.append(
                    f"{_record_label(path, record)}: train time range summary does not include {expected!r}"
                )
        else:
            expected = _extract_en_hour_range(train_range.get("constraint_context", ""))
            actual = _extract_en_hour_range(summary)
            if expected and actual != expected:
                errors.append(
                    f"{_record_label(path, record)}: train time range summary is {actual}, expected {expected}"
                )
    return errors


def validate(data_dir: Path = DATA_DIR) -> list[str]:
    zh_path = data_dir / "travelplanning_query_zh.json"
    en_path = data_dir / "travelplanning_query_en.json"
    zh_records = _load_json(zh_path)
    en_records = _load_json(en_path)

    errors: list[str] = []
    errors.extend(_validate_ids(zh_path, zh_records))
    errors.extend(_validate_ids(en_path, en_records))

    zh_ids = {str(record.get("id", "")) for record in zh_records}
    en_ids = {str(record.get("id", "")) for record in en_records}
    if zh_ids != en_ids:
        errors.append(
            "query id sets differ between zh and en files: "
            f"zh_only={sorted(zh_ids - en_ids)}, en_only={sorted(en_ids - zh_ids)}"
        )

    errors.extend(_validate_train_time_ranges(zh_path, zh_records, "zh"))
    errors.extend(_validate_train_time_ranges(en_path, en_records, "en"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory containing travelplanning_query_zh.json and travelplanning_query_en.json.",
    )
    args = parser.parse_args()

    errors = validate(args.data_dir)
    if errors:
        for error in errors:
            print(error)
        return 1

    print("travel planning query data ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
