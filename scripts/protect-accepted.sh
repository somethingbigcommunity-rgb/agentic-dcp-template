#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s [--apply [--solo-owner]]\n' "$0" >&2
}

if [[ $# -eq 0 ]]; then
  printf '%s\n' \
    'No remote settings changed. To protect accepted, run:' \
    '  bash scripts/protect-accepted.sh --apply                # Review policy: reviewer' \
    '  bash scripts/protect-accepted.sh --apply --solo-owner   # Review policy: solo-owner (Lite only)'
  exit 0
fi

reviews=1
if [[ "$1" != "--apply" || $# -gt 2 ]]; then
  usage
  exit 2
fi
if [[ $# -eq 2 ]]; then
  if [[ "$2" != "--solo-owner" ]]; then
    usage
    exit 2
  fi
  reviews=0
fi

if [[ $reviews -eq 0 ]]; then
  root=$(git rev-parse --show-toplevel)
  setting() {
    sed -n "s/^| $1 | \`\([^\`]*\)\`.*|\$/\1/p" "$root/AGENTS.md" 2>/dev/null | head -n 1
  }
  if [[ "$(setting 'Review policy')" != "solo-owner" || "$(setting 'Working mode')" != "Lite" ]]; then
    echo "Error: --solo-owner requires 'Review policy' solo-owner and 'Working mode' Lite in AGENTS.md." >&2
    exit 2
  fi
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
repo_url=$(gh repo view "$origin" --json url --jq .url)
host="${repo_url#https://}"
host="${host%%/*}"
if [[ ! "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] ||
   [[ ! "$host" =~ ^[A-Za-z0-9.:-]+$ ]] ||
   [[ "$repo_url" != "https://$host/$repo" ]]; then
  echo "Error: could not determine the GitHub repository and host for origin." >&2
  exit 1
fi

if ! protected=$(gh api --hostname "$host" "repos/$repo/branches/accepted" --jq .protected); then
  echo "Error: could not inspect accepted; no protection was changed." >&2
  exit 1
fi
case "$protected" in
  false) ;;
  true)
    echo "Error: accepted is already protected; inspect existing rules instead of replacing them." >&2
    exit 1
    ;;
  *)
    echo "Error: accepted protection status is unknown; no protection was changed." >&2
    exit 1
    ;;
esac

gh api \
  --hostname "$host" \
  --method PUT \
  "repos/$repo/branches/accepted/protection" \
  --input - <<JSON
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["gate / gate"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": $reviews
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

if [[ $reviews -eq 1 ]]; then
  printf 'Branch protection applied to %s: required PR, check "gate / gate", and one approval by a reviewer other than the author.\n' "$repo"
else
  printf 'Branch protection applied to %s: required PR and check "gate / gate"; solo-owner policy, the Human Owner merge is the HAG-01 approval.\n' "$repo"
fi
