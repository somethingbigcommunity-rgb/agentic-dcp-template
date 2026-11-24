#!/usr/bin/env python3
"""Deterministic, read-only Git & GitHub milestone advisor for ASE.

Inspects the repository's Git state, remote connectivity (no-remote vs
github-remote vs other-remote), .ase-install.json tracking mode (versioned vs
excluded), and AGENTS.md configuration (Project context: personal vs work,
Git mode: local vs remote), then outputs milestone-appropriate Git/GitHub
command proposals and the execution policy (ADR-002).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

MILESTONES = ("m0", "plan", "task", "review", "release")
SETTING_RE = re.compile(
    r"^\|\s*(?P<name>[^|]+?)\s*\|\s*`(?P<value>[^`]*)`",
    re.MULTILINE,
)


def _run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _parse_agents_config(repo: Path) -> dict[str, str]:
    candidates = [
        repo / "AGENTS.md",
        repo / ".agents" / "AGENTS.md",
        repo / ".ase" / "AGENTS.md",
    ]
    for path in candidates:
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            settings: dict[str, str] = {}
            for match in SETTING_RE.finditer(text):
                key = match.group("name").strip().lower()
                val = match.group("value").strip()
                if val and not val.startswith("<"):
                    settings[key] = val
            if settings:
                return settings
    return {}


def _read_install_manifest(repo: Path) -> dict[str, Any]:
    manifest = repo / ".agents" / ".ase-install.json"
    if manifest.is_file():
        try:
            return json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _detect_remote(repo: Path) -> tuple[str, str | None, str | None]:
    res = _run_git(repo, ["remote", "-v"])
    if res.returncode != 0 or not res.stdout.strip():
        return "no-remote", None, None

    remotes: dict[str, str] = {}
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            name, url = parts[0], parts[1]
            if name not in remotes or "(push)" in line:
                remotes[name] = url

    if not remotes:
        return "no-remote", None, None

    primary_name = "origin" if "origin" in remotes else sorted(remotes.keys())[0]
    primary_url = remotes[primary_name]
    lower_url = primary_url.lower()
    if "github.com" in lower_url or "github" in lower_url:
        return "github-remote", primary_name, primary_url
    return "other-remote", primary_name, primary_url


def _detect_branch_and_tracking(repo: Path) -> tuple[str, bool, int, int]:
    branch_res = _run_git(repo, ["branch", "--show-current"])
    branch = branch_res.stdout.strip() if branch_res.returncode == 0 else ""
    if not branch:
        head_res = _run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
        branch = head_res.stdout.strip() if head_res.returncode == 0 else "main"
    if not branch or branch == "HEAD":
        branch = "main"

    up_res = _run_git(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if up_res.returncode != 0 or not up_res.stdout.strip():
        return branch, False, 0, 0

    cnt_res = _run_git(repo, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])
    if cnt_res.returncode == 0 and cnt_res.stdout.strip():
        parts = cnt_res.stdout.strip().split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return branch, True, int(parts[0]), int(parts[1])
    return branch, True, 0, 0


def inspect_and_advise(
    repo: Path,
    milestone: str,
    context_override: str | None = None,
    git_mode_override: str | None = None,
    task_id: str | None = None,
    wp_id: str | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    config = _parse_agents_config(repo)
    manifest = _read_install_manifest(repo)

    project_context = (
        context_override
        or config.get("project context", "").lower()
        or "work"
    )
    if project_context not in ("personal", "work"):
        project_context = "work"

    git_mode = (
        git_mode_override
        or config.get("git mode", "").lower()
        or "local"
    )
    if git_mode not in ("local", "remote"):
        git_mode = "local"

    working_branch_cfg = config.get("working branch", "main") or "main"
    accepted_branch_cfg = config.get("accepted branch", "none") or "none"

    if manifest:
        versioned = bool(manifest.get("versioned", False))
        encapsulated = bool(manifest.get("encapsulated", True))
    else:
        versioned = True
        encapsulated = (repo / ".ase" / "project-memory").is_dir()

    artifacts_prefix = "deliverables"

    inside_git = _run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    is_git_repo = inside_git.returncode == 0 and inside_git.stdout.strip() == "true"

    agent_can_execute = project_context == "personal" and is_git_repo
    if not is_git_repo:
        execution_policy = (
            "Non-Git workspace (--no-git): no Git or GitHub commands apply."
        )
        return {
            "milestone": milestone,
            "is_git_repo": False,
            "remote_status": "no-remote",
            "remote_name": None,
            "remote_url": None,
            "branch": None,
            "has_upstream": False,
            "ahead": 0,
            "behind": 0,
            "dirty_count": 0,
            "versioned": versioned,
            "encapsulated": encapsulated,
            "project_context": project_context,
            "git_mode": git_mode,
            "agent_can_execute_after_confirmation": False,
            "execution_policy": execution_policy,
            "summary": "Workspace is not a Git repository; skip Git actions.",
            "commands": [],
        }

    status_res = _run_git(repo, ["status", "--porcelain"])
    dirty_lines = [
        line for line in status_res.stdout.splitlines() if line.strip()
    ]
    dirty_count = len(dirty_lines)

    remote_status, remote_name, remote_url = _detect_remote(repo)
    branch, has_upstream, ahead, behind = _detect_branch_and_tracking(repo)
    if not branch:
        branch = working_branch_cfg
    remote_ref = remote_name or "origin"

    if project_context == "personal":
        execution_policy = (
            "Project context is `personal`: I will NOT run Git commands before your review, "
            "but once you confirm (`HAG-01`), I can execute the proposed commit, push, tag, "
            "or release commands directly for you (I never merge into `accepted`)."
        )
    else:
        execution_policy = (
            "Project context is `work`: I have prepared the milestone Git/GitHub commands below "
            "for your convenience, but I will NEVER execute `git commit`, `git push`, branch, "
            "or remote commands in a work repository. Run them yourself when ready."
        )

    t_id = task_id or "T-0001"
    w_id = wp_id or "F-001"
    rel_tag = tag or "v0.1.0"
    commands: list[str] = []
    summary_parts: list[str] = []

    if milestone == "m0":
        if versioned:
            commands.append("git add -A")
            commands.append(
                f'git commit -m "{t_id}: I configured the initial project baseline"'
            )
            summary_parts.append(
                "ASE files are versioned: stage and commit the initial M0/M0-A baseline."
            )
        else:
            summary_parts.append(
                "ASE files are encapsulated and excluded via `.git/info/exclude`; "
                "no Git commit is required for the local M0-A baseline itself."
            )

        if remote_status == "no-remote":
            summary_parts.append(
                "No GitHub remote is connected (`git remote -v` is empty). "
                "You can keep the repository local-only or connect a GitHub repository:"
            )
            commands.append(
                f"gh repo create {repo.name} --private --source=. --remote=origin --push"
            )
        else:
            if versioned or ahead > 0 or not has_upstream:
                push_cmd = (
                    f"git push {remote_ref} {branch}"
                    if has_upstream
                    else f"git push -u {remote_ref} {branch}"
                )
                commands.append(push_cmd)
            if (
                git_mode == "remote"
                and accepted_branch_cfg
                and accepted_branch_cfg != "none"
            ):
                commands.append(
                    f"git branch {accepted_branch_cfg} && git push -u {remote_ref} {accepted_branch_cfg}"
                )
                summary_parts.append(
                    f"Remote `{remote_ref}` ({remote_url}) is connected; push `{branch}` "
                    f"and, once authorized, create `{accepted_branch_cfg}`."
                )
            else:
                summary_parts.append(
                    f"Remote `{remote_ref}` ({remote_url}) is connected on branch `{branch}`."
                )

    elif milestone == "plan":
        if not versioned:
            summary_parts.append(
                "Planning and ADR files are excluded from Git via `.git/info/exclude` "
                "(local unversioned mode); no Git commit or push is needed at this milestone."
            )
        else:
            commands.append("git add -A")
            commands.append(
                f'git commit -m "{t_id}: I defined the project plan and backlog baseline"'
            )
            if remote_status == "no-remote":
                summary_parts.append(
                    "Commit the approved plan/ADR snapshot locally (no remote is connected)."
                )
            else:
                push_cmd = (
                    f"git push {remote_ref} {branch}"
                    if has_upstream
                    else f"git push -u {remote_ref} {branch}"
                )
                commands.append(push_cmd)
                summary_parts.append(
                    f"Commit the approved plan/ADR snapshot and push to `{remote_ref}/{branch}`."
                )

    elif milestone == "task":
        commands.append("git status --short")
        commands.append("git add -A")
        if versioned or project_context == "personal":
            commit_msg = f"{t_id}: I implemented and verified the task changes"
        else:
            commit_msg = "I implemented and verified the changes"
        commands.append(f'git commit -m "{commit_msg}"')

        if remote_status == "no-remote":
            summary_parts.append(
                f"No remote is connected; commit the verified task diff on local branch `{branch}`."
            )
        else:
            push_cmd = (
                f"git push {remote_ref} {branch}"
                if has_upstream
                else f"git push -u {remote_ref} {branch}"
            )
            commands.append(push_cmd)
            summary_parts.append(
                f"Remote `{remote_ref}` ({remote_url}) is connected; commit the verified task diff "
                f"and push to `{remote_ref}/{branch}`."
            )

    elif milestone == "review":
        pr_body_path = f"{artifacts_prefix}/05-release-and-handover/pr-description.md"
        if dirty_count > 0:
            commands.append("git add -A")
            commit_msg = (
                f"{w_id}: I completed the Work Package review and verification"
                if (versioned or project_context == "personal")
                else "I completed the feature implementation and verification"
            )
            commands.append(f'git commit -m "{commit_msg}"')

        if remote_status == "github-remote":
            push_cmd = (
                f"git push {remote_ref} {branch}"
                if has_upstream
                else f"git push -u {remote_ref} {branch}"
            )
            commands.append(push_cmd)
            if (
                git_mode == "remote"
                and accepted_branch_cfg
                and accepted_branch_cfg != "none"
            ):
                commands.append(
                    f'gh pr create --base {accepted_branch_cfg} --head {branch} '
                    f'--title "{w_id}: Work Package delivery" --body-file {pr_body_path}'
                )
                summary_parts.append(
                    f"GitHub remote `{remote_ref}` is connected; push `{branch}` and open the "
                    f"`{branch} -> {accepted_branch_cfg}` Pull Request (human merges under HAG-01)."
                )
            else:
                commands.append(
                    f'gh pr create --head {branch} --title "Deliver verified changes" '
                    f"--body-file {pr_body_path}"
                )
                summary_parts.append(
                    f"GitHub remote `{remote_ref}` is connected; push `{branch}` and open the "
                    f"Pull Request using the verified PR description in `{pr_body_path}`."
                )
        elif remote_status == "other-remote":
            commands.append(f"git push -u {remote_ref} {branch}")
            summary_parts.append(
                f"Remote `{remote_ref}` ({remote_url}) is connected; push `{branch}` and open a "
                f"Pull/Merge Request using `{pr_body_path}`."
            )
        else:
            commands.append(
                f'git tag -a {w_id.lower()}-verified -m "I verified Work Package {w_id}"'
            )
            summary_parts.append(
                "No remote is connected; tag the verified Work Package locally or connect a GitHub "
                "remote (`gh repo create` / `git remote add origin <url>`) to push and open a PR."
            )

    elif milestone == "release":
        notes_path = f"{artifacts_prefix}/05-release-and-handover/release-notes.md"
        if dirty_count > 0:
            commands.append("git add -A")
            commands.append(f'git commit -m "I prepared release {rel_tag}"')
        commands.append(f'git tag -a {rel_tag} -m "Release {rel_tag}"')

        if remote_status == "github-remote":
            commands.append(f"git push {remote_ref} {branch} --tags")
            commands.append(
                f'gh release create {rel_tag} --target {branch} --title "{rel_tag}" '
                f"--notes-file {notes_path}"
            )
            summary_parts.append(
                f"GitHub remote `{remote_ref}` is connected; tag `{rel_tag}`, push `{branch}` and "
                f"tags, and publish the GitHub Release."
            )
        elif remote_status == "other-remote":
            commands.append(f"git push {remote_ref} {branch} --tags")
            summary_parts.append(
                f"Remote `{remote_ref}` is connected; tag `{rel_tag}` and push `{branch}` with tags."
            )
        else:
            summary_parts.append(
                f"No remote is connected; create annotated tag `{rel_tag}` locally. "
                "To publish on GitHub, connect a remote (`gh repo create` or `git remote add origin`) "
                f"and run `git push origin {branch} --tags`."
            )

    return {
        "milestone": milestone,
        "is_git_repo": True,
        "remote_status": remote_status,
        "remote_name": remote_name,
        "remote_url": remote_url,
        "branch": branch,
        "has_upstream": has_upstream,
        "ahead": ahead,
        "behind": behind,
        "dirty_count": dirty_count,
        "versioned": versioned,
        "encapsulated": encapsulated,
        "project_context": project_context,
        "git_mode": git_mode,
        "agent_can_execute_after_confirmation": agent_can_execute,
        "execution_policy": execution_policy,
        "summary": " ".join(summary_parts),
        "commands": commands,
    }


def format_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"### Git Milestone Proposal (`{report['milestone']}`)",
        "",
        f"- **Repository State:** "
        + (
            "non-Git workspace (`--no-git`)"
            if not report["is_git_repo"]
            else (
                f"branch `{report['branch']}` | "
                f"remote `{report['remote_status']}`"
                + (f" (`{report['remote_name']}` -> `{report['remote_url']}`)" if report["remote_url"] else "")
                + f" | uncommitted files: `{report['dirty_count']}`"
                + (
                    f" | ahead/behind upstream: `+{report['ahead']}/-{report['behind']}`"
                    if report["has_upstream"]
                    else " | upstream: `untracked`"
                )
            )
        ),
        f"- **Configuration:** `Project context: {report['project_context']}` | "
        f"`Git mode: {report['git_mode']}` | "
        f"`ASE files versioned: {str(report['versioned']).lower()}`",
        f"- **Milestone Guidance:** {report['summary']}",
        f"- **Execution Policy:** {report['execution_policy']}",
    ]
    if report["commands"]:
        lines.extend(["", "```sh", *report["commands"], "```"])
        if report["agent_can_execute_after_confirmation"]:
            lines.extend(
                [
                    "",
                    "Do you want me to execute these Git/GitHub commands for you now (`HAG-01`), or will you run them yourself?",
                ]
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--milestone",
        required=True,
        choices=MILESTONES,
        help="Project milestone reached (m0, plan, task, review, release).",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the repository root (default: current directory).",
    )
    parser.add_argument(
        "--context",
        choices=("personal", "work"),
        default=None,
        help="Override Project context (personal or work).",
    )
    parser.add_argument(
        "--git-mode",
        choices=("local", "remote"),
        default=None,
        help="Override Git mode (local or remote).",
    )
    parser.add_argument(
        "--task-id",
        default=None,
        help="Optional task ID (e.g. T-0004) for commit message proposals.",
    )
    parser.add_argument(
        "--wp-id",
        default=None,
        help="Optional Work Package or Feature ID (e.g. F-001) for review proposals.",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Optional release version tag (e.g. v0.2.0) for release proposals.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON.",
    )
    args = parser.parse_args()

    report = inspect_and_advise(
        repo=Path(args.repo),
        milestone=args.milestone,
        context_override=args.context,
        git_mode_override=args.git_mode,
        task_id=args.task_id,
        wp_id=args.wp_id,
        tag=args.tag,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
