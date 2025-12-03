## Arquitetura FoKS Intelligence

Este documento resume a espinha dorsal que liga o atalho **FoKS Intelligence** ao backend FastAPI, ao LM Studio e ao Task Runner. Toda a estrutura reside no repositório local protegido pelo Cursor – qualquer evolução precisa seguir essas mesmas camadas.

```mermaid
graph TD
    A[Usuário] --> B[FoKS Intelligence (Atalho)]
    B -->|HTTP POST /chat| C[FastAPI Global Interface]
    B -. Futuro .->|HTTP POST /vision/analyze| C
    B -. Futuro .->|HTTP POST /tasks/run| C

    C -->|router chat| D[LMStudioClient]
    D --> E[(LM Studio - Servidor Local)]

    C -->|router tasks| F[TaskRunner]
    F -->|open_url| G[open (macOS)]
    F -->|run_script| H[scripts .sh locais]
    F -->|say| I[say (macOS TTS)]
    F -. Futuro .-> J[Webhooks → n8n / Node-RED]

    C -->|router vision| K[Placeholder Vision]

    C -->|logging_utils| L[(logs/app.log)]
    D --> L
    F --> L

    L --> M[Observabilidade local]

    subgraph Repositório Protegido (Cursor)
        C
        D
        F
        K
    end
```

**Fluxo principal**
1. O usuário executa o atalho FoKS Intelligence e envia a entrada (texto/voz).
2. O atalho realiza um POST para o FastAPI na máquina local (`/chat`, `/vision/analyze` ou `/tasks/run`).
3. O router correspondente delega o trabalho para o serviço adequado:
   - `LMStudioClient` envia prompts para o LM Studio (API OpenAI-compatível).
   - `TaskRunner` executa automações macOS (`open`, `say`, `.sh`) e, futuramente, webhooks.
   - `vision` ainda atua como placeholder até o modelo ser integrado.
4. Tudo que acontece nas camadas internas gera logs em `logs/app.log`, permitindo auditoria rápida pelo FoKS Control Center.

Assim, o repositório FoKS_Intelligence continua sendo o núcleo arquitetural (“O Cursor agora protege a arquitetura”), e o atalho apenas conversa via HTTP com essa espinha dorsal. Qualquer expansão deve respeitar esse desenho.
# FoKS Intelligence - Arquitetura do Sistema

## Visão Geral

FoKS Intelligence é uma interface global para automação de IA no macOS, otimizada para Apple Silicon M3. O sistema fornece uma API RESTful para interagir com modelos de linguagem locais (LM Studio) e executar tarefas de automação no macOS.

## Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────┐
│                    Clientes                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │macOS     │  │n8n/      │  │Python    │  │Web       │   │
│  │Shortcuts │  │Node-RED  │  │Scripts  │  │Browser   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Port 8001)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Middleware Layer                                     │  │
│  │  - Authentication (API Key)                          │  │
│  │  - Rate Limiting (IP/User)                           │  │
│  │  - CORS                                               │  │
│  │  - GZip Compression                                   │  │
│  │  - M3 Optimization                                    │  │
│  │  - Monitoring                                         │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Router Layer                                         │  │
│  │  - /chat (chat, stream)                              │  │
│  │  - /vision/analyze                                   │  │
│  │  - /tasks/run                                        │  │
│  │  - /conversations (CRUD)                             │  │
│  │  - /system (info, metrics)                           │  │
│  │  - /metrics (Prometheus)                             │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Service Layer                                        │  │
│  │  - LMStudioClient (HTTP pool, retry, circuit breaker)│  │
│  │  - ConversationStore (DB operations, retry)           │  │
│  │  - ConversationCache (in-memory, TTL)                 │  │
│  │  - TaskRunner (macOS automation)                      │  │
│  │  - Monitoring (metrics collection)                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│  LM Studio       │          │  Database        │
│  (Local LLM)     │          │  SQLite/PostgreSQL│
│  Port 1234       │          │                  │
└──────────────────┘          └──────────────────┘
```

## Componentes Principais

### 1. Backend FastAPI

**Localização:** `backend/app/main.py`

**Responsabilidades:**
- Inicialização da aplicação
- Configuração de middlewares
- Registro de routers
- Exception handling global
- Graceful shutdown

**Versão:** 1.3.0

### 2. Middleware Layer

#### Authentication Middleware
- **Arquivo:** `backend/app/middleware/auth.py`
- Validação de API key via header `X-API-Key` ou `Authorization: Bearer`
- Endpoints públicos: `/health`, `/docs`, `/redoc`

#### Rate Limiting Middleware
- **Arquivo:** `backend/app/middleware/rate_limit.py`
- Rate limiting por IP ou User-ID (header `X-User-ID`)
- Configurável via `RATE_LIMIT_REQUESTS_PER_MINUTE`
- Headers de resposta: `X-RateLimit-Limit`, `X-RateLimit-Remaining`

#### M3 Optimization Middleware
- **Arquivo:** `backend/app/middleware/m3_middleware.py`
- Limita requisições concorrentes baseado em hardware M3
- Otimizações específicas para Apple Silicon

#### Monitoring Middleware
- **Arquivo:** `backend/app/middleware/monitoring_middleware.py`
- Coleta métricas de requisições
- Tracking de tempo de resposta
- Contagem de erros

### 3. Service Layer

#### LMStudioClient
- **Arquivo:** `backend/app/services/lmstudio_client.py`
- **Features:**
  - HTTP connection pooling (httpx)
  - Retry com exponential backoff
  - Circuit breaker pattern
  - Streaming support (SSE)
- **Configuração:** `LMSTUDIO_BASE_URL`, `LMSTUDIO_MODEL`

#### ConversationStore
- **Arquivo:** `backend/app/services/conversation_store.py`
- **Features:**
  - CRUD de conversas e mensagens
  - Retry logic para falhas de conexão
  - Connection pooling (SQLAlchemy)
- **Database:** SQLite (padrão) ou PostgreSQL

#### ConversationCache
- **Arquivo:** `backend/app/services/conversation_cache.py`
- **Features:**
  - Cache em memória com TTL (5 minutos)
  - LRU eviction (máximo 100 conversas)
  - Invalidação automática

#### TaskRunner
- **Arquivo:** `backend/app/services/task_runner.py`
- **Tasks suportadas:**
  - `open_url` - Abrir URL no navegador
  - `run_script` - Executar script shell
  - `say` - Text-to-speech
  - `notification` - Notificação macOS
  - `get_clipboard` / `set_clipboard` - Clipboard
  - `screenshot` - Screenshot (full/window/selection)
  - `open_app` - Abrir aplicativo

### 4. Database Layer

#### Models
- **Arquivo:** `backend/app/models/conversation.py`
- **Tabelas:**
  - `conversations` - Metadados de conversas
  - `messages` - Mensagens individuais

#### Migrations
- **Tool:** Alembic
- **Config:** `backend/alembic.ini`
- **Migrations:** `backend/alembic/versions/`

### 5. Configuration

#### Settings
- **Arquivo:** `backend/app/config.py`
- **Fonte:** Variáveis de ambiente + defaults
- **Validação:** No startup via `validate_settings()`

#### Hardware Detection
- **Classe:** `HardwareInfo`
- Detecta Apple Silicon, M3, cores, memória
- Otimizações automáticas baseadas em hardware

## Fluxo de Dados

### Chat Request Flow

```
1. Cliente → POST /chat/
2. RateLimitMiddleware → Verifica limite
3. AuthMiddleware → Valida API key (se configurado)
4. ChatRouter → Sanitiza input
5. ConversationStore → Busca/cria conversa (com cache)
6. LMStudioClient → Envia para LM Studio (com retry/circuit breaker)
7. ConversationStore → Salva resposta
8. Cache → Invalida cache
9. Response → Retorna para cliente
```

### Streaming Flow

```
1. Cliente → POST /chat/stream
2. Middlewares (mesmos do chat)
3. ChatRouter → Gera SSE stream
4. LMStudioClient → Stream do LM Studio
5. Yield chunks → Cliente recebe em tempo real
6. Salva conversa ao finalizar
```

## Segurança

### Autenticação
- API Key via header `X-API-Key` ou `Authorization: Bearer`
- Opcional em desenvolvimento, obrigatório em produção

### Rate Limiting
- Por IP (padrão) ou por User-ID
- Configurável: 60 req/min (padrão)

### Sanitização
- Input sanitization em todos os endpoints
- Secrets sanitizados nos logs
- Validação de URLs e paths

### CORS
- Configurável via `ALLOWED_ORIGINS`
- Restritivo em produção (remove localhost)

## Performance

### Otimizações M3
- Connection pooling HTTP
- Database connection pooling
- Cache de conversas frequentes
- GZip compression
- Circuit breaker para prevenir cascading failures

### Monitoramento
- Métricas Prometheus em `/metrics/prometheus`
- Health checks em `/health`
- Database stats em `/system/database/stats`
- Logs estruturados (JSON opcional)

## Deployment

### Desenvolvimento
```bash
cd backend
source .venv_foks/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Produção
- **Docker:** `docker-compose up`
- **Systemd:** Script em `scripts/systemd_service.sh`
- **Deploy:** Script em `scripts/deploy.sh`

## Dependências Externas

1. **LM Studio** - Servidor local de LLM (OpenAI-compatible)
   - URL: `http://127.0.0.1:1234`
   - Modelos: Qualquer modelo suportado pelo LM Studio

2. **Database** - SQLite (padrão) ou PostgreSQL 17
   - SQLite: Arquivo local
   - PostgreSQL: Via `DATABASE_URL`

## Escalabilidade

### Limitações Atuais
- Rate limiting em memória (não distribuído)
- Cache em memória (não compartilhado)
- Single instance

### Melhorias Futuras
- Redis para rate limiting distribuído
- Redis para cache compartilhado
- Load balancer para múltiplas instâncias
- Database read replicas

## Observabilidade

### Logs
- Estruturados (JSON opcional)
- Rotação automática (10MB, 10 backups)
- Níveis configuráveis por ambiente
- Secrets sanitizados

### Métricas
- Prometheus format
- Request/response times
- Error rates
- Task execution stats
- Uptime

### Health Checks
- `/health` - Status geral
- `/system/database/stats` - Database info
- `/metrics` - Application metrics

## Versionamento

### API Versioning
- Versão atual: v1 (`/api/v1/`)
- Backward compatibility: Endpoints sem versão ainda funcionam
- Estratégia: URL versioning (`/api/v1/`, `/api/v2/`)

### Changelog
- Manual: `CHANGELOG.md`
- Futuro: Automático via git hooks

## Testes

### Cobertura
- Unit tests: `tests/test_*.py`
- Integration tests: `tests/test_e2e.py`
- Target: >80% coverage

### CI/CD
- GitHub Actions: `.github/workflows/ci.yml`
- Python 3.9, 3.10, 3.11
- Linting, formatting, tests, coverage

## Documentação

- **API:** Swagger UI em `/docs`
- **ReDoc:** `/redoc`
- **Guias:** `docs/` directory
- **Exemplos:** `examples/` directory

