#!/bin/bash
# ABL Dashboard Automation Control Script

SCRIPT_DIR="/Users/rico/Library/Mobile Documents/com~apple~CloudDocs/Really Rico /Python Coding/American Betting League"
PLIST_SOURCE="$SCRIPT_DIR/com.abl.monitor.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.abl.monitor.plist"
MONITOR_SCRIPT="$SCRIPT_DIR/abl_monitor.py"
LOG_FILE="$SCRIPT_DIR/abl_monitor.log"

echo "======================================"
echo "ABL Dashboard Automation Control"
echo "======================================"
echo ""

case "$1" in
    install)
        echo "📦 Installing ABL Monitor..."

        # Copy plist to LaunchAgents
        cp "$PLIST_SOURCE" "$PLIST_DEST"
        echo "✅ LaunchAgent installed"

        # Load the service
        launchctl load "$PLIST_DEST"
        echo "✅ Service loaded and started"

        echo ""
        echo "🎉 Installation complete!"
        echo "The monitor will now run automatically and check for updates every 15 minutes."
        echo ""
        echo "Commands:"
        echo "  ./abl_control.sh status    - Check if monitor is running"
        echo "  ./abl_control.sh logs      - View recent log entries"
        echo "  ./abl_control.sh stop      - Stop the monitor"
        echo "  ./abl_control.sh restart   - Restart the monitor"
        ;;

    uninstall)
        echo "🗑️  Uninstalling ABL Monitor..."

        # Unload the service
        launchctl unload "$PLIST_DEST" 2>/dev/null
        echo "✅ Service stopped"

        # Remove plist
        rm -f "$PLIST_DEST"
        echo "✅ LaunchAgent removed"

        echo ""
        echo "✅ Uninstallation complete!"
        echo "You can reinstall anytime with: ./abl_control.sh install"
        ;;

    start)
        echo "▶️  Starting ABL Monitor..."
        launchctl load "$PLIST_DEST"
        echo "✅ Monitor started"
        ;;

    stop)
        echo "⏹️  Stopping ABL Monitor..."
        launchctl unload "$PLIST_DEST"
        echo "✅ Monitor stopped"
        ;;

    restart)
        echo "🔄 Restarting ABL Monitor..."
        launchctl unload "$PLIST_DEST" 2>/dev/null
        sleep 1
        launchctl load "$PLIST_DEST"
        echo "✅ Monitor restarted"
        ;;

    status)
        echo "📊 Checking monitor status..."
        echo ""
        if launchctl list | grep -q "com.abl.monitor"; then
            echo "✅ Monitor is RUNNING"
            echo ""
            if [ -f "$LOG_FILE" ]; then
                echo "Recent activity:"
                echo "----------------"
                tail -10 "$LOG_FILE"
            fi
        else
            echo "❌ Monitor is NOT running"
            echo "Start it with: ./abl_control.sh start"
        fi
        ;;

    logs)
        echo "📄 Recent log entries:"
        echo "====================="
        if [ -f "$LOG_FILE" ]; then
            tail -20 "$LOG_FILE"
        else
            echo "No log file found yet"
        fi
        ;;

    test)
        echo "🧪 Running single check test..."
        cd "$SCRIPT_DIR"
        python3 "$MONITOR_SCRIPT" --once
        ;;

    *)
        echo "Usage: $0 {install|uninstall|start|stop|restart|status|logs|test}"
        echo ""
        echo "Commands:"
        echo "  install    - Install and start the automated monitor"
        echo "  uninstall  - Stop and remove the automated monitor"
        echo "  start      - Start the monitor"
        echo "  stop       - Stop the monitor"
        echo "  restart    - Restart the monitor"
        echo "  status     - Check if monitor is running"
        echo "  logs       - View recent log entries"
        echo "  test       - Run a single check manually"
        exit 1
        ;;
esac

echo ""
