#!/bin/bash
# lint.sh - Interactive linting with staged fixes (ruff)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/bridge.sh"
source "$SCRIPT_DIR/lib/project_selector.sh"

# Ensure log directory exists
THAG_LOGS="${THAG_LOGS:-$THAG/logs}"
mkdir -p "$THAG_LOGS"

# Check ruff
if ! command -v ruff >/dev/null 2>&1; then
    echo "❌ Error: 'ruff' not found. Install with: pip install ruff" >&2
    exit 1
fi

# --- Project selection ---
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

# --- Process each project ---
for p in "${SELECTED_PROJECTS[@]}"; do
    [ -d "$p" ] || { echo "⚠ Skipping $p (not a directory)" >&2; continue; }
    name=$(basename "$p")
    echo ""
    echo "════════════════════════════════════════════"
    echo " Project: $name"
    echo "════════════════════════════════════════════"

    timestamp=$(date +%Y%m%d_%H%M%S)
    log="$THAG_LOGS/ruff_${name}_${timestamp}.txt"

    # Run ruff check – do not exit on failure
    set +e
    ruff check "$p" > "$log" 2>&1
    exit_code=$?
    set -e

    if [ $exit_code -eq 0 ]; then
        echo "  ✅ Clean – no issues found."
        rm -f "$log"
        continue
    fi

    echo "  ⚠ Issues found – log: $log"

    # --- SAFE COUNTING: strip non-numeric, default to 0 ---
    e722=$(grep -c "E722" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")
    e402=$(grep -c "E402" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")
    f841=$(grep -c "F841" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")
    e741=$(grep -c "E741" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")
    total=$(grep -c "^[EFW][0-9]" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")

    # Force numeric (strip leading zeros? no need)
    e722=$((e722 + 0))
    e402=$((e402 + 0))
    f841=$((f841 + 0))
    e741=$((e741 + 0))
    total=$((total + 0))

    # Safe other calculation – fallback to 0 on any error
    other=0
    if [ $total -ge $((e722 + e402 + f841 + e741)) ]; then
        other=$((total - e722 - e402 - f841 - e741))
    fi

    echo ""
    echo "  Breakdown:"
    echo "    🔴 E722 (bare except)    : $e722"
    echo "    🟠 E402 (import order)   : $e402"
    echo "    🟡 F841 (unused variable): $f841"
    echo "    🟢 E741 (ambiguous name) : $e741"
    echo "    ⚪ Other                 : $other"
    echo ""

    # --- FIX MENU – Now guaranteed to appear ---
    while true; do
        echo "  Fix options:"
        echo "    1. Auto-fix safe issues (F841, E741)"
        echo "    2. Fix bare excepts (E722) with sed"
        echo "    3. Fix import order (E402) - manual"
        echo "    4. View full log"
        echo "    5. Skip this project"
        read -p "  Choice: " choice

        case "$choice" in
            1)
                echo "  🔧 Running auto-fix (ruff check --fix)..."
                ruff check --fix "$p" > /dev/null 2>&1
                echo "  ✅ Auto-fixes applied."
                ;;
            2)
                echo "  🔧 Fixing bare excepts..."
                find "$p" -name "*.py" -exec sed -i 's/^\( *\)except:$/\1except Exception:/' {} \;
                find "$p" -name "*.py" -exec sed -i 's/^\( *\)except: /except Exception: /' {} \;
                echo "  ✅ Bare excepts converted to 'except Exception:'."
                ;;
            3)
                echo "  📝 Manual fix required for E402 (import order)."
                echo "     Move top-level imports above any sys.path.insert() etc."
                echo "     Files with E402:"
                grep "E402" "$log" | cut -d':' -f1 | sort -u | sed 's/^/     - /'
                read -p "     Press Enter when you have fixed them..."
                ;;
            4)
                less "$log"
                continue
                ;;
            5)
                echo "  ⏭ Skipping $name."
                break 2
                ;;
            *)
                echo "  ❌ Invalid choice, try again."
                continue
                ;;
        esac

        # --- Re-check after fixes ---
        echo "  🔍 Re-checking..."
        set +e
        ruff check "$p" > "$log.tmp" 2>&1
        new_exit=$?
        set -e
        mv "$log.tmp" "$log"

        if [ $new_exit -eq 0 ]; then
            echo "  ✅ All clean!"
            rm -f "$log"
            break
        else
            # Re-count remaining issues (safe)
            e722=$(grep -c "E722" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")
            e402=$(grep -c "E402" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")
            f841=$(grep -c "F841" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")
            e741=$(grep -c "E741" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")
            total=$(grep -c "^[EFW][0-9]" "$log" 2>/dev/null | tr -d '[:space:]' || echo "0")
            e722=$((e722 + 0)); e402=$((e402 + 0)); f841=$((f841 + 0)); e741=$((e741 + 0)); total=$((total + 0))
            other=0
            if [ $total -ge $((e722 + e402 + f841 + e741)) ]; then
                other=$((total - e722 - e402 - f841 - e741))
            fi
            echo "  ⚠ $total issues remaining."
        fi
    done
done

# --- Cleanup ---
find "$THAG_PROJECTS" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Rotate logs (keep last 3 per project)
for p in "${SELECTED_PROJECTS[@]}"; do
    name=$(basename "$p")
    ls -t "$THAG_LOGS"/ruff_${name}_*.txt 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null
done

echo ""
echo "✅ Linting complete."