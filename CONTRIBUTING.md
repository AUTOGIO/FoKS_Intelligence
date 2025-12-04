# Contributing to FoKS Intelligence (AUTOGIO)

Thanks for your interest in contributing! This project powers local automation on Apple Silicon and is designed to be **safe, structured, and production‑grade**.

- Backend: FastAPI + Pydantic + SQLAlchemy (async)  
- Ops: Shell + launchd + iTerm2 + Shortcuts + n8n / Node‑RED  
- Models: LM Studio (local LLMs, OpenAI‑compatible API)  
- External automation: FBP backend (in `/Users/<you>/Documents/FBP_Backend`)

Please read this document before opening PRs.

---

## 1. Ground Rules

- **Do not change business logic** unless:
  - Fixing path/config inconsistencies,
  - Fixing broken imports, tests or type errors,
  - Aligning with the documented architecture.
- **Respect the layering**:
  - Router → Service → Module/Core → External (DB, LM Studio, macOS).
- **Never commit secrets**:
  - No real credentials, tokens, or personal data.
  - `.env`, `*.env`, local DBs and logs must remain git‑ignored.
- **Prefer local & offline first**:
  - LM Studio over cloud APIs,
  - Local scripts over external webhooks, unless explicitly required.

---

## 2. Repository Layout (FoKS)

```text
FoKS_Intelligence/
├── backend/          # FastAPI application (core logic)
│   ├── app/
│   └── tests/
├── docs/             # Architecture, monitoring, deployment, etc.
├── ops/              # Ops, watchdogs, launchd, iTerm, Shortcuts, flows
├── scripts/          # Helper scripts (bootstrap, deploy, backups)
├── examples/         # Minimal usage examples
├── logs/             # Runtime logs (ignored by git)
└── README.md
```

If you add new modules, keep them consistent with this layout and with `docs/ARCHITECTURE.md`.

---

## 3. Development Environment

### 3.1. Backend (FoKS)

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

Or use the Ops script:

```bash
cd FoKS_Intelligence
bash ops/scripts/foks_boot.sh
```

### 3.2. FBP Backend (Optional)

The FBP backend lives outside this repo (e.g. `~/Documents/FBP_Backend`).  
Follow its own `README.md` and `PROJECT_FULL_REPORT.md`.

---

## 4. Coding Standards

### 4.1. Python

- Python 3.11+
- Full type hints (avoid `Any` when possible).
- Pydantic models for request/response validation.
- Async‑first (use `async`/`await`, `httpx`, async SQLAlchemy).
- Follow existing patterns in:
  - `backend/app/routers/*`
  - `backend/app/services/*`
  - `backend/app/utils/*`

Formatting & linting (from `backend/`):

```bash
ruff check .
ruff format .
pytest
```

### 4.2. Shell (Ops)

- `#!/usr/bin/env bash` + `set -euo pipefail`.
- Derive `PROJECT_ROOT` from `SCRIPT_DIR` (no hard‑coded absolute paths):

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
```

- Use `$HOME` instead of `/Users/<name>` when you really need a home path.
- Log to `ops/logs/` with clear timestamps and levels (`INFO`, `WARN`, `ERROR`).

---

## 5. Tests

From `backend/`:

```bash
pytest
pytest -q          # quiet
pytest -k lmstudio # subset
```

All new code should have at least basic test coverage. Prefer:

- **Unit tests** for pure functions / services.
- **Integration tests** for routers and LM Studio / FBP integration (mock when needed).

---

## 6. Documentation

- Keep `docs/` in sync with code changes.
- If you change behavior in:
  - `ops/` → update `docs/FoKS_Ops_Handbook.md` and/or `docs/FoKS_DevOps_QuickStart.md`.
  - Monitoring or metrics → update `docs/MONITORING.md` and `docs/FoKS_Monitoring_Guide.md`.
- Add entries to `CHANGELOG.md` (Keep a Changelog style):
  - Under `[Unreleased]`, group bullets into `Added`, `Changed`, `Fixed`, etc.

---

## 7. Git & Branching

- Main branch: `main`.
- Prefer feature branches:
  - `feature/<short-name>`
  - `fix/<issue-or-bug>`
  - `ops/<ops-change>`
- Commit messages:
  - Use present tense: `Add LM Studio watcher`, `Fix ops watchdog logging`.
  - Reference scope where helpful: `ops: add FoKS watchdog`, `backend: fix lmstudio client retry`.

Before opening a PR:

1. Run tests (`pytest`).
2. Run lint/format (`ruff check .`, `ruff format .`).
3. Ensure no secrets or local data are staged.
4. Update `README.md` / `docs/` / `CHANGELOG.md` if needed.

---

## 8. Reporting Bugs & Requesting Features

- **Bugs**: Include steps to reproduce, expected vs actual behavior, and relevant logs (scrubbed).
- **Features**: Explain the use case, not just the desired endpoint or script.
- Keep in mind:
  - This project optimizes for **local, private, Apple Silicon** use.
  - Anything that breaks this principle needs strong justification.

---

## 9. Code of Conduct

By participating in this project, you agree to abide by the
[Code of Conduct](CODE_OF_CONDUCT.md).


