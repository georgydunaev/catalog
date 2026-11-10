#!/usr/bin/env bash
# beacon.sh — Host-side synchronization beacon for branch 'main'
# Naming Agreements:
#   1) Explicit remotes 'github' and 'gitlab' only (never 'origin').
#   2) Main branch is always 'main' (never 'master').
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPO_DIR}"

# Enforce no 'origin' remote
if git remote get-url origin >/dev/null 2>&1; then
    if ! git remote get-url github >/dev/null 2>&1; then
        git remote rename origin github 2>/dev/null || true
    else
        git remote remove origin 2>/dev/null || true
    fi
fi

# Enforce 'main' branch
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")"
if [ "${BRANCH}" = "master" ]; then
    git branch -M master main 2>/dev/null || true
    BRANCH="main"
fi

git add -A
git commit -m "beacon sync $(date -u +%Y-%m-%dT%H:%M:%SZ)" || true

# Politely fetch and integrate before pushing to github
if git remote get-url github >/dev/null 2>&1; then
    if git fetch github main >/dev/null 2>&1; then
        if git rev-parse --verify github/main >/dev/null 2>&1; then
            if ! git merge-base --is-ancestor github/main HEAD 2>/dev/null; then
                git rebase -X ours github/main >/dev/null 2>&1 || {
                    git rebase --abort >/dev/null 2>&1 || true
                    git merge --no-edit -X ours --allow-unrelated-histories github/main >/dev/null 2>&1 || git merge --abort >/dev/null 2>&1 || true
                }
            fi
        fi
    fi
    git push github HEAD:main || true
fi

# Also keep Local GitLab synced if reachable
if git remote get-url gitlab >/dev/null 2>&1; then
    git push gitlab HEAD:main >/dev/null 2>&1 || true
fi
