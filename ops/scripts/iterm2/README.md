# iTerm2 Automation Profiles - FoKS Intelligence

## Overview
This directory contains comprehensive iTerm2 configuration for the FoKS automation ecosystem.

## Dynamic Profiles

**Location**: `~/Library/Application Support/iTerm2/DynamicProfiles/FoKS_Automation_Profiles.json`

### Available Profiles

1. **FoKS Intelligence — Backend (Prod)** (`⌘T` → select profile)
   - Opens `FoKS_Intelligence/backend`, activates `backend/.venv_foks`
   - Backend start is manual (e.g., `make run` or `ops/scripts/foks_boot.sh`) on port **8000**
   - Badge: `FoKS\n:8000`
   - Triggers: Highlights errors, warnings, startup messages

2. **FBP Backend - Socket Server**
   - Opens `FBP_Backend`, activates `~/.venvs/fbp`
   - Backend start is manual (e.g., `ops/scripts/fbp_boot.sh`) using `/tmp/fbp.sock`
   - Badge: `FBP\nUDS`
   - Socket: `/tmp/fbp.sock`

3. **NFA Automation - Batch Runner**
   - NFA batch processing interface
   - Output: `/Users/dnigga/Downloads/NFA_Outputs`
   - Quick commands for batch runs

4. **NFA Intelligence - Reporting**
   - Intelligence service interface
   - Reports: `./reports/`
   - API endpoint helpers

5. **REDESIM - Email Automation**
   - Gmail OAuth integration
   - Email collection and sending

6. **M3 Operations Dashboard**
   - System health monitoring
   - Service status checks
   - Colored status indicators

7. **Playwright Browser Console**
   - Browser automation debugging
   - Screenshot management
   - Codegen helper commands

8. **Logs Monitor - Live Tail**
   - Multi-source log monitoring
   - Interactive log selector
   - Color-coded log levels

9. **Quick Test Runner**
   - Health check interface
   - Integration test runner
   - API endpoint validation

10. **Environment Setup - Auto Config**
    - Automatic environment fixes
    - Dependency validation
    - Path configuration

11. **API Client - cURL Interactive**
    - Pre-configured API endpoints
    - Request/response highlighting
    - Unix socket helpers

## Python API Scripts

### automation_launcher.py
**Purpose**: Creates optimized workspace layouts (does not auto-start services)

**Functions**:
- `create_foks_workspace()` - Full 4-tab workspace
- `start_backends()` - Provides pane commands to start FoKS (port 8000) and FBP (/tmp/fbp.sock) manually via existing boot/make scripts
- `run_nfa_batch_visual()` - NFA batch with monitoring
- `health_check_dashboard()` - Continuous health monitoring

**Usage**:
```bash
# Option 1: Via iTerm2 Scripts menu
iTerm2 → Scripts → automation_launcher

# Option 2: Install as auto-launch script
cp automation_launcher.py ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch/
```

### status_bar_monitor.py
**Purpose**: Real-time backend status in status bar (display-only)

**Features**:
- FoKS backend status (✅/❌)
- FBP socket status
- NFA job count
- Auto-updates every 5s

**Installation**:
```bash
# Install script
cp status_bar_monitor.py ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch/

# Enable in iTerm2
# Settings → Profiles → Session → Status Bar
# Add "FoKS Monitor" component
```

### auto_restart_monitor.py
**Purpose**: Attempts to restart backends only while the script is running and AutoLaunch is enabled

**Monitors**:
- Traceback detection
- Connection errors
- Port conflicts
- Critical errors

**Actions** (only while active):
- Sends Ctrl+C to stop
- Cleans up resources (sockets)
- Restarts using the existing manual commands

**Installation**:
```bash
cp auto_restart_monitor.py ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch/
```

## Shell Integration

### Enable for zsh
```bash
# Profiles source shell integration when the file exists
# Install if missing:
curl -L https://iterm2.com/shell_integration/zsh \
  -o ~/.iterm2_shell_integration.zsh

echo 'source ~/.iterm2_shell_integration.zsh' >> ~/.zshrc
```

### Features Enabled
- ✅ Command history tracking
- ✅ Directory frecency
- ✅ Mark navigation (⌘⇧↑/↓)
- ✅ Alert on command completion
- ✅ SCP upload/download
- ✅ Auto-profile switching

## Triggers Configuration

### Automatic Highlights
All profiles include smart triggers:

**Success Indicators**:
- `✅`, `SUCCESS`, `OK`, `PASSED`
- Green foreground

**Error Indicators**:
- `❌`, `ERROR`, `FAILED`, `Exception`
- Red foreground, yellow background

**Warning Indicators**:
- `⚠️`, `WARNING`
- Orange foreground

**Info Indicators**:
- `INFO`, process-specific messages
- Blue foreground

### Custom Triggers
Edit in: Settings → Profiles → Advanced → Triggers

Example regex patterns:
```regex
# NFA number extraction
Processing NFA (\d+)

# API response codes
HTTP/\d\.\d" (2\d\d)    # Success
HTTP/\d\.\d" ([45]\d\d) # Error

# Job status
"status":\s*"(ok|success)"
```

## Badges

### Format
Profiles use two-line badges:
```
SERVICE_NAME
:PORT or UDS
```

Examples:
- `FoKS\n:8000`
- `FBP\nUDS`
- `NFA\nBatch`

### Custom Badge Variables
Available variables (use in Settings → Profiles → General → Badge):
```
\(session.name)
\(user.git_branch)
\(session.path)
\(session.hostname)
\(session.username)
```

## Hotkey Windows

### Create Dedicated Hotkey Windows
Settings → Keys → Hotkey Window

**Recommended Setup**:
1. **Logs Monitor**: `⌥⌘L`
   - Profile: Logs Monitor - Live Tail
   - Always visible, slide from top

2. **Quick Test**: `⌥⌘T`
   - Profile: Quick Test Runner
   - Slide from right

3. **API Client**: `⌥⌘A`
   - Profile: API Client - cURL Interactive
   - Slide from bottom

## AI Chat Integration

### Enable for Automation Sessions
Settings → General → AI → Enable AI Chat

**Recommended Permissions for Automation**:
- ✅ Check Terminal State
- ✅ View History
- ✅ View Manpages
- ❓ Run Commands (Ask before using)
- ❌ Write to filesystem (for safety)

**Use Cases**:
- Debugging Playwright errors
- Analyzing log patterns
- Explaining API responses
- Generating test commands

## Automatic Profile Switching

### Configure Rules
Settings → Profiles → Advanced → Automatic Profile Switching

**Example Rules**:
```
# Switch to FBP profile when in FBP directory
Path: /Users/dnigga/Documents/FBP_Backend/*
Profile: FBP Backend - Socket Server

# Switch to FoKS when in FoKS directory
Path: /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/*
Profile: FoKS Intelligence — Backend (Prod)

# Switch when SSHed
Hostname: *.sefaz.pb.gov.br
Profile: Remote Server
```

## Quick Start Guide

### 1. Install Dynamic Profiles
Profiles load from:
```
~/Library/Application Support/iTerm2/DynamicProfiles/FoKS_Automation_Profiles.json
```

Verify:
```bash
ls -la ~/Library/Application\ Support/iTerm2/DynamicProfiles/
```

### 2. Install Python API Scripts
```bash
# Create scripts directory
mkdir -p ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch

# Copy automation scripts
cp ops/scripts/iterm2/*.py ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch/

# Verify iTerm2 Python runtime
iTerm2 → Scripts → Manage → Install Python Runtime
```

### 3. Enable Shell Integration
```bash
# Option 1: Auto-load (already configured in profiles)
# Settings → Profiles → General → Command
# ✅ Load shell integration automatically

# Option 2: Manual
iTerm2 → Install Shell Integration
```

### 4. Launch Workspace
```bash
# Option 1: Via Scripts menu
iTerm2 → Scripts → automation_launcher

# Option 2: Via profile
⌘T → Select "FoKS Intelligence — Backend (Prod)"

# Option 3: Via hotkey (configure in Settings → Keys)
```

> Note: Production FoKS listens on port **8000**. Port **8001** is dev-only and must be started explicitly.

## Advanced Features

### Status Bar Components
Add to Settings → Profiles → Session → Status Bar:
1. FoKS Monitor (custom component)
2. CPU Utilization
3. Memory Utilization
4. Network Throughput
5. Current Directory

### Captured Output
All profiles enable captured output:
- Right-click output to capture
- Toolbelt → Captured Output
- Filter by regex patterns

### Command History
Integrated with shell integration:
- ⌘⇧; - Open command history
- ⌘; - Autocomplete
- Double-click to re-run

### Recent Directories
- ⌘⌥/ - Open directories popup
- Star frequently used dirs
- Option-double-click to cd

## Troubleshooting

### Profiles Not Loading
```bash
# Check for JSON errors
cat ~/Library/Application\ Support/iTerm2/DynamicProfiles/FoKS_Automation_Profiles.json | jq .

# Check Console.app for iTerm2 errors
open -a Console
```

### Python Scripts Not Running
```bash
# Verify Python runtime
~/Library/Application\ Support/iTerm2/iterm2env/versions/*/bin/python3 --version

# Reinstall if needed
iTerm2 → Scripts → Manage → Install Python Runtime

# Check script permissions
chmod +x ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch/*.py
```

### Shell Integration Not Working
```bash
# Verify installation
ls -la ~/.iterm2_shell_integration.zsh

# Re-source
source ~/.zshrc

# Check for conflicts
echo $PROMPT_COMMAND  # bash
echo $precmd_functions  # zsh
```

### Triggers Not Firing
Settings → Profiles → Advanced → Triggers
- ✅ Instant (must be checked)
- Test regex at https://regex101.com
- Verify parameters match format

## Performance Optimization

### For Large Outputs
Settings → Profiles → Terminal:
- Scrollback lines: 10,000 (not unlimited)
- ✅ Save lines to disk in alternate screen mode

### For Multiple Sessions
Settings → General → Services:
- ✅ Enable Python API
- ❌ Disable unused status bar components

### For Playwright Automation
Profile-specific (Playwright Browser Console):
- ✅ Unlimited scrollback (for debugging)
- ✅ Save screenshots to `output/nfa/screenshots/`
- Terminal type: `xterm-256color`

## Resources

- [iTerm2 Documentation](https://iterm2.com/documentation.html)
- [Python API Reference](https://iterm2.com/python-api/)
- [Dynamic Profiles Spec](https://iterm2.com/documentation-dynamic-profiles.html)
- [Shell Integration Guide](https://iterm2.com/documentation-shell-integration.html)
- [Triggers Documentation](https://iterm2.com/documentation-triggers.html)

## Support & Updates

Check for profile updates:
```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence
git pull origin main
cp ops/scripts/iterm2/FoKS_Automation_Profiles.json \
   ~/Library/Application\ Support/iTerm2/DynamicProfiles/
```

Report issues or request features via project issue tracker.
