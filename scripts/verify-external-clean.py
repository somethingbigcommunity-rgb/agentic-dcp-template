#!/usr/bin/env python3
"""Verify that external-facing artifacts contain zero references to the ASE framework.

Allowed in external artifacts:
  Standard project and backlog identifiers such as W-01, T-001, T-0001, REQ-001,
  F-001, US-001, WP-001, ADR-001.

Blocked in external artifacts:
  ASE framework names, internal DCP/HAG/M0-A methodology jargon, /ase-* commands,
  project-memory/ paths, .ase-install.json, and ase-lead agent references.
  With --check-first-person (or automatically on files in 05-release-and-handover/
  and state/reviews/), collaborative first-person plural pronouns ("we", "our",
  "us", "noi", "abbiamo") are also blocked so drafted messages use "I" / "Io".

Usage:
  python3 scripts/verify-external-clean.py <path> [<path> ...]
  python3 scripts/verify-external-clean.py --check-first-person <path> [<path> ...]
"""
from __future__ import annotations

import argparse
import re
import sys
import zlib
from pathlib import Path

FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Agentic Software Engineering", re.compile(r"Agentic\s+Software\s+Engineering", re.IGNORECASE)),
    ("ASE", re.compile(r"\bASE\b")),
    ("agentic-dcp-template", re.compile(r"\bagentic-dcp-template\b", re.IGNORECASE)),
    ("dcp-template", re.compile(r"\bdcp-template\b", re.IGNORECASE)),
    ("Development Context Package", re.compile(r"Development\s+Context\s+Package", re.IGNORECASE)),
    ("DCP", re.compile(r"\bDCP\b")),
    ("Project Memory", re.compile(r"Project\s+Memory", re.IGNORECASE)),
    ("project-memory/", re.compile(r"project-memory/")),
    ("HAG-01..07", re.compile(r"\bHAG-0[1-7]\b")),
    ("Human Approval Gate", re.compile(r"Human\s+Approval\s+Gate", re.IGNORECASE)),
    ("Iteration Protocol", re.compile(r"Iteration\s+Protocol", re.IGNORECASE)),
    ("/ase-* command", re.compile(r"(?<![A-Za-z0-9_])/ase-(?:setup|adopt|plan|task|review|roles|plugin)\b")),
    ("M0-A", re.compile(r"\bM0-A\b")),
    (".ase-install.json", re.compile(r"\.ase-install\.json\b")),
    ("ase-lead", re.compile(r"\base-lead\b", re.IGNORECASE)),
]

FIRST_PERSON_PLURAL_PATTERN = re.compile(
    r"\b(?:we|we've|we're|we'll|our|ours|us|noi|abbiamo|nostro|nostra|nostri|nostre)\b",
    re.IGNORECASE,
)

AUTO_FIRST_PERSON_DIR_MARKERS = ("05-release-and-handover", "reviews")

SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "graphify-out",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2",
    ".ttf", ".otf", ".eot", ".zip", ".tar", ".gz", ".bz2", ".xz", ".pyc",
    ".so", ".dylib", ".dll", ".exe", ".sqlite", ".db",
}


def scan_text(text: str, source: str, check_first_person: bool = False) -> list[str]:
    """Return a list of violation strings ('source:line: forbidden ...') for text."""
    findings: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for label, pattern in FORBIDDEN_PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append(
                    f"{source}:{line_no}: forbidden ASE reference '{match.group(0)}' (rule: {label})"
                )
        if check_first_person:
            for fp_match in FIRST_PERSON_PLURAL_PATTERN.finditer(line):
                findings.append(
                    f"{source}:{line_no}: forbidden first-person plural '{fp_match.group(0)}' "
                    f"(use first-person singular 'I'/'Io', never 'we'/'noi')"
                )
    return findings


def extract_pdf_text_segments(raw: bytes) -> list[str]:
    """Extract readable text segments and PDF literal strings from raw PDF bytes."""
    segments: list[str] = []
    # 1. Inspect uncompressed stream content
    decoded_raw = raw.decode("cp1252", errors="ignore")
    segments.append(decoded_raw)

    # 2. Decompress any FlateDecode streams if present
    for stream_match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.DOTALL):
        payload = stream_match.group(1)
        for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
            try:
                inflated = zlib.decompress(payload, wbits)
                segments.append(inflated.decode("cp1252", errors="ignore"))
                break
            except zlib.error:
                continue

    # 3. Reconstruct text inside PDF parentheses (...) on each line
    extracted_lines: list[str] = []
    for seg in segments:
        for line in seg.splitlines():
            literals = re.findall(r"\((?:\\.|[^\\()])*\)", line)
            if literals:
                cleaned = " ".join(
                    lit[1:-1].replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
                    for lit in literals
                )
                extracted_lines.append(cleaned)
            elif "/Title" in line or "/Author" in line or "/Subject" in line or "/Producer" in line:
                extracted_lines.append(line)
    return extracted_lines


def scan_file(path: Path, check_first_person: bool = False) -> list[str]:
    if not path.is_file():
        return [f"{path}: file does not exist"]
    suffix = path.suffix.lower()
    if suffix in BINARY_EXTENSIONS:
        return []
    auto_fp = check_first_person or any(marker in path.parts for marker in AUTO_FIRST_PERSON_DIR_MARKERS)
    if suffix == ".pdf":
        raw = path.read_bytes()
        lines = extract_pdf_text_segments(raw)
        return scan_text("\n".join(lines), str(path), check_first_person=auto_fp)
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_bytes().decode("cp1252", errors="ignore")
    return scan_text(content, str(path), check_first_person=auto_fp)


def iter_target_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    files: list[Path] = []
    for item in sorted(target.rglob("*")):
        if any(part in SKIP_DIRS for part in item.parts):
            continue
        if item.is_file() and item.name != ".gitkeep":
            files.append(item)
    return files


def scan_paths(paths: list[Path], check_first_person: bool = False) -> list[str]:
    findings: list[str] = []
    for target in paths:
        if not target.exists():
            findings.append(f"{target}: path does not exist")
            continue
        for file_path in iter_target_files(target):
            findings.extend(scan_file(file_path, check_first_person=check_first_person))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--check-first-person",
        action="store_true",
        help="Block first-person plural pronouns ('we', 'our', 'us', 'noi', 'abbiamo') in scanned files",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="Files or directories to verify")
    args = parser.parse_args(argv)

    findings = scan_paths(args.paths, check_first_person=args.check_first_person)
    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        print(f"FAIL: {len(findings)} forbidden ASE reference(s) found.", file=sys.stderr)
        return 1
    print(f"PASS: verified {len(args.paths)} target path(s) — zero ASE references found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
