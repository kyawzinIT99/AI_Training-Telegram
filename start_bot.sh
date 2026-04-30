#!/bin/bash
# ─────────────────────────────────────────────────────────
# AI Training Telegram Bot — Single-Instance Auto-Start
# Usage:
#   bash start_bot.sh --install    → register auto-start on login
#   bash start_bot.sh --uninstall  → remove auto-start
#   bash start_bot.sh --status     → check if bot is running
#   bash start_bot.sh              → run manually (foreground)
# ─────────────────────────────────────────────────────────

BOT_DIR="/Users/berry/Antigravity/AI training Telegram"
PYTHON="/opt/anaconda3/bin/python3"
LOG_FILE="$BOT_DIR/logs/bot.log"
PID_FILE="$BOT_DIR/logs/bot.pid"
PLIST="$HOME/Library/LaunchAgents/com.kyawzin.aitraining.bot.plist"

mkdir -p "$BOT_DIR/logs"

# ── Install as macOS Launch Agent ──
if [ "$1" == "--install" ]; then
    # Kill any running instances first
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null
        rm -f "$PID_FILE"
    fi
    pkill -f "python3 -m bot.main" 2>/dev/null
    sleep 1

    cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kyawzin.aitraining.bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>-m</string>
        <string>bot.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$BOT_DIR</string>
    <key>StandardOutPath</key>
    <string>$LOG_FILE</string>
    <key>StandardErrorPath</key>
    <string>$LOG_FILE</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
EOF
    launchctl unload "$PLIST" 2>/dev/null
    sleep 1
    launchctl load "$PLIST"
    echo "✅ Bot installed as auto-start service!"
    echo "   Auto-starts on every login. Logs: $LOG_FILE"
    echo "   Check status: bash start_bot.sh --status"
    exit 0
fi

# ── Uninstall ──
if [ "$1" == "--uninstall" ]; then
    launchctl unload "$PLIST" 2>/dev/null
    rm -f "$PLIST"
    pkill -f "python3 -m bot.main" 2>/dev/null
    echo "✅ Auto-start removed and bot stopped."
    exit 0
fi

# ── Status ──
if [ "$1" == "--status" ]; then
    if pgrep -f "python3 -m bot.main" > /dev/null; then
        PID=$(pgrep -f "python3 -m bot.main")
        echo "✅ Bot is RUNNING (PID: $PID)"
        echo "   Logs: tail -f $LOG_FILE"
    else
        echo "❌ Bot is NOT running"
        echo "   Start: bash start_bot.sh --install"
    fi
    exit 0
fi

# ── Manual run (foreground) ──
# Prevent double-start
if pgrep -f "python3 -m bot.main" > /dev/null; then
    echo "⚠️  Bot is already running! (PID: $(pgrep -f 'python3 -m bot.main'))"
    echo "   Use --status to check, or --install for auto-start."
    exit 1
fi

echo "🚀 Starting AI Training Bot (single instance)..."
echo "   Logs saved to: $LOG_FILE"
echo "   Press Ctrl+C to stop"
echo ""
cd "$BOT_DIR"
$PYTHON -m bot.main
