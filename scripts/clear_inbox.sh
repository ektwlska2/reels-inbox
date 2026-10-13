#!/usr/bin/env bash
# Remove summarized reels from the inbox branch, history included.
#
# Usage: scripts/clear_inbox.sh <reel-folder> [<reel-folder> ...]
#   e.g. scripts/clear_inbox.sh 2026-10-13-DdZS5zsAuCl
#
# Rebuilds `inbox` as one fresh commit holding only the reels that are left and force-pushes
# it (with a lease, so a reel that arrived in the meantime is never lost). When nothing is left
# the branch is deleted; the next shared reel recreates it.
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: $0 <reel-folder>..." >&2; exit 1; }

git fetch -q origin +refs/heads/inbox:refs/remotes/origin/inbox
old=$(git rev-parse refs/remotes/origin/inbox)

tmp=$(mktemp -d)
trap 'git worktree remove --force "$tmp" >/dev/null 2>&1 || true; rm -rf "$tmp"' EXIT
git worktree add -q --detach "$tmp" "$old"

for folder in "$@"; do
  rm -rf "$tmp/reels/$folder"
done

if [ -z "$(ls -A "$tmp/reels" 2>/dev/null)" ]; then
  git push -q --force-with-lease=inbox:"$old" origin :inbox
  echo "inbox is empty; branch deleted"
  exit 0
fi

git -C "$tmp" add -A reels
tree=$(git -C "$tmp" write-tree)
commit=$(git commit-tree "$tree" -m "Unreviewed reels")
git push -q --force-with-lease=inbox:"$old" origin "$commit":refs/heads/inbox
echo "inbox now holds: $(ls "$tmp/reels" | tr '\n' ' ')"
