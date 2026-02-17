#!/bin/bash
# ruff_projects.sh - Check/fix Kodi plugins with interactive menu
source "$(dirname "$0")/bridge.sh"
source "$(dirname "$0")/lib/project_selector.sh"

# If no arguments, show menu
if [ $# -eq 0 ]; then
    select_projects
else
    # Accept explicit paths or names
    SELECTED_PROJECTS=()
    for arg in "$@"; do
        if [[ "$arg" == */* ]]; then
            SELECTED_PROJECTS+=("$arg")
        else
            SELECTED_PROJECTS+=("$THAG_PROJECTS/$arg")
        fi
    done
fi

# Run ruff check
for p in "${SELECTED_PROJECTS[@]}"; do
    [ -d "$p" ] || { echo "⚠ Skipping $p (not a directory)"; continue; }
    name=$(basename "$p")
    log="$THAG_LOGS/ruff_${name}_$(date +%Y%m%d_%H%M%S).txt"
    echo "🔍 Checking: $name"
    if ruff check "$p" > "$log" 2>&1; then
        echo "  ✅ Clean"
        rm "$log"  # no issues, remove empty log
    else
        echo "  ⚠ Issues: $log"
    fi
done

# Fix prompt
read -p "Fix issues? (y/n): " fix
if [[ "$fix" == "y" ]]; then
    for p in "${SELECTED_PROJECTS[@]}"; do
        name=$(basename "$p")
        log="$THAG_LOGS/ruff_fix_${name}_$(date +%Y%m%d_%H%M%S).txt"
        echo "🔧 Fixing: $name"
        ruff check --fix "$p" > "$log" 2>&1
    done
fi

# Clean pycache
find "$THAG_PROJECTS" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Rotate logs (keep last 3 per project)
for p in "${SELECTED_PROJECTS[@]}"; do
    name=$(basename "$p")
    ls -t "$THAG_LOGS"/ruff_${name}_*.txt 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null
    ls -t "$THAG_LOGS"/ruff_fix_${name}_*.txt 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null
done

echo "✅ Done"