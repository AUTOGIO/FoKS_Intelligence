## FoKS Ops Handbook

> Central guide for operating FoKS Intelligence, FBP backend and LM Studio on macOS (Apple Silicon).

### 1. Overview

- **FoKS backend**: FastAPI service under `backend/` in `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence`.
- **FBP backend**: Automation backend in `/Users/dnigga/Documents/FBP_Backend`.
- **LM Studio**: Local LLM server at `http://127.0.0.1:1234`.
- **Ops layer**: All operational tooling lives under `ops/`.

_Screenshot placeholder_: `![FoKS Ops Overview](./images/foks_ops_overview.png)`

### 2. Directory Structure (Ops)

- `ops/scripts/` – startup/shutdown/watch scripts (`foks_boot.sh`, `fbp_boot.sh`, `lmstudio_watch.sh`, `kill_all.sh`).
- `ops/health/` – Python health checkers (`check_foks.py`, `check_fbp.py`, `check_lmstudio.py`).
- `ops/monitors/` – watchdogs and `system_dashboard.sh`.
- `ops/iterm/` – iTerm2 Dynamic Profiles JSON.
- `ops/shortcuts/` – macOS Shortcuts JSON blueprints.
- `ops/nodered/`, `ops/n8n/` – sample flows/workflows.
- `ops/launchd/` – `launchd` plists for macOS startup.
- `ops/logs/` – runtime logs and PID files.

### 3. Normal Operations

- **Start FoKS only**
  - `bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/foks_boot.sh`
- **Start FBP only**
  - `bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/fbp_boot.sh`
- **Start LM Studio watcher**
  - `bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/lmstudio_watch.sh`

_Screenshot placeholder_: `![FoKS Control iTerm](./images/foks_ops_iterm.png)`

### 4. Restart Procedures

- **Safe full restart (FoKS + FBP + watchers)**:
  - `bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/kill_all.sh`
  - Then re-run the desired `*_boot.sh` scripts.
- **Using macOS Shortcuts**:
  - Import JSON from `ops/shortcuts/`:
    - `FoKS_Restart.shortcut.json`
    - `FBP_Restart.shortcut.json`
    - `FoKS_FBP_LMStudio_Health_Report.shortcut.json`
    - `FoKS_Run_Task.shortcut.json`

### 5. Health-Check Conventions

- **FoKS**: `/health`, `/system/status`, `/metrics` via `ops/health/check_foks.py`.
- **FBP**: `/health` via `ops/health/check_fbp.py` (detects Google/Gmail dependency issues).
- **LM Studio**: `/v1/models` and streaming test via `ops/health/check_lmstudio.py`.

_Screenshot placeholder_: `![Health Dashboard](./images/foks_health_dashboard.png)`

### 6. PID & Logging Conventions

- PID files stored under `ops/logs/`:
  - `foks_backend.pid`, `fbp_backend.pid`
  - `lmstudio_watch.pid`
  - `watchdog_foks.pid`, `watchdog_fbp.pid`, `watchdog_lmstudio.pid`
- Log files examples:
  - `foks_boot.log`, `foks_backend.out`
  - `fbp_boot.log`, `fbp_backend.out`
  - `lmstudio_watch.log`, `watchdog_*.log`, `system_dashboard.log`

### 7. Troubleshooting Matrix

| Symptom                                  | Check / Command                                                                                          | Expected Result / Fix                                                                                     |
|------------------------------------------|----------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| FoKS not responding on port 8000        | `python3 ops/health/check_foks.py`                                                                       | If FAIL, run `kill_all.sh` then `foks_boot.sh`. Check `ops/logs/foks_boot.log`.                          |
| FBP /health failing with Google errors  | `python3 ops/health/check_fbp.py`                                                                        | If Google hint appears, activate FBP venv and run `pip install -r requirements.txt`.                      |
| LM Studio offline                        | `python3 ops/health/check_lmstudio.py`                                                                   | Start LM Studio app or check `lmstudio_watch.log`.                                                        |
| High CPU on FoKS/FBP                     | View `watchdog_foks.log` / `watchdog_fbp.log`                                                            | Watchdog will auto-restart if CPU > 95% for 30s; if looping, inspect traffic/load.                        |
| Launchd services not starting           | `launchctl list | grep foks`                                                                            | Ensure `.plist` files are copied to `~/Library/LaunchAgents` and permissions (`chmod +x` on shell files). |


