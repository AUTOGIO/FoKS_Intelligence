# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **FoKS Clients Integration** (2026-01-01):
  - Raycast Extension: Quick access to FoKS Intelligence from Raycast
    - Health check command
    - Quick command (natural language)
    - NFA trigger form
    - Task listing
  - LM Studio Agent: Function calling agent for FoKS Intelligence
    - 100% local AI via LM Studio
    - Function calling support (health_check, trigger_nfa, run_task, chat)
    - Rich CLI interface
    - M3 optimized
  - Both clients located in `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Clients/`

---

## [1.3.0] - Monitoring & System Info

### Added

- Sistema de métricas completo exposto em `/metrics`.
- Middleware de monitoramento automático para todas as requisições HTTP.
- Rastreamento de requests (tempo de resposta, sucesso, erros).
- Rastreamento de tasks (tempo, sucesso por tipo).
- Uptime tracking com formato legível.
- Endpoint `/system/info` com informações detalhadas do sistema.
- Endpoint `/system/metrics` (alias para `/metrics`).
- `app/utils/helpers.py` com utilitários:
  - `generate_request_id()` – IDs únicos de requisição.
  - `encode_base64_image()` – codificação de imagens.
  - `format_response_time()` – formatação de tempos.
  - `safe_get_nested()` – acesso seguro a dicts aninhados.
  - `truncate_text()` – truncamento de texto.
- `scripts/check_health.sh` – script shell para health check completo.

### Changed

- Métricas agora são coletadas automaticamente em todas as requisições.
- Tasks passam a registrar tempo de execução.
- Health check retorna informações mais ricas de estado.

### Tests

- Testes para `MonitoringService` (7 testes).
- Testes para helpers (5 testes).
- Total: 38 testes, todos passando no momento do release.

---

## [1.2.0] - Best Practices Implementation

### Added

- Testes unitários e de integração (26 testes, todos passando).
- Type hints completos em todo o código.
- Docstrings Google‑style em funções públicas.
- Configuração de linting (Ruff) e formatação (Black).
- Type checking com MyPy.
- Hooks de pre‑commit para lint/format.
- Validação robusta de inputs em `app/utils/validators.py`.
- Sanitização de texto para reduzir risco de injection.
- Rate‑limiting middleware (60 req/min por IP).
- Exception handler global.
- Validação de parâmetros de tasks antes de execução.
- Makefile com comandos de desenvolvimento.
- `.gitignore` completo.
- `.env.example` documentado.
- Health check detalhado com dados de sistema.
- Documentação de melhores práticas em `docs/`.
- Logging estruturado com mais contexto.
- Exception tracking com stack traces.

### Changed

- Health check passou a retornar versão, Python version, platform e status de configurações.
- Tasks inválidas retornam HTTP 400 ao invés de falhar durante a execução.
- Compatibilização com Pydantic v2 (`model_dump` vs `dict`).
- Código formatado e lintado de forma consistente.

### Dependencies

- Adicionados: `pytest`, `pytest-asyncio`, `pytest-cov`.
- Adicionados: `black`, `ruff`, `mypy`, `pre-commit`.
- Adicionado: `slowapi` (para futuro rate limiting distribuído).

---

## [1.1.0] - Expansão de Funcionalidades

### Added

- Novas tasks:
  - `notification` – notificações macOS.
  - `get_clipboard` – ler conteúdo do clipboard.
  - `set_clipboard` – definir conteúdo do clipboard.
  - `screenshot` – screenshots (full/window/selection) em base64.
  - `open_app` – abrir aplicativos macOS.
- Vision endpoint aprimorado:
  - Suporte a imagens base64.
  - Extração de metadados (formato, dimensões).
  - Preparado para integração com modelos vision.
- Documentação:
  - Guia completo de integração (n8n, Node‑RED, Python, JS).
  - Exemplos práticos de uso.
  - Scripts de teste para novas funcionalidades.

### Changed

- `TaskRunner` refatorado para arquitetura mais escalável.
- Tratamento de erros mais robusto em todas as tasks.
- Logs mais detalhados para automações.

### Dependencies

- Adicionado `pillow` para processamento de imagens.

---

## [1.0.0] - Versão Inicial

### Added

- Backend FastAPI inicial.
- Integração com LM Studio (API OpenAI‑compatible local).
- Endpoints principais:
  - `/chat/`
  - `/vision/analyze`
  - `/tasks/run`
- Tasks básicas:
  - `say`
  - `open_url`
  - `run_script`
- Sistema de logging.
- Scripts de inicialização.
- Control Center interativo.
- Documentação básica.
