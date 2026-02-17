#!/bin/bash
# release_info.sh - Extract news, update CHANGELOG, generate AI handoff
# Usage: release_info.sh [project...]

set -euo pipefail
source "$(dirname "$0")/bridge.sh"
source "$(dirname "$0")/lib/project_selector.sh"

# Check dependencies
command -v jq >/dev/null 2>&1 || { echo "❌ Error: 'jq' not found. Install with: pkg install jq" >&2; exit 1; }

# Select projects (if none, interactive; else use provided)
if [ $# -eq 0 ]; then
    select_projects
else
    SELECTED_PROJECTS=()
    for arg in "$@"; do
        if [[ "$arg" == */* ]]; then
            SELECTED_PROJECTS+=("$arg")
        else
            SELECTED_PROJECTS+=("$THAG_PROJECTS/$arg")
        fi
    done
fi

mkdir -p "$THAG_SYSTEM/state/release" "$THAG_SHARE/handoffs"
JSON_OUT="$THAG_SYSTEM/state/release/release_summary.json"
> "$JSON_OUT"

for p in "${SELECTED_PROJECTS[@]}"; do
    [ -d "$p" ] || { echo "⚠ Skipping $p (not a directory)" >&2; continue; }
    name=$(basename "$p")
    xml="$p/addon.xml"
    [ -f "$xml" ] || { echo "⚠ No addon.xml in $p" >&2; continue; }

    version=$(grep -o 'version="[^"]*"' "$xml" | head -1 | cut -d'"' -f2)
    news=$(sed -n '/<news>/,/<\/news>/p' "$xml" | sed '1s/<news>//; $s/<\/news>//' | xargs)
    [ -z "$news" ] && news="Minor fixes."

    jq -n --arg a "$name" --arg v "$version" --arg n "$news" --arg ts "$(date -Iseconds)" \
        '{addon: $a, version: $v, news: $n, timestamp: $ts}' >> "$JSON_OUT"

    changelog="$p/CHANGELOG.md"
    if ! grep -q "^## $version" "$changelog" 2>/dev/null; then
        { echo "## $version ($(date +%Y-%m-%d))"; echo "$news"; echo ""; [ -f "$changelog" ] && cat "$changelog"; } > "${changelog}.tmp"
        mv "${changelog}.tmp" "$changelog"
    fi
done

# Generate handoff only if we processed at least one project
if [ -s "$JSON_OUT" ]; then
    cat > "$THAG_SHARE/handoffs/current_state.yaml" <<EOF
# AI Handoff: Repository Release Status
generated: $(date -Iseconds)
releases:
$(jq -r '.addon + " " + .version' "$JSON_OUT" | tail -5 | sed 's/^/  - /')
mode: release
next_tasks:
  - "Update addon.xml news for next release"
  - "Push git tags"
EOF
    echo "✅ Release info updated. Handoff: share/handoffs/current_state.yaml"
else
    echo "⚠ No valid addons processed; handoff not updated." >&2
fi