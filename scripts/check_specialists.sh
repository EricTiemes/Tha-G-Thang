#!/usr/bin/env bash

SPECIALISTS_DIR="./specialists"

if [[ ! -d "$SPECIALISTS_DIR" ]]; then
    echo "❌ Specialists folder not found: $SPECIALISTS_DIR"
    exit 1
fi

echo "🔍 Scanning specialists for potential issues..."
echo ""

# Counters
total=0
bad=0

for file in "$SPECIALISTS_DIR"/*.yaml; do
    [[ -f "$file" ]] || continue
    total=$((total+1))
    
    # Extract the system_prompt block (multiline after "system_prompt: |")
    # This simple sed extracts from that line to the next line starting with non-space or EOF
    prompt=$(sed -n '/^system_prompt: |/{
        s/^system_prompt: |//
        :a; n; /^[^ ]/q; p; ba
    }' "$file" | sed 's/^  //' | tr '\n' ' ' | sed 's/  */ /g')
    
    # Remove leading/trailing spaces
    prompt=$(echo "$prompt" | sed 's/^ *//;s/ *$//')
    
    reasons=""
    
    # Check for JSON
    if [[ "$prompt" == *"{"*"}"* ]]; then
        reasons+=" contains JSON,"
    fi
    
    # Check for markdown code fences
    if [[ "$prompt" == *'```'* ]]; then
        reasons+=" contains markdown code fence,"
    fi
    
    # Check for user‑directed phrase
    if [[ "$prompt" == *"Please provide instructions"* ]]; then
        reasons+=" user‑directed,"
    fi
    
    # Check for fallback phrase
    if [[ "$prompt" == *"You can handle the following tasks:"* ]]; then
        reasons+=" fallback template,"
    fi
    
    # Check length
    if [[ ${#prompt} -lt 20 ]]; then
        reasons+=" too short (<20 chars),"
    fi
    
    # If any reasons, print
    if [[ -n "$reasons" ]]; then
        bad=$((bad+1))
        # Remove trailing comma
        reasons=${reasons%,}
        echo "❌ $(basename "$file"):$reasons"
        # Optionally show a snippet (first 100 chars)
        echo "   → ${prompt:0:100}..."
        echo ""
    fi
done

echo "📊 Scanned $total specialists. Found $bad with potential issues."