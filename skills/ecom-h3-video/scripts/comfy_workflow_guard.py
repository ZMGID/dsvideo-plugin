#!/usr/bin/env python3
"""Reject undeclared changes between two ComfyUI workflow JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class WorkflowMutationError(ValueError):
    pass


def _pointer_part(value: Any) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _child_path(path: str, key: Any) -> str:
    return f"{path}/{_pointer_part(key)}"


def changed_paths(before: Any, after: Any, path: str = "") -> list[str]:
    if type(before) is not type(after):
        return [path or "/"]

    if isinstance(before, dict):
        changes: list[str] = []
        for key in sorted(before.keys() | after.keys(), key=str):
            child = _child_path(path, key)
            if key not in before or key not in after:
                changes.append(child)
            else:
                changes.extend(changed_paths(before[key], after[key], child))
        return changes

    if isinstance(before, list):
        changes = []
        shared = min(len(before), len(after))
        for index in range(shared):
            changes.extend(changed_paths(before[index], after[index], _child_path(path, index)))
        for index in range(shared, max(len(before), len(after))):
            changes.append(_child_path(path, index))
        return changes

    return [] if before == after else [path or "/"]


def assert_only_allowed_changes(
    original: Any,
    candidate: Any,
    allowed_paths: set[str],
) -> list[str]:
    invalid_allowed = sorted(path for path in allowed_paths if not path.startswith("/"))
    if invalid_allowed:
        raise ValueError(
            "Allowed paths must be JSON Pointers beginning with '/': "
            + ", ".join(invalid_allowed)
        )

    changes = sorted(set(changed_paths(original, candidate)))
    unexpected = [path for path in changes if path not in allowed_paths]
    if unexpected:
        raise WorkflowMutationError(
            "Candidate workflow changes undeclared paths: " + ", ".join(unexpected)
        )
    return changes


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read workflow JSON {path}: {error}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify that a derived ComfyUI workflow changes only declared JSON paths."
    )
    parser.add_argument("original", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="JSON_POINTER",
        help="exact changed JSON path to permit; repeat once per allowed field",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        changes = assert_only_allowed_changes(
            _load_json(args.original),
            _load_json(args.candidate),
            set(args.allow),
        )
        print(json.dumps({"status": "ok", "changed_paths": changes}, ensure_ascii=False, indent=2))
        return 0
    except ValueError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
