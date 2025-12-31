# FoKS Automation Terminal Suite
## Professional User Guide

**Version:** 1.0.0  
**Published:** 15 December 2025  
**Audience:** FoKS automation engineers, DevOps operators, QA analysts

---

## 1. Introduction
The FoKS Automation Terminal Suite delivers a curated set of iTerm2 profiles, Python automation scripts, and shell enhancements designed to orchestrate the FoKS/FBP automation stack. This guide describes how to activate, operate, and customize the environment with practical, real-world examples.

---

## 2. Prerequisites Checklist
| Requirement | Minimum Version | Verification Command |
|-------------|-----------------|----------------------|
| macOS | 14.0 Sonoma | `sw_vers` |
| iTerm2 | 3.5+ | iTerm2 → About iTerm2 |
| Homebrew | 4.0+ | `brew --version` |
| Python runtime (iTerm2) | Provided by iTerm2 | iTerm2 → Scripts → Manage |
| FoKS repository | Latest main | `git -C FoKS_Intelligence status` |
| FBP repository | Latest main | `git -C FBP_Backend status` |

> **Quick Install**: `bash ops/scripts/iterm2/install.sh`

---

## 3. Installation & Activation
### 3.1 Automated Setup (Recommended)
```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence
bash ops/scripts/iterm2/install.sh
```
**Result:**
- Dynamic profiles loaded into `~/Library/Application Support/iTerm2/DynamicProfiles/`
- Python automation scripts placed in `~/Library/Application Support/iTerm2/Scripts/AutoLaunch/`
- Shell integration and helper aliases appended to `~/.zshrc`

### 3.2 Manual Activation (Summary)
1. Copy JSON profiles into the DynamicProfiles directory.
2. Copy Python scripts into `Scripts/AutoLaunch` (ensure `chmod +x`).
3. Install the iTerm2 Python runtime:
   - iTerm2 → Scripts → Manage → Install Python Runtime
4. Restart iTerm2 or reload the profiles (Settings → Profiles → Other Actions → Reload All Profiles).

---

## 4. Profile Catalog
| Profile | Purpose | Default Badge | Sample Command |
|---------|---------|---------------|----------------|
| FoKS Intelligence — Backend (Prod) | FastAPI backend (port 8000 production; 8001 is dev-only when started explicitly) | `FoKS\n:8000` | `bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/foks_boot.sh` |
| FBP Backend - Socket Server | FBP Playwright service (Unix socket) | `FBP\nUDS` | `bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/fbp_boot.sh` |
| NFA Automation - Batch Runner | End-to-end NFA batch runs | `NFA\nBatch` | `python run_rental_nfa_batch.py` |
| NFA Intelligence - Reporting | Run intelligence service and analyze reports | `NFA\nINTEL` | `curl http://localhost:8000/nfa/intelligence/run` |
| REDESIM - Email Automation | Gmail OAuth and email drafting | `REDESIM\nEmail` | `python -m app.modules.redesim.email_collector` |
| M3 Operations Dashboard | Health status overview | `M3\nOPS` | `bash ops/scripts/m3_system_dashboard.sh` |
| Playwright Browser Console | Visual debugging for Playwright | `🎭\nPW` | `python run_nfa_automation_visual.py` |
| Logs Monitor - Live Tail | Watch FoKS/FBP/NFA log streams | `📜\nLOGS` | `tail -f logs/nfa_history.log` |
| Quick Test Runner | Health and regression checks | `🧪\nTEST` | `curl http://localhost:8000/health | jq` |
| Environment Setup - Auto Config | Run environment autofix | `⚙️\nSETUP` | `bash ops/scripts/foks_env_autofix.sh` |
| API Client - cURL Interactive | REST & socket testing | `🌐\nAPI` | `curl --unix-socket /tmp/fbp.sock http://localhost/socket-health` |

---

## 5. Python Automation Scripts
Located in `~/Library/Application Support/iTerm2/Scripts/AutoLaunch/`.

### 5.1 automation_launcher.py
- Creates a four-tab workspace (layout only, does not auto-start services):
  1. Backend Services (FoKS + FBP split panes)
  2. NFA Automation (batch runner, intelligence monitor, live logs)
  3. Operations (dashboard + tests)
  4. Development (Playwright console + API client)
- **Run:** iTerm2 → Scripts → automation_launcher

### 5.2 status_bar_monitor.py
- Adds “FoKS Monitor” status bar component showing FoKS, FBP, and NFA run counts.
- **Enable:** Settings → Profiles → Session → Status Bar → Add “FoKS Monitor”.

### 5.3 auto_restart_monitor.py
- Watches sessions for crash signatures.
- Attempts restart only while the script is installed, enabled, and running.

### 5.4 ai_error_handler.py
- Detects Python tracebacks or automation failures.
- Offers AI-assisted debugging prompts (automatically copies context to clipboard).

---

## 6. Shell Enhancements
The installer appends to `~/.zshrc` and creates `~/.foks_iterm2_config`.

### 6.1 Key Aliases
```bash
foks-start   # Activate FoKS venv and start backend
fbp-start    # Activate FBP venv and start socket server
nfa-run      # Run rental batch automation
all-health   # Combined FoKS + FBP health check
```

### 6.2 Profile Switches
```bash
foks-backend   # Switch active terminal to FoKS profile
fbp-backend    # Switch active terminal to FBP profile
nfa-batch      # Switch to NFA batch runner profile
```

### 6.3 Badge Updates
```bash
update-badge "FoKS Backend\n$(date +%H:%M)"
```
Automatically invoked via precmd hook when inside Git repositories.

---

## 7. Common Operational Flows
### 7.1 Daily Startup (DevOps Engineer)
1. Launch iTerm2 → Scripts → automation_launcher.
2. Pane 1 (FoKS Backend): `foks-start`
3. Pane 2 (FBP Backend): `fbp-start`
4. Pane 3 (Operations): Monitor dashboard output for ✅/⚠️ alerts.
5. Pane 4 (Logs): `tail -f /Users/dnigga/Downloads/NFA_Outputs/nfa_runs.jsonl`

### 7.2 NFA Regression Run (QA Analyst)
```bash
# Profile: NFA Automation - Batch Runner
python ops/scripts/nfa/nfa_job.py --data-inicial 08/12/2025 --data-final 08/12/2025 --headless

# Observe live progress (automatic highlight triggers)
# Errors appear in red background, successes in green.
```
**Reports:** Generated under `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/reports/`

### 7.3 Investigating Failures (Automation Specialist)
1. Open Logs Monitor profile.
2. When ai_error_handler prompts for help, press “Open AI Chat”.
3. Paste clipboard contents into AI chat window.
4. Apply suggested fix and rerun `Quick Test Runner` profile → option 4 (integration tests).

---

## 8. Monitoring & Alerting
### 8.1 Status Bar
Displays `FoKS`, `FBP`, `NFAs` with ✅/❌ indicators. Update cadence: 5 seconds.

### 8.2 Trigger Colors
| Color | Meaning |
|-------|---------|
| Green text | Success messages (e.g., “Application startup complete”) |
| Red text / Yellow background | Critical errors (Exception, FAILED) |
| Orange text | Warnings (WARNING, ⚠️) |
| Blue text | Informational cues (INFO, processing markers) |

### 8.3 Alerts
- Command completion notifications via shell integration (Edit → Marks and Annotations → Alert on Next Mark).
- Backends restart only while `auto_restart_monitor.py` is installed, enabled, and running.

---

## 9. Troubleshooting
| Symptom | Resolution |
|---------|------------|
| VS Code terminal exits with “Error Code 1” | Confirm `ops/scripts/foks_venv_guard.sh` lacks `set -euo pipefail`. Run `source ~/.zshrc`. |
| iTerm2 scripts fail to run | Install Python runtime: iTerm2 → Scripts → Manage → Install Python Runtime |
| Dynamic profiles missing | Verify JSON: `cat ~/Library/Application\ Support/iTerm2/DynamicProfiles/FoKS_Automation_Profiles.json | jq .` |
| Auto-launch scripts disabled | iTerm2 → Scripts → Manage → Enable AutoLaunch Scripts |
| Shell integration inactive | `curl -L https://iterm2.com/shell_integration/zsh -o ~/.iterm2_shell_integration.zsh` then `source ~/.zshrc` |
| AI prompt not copying | Confirm clipboard access: System Settings → Privacy & Security → Clipboard |

---

## 10. Customization Scenarios
### 10.1 New Profile for LM Studio
```json
{
  "Name": "LM Studio Inference",
  "Guid": "lmstudio-profile-001",
  "Custom Command": "Yes",
  "Command": "cd /Users/dnigga/.lmstudio && lmstudio --serve --port 5100",
  "Badge Text": "LM\nStudio",
  "Tags": ["lmstudio", "ml"],
  "Triggers": [
    {
      "regex": "Server listening on",
      "action": "HighlightTrigger",
      "parameter": "{#00ff00,}"
    }
  ]
}
```

### 10.2 Window Workflow for Obsidian Notes
```python
async def open_obsidian_workspace(connection):
    window = await iterm2.Window.async_create(connection)
    tab = await window.async_create_tab(profile="API Client - cURL Interactive")
    await tab.async_set_title("Obsidian Ops")
    session = tab.current_session
    await session.async_send_text("open -a Obsidian /Users/dnigga/Obsidian/Business\n")
```

### 10.3 Cursor IDE Integration
Add to `~/.foks_iterm2_config`:
```bash
alias cursor-launch="open -a Cursor /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence"
```

---

## 11. Maintenance & Updates
| Task | Frequency | Command |
|------|-----------|---------|
| Pull latest automation assets | Weekly | `git pull` in FoKS_Intelligence |
| Refresh iTerm profiles | After updates | `bash ops/scripts/iterm2/install.sh` |
| Verify Python runtime | Quarterly | iTerm2 → Scripts → Manage |
| Review AI permissions | Quarterly | iTerm2 AI Chat → info button |

---

## 12. Support & Contact
- **Primary Engineer:** dnigga (FoKS Automation Lead)
- **Escalation Path:** FoKS Slack #automation-support → NFA Squad lead → Ops Engineering
- **Issue Tracking:** Create tickets in FoKS Jira under component “Automation/iTerm Suite”.

### When Reporting Issues Include:
1. iTerm2 version (`iTerm2 → About`)
2. Profile name and GUID
3. Reproduction steps (commands or scripts executed)
4. Relevant logs (FoKS, FBP, or NFA output)
5. Screenshots of trigger highlights or status bar indicators

---

## 13. Revision History
| Date | Version | Author | Notes |
|------|---------|--------|-------|
| 2025-12-15 | 1.0.0 | Automation Office | Initial publication |

---

**End of Guide**
