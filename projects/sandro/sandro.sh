#!/bin/bash
# SANDRO - Central Command Interface
# Voice-first daily companion

SANDRO_DIR="$HOME/SandroBrain"
CONFIG_DIR="$SANDRO_DIR/config"
DATA_DIR="$SANDRO_DIR/data"
AUDIO_DIR="$SANDRO_DIR/audio"
VAULT_DIR="$SANDRO_DIR/vault"
SCRIPTS_DIR="$SANDRO_DIR/scripts"

# Ensure directories exist
mkdir -p $DATA_DIR/history $AUDIO_DIR $VAULT_DIR

# Wake Ollama if needed
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[Sandro is waking up...]"
    termux-wake-lock
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# Audio feedback function
play_ack() {
    # Create a pleasant chime (C major arpeggio)
    if [ ! -f "$AUDIO_DIR/chirp.wav" ]; then
        ffmpeg -f lavfi -i "sine=frequency=523.25:duration=0.08" \
               -f lavfi -i "sine=frequency=659.25:duration=0.08" \
               -f lavfi -i "sine=frequency=783.99:duration=0.08" \
               -filter_complex "[0:a][1:a][2:a]concat=n=3:v=0:a=1" \
               $AUDIO_DIR/chirp.wav -y 2>/dev/null
    fi
    termux-open $AUDIO_DIR/chirp.wav 2>/dev/null || true
}

# Quick TTS function
speak() {
    echo "$1" | piper --model $CONFIG_DIR/en_US-ryan-high.onnx \
                    --output_file $AUDIO_DIR/output.wav 2>/dev/null
    termux-open $AUDIO_DIR/output.wav
}

# Route based on command type
route_command() {
    TEXT="$1"
    TEXT_LOWER=$(echo "$TEXT" | tr '[:upper:]' '[:lower:]')
    
    # QUICK MODE PATTERNS (No LLM - Fast)
    
    # Grocery add
    if echo "$TEXT_LOWER" | grep -qE "(add|buy|need).*grocer|groceries"; then
        ITEM=$(echo "$TEXT" | sed -E 's/.*(add|buy|need)//gi; s/to the grocery//gi; s/to groceries//gi; s/groceries//gi' | xargs)
        if [ ! -z "$ITEM" ]; then
            echo "- [ ] $ITEM" >> $VAULT_DIR/Groceries.md
            speak "Added $ITEM to your list, mi amigo"
            return
        fi
    fi
    
    # Task/Reminder
    if echo "$TEXT_LOWER" | grep -qE "(remind|remember|todo|task|don't forget)"; then
        TASK=$(echo "$TEXT" | sed -E 's/(remind me|remember to|add task|don't forget)//gi' | xargs)
        if [ ! -z "$TASK" ]; then
            echo "- [ ] $TASK #task $(date +%H:%M)" >> $VAULT_DIR/Inbox.md
            speak "I'll remind you to $TASK"
            return
        fi
    fi
    
    # Quick note
    if echo "$TEXT_LOWER" | grep -qE "^(note|write down|capture|log)"; then
        NOTE=$(echo "$TEXT" | sed -E 's/^(note|write down|capture|log)//gi' | xargs)
        if [ ! -z "$NOTE" ]; then
            echo "- $NOTE $(date +%Y-%m-%d %H:%M)" >> $VAULT_DIR/Inbox.md
            speak "Noted"
            return
        fi
    fi
    
    # Brief/Status
    if echo "$TEXT_LOWER" | grep -qE "(brief|status|what.*up|what.*plan|schedule|agenda)"; then
        $SCRIPTS_DIR/daily_brief.sh
        return
    fi
    
    # DEEP MODE (LLM Processing)
    $SCRIPTS_DIR/deep_chat.sh "$TEXT"
}

# Main execution
case "$1" in
    "listen"|"")
        play_ack
        echo "[Listening...]"
        termux-microphone-record -f $AUDIO_DIR/input.wav -l 8 -r 16000 -c 1
        sleep 8
        
        echo "[Processing...]"
        whisper-cli -m ~/models/ggml-small.bin \
                    -f $AUDIO_DIR/input.wav \
                    -l en -otxt -of $AUDIO_DIR/input --dtwait 0 2>/dev/null
        
        TEXT=$(cat $AUDIO_DIR/input.txt 2>/dev/null | sed 's/^[[:space:]]*//')
        echo "You: $TEXT"
        
        if [ ! -z "$TEXT" ]; then
            route_command "$TEXT"
        else
            speak "I didn't catch that, mi amigo"
        fi
        ;;
    "text")
        # Text mode for quiet environments
        if [ ! -z "$2" ]; then
            route_command "$2"
        else
            echo "Usage: sandro.sh text 'your message'"
        fi
        ;;
    "brief")
        $SCRIPTS_DIR/daily_brief.sh
        ;;
    "chat")
        # Direct deep chat
        $SCRIPTS_DIR/deep_chat.sh "$2"
        ;;
    "mood")
        # Log mood directly
        $SCRIPTS_DIR/log_mood.sh "$2"
        ;;
    *)
        echo "Sandro - Your Voice Companion"
        echo "Usage:"
        echo "  sandro.sh           - Start voice listening"
        echo "  sandro.sh text 'msg' - Text input mode"
        echo "  sandro.sh brief     - Daily briefing"
        echo "  sandro.sh chat '?'  - Direct conversation"
        ;;
esac