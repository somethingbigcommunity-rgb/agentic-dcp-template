#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  printf '%s\n' \
    'No remote settings changed. To protect accepted, run:' \
    '  bash scripts/protect-accepted.sh --apply'
  exit 0
fi

if [[ $# -ne 1 || "$1" != "--apply" ]]; then
  printf 'Usage: %s [--apply]\n' "$0" >&2
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: GitHub CLI (gh) is required." >&2
  exit 1
fi

repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
if [[ -z "$repo" ]]; then
  echo "Error: could not determine the current GitHub repository." >&2
  exit 1
fi

gh api "repos/$repo/branches/accepted" --jq .name >/dev/null
gh api \
  --method PUT \
  "repos/$repo/branches/accepted/protection" \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["gate / gate"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

printf 'Branch protection applied to %s: required check "gate / gate" and one human approval.\n' "$repo"
