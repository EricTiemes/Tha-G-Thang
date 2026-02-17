#!/bin/bash
# debug_bundle.sh - Quick test build with dev timestamp
# Usage: ./debug_bundle.sh [project...]

source "$(dirname "$0")/bridge.sh"

BUILD_ID="dev.$(date +%Y%m%d_%H%M)"
scripts/bundle.sh "$@" --build-id "$BUILD_ID"