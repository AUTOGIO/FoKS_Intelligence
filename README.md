# FoKS Intelligence (AUTOGIO)

FoKS Intelligence is the **local automation brain** that connects the FoKS macOS Shortcut, LM Studio, the Task Runner and other Apple‑Silicon‑first workflows.  
It follows the `project-name_autogio` convention and implements a protected FastAPI backend validated against the master architecture documents.

- **Goal**: orchestrate local automations with n8n / Node‑RED‑friendly contracts, keeping data 100% on your M‑series Mac.  
- **Stack**: FastAPI + Pydantic + SQLAlchemy (async), optional Playwright, LM Studio, shell / ops scripts.  
- **Target hardware**: Apple Silicon (M3), local‑only by default.  
- **Authoritative docs**:  
  - `/Volumes/MICRO/🦑_PROJECTS/REDESIM/REDESIM_Email_Extractor/.../README.md`  
  - `/Users/dnigga/Documents/FBP_Backend/PROJECT_FULL_REPORT.md`

> Nota: README em estilo open‑source, mas o código e comentários seguem os padrões arquiteturais definidos nos documentos mestres acima.

---

## Overview & Architecture

High‑level components:

- **FoKS Backend** – FastAPI service under `backend/app/`, exposes `/chat`, `/vision/analyze`, `/tasks`, `/conversations`, `/system`, `/metrics`.  
- **LM Studio** – local LLM server (OpenAI‑compatible API) on `http://127.0.0.1:1234`.  
- **Task Runner** – macOS automation layer (open URL, run scripts, TTS, notifications, clipboard, screenshots, apps).  
- **FBP Backend** – external automation backend (`~/Documents/FBP_Backend`) used for NFA/REDESIM flows. FoKS now connects via UNIX socket `/tmp/fbp.sock` by default; set `FBP_TRANSPORT=port` and `FBP_PORT=<port>` for TCP debugging.
- **Ops Layer** – scripts, watchdogs, launchd, Shortcuts, Node‑RED and n8n flows in `ops/`.

### Mermaid Diagram (FoKS + FBP + LM Studio + macOS)

```mermaid
graph TD
    U[User] --> S[FoKS macOS Shortcut]
    U --> N8[n8n / Node-RED]

    S -->|HTTP POST /chat| G[FoKS FastAPI Backend]
    S -.->|/vision/analyze| G
    S -.->|/tasks/run| G

    N8 -->|HTTP nodes| G

    G -->|LMStudioClient| L[LM Studio<br/>localhost:1234]
    G -->|TaskRunner| T[macOS Automation<br/>(open, say, scripts,...)]
    G -->|Webhooks / APIs| F[FBP Backend<br/>~/Documents/FBP_Backend]

    G -->|logging_utils| LG[(logs/app.log)]

    subgraph FoKS Repository
        G
        LG
    end
```

For more details, see:

- `docs/ARCHITECTURE.md`
- `docs/MONITORING.md`
- `docs/FoKS_Ops_Handbook.md`

---

## Project Structure

```text
FoKS_Intelligence/
├── backend/
│   ├── app/
│   │   ├── routers/       # HTTP endpoints (thin)
│   │   ├── services/      # Business logic & integrations
│   │   ├── models/        # Pydantic & ORM models
│   │   ├── middleware/    # auth, monitoring, rate limiting, M3 tuning
│   │   ├── utils/         # shared helpers
│   │   └── config/        # settings & env bindings
│   └── tests/             # pytest suite
├── ops/                   # iTerm, launchd, watchdogs, health, flows
├── docs/                  # architecture, monitoring, deployment, etc.
├── scripts/               # bootstrap, deploy, backups, helpers
├── examples/              # example Python clients / flows
├── logs/                  # runtime logs (git-ignored)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
└── CODE_OF_CONDUCT.md
```

Key architectural rule: **Router → Service → Module/Core → External**.  
Routers must stay thin; business logic belongs in services and lower layers.

---

## Quick Start (Local, Apple Silicon)

### 1. Backend (FoKS)

```bash
cd FoKS_Intelligence/backend
python3 -m venv .venv_foks
source .venv_foks/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or via the Ops script:

```bash
cd FoKS_Intelligence
chmod +x ops/scripts/*.sh ops/monitors/*.sh
bash ops/scripts/foks_boot.sh
```

Quick smoke tests:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá FoKS!", "source": "manual_curl"}'
```

### 2. LM Studio

1. Start LM Studio and expose the HTTP server (OpenAI‑compatible) on port `1234`.  
2. Configure the model you want to use.  
3. Use the LM Studio health script:

```bash
cd FoKS_Intelligence
python3 ops/health/check_lmstudio.py
```

### 3. FBP Backend (Optional but Recommended)

The FBP backend repository lives separately (e.g. `~/Documents/FBP_Backend`).  
Follow its own `README.md` and `PROJECT_FULL_REPORT.md` to set it up, then use:

```bash
cd FoKS_Intelligence
bash ops/scripts/fbp_boot.sh
```

---

## Development Setup

### Testing Requirements

To run FoKS test suite:

```bash
pip install pytest pytest-asyncio

pytest -q
```

---

## Ops & Monitoring

The `ops/` folder contains the **FoKS Ops Environment**:

- `ops/scripts/`
  - `foks_boot.sh` – start FoKS backend with venv + PID management.
  - `fbp_boot.sh` – start FBP backend (if present).
  - `lmstudio_watch.sh` – continuous LM Studio availability checks.
  - `kill_all.sh` – stop FoKS, FBP, watchers and clear stale PIDs.
- `ops/health/`
  - `check_foks.py` – checks `/health`, `/system/info`, `/metrics`.
  - `check_fbp.py` – robust health check with Google/Gmail dependency hints.
  - `check_lmstudio.py` – verifies `/v1/models` and streaming support.
- `ops/monitors/`
  - `watchdog_foks.sh` – restarts FoKS on repeated failures or high CPU.
  - `watchdog_fbp.sh` – analogous watchdog for FBP, with dependency hints.
  - `watchdog_lmstudio.sh` – macOS notifications when LM Studio goes offline/online.
  - `system_dashboard.sh` – snapshot of CPU, RAM, GPU/ANE hints, PIDs, LM Studio model, FBP request rate.
- `ops/iterm/`
  - Dynamic profiles for FoKS Ops, FBP Ops, and LM Studio model management.
- `ops/shortcuts/`
  - JSON blueprints for macOS Shortcuts (restart, health report, run task).
- `ops/nodered/` and `ops/n8n/`
  - Example flows/workflows integrating FoKS tasks, LM Studio and FBP.
- `ops/launchd/`
  - `launchd` plists to start FoKS + watchdogs at login.

See:

- `docs/FoKS_Ops_Handbook.md`
- `docs/FoKS_DevOps_QuickStart.md`
- `docs/FoKS_Monitoring_Guide.md`

---

## Testing

From `backend/`:

```bash
pytest
pytest -q                 # modo silencioso
pytest -k lmstudio        # subconjunto
```

Coverage artefacts, local DBs e logs são ignorados por `.gitignore`.  
Veja também `docs/PRODUCTION_CHECKLIST.md` e `docs/PRODUCTION_90_PERCENT.md` para orientações de hardening.

---

## Automation Integrations

- **macOS Shortcuts**  
  - FoKS Shortcut → POST para `/chat`, `/vision/analyze`, `/tasks/run` ou `/conversations`.  
  - Detalhes em `docs/SHORTCUT_SETUP.md` e `ops/shortcuts/*.shortcut.json`.

- **n8n / Node‑RED**  
  - Use nodes HTTP apontando para:
    - `POST http://127.0.0.1:8000/chat`
    - `POST http://127.0.0.1:8000/tasks`
    - `GET  http://127.0.0.1:8000/conversations`
    - `GET  http://127.0.0.1:8000/metrics`
    - `GET  http://127.0.0.1:8000/system/info`
    - `GET  http://127.0.0.1:8000/health`  
  - Exemplos:
    - Node‑RED: `ops/nodered/*.json`
    - n8n: `ops/n8n/*.json`

- **FBP Backend**  
  - Exposto via endpoints HTTP próprios (ver `FBP_Backend/docs/`).
  - Pode ser orquestrado a partir do FoKS (via services) ou diretamente por n8n / Node‑RED.

---

## Contributing & Governance

- Contribution guidelines: see [`CONTRIBUTING.md`](CONTRIBUTING.md)  
- Security policy: see [`SECURITY.md`](SECURITY.md)  
- Code of Conduct: see [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)  
- Changelog: see [`CHANGELOG.md`](CHANGELOG.md)

When proposing changes:

1. Respect the **Router → Service → Module/Core** layering.
2. Prefer small, incremental PRs.
3. Keep `docs/` and `ops/` in sync with behavior changes.
4. Do not include secrets, local DBs, LM Studio models or venvs in commits.

---

## GitHub & AUTOGIO

This repository is intended to be published under the GitHub repository `dnigga/AUTOGIO`.

High‑level steps (to be run manually on your machine):

```bash
cd FoKS_Intelligence

# Initialize repo if needed
git init

# Ensure ignore rules are correct
cat .gitignore

# Connect to AUTOGIO (HTTPS)
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/dnigga/AUTOGIO.git

# Stage and commit
git add .
git commit -m "FoKS + FBP + Ops unified system — Initial public release"

# Push main branch
git branch -M main
git push -u origin main
```

> Antes de fazer o push público, revise se não há segredos, dados sensíveis ou caminhos muito específicos da máquina que deveriam ser movidos para variáveis de ambiente ou documentação.

