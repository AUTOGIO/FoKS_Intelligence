# foks-intelligence_autogio

FoKS Intelligence é o núcleo local que liga o Atalho “FoKS Intelligence”, LM Studio, Task Runner e demais automações Apple Silicon. Este repositório segue o padrão `project-name_autogio`, mantendo o backend FastAPI validado pelos documentos mestres.

---

## 🔹 Visão geral

- **Objetivo**: orquestrar automações locais com contratos n8n/Node-RED, mantendo dados 100% na máquina M3.
- **Stack**: FastAPI + Pydantic + SQLAlchemy (async), Playwright opcional, LM Studio, scripts Shell.
- **Hardware alvo**: Apple Silicon M3 (16GB, 16-core Neural Engine). 
- **Caminho base**: `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence`.
- **Autoridade**: seguir `/Volumes/MICRO/🦑_PROJECTS/REDESIM/.../README.md` e `/Users/dnigga/Documents/FBP_Backend/PROJECT_FULL_REPORT.md`.

---

## 🔹 Arquitetura protegida

```
backend/app
├── routers/      # Endpoints (HTTP fino, validação inicial)
├── services/     # Orquestrações + integrações externas
├── models/       # Pydantic/ORM
├── middleware/   # Cross-cutting (auth, monitoring, rate limit)
├── utils/        # Helpers reutilizáveis
└── config/       # Settings e env bindings
```

- Router → Service → Module/Core sempre respeitado.
- Logs centralizados em `/logs` (limpo por `.gitignore`, com `.gitkeep`).
- Dados transitórios ficam em `backend/data/`.

---

## 🔹 Estrutura normalizada

```
/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence
├── backend/
│   ├── app/...
│   ├── data/.gitkeep
│   ├── requirements.txt
│   └── tests/
├── docs/ (arquitetura, DR, checklists)
├── scripts/ (start_backend, control center, deploy, backups)
├── examples/ (usos do SDK)
├── logs/.gitkeep
├── README.md
└── QUICK_START.md
```

---

## 🔹 Setup rápido (Apple Silicon M3)

```bash
# 1. Garantir permissões
chmod +x /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/scripts/*.sh

# 2. Provisionar backend
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend
python3 -m venv .venv_foks
source .venv_foks/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Subir FastAPI protegido
/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/scripts/start_backend.sh
```

Testes rápidos:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"Olá FoKS!", "source":"manual_curl"}'
```

---

## 🔹 Automação & integrações

- **Atalho FoKS**: segue o fluxo `Solicitar Entrada` → construir JSON → POST `/chat` → notificar usuário (detalhado em `docs/SHORTCUT_SETUP.md`).
- **n8n / Node-RED**: respostas seguem modelos em `backend/app/models.py` e podem ser consumidas como nodes HTTP sigilosos.
- **LM Studio**: configurado via `LMStudioClient`, usando modelos MLX/ANE da pasta `/Volumes/MICRO/LM_STUDIO_MODELS`.
- **Task Runner**: `/tasks/run` autoriza `open_url`, `run_script`, `say`, mantendo logs e métricas em `docs/MONITORING.md`.

---

## 🔹 Testes, observabilidade e hardening

- Testes `pytest` + cobertura HTML (`backend/tests/*`). Artefatos de cobertura e DB locais estão ignorados.
- Middlewares de auth, rate-limit e monitoramento ficam em `backend/app/middleware`.
- Scripts em `scripts/` fornecem:
  - `start_backend.sh` – provisiona venv e roda uvicorn.
  - `foks_control_center.sh` – dashboard interativo com métricas (`top`) e log tail.
  - `backup_*` – snapshots de banco/logs.

---

## 🔹 Próximas evoluções sugeridas

- Nova task n8n → service dedicado no `task_runner`.
- Conectar Playwright vision ao endpoint `/vision/analyze`.
- Automatizar benchmarks MLX/ANE (ver `docs/M3_OPTIMIZATION.md`).
- Publicar coleção de fluxos Node-RED pronta para `foks-intelligence_autogio`.

---

## 🔹 Contato & manutenção

- Sempre validar camadas antes de adicionar arquivos.
- Usar caminhos absolutos nos exemplos e scripts.
- Ao atualizar, descreva mudanças em `CHANGELOG.md` e mantenha `docs/` sincronizado.
