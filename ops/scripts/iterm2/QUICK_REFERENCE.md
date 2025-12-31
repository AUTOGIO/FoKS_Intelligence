# FoKS iTerm2 Automation - Quick Reference

## 🚀 Installation

```bash
bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/iterm2/install.sh
```

## 📋 Available Profiles

| Profile | Shortcut | Purpose |
|---------|----------|---------|
| FoKS Intelligence — Backend (Prod) | `⌘T` → select | FoKS FastAPI backend on port 8000 (dev-only port 8001 when started explicitly) |
| FBP Backend - Socket Server | `⌘T` → select | FBP Unix socket server (`/tmp/fbp.sock`) |
| NFA Automation - Batch Runner | `⌘T` → select | NFA batch processing |
| NFA Intelligence - Reporting | `⌘T` → select | Intelligence service |
| REDESIM - Email Automation | `⌘T` → select | Gmail integration |
| M3 Operations Dashboard | `⌘T` → select | System monitoring |
| Playwright Browser Console | `⌘T` → select | Browser automation |
| Logs Monitor - Live Tail | `⌘T` → select | Log monitoring |
| Quick Test Runner | `⌘T` → select | Health checks |
| API Client - cURL Interactive | `⌘T` → select | API testing |

## 🐍 Python API Scripts

### automation_launcher.py
Creates full workspace layout with 4 tabs (layout only, does not auto-start services)

**Run**: `iTerm2 → Scripts → automation_launcher`

### status_bar_monitor.py
Real-time status in status bar

**Enable**: `Settings → Profiles → Session → Status Bar → Add "FoKS Monitor"`

### auto_restart_monitor.py
Attempts to restart backends only while the script is running and AutoLaunch scripts are enabled

### ai_error_handler.py
AI-assisted debugging

**Runs at session start when placed in AutoLaunch and AutoLaunch scripts are enabled**

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘T` | New tab with profile selector |
| `⌘D` | Split pane vertically |
| `⌘⇧D` | Split pane horizontally |
| `⌘⇧↑/↓` | Navigate marks |
| `⌘⇧;` | Command history |
| `⌘⌥/` | Recent directories |
| `⌘⇧A` | Select output of last command |
| `⌘⌥A` | Alert on next mark |
| `⌥⌘E` | Explain output with AI |

## 🎨 Trigger Highlights

| Pattern | Color | Meaning |
|---------|-------|---------|
| ✅ SUCCESS OK | 🟢 Green | Success |
| ❌ ERROR FAILED | 🔴 Red | Error |
| ⚠️ WARNING | 🟠 Orange | Warning |
| INFO | 🔵 Blue | Info |
| HTTP/1.1 2XX | 🟢 Green | HTTP Success |
| HTTP/1.1 4XX/5XX | 🔴 Red | HTTP Error |

## 🔧 Quick Commands

```bash
# Source FoKS configuration
source ~/.foks_iterm2_config

# Start backends (manual start)
foks-start          # FoKS backend on port 8000
fbp-start           # FBP backend
nfa-run             # NFA batch

# Health checks
foks-health         # FoKS only
fbp-health          # FBP only
all-health          # All services

# Profile switching
foks-backend        # Switch to FoKS profile
fbp-backend         # Switch to FBP profile
nfa-batch           # Switch to NFA profile

# Badge update
update-badge "TEXT\\nLINE2"
```

## 🌐 API Endpoints

### FoKS (HTTP)
```bash
# Health (production)
curl http://localhost:8000/health | jq

# Run task (prod)
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{"type":"nfa","args":{}}'

# NFA Intelligence (prod)
curl -X POST http://localhost:8000/nfa/intelligence/run \
  -H "Content-Type: application/json" \
  -d @payload.json
```
> Production port is 8000. Port 8001 is dev-only and must be started explicitly when needed.

### FBP (Unix Socket)
```bash
# Health
curl --unix-socket /tmp/fbp.sock \
  http://localhost/socket-health | jq

# NFA Create
curl --unix-socket /tmp/fbp.sock \
  -X POST http://localhost/api/nfa/create \
  -H "Content-Type: application/json" \
  -d @nfa_payload.json

# NFA Batch
curl --unix-socket /tmp/fbp.sock \
  -X POST http://localhost/api/nfa/batch \
  -H "Content-Type: application/json" \
  -d @batch_payload.json
```

## 🧪 Testing

```bash
# Backend health (prod)
curl -s http://localhost:8000/health | jq .
curl -s --unix-socket /tmp/fbp.sock http://localhost/socket-health | jq .

# NFA self-test
bash /Users/dnigga/Documents/FBP_Backend/ops/nfa_self_test.sh

# Integration tests
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend
pytest tests/ -v
```

## 📊 Monitoring

### Live Logs
```bash
# FoKS logs
tail -f /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/logs/*.log

# FBP logs
tail -f /Users/dnigga/Documents/FBP_Backend/logs/*.log

# NFA runs
tail -f /Users/dnigga/Downloads/NFA_Outputs/nfa_runs.jsonl

# NFA history
tail -f /Users/dnigga/Documents/FBP_Backend/logs/nfa_history.log
```

### System Dashboard
```bash
bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/m3_system_dashboard.sh
```

## 🐛 Debugging

### Playwright
```bash
# Codegen for selectors
playwright codegen https://www4.sefaz.pb.gov.br/atf/

# Visual debugging
python run_nfa_automation_visual.py

# Screenshots
ls -la /Users/dnigga/Documents/FBP_Backend/output/nfa/screenshots/
```

### AI-Assisted
1. Error detected → AI prompt copied to clipboard
2. `⌥⌘E` → Explain output with AI
3. Window → AI Chat → Paste prompt

## 📁 Important Paths

```bash
# Projects
/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence
/Users/dnigga/Documents/FBP_Backend

# Virtual Environments
/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/.venv_foks
~/.venvs/fbp

# Outputs
/Users/dnigga/Downloads/NFA_Outputs
/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/reports

# iTerm2 Config
~/Library/Application Support/iTerm2/DynamicProfiles/
~/Library/Application Support/iTerm2/Scripts/AutoLaunch/

# Shell Integration
~/.iterm2_shell_integration.zsh
~/.foks_iterm2_config
```

## 🔄 Workspace Layouts

### Full Automation Workspace
```
Tab 1: Backend Services
├─ FoKS Backend (top)
└─ FBP Backend (bottom)

Tab 2: NFA Automation
├─ Batch Runner (left)
├─ Intelligence (top right)
└─ Logs (bottom right)

Tab 3: Operations
├─ M3 Dashboard (left)
└─ Test Runner (right)

Tab 4: Development
├─ Playwright Console (left)
└─ API Client (right)
```

**Launch**: `iTerm2 → Scripts → automation_launcher`

## 🆘 Troubleshooting

### Profiles not loading
```bash
# Validate JSON
cat ~/Library/Application\ Support/iTerm2/DynamicProfiles/FoKS_Automation_Profiles.json | jq .

# Check Console.app for errors
open -a Console
# Filter: iTerm2
```

### Python scripts not running
```bash
# Check Python runtime
ls ~/Library/Application\ Support/iTerm2/iterm2env/versions/*/bin/python3

# Reinstall
# iTerm2 → Scripts → Manage → Install Python Runtime
```

### Shell integration issues
```bash
# Re-install
curl -L https://iterm2.com/shell_integration/zsh \
  -o ~/.iterm2_shell_integration.zsh

# Re-source
source ~/.zshrc
```

## 📚 Resources

- **Full Documentation**: `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/iterm2/README.md`
- **iTerm2 Docs**: https://iterm2.com/documentation.html
- **Python API**: https://iterm2.com/python-api/
- **Dynamic Profiles**: https://iterm2.com/documentation-dynamic-profiles.html

## 🎯 Common Workflows

### Start Development Session
```bash
1. ⌘T → "FoKS Intelligence — Backend (Prod)"
2. ⌘D → Split vertical
3. In right pane: fbp-start
4. In left pane: foks-start
5. ⌘T → "Logs Monitor - Live Tail"
6. Select option 3 (NFA Batch Runs)
```

### Run NFA Batch
```bash
1. ⌘T → "NFA Automation - Batch Runner"
2. python run_rental_nfa_batch.py
3. ⌘D → Split
4. tail -f /Users/dnigga/Downloads/NFA_Outputs/nfa_runs.jsonl
```

### Debug Error
```bash
1. If ai_error_handler is installed and running, it copies an AI prompt to the clipboard
2. Open AI Chat manually
3. Paste clipboard → Get suggestion
4. Apply fix
5. Test with Quick Test Runner profile
```

---

**Last Updated**: December 15, 2025  
**Version**: 1.0.0
