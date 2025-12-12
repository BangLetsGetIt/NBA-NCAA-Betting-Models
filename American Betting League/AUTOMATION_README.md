# ABL Dashboard Automation

This system automatically monitors your Google Spreadsheet and regenerates the dashboard whenever the data is updated.

## How It Works

1. **Monitoring Script** (`abl_monitor.py`) - Checks the spreadsheet every 15 minutes
2. **Change Detection** - Compares data hash to detect updates
3. **Auto Generation** - Runs `abl_recap.py` automatically when changes are detected
4. **Background Service** - Runs continuously in the background via macOS LaunchAgent

## Quick Start

### Install and Start Automation

```bash
cd "/Users/rico/Library/Mobile Documents/com~apple~CloudDocs/Really Rico /Python Coding/American Betting League"
./abl_control.sh install
```

That's it! The monitor is now running in the background.

## Commands

```bash
# Check if monitor is running
./abl_control.sh status

# View recent activity
./abl_control.sh logs

# Run a single check manually (for testing)
./abl_control.sh test

# Restart the monitor
./abl_control.sh restart

# Stop the monitor
./abl_control.sh stop

# Remove automation completely
./abl_control.sh uninstall
```

## What Happens Automatically

1. Every 15 minutes, the monitor checks your Google Sheet
2. If data has changed:
   - ✅ Dashboard is regenerated
   - ✅ Activity is logged
   - ✅ You can open the latest `dashboard.html`
3. If no changes:
   - Nothing happens (saves resources)

## Log Files

- `abl_monitor.log` - Main activity log (when checks happen, when dashboard is generated)
- `monitor_stdout.log` - Standard output from the monitor
- `monitor_stderr.log` - Error output (if any issues occur)

## Customization

Edit `abl_monitor.py` to change:
- `CHECK_INTERVAL = 900` - How often to check (in seconds)
  - 900 = 15 minutes
  - 600 = 10 minutes
  - 1800 = 30 minutes

After changing settings:
```bash
./abl_control.sh restart
```

## Troubleshooting

### Monitor not running?
```bash
./abl_control.sh status
./abl_control.sh start
```

### Not detecting updates?
```bash
# Run a manual test
./abl_control.sh test

# Check logs for errors
./abl_control.sh logs
```

### Dashboard not generating?
Check the monitor log:
```bash
cat abl_monitor.log
```

## How to Stop Automation

Temporarily:
```bash
./abl_control.sh stop
```

Permanently:
```bash
./abl_control.sh uninstall
```

You can always reinstall with `./abl_control.sh install`
