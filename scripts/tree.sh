#!/bin/bash
# tree.sh - Generate directory tree with exclusions
# Usage: tree.sh [target_path] [output_name] [-I pattern1|pattern2]

set -euo pipefail
source "$(dirname "$0")/bridge.sh"

usage() {
    echo "Usage: $0 [target_path] [output_name] [-I pattern1|pattern2]"
    echo "  -I : exclude patterns (pipe-separated, e.g., 'projects|sandro|vault')"
    exit 1
}

TARGET="${1:-$THAG}"
NAME="${2:-tree_$(date +%Y%m%d_%H%M%S)}"
shift 2 2>/dev/null || true

EXCLUDE_PATTERNS="*/\.*|*/__pycache__/*"  # default exclusions

while [ $# -gt 0 ]; do
    case "$1" in
        -I)
            [ $# -lt 2 ] && { echo "❌ Error: -I requires pattern" >&2; usage; }
            EXCLUDE_PATTERNS="${EXCLUDE_PATTERNS}|$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "❌ Unknown option: $1" >&2
            usage
            ;;
    esac
done

OUTPUT="$THAG_LOGS/${NAME}.txt"
mkdir -p "$THAG_LOGS"

# Build find command with exclusions
FIND_CMD="find \"$TARGET\""
IFS='|' read -ra PATTERNS <<< "$EXCLUDE_PATTERNS"
for pat in "${PATTERNS[@]}"; do
    FIND_CMD+=" -not -path \"*${pat}*\""
done
FIND_CMD+=" | sort | sed \"s|$TARGET||; s|^/||; s|^|  |\""

eval "$FIND_CMD" > "$OUTPUT"

# Keep latest 3
ls -t "$THAG_LOGS"/tree_*.txt 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null

echo "✅ Tree saved: $OUTPUT"