#!/bin/bash
# git_sync.sh - Commit public changes to GitHub
# Usage: git_sync.sh [-m "commit message"]

set -euo pipefail
source "$(dirname "$0")/bridge.sh"

cd "$THAG"
[ -d ".git" ] || { echo "❌ Not a git repo. Run git_init.sh first." >&2; exit 1; }

# Default commit message
COMMIT_MSG="Daily sync $(date +'%Y-%m-%d')"

# Parse options
while [ $# -gt 0 ]; do
    case "$1" in
        -m)
            [ $# -lt 2 ] && { echo "❌ Error: -m requires message" >&2; exit 1; }
            COMMIT_MSG="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-m \"commit message\"]"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Ensure public directories exist (don't fail if missing)
mkdir -p projects share
git add projects/ share/ README.md 2>/dev/null || true
# git add docs/   # uncomment if docs/ is public

if ! git diff --staged --quiet; then
    git commit -m "$COMMIT_MSG"
    echo "✅ Committed locally."
    read -p "Push to GitHub? (y/n): " -n 1 -r; echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push && echo "✅ Pushed."
    fi
else
    echo "✅ No public changes to commit."
fi