#!/bin/bash
# bump_version.sh - Update addon.xml version
# Usage: bump_version.sh [project...] <part|version> [suffix]
#   part: major|minor|patch
#   version: explicit X.Y.Z
#   suffix: e.g., alpha.1, beta.2 (optional)

set -euo pipefail
source "$(dirname "$0")/bridge.sh"
source "$(dirname "$0")/lib/project_selector.sh"

usage() {
    echo "Usage: $0 [project...] <major|minor|patch|X.Y.Z> [suffix]"
    echo "  - project names or paths (omit for interactive menu)"
    echo "  - version part or explicit version (required)"
    echo "  - optional suffix (e.g., alpha.1, beta.2, rc.1)"
    exit 1
}

# Need at least version part
[ $# -lt 1 ] && usage

# Extract version part and optional suffix from end of args
if [ $# -ge 2 ] && [[ ! "${@: -2:1}" =~ ^(major|minor|patch|[0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
    # Second-last is suffix? No, version part must be last or second-last?
    # Convention: last = version part, second-last = suffix (if present)
    SUFFIX="${@: -2:1}"
    PART="${@: -1}"
    PROJECT_ARGS=("${@:1:$#-2}")
else
    SUFFIX=""
    PART="${@: -1}"
    PROJECT_ARGS=("${@:1:$#-1}")
fi

# Validate version part
if [[ ! "$PART" =~ ^(major|minor|patch|[0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
    echo "❌ Error: version must be major|minor|patch or X.Y.Z" >&2
    usage
fi

# Select projects
if [ ${#PROJECT_ARGS[@]} -eq 0 ]; then
    select_projects
else
    SELECTED_PROJECTS=()
    for arg in "${PROJECT_ARGS[@]}"; do
        if [[ "$arg" == */* ]]; then
            SELECTED_PROJECTS+=("$arg")
        else
            SELECTED_PROJECTS+=("$THAG_PROJECTS/$arg")
        fi
    done
fi

# Apply bump to each project
for p in "${SELECTED_PROJECTS[@]}"; do
    [ -d "$p" ] || { echo "⚠ Skipping $p (not a directory)" >&2; continue; }
    xml="$p/addon.xml"
    [ -f "$xml" ] || { echo "⚠ No addon.xml in $p" >&2; continue; }

    CURRENT=$(grep -o 'version="[^"]*"' "$xml" | head -1 | cut -d'"' -f2)
    BASE_VERSION=$(echo "$CURRENT" | sed 's/-[a-z0-9.]*$//')

    if [[ "$PART" =~ ^(major|minor|patch)$ ]]; then
        IFS='.' read -r MAJ MIN PATCH <<< "$BASE_VERSION"
        case "$PART" in
            major) MAJ=$((MAJ+1)); MIN=0; PATCH=0 ;;
            minor) MIN=$((MIN+1)); PATCH=0 ;;
            patch) PATCH=$((PATCH+1)) ;;
        esac
        NEW_VERSION="$MAJ.$MIN.$PATCH"
    else
        NEW_VERSION="$PART"
    fi

    [ -n "$SUFFIX" ] && NEW_VERSION="${NEW_VERSION}-${SUFFIX}"

    sed -i "s/version=\"[^\"]*\"/version=\"$NEW_VERSION\"/" "$xml"
    echo "✅ $(basename "$p"): $CURRENT → $NEW_VERSION"
done