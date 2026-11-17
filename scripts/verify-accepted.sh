#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[0-9]+$ ]]; then
  echo "Usage: $0 <merged-pr-number>" >&2
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: GitHub CLI (gh) is required." >&2
  exit 1
fi

if ! origin=$(git remote get-url origin); then
  echo "Error: an origin remote is required." >&2
  exit 1
fi

repo=$(gh repo view "$origin" --json nameWithOwner --jq .nameWithOwner)
if [[ ! "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "Error: could not determine the GitHub repository from origin." >&2
  exit 1
fi

accepted_sha=$(gh api "repos/$repo/branches/accepted" --jq .commit.sha)
pr_state=$(gh pr view "$1" --repo "$repo" --json state --jq .state)
pr_base=$(gh pr view "$1" --repo "$repo" --json baseRefName --jq .baseRefName)
pr_head=$(gh pr view "$1" --repo "$repo" --json headRefName --jq .headRefName)
pr_head_repo=$(gh pr view "$1" --repo "$repo" --json headRepository --jq .headRepository.nameWithOwner)
pr_merge_sha=$(gh pr view "$1" --repo "$repo" --json mergeCommit --jq .mergeCommit.oid)
pr_url=$(gh pr view "$1" --repo "$repo" --json url --jq .url)

if [[ "$pr_state" != "MERGED" || "$pr_base" != "accepted" || "$pr_head" != "main" || "$pr_head_repo" != "$repo" ]]; then
  echo "Error: PR #$1 must be a merged same-repository main → accepted PR." >&2
  exit 1
fi
if [[ ! "$accepted_sha" =~ ^([0-9a-f]{40}|[0-9a-f]{64})$ || "$pr_merge_sha" != "$accepted_sha" ]]; then
  echo "Error: remote accepted is not at the merge commit of PR #$1." >&2
  exit 1
fi

printf 'Verified current remote accepted tip %s is the merge commit of PR #%s (%s).\n' \
  "$accepted_sha" "$1" "$pr_url"
printf 'This checks the current tip only; it cannot detect a direct update later replaced by a PR merge.\n'
