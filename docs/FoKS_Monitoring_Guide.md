## FoKS Monitoring Guide

How to monitor FoKS, FBP and LM Studio health and performance from the Ops layer.

_Screenshot placeholder_: `![Monitoring Overview](./images/foks_monitoring_overview.png)`

### 1. Core Monitoring Tools

- **Health scripts** (Python):
  - `ops/health/check_foks.py`
  - `ops/health/check_fbp.py`
  - `ops/health/check_lmstudio.py`
- **Watchdogs** (shell):
  - `ops/monitors/watchdog_foks.sh`
  - `ops/monitors/watchdog_fbp.sh`
  - `ops/monitors/watchdog_lmstudio.sh`
- **System dashboard**:
  - `ops/monitors/system_dashboard.sh`

### 2. Running Health Checks

```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence

python3 ops/health/check_foks.py
python3 ops/health/check_fbp.py
python3 ops/health/check_lmstudio.py
```

_Screenshot placeholder_: `![Health Check Output](./images/foks_health_output.png)`

### 3. Watchdog Behaviour

- **FoKS watchdog**
  - Restarts FoKS if:
    - `/health` fails 3 consecutive times.
    - PID file is missing or PID is dead.
    - CPU usage for the FoKS PID is >95% for at least 30 seconds.
  - Logs to `ops/logs/watchdog_foks.log`.

- **FBP watchdog**
  - Similar to FoKS but with extra detection for Google/Gmail dependency errors.
  - Logs hints when `/health` indicates Google-related tracebacks.
  - Logs to `ops/logs/watchdog_fbp.log`.

- **LM Studio watchdog**
  - Does **not** restart LM Studio.
  - Only alerts via macOS notifications when LM Studio goes offline/online.
  - Logs to `ops/logs/watchdog_lmstudio.log`.

### 4. System Dashboard

Run:

```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence
bash ops/monitors/system_dashboard.sh
```

The dashboard prints:

- **CPU usage** (via `top`).
- **RAM usage** (approx via `vm_stat`).
- **GPU / ANE hints** (via `powermetrics` if available; may require `sudo`).
- **Active PIDs** for FoKS and FBP (based on PID files).
- **LM Studio active model** (first model from `/v1/models`).
- **FBP request rate (approx)** based on `ops/logs/fbp_backend.out`.

_Screenshot placeholder_: `![System Dashboard](./images/foks_system_dashboard.png)`

### 5. PID, Logging & Conventions

- **PID files** are stored under `ops/logs/`:
  - `foks_backend.pid`, `fbp_backend.pid`
  - `lmstudio_watch.pid`
  - `watchdog_foks.pid`, `watchdog_fbp.pid`, `watchdog_lmstudio.pid`
- **Log naming**:
  - `*_boot.log` – startup logs.
  - `*_backend.out` – uvicorn/stdout logs.
  - `watchdog_*.log` – watchdog activity.
  - `lmstudio_watch.log` – LM Studio polling.
  - `system_dashboard.log` – dashboard snapshots.

### 6. Troubleshooting Matrix (Monitoring)

| Issue                                   | Where to Look                                      | Likely Cause / Fix                                                                |
|----------------------------------------|----------------------------------------------------|-----------------------------------------------------------------------------------|
| FoKS restarts frequently               | `watchdog_foks.log`, `foks_backend.out`           | High traffic, bad requests or config; inspect logs before disabling watchdog.    |
| FBP restarts frequently                | `watchdog_fbp.log`, `fbp_backend.out`             | Google libs missing or unstable integration; reinstall deps in FBP venv.         |
| LM Studio offline alerts               | `watchdog_lmstudio.log`, LM Studio app status     | LM Studio closed/crashed; reopen app or check port 1234 conflicts.               |
| Dashboard missing GPU data            | Console output from `system_dashboard.sh`         | `powermetrics` not installed or not run with sudo; consider `sudo powermetrics`. |
| PID file exists but service is down   | Corresponding `*_boot.log` and `watchdog_*.log`   | Stale PID cleaned by `kill_all.sh` or watchdog; re-run the appropriate boot script. |


