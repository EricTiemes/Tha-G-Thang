#!/usr/bin/env bash

# --- YOU CAN CHANGE THESE TWO LINES ---
SOURCE_BASE="./prompts"
TARGET_BASE="./specialists"
# --------------------------------------

mkdir -p "$TARGET_BASE"

for folder in "$SOURCE_BASE"/*/; do
    [[ -d "$folder" ]] || continue
    name=$(basename "$folder")
    
    if [[ -f "$TARGET_BASE/$name.yaml" ]]; then
        echo "⏭️  Skipping $name (already exists)"
        continue
    fi
    
    echo "📁 Next: $name"
    echo "────────────────────────"
    
    bash ./create_specialists.sh "$name"
    
    echo ""
    echo "✅ Done: $name"
    echo "────────────────────────"
    echo ""
    
    read -p "⏸️  Press Enter for next folder (or Ctrl+C to stop)..."
    echo ""
done

echo "🎉 All missing specialists generated!"