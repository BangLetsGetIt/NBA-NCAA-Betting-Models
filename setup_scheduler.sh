#!/bin/bash
# Setup script for NBA 3PT Props scheduler

echo "==================================================================="
echo "NBA 3PT Props Model - Scheduler Setup"
echo "==================================================================="
echo ""

# Function to check if scheduler is running
check_status() {
    if launchctl list | grep -q "com.rico.nba3ptprops"; then
        echo "✓ Scheduler is ACTIVE"
        echo "  The model will run automatically at:"
        echo "  - 10:00 AM"
        echo "  - 3:00 PM"
        echo "  - 6:00 PM"
        echo ""
        echo "  Logs: /Users/rico/sports-models/nba/logs/launchd_output.log"
        return 0
    else
        echo "✗ Scheduler is NOT running"
        return 1
    fi
}

# Main menu
case "$1" in
    start)
        echo "Starting scheduler..."
        launchctl load /Users/rico/Library/LaunchAgents/com.rico.nba3ptprops.plist
        check_status
        ;;
    stop)
        echo "Stopping scheduler..."
        launchctl unload /Users/rico/Library/LaunchAgents/com.rico.nba3ptprops.plist
        echo "✓ Scheduler stopped"
        ;;
    restart)
        echo "Restarting scheduler..."
        launchctl unload /Users/rico/Library/LaunchAgents/com.rico.nba3ptprops.plist 2>/dev/null
        launchctl load /Users/rico/Library/LaunchAgents/com.rico.nba3ptprops.plist
        check_status
        ;;
    status)
        check_status
        ;;
    logs)
        echo "Showing recent logs..."
        echo ""
        tail -50 /Users/rico/sports-models/nba/logs/launchd_output.log
        ;;
    test)
        echo "Running model manually (test run)..."
        echo ""
        cd /Users/rico/sports-models/nba
        python3 nba_3pt_props_model.py
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "Commands:"
        echo "  start    - Enable automatic scheduling (3x daily)"
        echo "  stop     - Disable automatic scheduling"
        echo "  restart  - Restart the scheduler"
        echo "  status   - Check if scheduler is running"
        echo "  logs     - View recent execution logs"
        echo "  test     - Run model manually (doesn't affect schedule)"
        echo ""
        exit 1
        ;;
esac

exit 0
