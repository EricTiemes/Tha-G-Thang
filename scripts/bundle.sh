#!/bin/bash
# bundle.sh - Create addon zip with versioned filename
# Usage: bundle.sh [project...] [--build-id ID|dev]
#   --build-id ID : custom build identifier (appended with +)
#   dev           : shortcut for dev.YYYYMMDD_HHMM

set -euo pipefail
source "$(dirname "$0")/bridge.sh"
source "$(dirname "$0")/lib/project_selector.sh"

usage() {
    echo "Usage: $0 [project...] [--build-id ID|dev]"
    echo "  - project names or paths (omit for interactive menu)"
    echo "  - --build-id ID : custom suffix (e.g., --build-id alpha.1)"
    echo "  - dev           : auto dev timestamp (dev.YYYYMMDD_HHMM)"
    exit 1
}

# Check dependencies
command -v zip >/dev/null 2>&1 || { echo "❌ Error: 'zip' not found. Install with: pkg install zip" >&2; exit 1; }

# Parse arguments
BUILD_ID=""
PROJECT_ARGS=()

while [ $# -gt 0 ]; do
    case "$1" in
        --build-id)
            [ $# -lt 2 ] && { echo "❌ Error: --build-id requires value" >&2; usage; }
            BUILD_ID="$2"
            shift 2
            ;;
        dev)
            BUILD_ID="dev.$(date +%Y%m%d_%H%M)"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            PROJECT_ARGS+=("$1")
            shift
            ;;
    esac
done

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

# Bundle each
for p in "${SELECTED_PROJECTS[@]}"; do
    [ -d "$p" ] || { echo "⚠ Skipping $p (not a directory)" >&2; continue; }
    xml="$p/addon.xml"
    [ -f "$xml" ] || { echo "⚠ No addon.xml in $p" >&2; continue; }

    ADDON_ID=$(grep -o 'id="[^"]*"' "$xml" | head -1 | cut -d'"' -f2)
    VERSION=$(grep -o 'version="[^"]*"' "$xml" | head -1 | cut -d'"' -f2)

    if [ -n "$BUILD_ID" ]; then
        FILENAME="${ADDON_ID}-${VERSION}+${BUILD_ID}.zip"
    else
        FILENAME="${ADDON_ID}-${VERSION}.zip"
    fi

    OUTPUT="$THAG_ZIPS/$FILENAME"
    mkdir -p "$THAG_ZIPS"

    ( cd "$(dirname "$p")" && zip -r "$OUTPUT" "$(basename "$p")" \
        -x "*.git*" "*/__pycache__/*" "*.pyc" "*.swp" "*.swo" "*~" >/dev/null )

    echo "✅ $(basename "$p"): $FILENAME"
done