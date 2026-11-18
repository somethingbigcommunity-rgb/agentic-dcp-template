#!/usr/bin/env python3
"""Verify Lite P0 checks without changing Git or GitHub settings."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


class CheckError(Exception):
    """A required setup check could not be verified."""


REQUIRED_FILES = (
    "AGENTS.md",
    "project-memory/README.md",
    "project-memory/dcp/01-requirements/mvp-specification.md",
    "project-memory/dcp/04-implementation/iteration-protocol.md",
    "project-memory/state/PROJECT_STATE.md",
    "project-memory/state/M0_CHECKLIST.md",
    "project-memory/state/IMPLEMENTATION_STATUS.md",
    "project-memory/state/NEXT_TASK.md",
    "project-memory/state/TASK_LOG.md",
    "project-memory/state/KNOWN_ISSUES.md",
    "project-memory/state/TRACEABILITY.md",
    "templates/task-template.md",
    ".github/workflows/fast.yml",
    ".github/workflows/gate.yml",
    ".github/workflows/m0-smoke.yml",
)


# Minimum required approvals per review policy. Under solo-owner a PR is still
# required, and the Human Owner's own merge is the HAG-01 approval.
REVIEW_POLICIES = {"reviewer": 1, "solo-owner": 0}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    phase = parser.add_mutually_exclusive_group(required=True)
    phase.add_argument("--local", action="store_true", help="Run local P0 checks only")
    phase.add_argument(
        "--hosted",
        action="store_true",
        help="Also verify GitHub branches, protection, and hosted Actions evidence",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")
    parser.add_argument("--tested-commit", help="Full SHA of the verified setup commit")
    parser.add_argument("--task", help="Setup task ID, required for hosted checks")
    args = parser.parse_args()
    if args.hosted and (not args.tested_commit or not args.task):
        parser.error("--hosted requires --tested-commit and --task")
    if args.local and (args.tested_commit or args.task):
        parser.error("--tested-commit and --task apply only to --hosted")
    return args


def command(args: list[str], cwd: Path, label: str) -> str:
    try:
        result = subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise CheckError(f"{label} could not run: {exc}") from exc
    if result.returncode:
        details = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
        raise CheckError(f"{label} failed (exit {result.returncode}): {details}")
    return result.stdout


def json_command(args: list[str], cwd: Path, label: str) -> object:
    output = command(args, cwd, label)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise CheckError(f"{label} returned invalid JSON: {exc}") from exc


def require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise CheckError(f"{label} is not a JSON object")
    return dict(value)


def configuration(root: Path) -> dict[str, str]:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    section = text.partition("## Project configuration")[2]
    if not section:
        raise CheckError("AGENTS.md is missing the Project configuration section")
    section = section.split("\n## ", 1)[0]
    section = re.sub(r"<!--.*?-->", "", section, flags=re.DOTALL)
    result: dict[str, str] = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            raise CheckError("Project configuration rows must have exactly two cells")
        key, value = cells
        if key in result:
            raise CheckError(f"duplicate project configuration setting: {key}")
        result[key] = value.strip("`").strip()
    return result


def check_local(root: Path) -> None:
    if not root.is_dir():
        raise CheckError(f"project root is not a directory: {root}")
    git_root = Path(command(["git", "rev-parse", "--show-toplevel"], root, "Git root").strip())
    if git_root.resolve() != root:
        raise CheckError("the supplied root is not the Git repository root")

    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise CheckError(f"required regular file is missing: {relative}")
    for relative in ("project-memory/adr", "project-memory/dcp/04-implementation/tasks"):
        if not (root / relative).is_dir():
            raise CheckError(f"required Project Memory directory is missing: {relative}")

    settings = configuration(root)
    expected = {
        "Working mode": "Lite",
        "Working branch": "main",
        "Accepted branch": "accepted",
        "Fast CI command": "scripts/ci/fast.sh",
        "Gate CI command": "scripts/ci/gate.sh",
    }
    for key, value in expected.items():
        if settings.get(key) != value:
            raise CheckError(f"{key} must be {value!r} for Lite P0")
    if settings.get("Engine") not in {"antigravity", "vscode"}:
        raise CheckError("Engine must be 'antigravity' or 'vscode' for Lite P0")
    policy = settings.get("Review policy")
    if policy not in REVIEW_POLICIES:
        raise CheckError("Review policy must be 'reviewer' or 'solo-owner'")
    stack = settings.get("Stack", "").strip()
    if not stack or "to be defined" in stack.lower() or stack.startswith("<"):
        raise CheckError("Stack must contain an approved project-specific value")

    for relative in ("scripts/ci/fast.sh", "scripts/ci/gate.sh"):
        path = root / relative
        if not path.is_file() or path.is_symlink() or not os.access(path, os.X_OK):
            raise CheckError(f"{relative} must be a regular executable file")
        command(["bash", "-n", relative], root, f"syntax check for {relative}")
        print(f"Running {relative}", flush=True)
        try:
            result = subprocess.run(["bash", relative], cwd=root, check=False)
        except OSError as exc:
            raise CheckError(f"{relative} could not run: {exc}") from exc
        if result.returncode:
            raise CheckError(f"{relative} failed (exit {result.returncode})")
    print("Local checks passed. Local evidence alone does not complete M0.")


def check_protection(value: object, policy: str) -> None:
    protection = require_object(value, "accepted protection")
    checks = require_object(protection.get("required_status_checks"), "required status checks")
    contexts = checks.get("contexts")
    check_entries = checks.get("checks")
    names: set[str] = set()
    if isinstance(contexts, list):
        names.update(item for item in contexts if isinstance(item, str))
    if isinstance(check_entries, list):
        for item in check_entries:
            if isinstance(item, dict) and isinstance(item.get("context"), str):
                names.add(item["context"])
    if checks.get("strict") is not True or "gate / gate" not in names:
        raise CheckError("accepted must require strict status check 'gate / gate'")

    reviews = require_object(protection.get("required_pull_request_reviews"), "required reviews")
    count = reviews.get("required_approving_review_count")
    minimum = REVIEW_POLICIES[policy]
    if not isinstance(count, int) or isinstance(count, bool) or count < minimum:
        raise CheckError(
            f"accepted must require a pull request with at least {minimum} approving review(s) "
            f"for review policy {policy!r}"
        )
    bypass = reviews.get("bypass_pull_request_allowances")
    if bypass is not None:
        allowances = require_object(bypass, "review bypass allowances")
        for kind in ("users", "teams", "apps"):
            if kind in allowances and allowances[kind] != []:
                raise CheckError(f"accepted permits {kind} to bypass the required review")

    for key, expected in (
        ("enforce_admins", True),
        ("allow_force_pushes", False),
        ("allow_deletions", False),
    ):
        setting = require_object(protection.get(key), key)
        if setting.get("enabled") is not expected:
            raise CheckError(f"accepted protection requires {key}.enabled = {expected}")


def check_procedural_hag01(root: Path) -> None:
    checklist = (root / "project-memory/state/M0_CHECKLIST.md").read_text(
        encoding="utf-8"
    )
    if not re.search(
        r"(?m)^HAG-06 procedural accepted-gate fallback: APPROVED — \d{4}-\d{2}-\d{2}$",
        checklist,
    ):
        raise CheckError(
            "accepted is unprotected; record explicit HAG-06 procedural fallback approval "
            "in M0_CHECKLIST.md"
        )
    if not re.search(
        r"(?m)^Reason and accepted residual risk: (?!PENDING$).+$", checklist
    ):
        raise CheckError(
            "record why branch protection is unavailable and the accepted residual risk "
            "in M0_CHECKLIST.md"
        )
    audit = root / "scripts/verify-accepted.sh"
    if not audit.is_file() or audit.is_symlink() or not os.access(audit, os.X_OK):
        raise CheckError("procedural accepted gate requires executable scripts/verify-accepted.sh")
    print(
        "accepted is unprotected; HAG-06 procedural fallback is recorded. "
        "Direct pushes and early merges are not technically blocked."
    )


def successful_run(
    root: Path, repo: str, workflow: str, commit: str, event: str
) -> str:
    result = json_command(
        [
            "gh", "run", "list", "--repo", repo, "--workflow", workflow,
            "--branch", "main", "--commit", commit, "--event", event,
            "--limit", "50", "--json", "headSha,headBranch,event,status,conclusion,url",
        ],
        root,
        f"{workflow} runs",
    )
    if not isinstance(result, list):
        raise CheckError(f"{workflow} run list is not a JSON array")
    for value in result:
        run = require_object(value, f"{workflow} run")
        if (
            run.get("headSha") == commit
            and run.get("headBranch") == "main"
            and run.get("event") == event
        ):
            if run.get("status") != "completed" or run.get("conclusion") != "success":
                raise CheckError(f"latest {workflow} run for {commit} is not successful")
            url = run.get("url")
            if not isinstance(url, str) or not url.startswith("https://"):
                raise CheckError(f"{workflow} run has no valid evidence URL")
            return url
    raise CheckError(f"no {workflow} {event} run found for main at {commit}")


def check_hosted(root: Path, tested_commit: str, task: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", tested_commit):
        raise CheckError("--tested-commit must be a full lowercase Git commit SHA")
    if not re.fullmatch(r"T-\d{4}", task):
        raise CheckError("--task must match T-NNNN")
    task_paths = list((root / "project-memory/dcp/04-implementation/tasks").glob(f"{task}-*.md"))
    if len(task_paths) != 1 or not task_paths[0].is_file() or task_paths[0].is_symlink():
        raise CheckError(f"expected exactly one regular task file for {task}")
    task_path = task_paths[0].relative_to(root).as_posix()

    branch = command(["git", "branch", "--show-current"], root, "current branch").strip()
    if branch != "main":
        raise CheckError("hosted M0 verification requires the main branch")
    if command(["git", "status", "--porcelain"], root, "worktree status").strip():
        raise CheckError("hosted M0 verification requires a clean worktree")
    head = command(["git", "rev-parse", "HEAD"], root, "main commit").strip()
    command(["git", "cat-file", "-e", f"{tested_commit}:{task_path}"], root, "setup task at tested commit")
    command(["git", "merge-base", "--is-ancestor", tested_commit, head], root, "setup commit ancestry")
    allowed = {
        task_path,
        "project-memory/state/PROJECT_STATE.md",
        "project-memory/state/M0_CHECKLIST.md",
        "project-memory/state/TASK_LOG.md",
    }

    accepted = command(
        ["git", "rev-parse", "--verify", "refs/heads/accepted"], root, "local accepted"
    ).strip()
    command(["git", "merge-base", "--is-ancestor", accepted, head], root, "accepted ancestry")
    for label, commit in (("main", head), ("accepted", accepted)):
        changed = command(
            ["git", "diff", "--name-only", "-z", tested_commit, commit],
            root,
            f"{label} changes since the verified setup commit",
        )
        unexpected = [path for path in changed.split("\0") if path and path not in allowed]
        if unexpected:
            raise CheckError(
                f"{label} changes since the tested commit are not setup-state-only: "
                + ", ".join(unexpected)
            )
    origin = command(["git", "remote", "get-url", "origin"], root, "origin remote").strip()
    parsed_origin = urlsplit(origin)
    if parsed_origin.password is not None or (
        parsed_origin.scheme in {"http", "https"} and parsed_origin.username is not None
    ):
        raise CheckError("origin must not contain embedded credentials")
    refs_output = command(
        ["git", "ls-remote", "--heads", "origin", "refs/heads/main", "refs/heads/accepted"],
        root,
        "origin branches",
    )
    refs: dict[str, str] = {}
    for line in refs_output.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            raise CheckError("origin returned an invalid branch listing")
        refs[parts[1]] = parts[0]
    if refs.get("refs/heads/main") != head or refs.get("refs/heads/accepted") != accepted:
        raise CheckError("local and origin main/accepted must exist and have matching commits")

    repo_info = require_object(
        json_command(
            ["gh", "repo", "view", origin, "--json", "nameWithOwner,url,defaultBranchRef"],
            root,
            "GitHub origin",
        ),
        "GitHub origin",
    )
    name = repo_info.get("nameWithOwner")
    repo_url = repo_info.get("url")
    default_branch = require_object(repo_info.get("defaultBranchRef"), "default branch")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
        raise CheckError("GitHub origin did not return a valid owner/repository")
    if not isinstance(repo_url, str):
        raise CheckError("GitHub origin did not return a repository URL")
    parsed = urlsplit(repo_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.path.rstrip("/") != f"/{name}"
        or parsed.query
        or parsed.fragment
    ):
        raise CheckError("GitHub origin returned an invalid repository URL")
    if default_branch.get("name") != "main":
        raise CheckError("the GitHub default branch must be main")
    host = parsed.netloc
    repo = f"{host}/{name}"
    accepted_branch = require_object(
        json_command(
            ["gh", "api", "--hostname", host, f"repos/{name}/branches/accepted"],
            root,
            "accepted branch",
        ),
        "accepted branch",
    )
    if accepted_branch.get("protected") is True:
        protection = json_command(
            [
                "gh",
                "api",
                "--hostname",
                host,
                f"repos/{name}/branches/accepted/protection",
            ],
            root,
            "accepted protection",
        )
        check_protection(protection, configuration(root)["Review policy"])
    elif accepted_branch.get("protected") is False:
        check_procedural_hag01(root)
    else:
        raise CheckError("GitHub did not return an explicit accepted protection status")

    fast_url = successful_run(root, repo, "fast.yml", head, "push")
    smoke_url = successful_run(root, repo, "m0-smoke.yml", tested_commit, "workflow_dispatch")
    print(f"Hosted Fast evidence for {head}: {fast_url}")
    print(f"Hosted Gate smoke evidence for {tested_commit}: {smoke_url}")
    print("Verify the remaining human checklist items; the actual PR gate is not tested by the M0 smoke.")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    try:
        check_local(root)
        if args.hosted:
            check_hosted(root, args.tested_commit, args.task)
    except (CheckError, OSError, UnicodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
