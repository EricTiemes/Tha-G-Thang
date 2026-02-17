#!/bin/bash
# project_selector.sh - Common project selection functions
# Usage: source project_selector.sh; select_projects

select_projects() {
    cd "$THAG_PROJECTS" || exit 1
    mapfile -t PLUGINS < <(find . -maxdepth 1 -type d -name "plugin.*" | sort)
    [ ${#PLUGINS[@]} -eq 0 ] && echo "❌ No plugins found" && exit 1

    echo "=== Select Projects ==="
    for i in "${!PLUGINS[@]}"; do
        name=$(basename "${PLUGINS[$i]}")
        echo "$((i+1)). $name"
    done
    echo "a. All"
    read -p "Select (comma-separated, range, or a): " sel

    SELECTED_PROJECTS=()
    if [[ "$sel" == "a" ]]; then
        SELECTED_PROJECTS=("${PLUGINS[@]}")
    else
        # Expand comma/range syntax: e.g., 1,3-5,2
        for part in ${sel//,/ }; do
            if [[ "$part" =~ ^([0-9]+)-([0-9]+)$ ]]; then
                for ((i=${BASH_REMATCH[1]}; i<=${BASH_REMATCH[2]}; i++)); do
                    SELECTED_PROJECTS+=("${PLUGINS[$((i-1))]}")
                done
            else
                SELECTED_PROJECTS+=("${PLUGINS[$((part-1))]}")
            fi
        done
    fi

    # Deduplicate and preserve order
    SELECTED_PROJECTS=($(printf "%s\n" "${SELECTED_PROJECTS[@]}" | awk '!seen[$0]++'))
    echo "✅ Selected: ${#SELECTED_PROJECTS[@]} project(s)"
}