#!/bin/bash
# server.sh [path] [port]
source "$(dirname "$0")/bridge.sh"

TARGET="${1:-$THAG}"
PORT="${2:-3000}"

[ ! -d "$TARGET" ] && echo "Path not found: $TARGET" && exit 1

cd "$TARGET"
echo "Server: http://localhost:$PORT"
echo "Path: $TARGET"
python -m http.server "$PORT"
