#!/bin/bash
# bridge.sh - Environment variables for Tha-G-Thang
# Usage: source bridge.sh

export THAG="/storage/emulated/0/Tha-G-Thang"
export THAG_PROJECTS="$THAG/projects"
export THAG_SHARE="$THAG/share"
export THAG_SYSTEM="$THAG/system"
export THAG_LOGS="$THAG/logs"
export THAG_ZIPS="$THAG/zips"

# Generic aliases – no hardcoded projects
alias thag='cd "$THAG"'
alias projects='cd "$THAG_PROJECTS"'
alias scripts='cd "$THAG/scripts"'
alias logs='cd "$THAG_LOGS"'
alias zips='cd "$THAG_ZIPS"'

alias lint='scripts/lint.sh'
alias ruff='scripts/ruff_projects.sh'
alias bump='scripts/bump_version.sh'
alias bundle='scripts/bundle.sh'
alias debug='scripts/debug_bundle.sh'
alias release='scripts/release_info.sh'
alias sync='scripts/git_sync.sh'
alias handoff='cat $THAG_SHARE/handoffs/current_state.yaml'