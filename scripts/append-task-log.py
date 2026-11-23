#!/usr/bin/env python3
"""Append one validated task result or lifecycle transition to the project's task log."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

HEADER = "| Date | Task | Parent | Engine | Outcome | Correction cycles | Note |"
SEPARATOR = "|------|------|--------|--------|---------|------------------|------|"
TASK_ID = re.compile(r"T-\d{4}(?:\.\d+)*\Z")
PARENT_ID = re.compile(
    r"(?:REQ-\d{3}|W-\d{2}|F-\d{3}|WP-\d{3}|US-\d{3}|T-\d{4}(?:\.\d+)*|ADR-\d{3}|BUG-\d{3})\Z"
)
ALLOWED_OUTCOMES = ("DONE", "BLOCKED", "PAUSED", "DEFERRED", "SUPERSEDED")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path, help="Path to state/TASK_LOG.md")
    parser.add_argument("--date", required=True, help="Completion date in YYYY-MM-DD format")
    parser.add_argument("--task", required=True, help="Task ID (T-NNNN or WBS T-NNNN.1)")
    parser.add_argument("--parent", default="", help="Optional parent ID")
    parser.add_argument("--engine", required=True, choices=("antigravity", "vscode", "ai-studio"))
    parser.add_argument("--outcome", required=True, choices=ALLOWED_OUTCOMES)
    parser.add_argument("--cycles", required=True, type=int, help="Failed verification cycles (0-3)")
    parser.add_argument("--note", required=True, help="Concise completion note")
    return parser.parse_args()


def clean_cell(value: str) -> str:
    return " ".join(value.replace("|", r"\|").split())


def append_entry(args: argparse.Namespace) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        raise ValueError("--date must use the YYYY-MM-DD format")
    try:
        date.fromisoformat(args.date)
    except ValueError as exc:
        raise ValueError("--date must be a valid YYYY-MM-DD date") from exc
    if not TASK_ID.fullmatch(args.task):
        raise ValueError("--task must match T-NNNN (or WBS T-NNNN.1)")
    if args.parent and not PARENT_ID.fullmatch(args.parent):
        raise ValueError("--parent must be a supported project ID or empty")
    if not 0 <= args.cycles <= 3:
        raise ValueError("--cycles must be between 0 and 3")
    if not args.note.strip():
        raise ValueError("--note must not be empty")

    if not args.log.is_file():
        raise ValueError(f"task log does not exist: {args.log}")
    content = args.log.read_text(encoding="utf-8")
    lines = content.splitlines()
    nonempty_lines = [line for line in lines if line.strip()]
    if len(nonempty_lines) < 3 or nonempty_lines[1] != HEADER or nonempty_lines[2] != SEPARATOR:
        raise ValueError(f"task log has an unexpected format: {args.log}")
    duplicate_exists = False
    for line in nonempty_lines[3:]:
        if line.startswith("|"):
            fields = line.split("|")
            if len(fields) > 5 and fields[2].strip() == args.task and fields[5].strip() in ("DONE", "BLOCKED", "SUPERSEDED"):
                duplicate_exists = True
                break
    if duplicate_exists:
        raise ValueError(f"task {args.task} already has a log entry")

    row = "| " + " | ".join(
        clean_cell(value)
        for value in (
            args.date,
            args.task,
            args.parent or "-",
            args.engine,
            args.outcome,
            str(args.cycles),
            args.note,
        )
    ) + " |"
    with args.log.open("a", encoding="utf-8", newline="") as log:
        if content and not content.endswith("\n"):
            log.write("\n")
        log.write(row + "\n")


def main() -> int:
    args = parse_args()
    try:
        append_entry(args)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
