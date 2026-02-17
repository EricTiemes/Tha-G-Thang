#!/usr/bin/env bash

SOURCE_BASE="./prompts"
TARGET_BASE="./specialists"
MODEL="qwen2.5:1.5b"

# Auto‑start Ollama if needed
if ! ollama list &>/dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    for i in {1..5}; do
        sleep 1
        ollama list &>/dev/null && break
    done
fi

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <subfolder>"
    exit 1
fi

SUB="$1"
SOURCE_DIR="$SOURCE_BASE/$SUB"
TARGET_DIR="$TARGET_BASE"
mkdir -p "$TARGET_DIR"

[[ ! -d "$SOURCE_DIR" ]] && echo "❌ Folder not found: $SOURCE_DIR" && exit 1

md_files=( "$SOURCE_DIR"/*.md )
[[ ${#md_files[@]} -eq 0 ]] && echo "⚠️  No .md files" && exit 0

# Build role list
roles=""
for file in "${md_files[@]}"; do
    name=$(basename "$file" .md | sed 's/ (Prompt)$//')
    roles+="$name"$'\n'
done

# Proven prompt
prompt="Write a system prompt for an AI assistant that can handle these tasks:
$roles
Output only the system prompt, nothing else."

# Generate (no stderr capture, so only model output comes through)
raw=$(echo "$prompt" | ollama run "$MODEL")

# Clean – just in case
clean=$(echo "$raw" | tr -d '\r' | sed 's/^ *//;s/ *$//')
[[ -z "$clean" ]] && clean="You are a $SUB specialist. You can handle: $(echo "$roles" | tr '\n' ' ')."

# Write YAML
outfile="$TARGET_DIR/$SUB.yaml"
cat > "$outfile" << EOF
# $SUB Specialist
# Generated: $(date)
# Model: $MODEL

name: "$SUB Specialist"
roles: ${#md_files[@]}
system_prompt: |
  $clean
EOF

echo "✅ $outfile"