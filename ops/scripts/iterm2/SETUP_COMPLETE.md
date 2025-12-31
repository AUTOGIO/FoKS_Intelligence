# 🎯 FoKS iTerm2 Automation Ecosystem - Complete Setup

## 📦 What Was Created

### 1. Dynamic Profiles (11 profiles)
**Location**: `~/Library/Application Support/iTerm2/DynamicProfiles/FoKS_Automation_Profiles.json`

- ✅ **FoKS Intelligence - Backend** - FoKS FastAPI backend environment
- ✅ **FBP Backend - Socket Server** - FBP Unix socket server
- ✅ **NFA Automation - Batch Runner** - NFA batch processing
- ✅ **NFA Intelligence - Reporting** - Intelligence service with reports
- ✅ **REDESIM - Email Automation** - Gmail OAuth integration
- ✅ **M3 Operations Dashboard** - System health monitoring
- ✅ **Playwright Browser Console** - Browser automation debugging
- ✅ **Logs Monitor - Live Tail** - Multi-source log monitoring
- ✅ **Quick Test Runner** - Health checks and tests
- ✅ **Environment Setup - Auto Config** - Auto environment fixing
- ✅ **API Client - cURL Interactive** - API endpoint testing

### 2. Python API Scripts (4 scripts)
**Location**: `~/Library/Application Support/iTerm2/Scripts/AutoLaunch/`

- ✅ **automation_launcher.py** - Creates full workspace layouts
- ✅ **status_bar_monitor.py** - Real-time backend status
- ✅ **auto_restart_monitor.py** - Auto-restart crashed backends
- ✅ **ai_error_handler.py** - AI-assisted debugging

### 3. Documentation
**Location**: `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/iterm2/`

- ✅ **README.md** - Complete documentation (400+ lines)
- ✅ **QUICK_REFERENCE.md** - Quick reference card
- ✅ **install.sh** - Installation script

### 4. Shell Configuration
**Location**: `~/.foks_iterm2_config`

- ✅ Custom aliases (foks-start, fbp-start, nfa-run)
- ✅ Health check functions
- ✅ Profile switching helpers
- ✅ Auto badge updates

## 🚀 Installation

### Option 1: Automated (Recommended)
```bash
bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/iterm2/install.sh
```

This will:
1. Install iTerm2 (if needed)
2. Create all necessary directories
3. Install dynamic profiles
4. Install Python API scripts
5. Set up shell integration
6. Create aliases and functions

### Option 2: Manual
```bash
# 1. Ensure iTerm2 is installed
brew install --cask iterm2

# 2. Dynamic profiles are already in place
ls ~/Library/Application\ Support/iTerm2/DynamicProfiles/FoKS_Automation_Profiles.json

# 3. Copy Python scripts
cp /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/iterm2/*.py \
   ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch/

# 4. Install Python runtime
# iTerm2 → Scripts → Manage → Install Python Runtime

# 5. Enable shell integration
curl -L https://iterm2.com/shell_integration/zsh \
  -o ~/.iterm2_shell_integration.zsh
echo 'source ~/.iterm2_shell_integration.zsh' >> ~/.zshrc

# 6. Source configuration
source ~/.foks_iterm2_config
source ~/.zshrc
```

## 🎨 Key Features

### 1. Smart Triggers
All profiles include automatic highlighting:
- ✅ **Green**: Success, OK, PASSED
- ❌ **Red**: Error, FAILED, Exception
- ⚠️ **Orange**: WARNING
- 🔵 **Blue**: INFO

### 2. Custom Badges
Two-line format showing service and port/type:
```
FoKS        FBP         NFA
:8000       UDS         Batch
```

### 3. Shell Integration Features
- Command history tracking
- Directory frecency
- Mark navigation (⌘⇧↑/↓)
- Alert on command completion
- SCP upload/download
- Auto-profile switching

### 4. Python API Automation
- **Workspace Layouts**: 4-tab pre-configured setups
- **Status Bar**: Real-time backend monitoring
- **Auto-Restart**: Crash detection and recovery
- **AI Debugging**: Automatic error analysis

### 5. AI Chat Integration
- Error detection → AI prompt
- Command output explanation (⌥⌘E)
- Terminal state access
- Command execution assistance

## 📋 Quick Start

### 1. First Time Setup
```bash
# Run installation
bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/iterm2/install.sh

# Reload shell
source ~/.zshrc

# Restart iTerm2 or reload profiles
# iTerm2 → Settings → Profiles → Other Actions → Reload All Profiles
```

### 2. Launch Workspace
```bash
# Method 1: Via Scripts menu
iTerm2 → Scripts → automation_launcher

# Method 2: Via profile
⌘T → Select "FoKS Intelligence - Backend"

# Method 3: Via alias
foks-backend
```

### 3. Start Backends
```bash
# In first pane
foks-start

# In second pane (⌘D to split)
fbp-start

# Check health
all-health
```

### 4. Run NFA Batch
```bash
# In new tab (⌘T)
⌘T → "NFA Automation - Batch Runner"
nfa-run
```

## 🎯 Common Workflows

### Development Session
1. Launch workspace: `iTerm2 → Scripts → automation_launcher`
2. Backends start automatically in Tab 1
3. Monitor in Tab 3 (Operations)
4. Code in your editor
5. Test in Tab 4 (Development)

### NFA Batch Processing
1. `⌘T` → "NFA Automation - Batch Runner"
2. Run: `python run_rental_nfa_batch.py`
3. `⌘D` → Split for logs
4. Monitor: `tail -f /Users/dnigga/Downloads/NFA_Outputs/nfa_runs.jsonl`

### Debugging
1. Error appears → AI handler detects it
2. Prompt copied to clipboard
3. `Window → AI Chat`
4. Paste and get solution
5. Apply fix
6. Test with `Quick Test Runner` profile

### Monitoring
1. `⌘T` → "M3 Operations Dashboard"
2. `⌘D` → "Quick Test Runner"
3. Watch status bar for real-time updates
4. Use `all-health` for manual checks

## 🔧 Customization

### Add Custom Profile
Edit: `~/Library/Application Support/iTerm2/DynamicProfiles/FoKS_Automation_Profiles.json`

```json
{
  "Name": "My Custom Profile",
  "Guid": "my-unique-guid-001",
  "Custom Command": "Yes",
  "Command": "cd /path && echo 'Hello' && exec zsh",
  "Working Directory": "/path",
  "Badge Text": "CUSTOM\\nBADGE",
  "Tags": ["custom", "automation"]
}
```

### Add Custom Trigger
Settings → Profiles → Advanced → Triggers:
- Regex: `Your pattern here`
- Action: `HighlightTrigger`
- Parameter: `{#rrggbb,#rrggbb}` (foreground, background)

### Modify Python Scripts
Edit files in:
```
~/Library/Application Support/iTerm2/Scripts/AutoLaunch/
```

Restart iTerm2 to reload scripts.

### Create Hotkey Window
Settings → Keys → Hotkey Window:
- Choose profile
- Set hotkey (e.g., `⌥⌘L` for logs)
- Configure animation and position

## 📊 Status Bar Configuration

### Enable FoKS Monitor
1. Settings → Profiles → Session
2. Status Bar → Configure Status Bar
3. Drag "FoKS Monitor" to active components
4. Customize position and appearance

### Add Other Components
- CPU Utilization
- Memory Utilization
- Network Throughput
- Current Directory
- Git Branch

## 🆘 Troubleshooting

### Profiles not showing
```bash
# Validate JSON
cat ~/Library/Application\ Support/iTerm2/DynamicProfiles/FoKS_Automation_Profiles.json | jq .

# Check Console.app
open -a Console
# Filter: iTerm2
```

### Python scripts not working
```bash
# Check runtime
ls ~/Library/Application\ Support/iTerm2/iterm2env/versions/*/bin/python3

# Reinstall
# iTerm2 → Scripts → Manage → Install Python Runtime

# Check permissions
chmod +x ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch/*.py
```

### Shell integration issues
```bash
# Verify installation
ls -la ~/.iterm2_shell_integration.zsh

# Re-source
source ~/.iterm2_shell_integration.zsh
source ~/.zshrc

# Check for conflicts
echo $PROMPT_COMMAND  # bash
echo $precmd_functions  # zsh
```

### Auto-restart not working
```bash
# Check if script is running
ps aux | grep auto_restart_monitor

# Check script errors
cat ~/Library/Logs/iTerm2/python_scripts.log
```

## 📚 Documentation Links

- **Full README**: [ops/scripts/iterm2/README.md](./README.md)
- **Quick Reference**: [ops/scripts/iterm2/QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- **iTerm2 Docs**: https://iterm2.com/documentation.html
- **Python API**: https://iterm2.com/python-api/
- **Dynamic Profiles**: https://iterm2.com/documentation-dynamic-profiles.html
- **Shell Integration**: https://iterm2.com/documentation-shell-integration.html
- **AI Chat**: https://iterm2.com/documentation-ai-chat.html

## 🎓 Learning Resources

### Tutorials
1. **Basic Usage**: Start with "FoKS Intelligence - Backend" profile
2. **Splits & Tabs**: Practice with `⌘D` and `⌘T`
3. **Triggers**: Watch for colored highlights in logs
4. **Shell Integration**: Use `⌘⇧↑/↓` to navigate marks
5. **Python API**: Run `automation_launcher` to see workspace creation

### Practice Workflows
1. Start both backends and monitor logs
2. Run NFA batch with visual monitoring
3. Use AI Chat to explain command output
4. Create custom profile for your workflow
5. Write Python script to automate window layouts

## 🔄 Updates

### Check for Updates
```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence
git pull origin main
```

### Re-install Profiles
```bash
bash ops/scripts/iterm2/install.sh
```

### Update Python Scripts
```bash
cp ops/scripts/iterm2/*.py \
   ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch/
```

---

## ✨ Summary

You now have a **complete iTerm2 automation ecosystem** with:

✅ **11 optimized profiles** for every automation task  
✅ **4 Python scripts** for workspace automation  
✅ **Smart triggers** for error/success highlighting  
✅ **Shell integration** for command tracking  
✅ **AI assistance** for debugging  
✅ **Auto-restart** for crash recovery  
✅ **Status monitoring** in status bar  
✅ **Complete documentation** and quick reference

**Next Steps**:
1. Run `install.sh` to complete setup
2. Restart iTerm2
3. Launch workspace with `automation_launcher`
4. Start coding with optimized terminal workflows!

---

**Created**: December 15, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅
