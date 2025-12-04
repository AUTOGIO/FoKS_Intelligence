## FoKS DevOps QuickStart

Short guide to bring FoKS, FBP and LM Studio online on macOS (Apple Silicon).

_Screenshot placeholder_: `![DevOps QuickStart](./images/foks_quickstart.png)`

### 1. Prerequisites

- macOS with Apple Silicon (M3 iMac).
- Python 3.11+ installed.
- LM Studio installed and listening on `http://127.0.0.1:1234`.
- Repositories:
  - FoKS: `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence`
  - FBP: `/Users/dnigga/Documents/FBP_Backend`

### 2. One-Time Setup

```bash
# Ensure FoKS Ops scripts are executable
chmod +x /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/*.sh
chmod +x /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/monitors/*.sh
```

Copy `launchd` plists:

```bash
mkdir -p ~/Library/LaunchAgents ~/Library/Logs/FoKS
cp /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/launchd/*.plist ~/Library/LaunchAgents/
```

Load services:

```bash
launchctl load ~/Library/LaunchAgents/com.foks.bootstrap.plist
launchctl load ~/Library/LaunchAgents/com.foks.watchdog.plist
launchctl load ~/Library/LaunchAgents/com.lmstudio.watch.plist
```

### 3. Starting Services (Manual)

- **FoKS backend**
  - `bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/foks_boot.sh`
- **FBP backend**
  - `bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/fbp_boot.sh`
- **LM Studio watcher**
  - `bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/lmstudio_watch.sh`

### 4. Health Checks

```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence

python3 ops/health/check_foks.py
python3 ops/health/check_fbp.py
python3 ops/health/check_lmstudio.py
```

### 5. Quick Restart Recipes

- **Everything (FoKS, FBP, watchers)**:
  - `bash ops/scripts/kill_all.sh`
  - Then call `foks_boot.sh` and/or `fbp_boot.sh`.
- **LM Studio only**:
  - Restart LM Studio app.
  - Watch logs: `tail -f ops/logs/lmstudio_watch.log`

### 6. iTerm2 Profiles

- Copy JSON files from `ops/iterm/` into iTerm2 Dynamic Profiles folder:
  - `FoKS_Ops_Terminal.json`
  - `FBP_Ops_Terminal.json`
  - `LMStudio_ModelManager.json`
- Then open iTerm2 and select the corresponding profile:
  - **FoKS Ops Terminal** – auto `cd` + venv + `PYTHONPATH`.
  - **FBP Ops Terminal** – auto `cd` + venv + log tail.
  - **LM Studio Model Manager** – live `/v1/models` refresh every 5s.

### 7. Troubleshooting Fast Path

- If **FoKS** is down:
  - Run: `python3 ops/health/check_foks.py`
  - If failing: `bash ops/scripts/kill_all.sh && bash ops/scripts/foks_boot.sh`
- If **FBP** shows Google errors:
  - Run: `python3 ops/health/check_fbp.py`
  - Install deps inside FBP venv: `pip install -r requirements.txt`.
- If **LM Studio** is offline:
  - Start LM Studio app and check: `python3 ops/health/check_lmstudio.py`.


