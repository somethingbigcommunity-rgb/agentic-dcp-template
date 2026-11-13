#!/usr/bin/env python3
"""Rebuild the Project Memory traceability matrix from canonical artifacts."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:REQ-\d{3}|W-\d{2}|F-\d{3}|WP-\d{3}|US-\d{3}|T-\d{4})(?!\d)"
)
TEST_ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"(?P<three>REQ|WP|US|F)[-_](?P<number_three>\d{3})|"
    r"(?P<wave>W)[-_](?P<number_wave>\d{2})|"
    r"(?P<task>T)[-_](?P<number_task>\d{4})"
    r")(?!\d)"
)
REQUIREMENT_HEADING = re.compile(r"^#{1,6}\s+(REQ-\d{3})\s+[—-]\s+(.+?)\s*$")
TASK_COMMIT = re.compile(r"^(T-\d{4}):(?:\s|$)")


@dataclass(frozen=True)
class Artifact:
    identifier: str
    title: str
    parent: str
    requirements: tuple[str, ...]
    status: str
    path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")
    parser.add_argument(
        "--mode",
        choices=("lite", "standard", "enterprise"),
        default="lite",
        help="Project mode; non-Lite modes block when a requirement has no named test",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("project-memory/state/TRACEABILITY.md"),
        help="Output path relative to --root unless absolute",
    )
    parser.add_argument("--tests-dir", type=Path, default=Path("tests"))
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Do not read commit subjects (useful for isolated validation)",
    )
    return parser.parse_args()


def parse_front_matter(path: Path) -> dict[str, str | tuple[str, ...]]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", text, re.DOTALL)
    if not match:
        return {}

    fields: dict[str, str | tuple[str, ...]] = {}
    lines = match.group(1).splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        field = re.match(r"^([a-zA-Z_][\w-]*):(?:\s*(.*))?$", line)
        if not field:
            index += 1
            continue
        key, value = field.groups()
        value = (value or "").strip()
        if value:
            if value.startswith("[") and value.endswith("]"):
                fields[key] = tuple(
                    item.strip().strip("'\"")
                    for item in value[1:-1].split(",")
                    if item.strip()
                )
            else:
                fields[key] = value.strip("'\"")
            index += 1
            continue

        items: list[str] = []
        index += 1
        while index < len(lines) and re.match(r"^\s+-\s+", lines[index]):
            items.append(re.sub(r"^\s+-\s+", "", lines[index]).strip().strip("'\""))
            index += 1
        fields[key] = tuple(items) if items else ""
    return fields


def artifact(path: Path) -> Artifact:
    fields = parse_front_matter(path)
    identifier = str(fields.get("id", ""))
    title = identifier
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if heading:
            title = heading.group(1)
            if identifier:
                title = re.sub(
                    rf"^{re.escape(identifier)}\s+[—-]\s*",
                    "",
                    title,
                )
            break
    raw_requirements = fields.get("requirements", ())
    requirements = (
        tuple(raw_requirements)
        if isinstance(raw_requirements, tuple)
        else tuple(ID_PATTERN.findall(raw_requirements))
    )
    return Artifact(
        identifier=identifier,
        title=title,
        parent=str(fields.get("parent", "")),
        requirements=requirements,
        status=str(fields.get("status", "")),
        path=path,
    )


def read_artifacts(directory: Path) -> dict[str, Artifact]:
    if not directory.is_dir():
        return {}
    result: dict[str, Artifact] = {}
    for path in sorted(directory.rglob("*.md")):
        item = artifact(path)
        if item.identifier:
            if item.identifier in result:
                raise ValueError(f"duplicate ID {item.identifier}: {result[item.identifier].path} and {path}")
            result[item.identifier] = item
    return result


def read_requirements(root: Path) -> dict[str, str]:
    directory = root / "project-memory/dcp/01-requirements"
    result: dict[str, str] = {}
    if not directory.is_dir():
        return result
    for path in sorted(directory.rglob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = REQUIREMENT_HEADING.match(line)
            if match:
                identifier, title = match.groups()
                if identifier in result:
                    raise ValueError(f"duplicate requirement {identifier}: {path}")
                result[identifier] = title
    return result


def markdown_cell(values: set[str] | list[str] | tuple[str, ...]) -> str:
    return ", ".join(sorted(value.replace("|", r"\|") for value in values)) or "—"


def build_matrix(
    root: Path,
    mode: str,
    no_git: bool = False,
    tests_dir: Path = Path("tests"),
) -> tuple[str, list[str], list[str]]:
    memory = root / "project-memory"
    requirements = read_requirements(root)
    stories = read_artifacts(memory / "dcp/01-requirements/user-stories")
    features = read_artifacts(memory / "dcp/04-implementation/features")
    waves = read_artifacts(memory / "dcp/04-implementation/waves")
    tasks = read_artifacts(memory / "dcp/04-implementation/tasks")

    errors: list[str] = []
    warnings: list[str] = []
    for item in stories.values():
        if not item.parent:
            errors.append(f"{item.identifier} is missing its Feature parent")
        elif item.parent not in features:
            errors.append(f"{item.identifier} has unresolved Feature parent {item.parent}")
        for requirement in item.requirements:
            if requirement not in requirements:
                errors.append(f"{item.identifier} references unknown requirement {requirement}")
    for item in features.values():
        if not item.parent:
            errors.append(f"{item.identifier} is missing its Wave parent")
        elif item.parent not in waves:
            errors.append(f"{item.identifier} has unresolved Wave parent {item.parent}")
        for requirement in item.requirements:
            if requirement not in requirements:
                errors.append(f"{item.identifier} references unknown requirement {requirement}")
    for item in tasks.values():
        if item.parent and item.parent not in stories and item.parent not in features:
            errors.append(f"{item.identifier} has unresolved parent {item.parent}")

    tests_dir = tests_dir if tests_dir.is_absolute() else root / tests_dir
    test_files = sorted(tests_dir.rglob("*")) if tests_dir.is_dir() else []
    test_files = [path for path in test_files if path.is_file() and path.suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".cs"}]
    tests_by_id: dict[str, list[str]] = {}
    for path in test_files:
        for match in TEST_ID_PATTERN.finditer(path.name):
            prefix, number = (
                (match.group("three"), match.group("number_three"))
                if match.group("three")
                else (match.group("wave"), match.group("number_wave"))
                if match.group("wave")
                else (match.group("task"), match.group("number_task"))
            )
            identifier = f"{prefix}-{number}"
            tests_by_id.setdefault(identifier, []).append(path.relative_to(root).as_posix())

    commit_subjects: dict[str, list[str]] = {}
    all_commit_subjects: dict[str, list[str]] = {}
    if not no_git:
        history_commands = (
            (all_commit_subjects, ["git", "log", "--reverse", "--format=%s", "HEAD"]),
            (
                commit_subjects,
                [
                    "git",
                    "log",
                    "--format=%s",
                    "HEAD",
                    "--",
                    ".",
                    ":(exclude)project-memory/state/**",
                    ":(exclude)project-memory/dcp/04-implementation/tasks/**",
                ],
            ),
        )
        for subjects_by_task, command in history_commands:
            completed = subprocess.run(
                command, cwd=root, check=False, capture_output=True, text=True
            )
            if completed.returncode:
                raise RuntimeError(f"could not read git history: {completed.stderr.strip()}")
            for subject in completed.stdout.splitlines():
                match = TASK_COMMIT.match(subject)
                if match:
                    subjects_by_task.setdefault(match.group(1), []).append(subject)
        for identifier, subjects in all_commit_subjects.items():
            if identifier not in commit_subjects:
                commit_subjects[identifier] = [subjects[0]]

    stories_by_requirement: dict[str, set[str]] = {}
    features_by_requirement: dict[str, set[str]] = {}
    for story in stories.values():
        story_requirements = set(story.requirements)
        feature = features.get(story.parent)
        if feature:
            story_requirements.update(feature.requirements)
        for requirement in story_requirements:
            stories_by_requirement.setdefault(requirement, set()).add(story.identifier)
            if feature:
                features_by_requirement.setdefault(requirement, set()).add(feature.identifier)
    for feature in features.values():
        for requirement in feature.requirements:
            features_by_requirement.setdefault(requirement, set()).add(feature.identifier)

    tasks_by_parent: dict[str, set[str]] = {}
    for task in tasks.values():
        if task.parent:
            tasks_by_parent.setdefault(task.parent, set()).add(task.identifier)
        if task.status in {"DONE", "IN_REVIEW"} and not no_git and not commit_subjects.get(task.identifier):
            warnings.append(f"{task.identifier} has no matching T-NNNN commit subject")

    headers = [
        "# Traceability",
        "",
        "Generated by `scripts/build-traceability.py`; do not edit by hand.",
        "",
        f"Project mode: **{mode.title()}**.",
        "",
        "| Requirement | User Stories | Features | Waves | Work Package / PR title | Tasks | Tests | Task commits |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for requirement, title in sorted(requirements.items()):
        related_stories = stories_by_requirement.get(requirement, set())
        related_features = features_by_requirement.get(requirement, set())
        related_waves = {
            features[feature].parent
            for feature in related_features
            if feature in features and features[feature].parent
        }
        work_packages = {
            f"{feature}: {features[feature].title}"
            for feature in related_features
            if feature in features
        }
        related_tasks = {
            task
            for parent in related_stories | related_features
            for task in tasks_by_parent.get(parent, set())
        }
        related_test_ids = {requirement} | related_stories
        related_tests = {
            file
            for identifier in related_test_ids
            for file in tests_by_id.get(identifier, [])
        }
        commits = {
            subject
            for task in related_tasks
            for subject in commit_subjects.get(task, [])
        }
        headers.append(
            "| "
            + " | ".join(
                (
                    f"{requirement} — {title}",
                    markdown_cell(related_stories),
                    markdown_cell(related_features),
                    markdown_cell(related_waves),
                    markdown_cell(work_packages),
                    markdown_cell(related_tasks),
                    markdown_cell(related_tests),
                    markdown_cell(commits),
                )
            )
            + " |"
        )
        if not related_stories:
            warnings.append(f"{requirement} has no linked User Story")
        if not related_tests:
            message = f"{requirement} has no test file named with {requirement} or its User Story ID"
            if mode == "lite":
                warnings.append(message)
            else:
                errors.append(message)

    linked_story_ids = {
        story_id for story_ids in stories_by_requirement.values() for story_id in story_ids
    }
    for story in sorted(stories.values(), key=lambda item: item.identifier):
        if story.identifier in linked_story_ids:
            continue
        feature = features.get(story.parent)
        related_features = {feature.identifier} if feature else set()
        related_waves = {feature.parent} if feature and feature.parent else set()
        related_tasks = tasks_by_parent.get(story.identifier, set())
        related_tests = tests_by_id.get(story.identifier, [])
        commits = {
            subject
            for task in related_tasks
            for subject in commit_subjects.get(task, [])
        }
        headers.append(
            "| "
            + " | ".join(
                (
                    "—",
                    f"{story.identifier} — {story.title}",
                    markdown_cell(related_features),
                    markdown_cell(related_waves),
                    markdown_cell(
                        {
                            f"{feature_id}: {features[feature_id].title}"
                            for feature_id in related_features
                            if feature_id in features
                        }
                    ),
                    markdown_cell(related_tasks),
                    markdown_cell(related_tests),
                    markdown_cell(commits),
                )
            )
            + " |"
        )
        warnings.append(f"{story.identifier} has no linked requirement")
        if not related_tests:
            warnings.append(f"{story.identifier} has no named test file")

    if not requirements:
        warnings.append("No functional requirements were found")
    if not test_files:
        warnings.append("No test files were found under tests/")
    headers.append("")
    if warnings:
        headers.extend(["## Warnings", ""] + [f"- {warning}" for warning in warnings] + [""])
    if errors:
        headers.extend(["## Errors", ""] + [f"- {error}" for error in errors] + [""])
    if not warnings and not errors:
        headers.extend(["## Result", "", "No traceability gaps detected.", ""])
    return "\n".join(headers), warnings, errors


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    try:
        content, warnings, errors = build_matrix(
            root, args.mode, args.no_git, args.tests_dir
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print(f"Traceability matrix written to {output}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
