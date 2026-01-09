# FoKS Intelligence - Project Architecture Map

**Generated:** 2025-01-27
**Status:** ✅ Active Maintenance Mode

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    subgraph "External Integration"
        S[macOS Shortcuts] -->|Trigger| G
        N8[n8n / Node-RED] -->|Trigger| G
    end

    subgraph "FoKS Intelligence (Control Plane)"
        G[FoKS FastAPI Backend<br/>'Non-Autonomous Control Plane']
        LG[(logs/app.log)]
    end

    subgraph "FBP Backend (Execution Engine)"
        F[FBP Backend<br/>~/Documents/FBP_Backend]
    end

    subgraph "Local AI"
        L[LM Studio<br/>localhost:1234]
    end

    G -->|"Command (deterministic)"| F
    F -->|"Result + evidence (no logic)"| G
    G -->|"Consultation only (no authority)"| L
    G -->|Orchestrate| T[macOS Automation<br/>(open, say, scripts,...)]

    G --- LG
```

**Architecture Rule:** Router → Service → Core → External (NEVER skip layers)

---

## 📁 Directory Structure

```
FoKS_Intelligence/
├── backend/
│   └── app/
│       ├── main.py                    # FastAPI app initialization
│       ├── config.py                  # Settings & configuration
│       ├── routers/                   # HTTP endpoints (thin layer)
│       ├── services/                  # Business logic (thick layer)
│       ├── models/                    # Pydantic models + DB models
│       ├── middleware/                # Cross-cutting concerns
│       ├── utils/                     # Shared utilities
│       └── config/                    # Configuration modules
├── ops/
│   └── scripts/                       # Operational scripts
└── docs/                              # Documentation
```

---

## 🔌 Router Layer (`backend/app/routers/`)

**Purpose:** Thin HTTP interface layer. Validates requests, delegates to services, formats responses.

### 1. `chat.py` - Chat Interface

- **Endpoint:** `POST /chat/`
- **Service:** `chat_service.generate_chat_response()`
- **Models:** `ChatRequest` → `ChatResponse`
- **Flow:** Request → ChatService → LMStudioClient → LM Studio
- **Features:**
  - Message validation
  - History support
  - Model selection
  - Task type & tools detection

### 2. `tasks.py` - Task Execution

- **Endpoint:** `POST /tasks/run`
- **Service:** `TaskRunner.run_task()`
- **Models:** `TaskRequest` → `TaskResult`
- **Flow:** Request → TaskRunner → FBP Service (for nfa/redesim/browser/utils) OR macOS automation
- **Features:**
  - Task type routing
  - Timeout handling
  - FBP delegation for automation tasks

### 3. `conversations.py` - Conversation Management

- **Endpoints:**
  - `POST /conversations/` - Create conversation
  - `GET /conversations/` - List conversations
  - `GET /conversations/{id}` - Get conversation
  - `GET /conversations/{id}/messages` - Get messages
  - `DELETE /conversations/{id}` - Delete conversation
  - `PATCH /conversations/{id}/title` - Update title
  - `GET /conversations/{id}/export` - Export (JSON/JSONL)
- **Services:** `conversation_store`, `conversation_cache`, `webhook_service`
- **Models:** `ConversationCreate`, `ConversationResponse`, `MessageResponse`
- **Features:**
  - CRUD operations
  - Caching (in-memory, TTL)
  - Webhook notifications
  - Export functionality

### 4. `vision.py` - Vision Analysis

- **Endpoint:** `POST /vision/analyze`
- **Service:** `vision_service.analyze_image()`
- **Models:** `VisionRequest` → `VisionResponse`
- **Flow:** Request → VisionService → LMStudioClient → LM Studio (multimodal)
- **Features:**
  - Base64 image decoding
  - Multimodal model support

### 5. `system.py` - System Information

- **Endpoints:**
  - `GET /system/info` - System info (M3-specific)
  - `GET /system/recommendations` - Model recommendations
  - `GET /system/metrics` - Application metrics
  - `GET /system/database/stats` - Database statistics
- **Services:** `monitoring`, `utils.m3_optimizations`, `utils.db_monitoring`
- **Features:**
  - Hardware detection
  - Model recommendations
  - Database stats

### 6. `metrics.py` - Metrics Endpoint

- **Endpoints:**
  - `GET /metrics` - JSON summary
  - `GET /metrics/prometheus` - Prometheus format
- **Service:** `monitoring.get_stats()`
- **Features:**
  - Request/response metrics
  - Task execution stats
  - Uptime tracking

### 7. `tools_dashboard.py` - Dashboard Tools

- **Endpoint:** `POST /tools/dashboard/daily-engineering`
- **Service:** `dashboard_tools.build_daily_engineering_briefing()`
- **Models:** `DailyEngineeringBriefingRequest` → `DailyEngineeringBriefingResponse`
- **Features:**
  - Git commit analysis
  - Branch tracking
  - System health aggregation
  - Obsidian notes integration
  - LM Studio-generated markdown briefings

---

## ⚙️ Service Layer (`backend/app/services/`)

**Purpose:** Business logic, orchestration, error handling. NEVER place business logic in routers.

### Core Services

#### 1. `chat_service.py`

- **Function:** `generate_chat_response()`
- **Dependencies:** `LMStudioClient`, `model_registry`
- **Responsibilities:**
  - Model selection (default vs. task-specific)
  - History management
  - Streaming support
  - Tools detection

#### 2. `lmstudio_client.py` - LM Studio Client

- **Class:** `LMStudioClient`
- **Features:**
  - HTTP connection pooling (httpx)
  - Retry with exponential backoff
  - Circuit breaker pattern
  - Streaming support
  - Model management
- **Config:** `LMSTUDIO_BASE_URL`, `LMSTUDIO_MODEL`

#### 3. `fbp_client.py` - FBP Backend Client

- **Class:** `FBPClient`
- **Transport:** UNIX Socket (`/tmp/fbp.sock`) OR HTTP
- **Config:** `FBP_TRANSPORT` (socket/http), `FBP_SOCKET_PATH`
- **Methods:**
  - `health()` - Health check
  - `nfa(data)` - NFA automation
  - `redesim(data)` - REDESIM automation
  - `browser(data)` - Browser actions
  - `utils(data)` - Utility functions
- **Features:**
  - Automatic retry logic
  - Timeout handling
  - Connection pooling
  - Socket transport via `httpx.AsyncHTTPTransport(uds=...)`

#### 4. `fbp_service.py` - FBP Service Wrapper

- **Functions:**
  - `run_health_check()`
  - `run_nfa(payload)`
  - `run_redesim(payload)`
  - `run_browser_action(payload)`
  - `run_utils(payload)`
- **Purpose:** Thin wrapper around `FBPClient` for service layer abstraction

#### 5. `task_runner.py` - Task Execution Engine

- **Class:** `TaskRunner`
- **Method:** `run_task(task_type, args, timeout)`
- **Task Types:**
  - **FBP Delegation:** `nfa`, `redesim`, `browser`, `utils` → `fbp_service`
  - **macOS Automation:**
    - `run_shell` - Execute shell command
    - `run_script` - Execute script file
    - `run_apple_script` - Execute AppleScript
    - `run_shortcut` - Run macOS Shortcut
    - `run_keyboard_maestro_macro` - Run Keyboard Maestro macro
    - `open_url` - Open URL
    - `open_app` - Open application
    - `notify` - macOS notification
    - `say` - Text-to-speech
    - `system_status` - System metrics
- **Features:**
  - Timeout handling
  - Error wrapping
  - Duration tracking
  - FBP delegation for automation tasks

#### 6. `conversation_store.py` - Database Operations

- **Class:** `ConversationStore`
- **Features:**
  - CRUD operations
  - Connection pooling
  - Retry logic
  - Message management
- **Database:** SQLite (default) or PostgreSQL

#### 7. `conversation_cache.py` - In-Memory Cache

- **Class:** `ConversationCache`
- **Features:**
  - TTL-based expiration (5 minutes)
  - LRU eviction (max 100)
  - Automatic invalidation

#### 8. `vision_service.py` - Vision Analysis

- **Function:** `analyze_image()`
- **Dependencies:** `LMStudioClient`
- **Features:**
  - Image processing
  - Multimodal model support

#### 9. `dashboard_tools.py` - Engineering Briefings

- **Function:** `build_daily_engineering_briefing()`
- **Dependencies:** `FBPClient`, `LMStudioClient`, `monitoring`
- **Features:**
  - Git commit analysis (last 24h)
  - Branch tracking (feature/_, fix/_)
  - Directory change detection
  - System health aggregation (FoKS, FBP, LM Studio)
  - Obsidian notes integration
  - LM Studio-generated markdown

#### 10. `monitoring.py` - Metrics Collection

- **Class:** `Monitoring`
- **Features:**
  - Request/response tracking
  - Task execution stats
  - Uptime calculation
  - Error counting

#### 11. `webhook_service.py` - Webhook Notifications

- **Class:** `WebhookService`
- **Features:**
  - Async webhook delivery
  - Retry logic
  - Event types: `conversation.created`, etc.

#### 12. `model_registry.py` - Model Management

- **Functions:**
  - `resolve_model(name)`
  - `get_default_model(task_type)`
  - `list_models()`
- **Features:**
  - Model metadata
  - Task-specific model selection
  - Tools support detection

#### 13. `cleanup_scheduler.py` - Data Cleanup

- **Purpose:** Scheduled cleanup of old data
- **Features:**
  - Conversation cleanup
  - Cache invalidation

#### 14. `logging_utils.py` - Structured Logging

- **Function:** `get_logger(name)`
- **Features:**
  - Structured JSON logging
  - Context preservation
  - Log rotation

---

## 📦 Models Layer (`backend/app/models/`)

### Pydantic Models (`models.py`)

#### Request Models

- `ChatRequest` - Chat message with history, metadata
- `VisionRequest` - Image analysis request
- `TaskRequest` - Task execution request
- `ConversationCreate` - New conversation
- `DailyEngineeringBriefingRequest` - Briefing generation

#### Response Models

- `ChatResponse` - Chat reply with raw data
- `VisionResponse` - Vision analysis result
- `TaskResult` - Task execution result
- `ConversationResponse` - Conversation details
- `ConversationListResponse` - Paginated conversations
- `MessageResponse` - Individual message
- `DailyEngineeringBriefingResponse` - Markdown briefing

#### Data Models

- `ChatMessage` - Message with role and content

### Database Models (`conversation.py`)

- `Conversation` - SQLAlchemy model
- `Message` - SQLAlchemy model

---

## 🛠️ Core Layer (`backend/app/utils/`)

### Utilities

- `circuit_breaker.py` - Circuit breaker pattern
- `db_monitoring.py` - Database statistics
- `helpers.py` - General helpers
- `m3_optimizations.py` - M3 hardware detection & recommendations
- `shutdown.py` - Graceful shutdown
- `timeout.py` - Timeout utilities
- `token_bucket.py` - Rate limiting
- `validators.py` - Input validation

---

## 🔧 Middleware Layer (`backend/app/middleware/`)

### Middleware Components

1. **`auth.py`** - API key authentication
2. **`rate_limit.py`** - Rate limiting (IP/User-ID)
3. **`m3_middleware.py`** - M3 optimization middleware
4. **`monitoring_middleware.py`** - Request metrics collection

---

## 🔌 FBP Integration (UNIX Socket)

### Architecture Rule

**FBP may ONLY be called via UNIX socket through FoKS service code.**

### Implementation

1. **Transport:** UNIX Socket (`/tmp/fbp.sock`)
2. **Client:** `FBPClient` in `backend/app/services/fbp_client.py`
3. **Service:** `FBPService` in `backend/app/services/fbp_service.py`
4. **Config:**
   - `FBP_TRANSPORT=socket` (default)
   - `FBP_SOCKET_PATH=/tmp/fbp.sock` (default)
5. **Usage:**

   ```python
   # In service layer only
   from app.services import fbp_service
   result = await fbp_service.run_nfa(payload)
   ```

### Socket Transport

- Uses `httpx.AsyncHTTPTransport(uds=socket_path)`
- Automatic retry and error handling
- Connection pooling

---

## 📜 Operations Scripts (`ops/scripts/`)

### Bootstrap Scripts

- `foks_boot_optimized.sh` - FoKS backend startup (M3 optimized)
- `start_fbp_m3.sh` - FBP backend startup (UNIX socket)
- `fbp_boot.sh` - FBP bootstrap (legacy)
- `fbp_boot_optimized.sh` - FBP bootstrap (M3 optimized)

### Setup Scripts

- `setup_m3_modern.sh` - M3 environment setup
- `apply_m3_optimizations.sh` - Apply M3 optimizations
- `verify_m3_setup.sh` - Verify M3 configuration

### Diagnostic Scripts

- `foks_full_diagnostic.sh` - Full system diagnostic
- `foks_env_autofix.sh` - Environment auto-fix
- `test_foks_env.sh` - Environment testing
- `foks_venv_guard.sh` - Virtualenv guard

### Monitoring Scripts

- `m3_system_dashboard.sh` - System dashboard
- `m3_quick_start.sh` - Quick start script
- `lmstudio_watch.sh` - LM Studio monitoring

### Utility Scripts

- `kill_all.sh` - Kill all FoKS/FBP processes
- `nfa_runner.sh` - NFA pipeline runner
- `fix_best_practices.sh` - Best practices fixes

---

## 📚 Documentation (`docs/`)

### Architecture & Design

- `ARCHITECTURE.md` - System architecture
- `BEST_PRACTICES.md` - Coding standards
- `M3_OPTIMIZATION.md` - M3 optimization guide
- `M3_OPTIMIZATION_GUIDE.md` - Detailed M3 guide
- `M3_OPTIMIZATION_SUMMARY.md` - M3 summary

### Operations

- `FoKS_Ops_Handbook.md` - Operations handbook
- `FoKS_DevOps_QuickStart.md` - Quick start guide
- `FoKS_Monitoring_Guide.md` - Monitoring guide
- `DEPLOYMENT.md` - Deployment guide
- `TROUBLESHOOTING.md` - Troubleshooting guide
- `DISASTER_RECOVERY.md` - Disaster recovery

### Integration

- `API_REFERENCE.md` - API documentation
- `INTEGRATION_EXAMPLES.md` - Integration examples
- `SHORTCUT_SETUP.md` - macOS Shortcuts setup
- `CONVERSATIONS.md` - Conversation management

### Database

- `POSTGRESQL_SETUP.md` - PostgreSQL setup
- `MONITORING.md` - Monitoring documentation

### Reports

- `ENVIRONMENT_HEALING_REPORT.md` - Environment fixes
- `PRODUCTION_90_PERCENT.md` - Production readiness
- `PRODUCTION_CHECKLIST.md` - Production checklist

---

## 🔄 Data Flow Examples

### Chat Request Flow

```
1. Client → POST /chat/
2. RateLimitMiddleware → Check limits
3. AuthMiddleware → Validate API key
4. ChatRouter → Validate ChatRequest
5. ChatService → Select model, prepare history
6. LMStudioClient → HTTP POST to LM Studio
7. LM Studio → Generate response
8. ChatService → Format response
9. ChatRouter → Return ChatResponse
```

### Task Execution Flow (FBP)

```
1. Client → POST /tasks/run (type="nfa")
2. TasksRouter → Validate TaskRequest
3. TaskRunner → Detect FBP task type
4. TaskRunner → Delegate to fbp_service.run_nfa()
5. FBPService → Call FBPClient.nfa()
6. FBPClient → UNIX Socket request to /tmp/fbp.sock
7. FBP Backend → Execute NFA automation
8. FBPClient → Receive response
9. TaskRunner → Wrap in TaskResult
10. TasksRouter → Return TaskResult
```

### Conversation Management Flow

```
1. Client → POST /conversations/
2. ConversationsRouter → Validate ConversationCreate
3. ConversationStore → Create conversation in DB
4. WebhookService → Send webhook (if enabled)
5. ConversationsRouter → Return ConversationResponse
```

---

## ⚠️ Architecture Rules

### ✅ DO

- **Router → Service → Core → External** (always follow layers)
- Place business logic in services, not routers
- Use Pydantic models for validation
- Use structured logging
- Handle errors gracefully
- Use async/await throughout
- Call FBP via `fbp_service` wrapper (UNIX socket)

### ❌ DON'T

- Skip service layer (router calling core directly)
- Place business logic in routers
- Call FBP directly from routers
- Use synchronous code where async exists
- Hardcode values (use config/env)
- Skip error handling
- Skip logging

---

## 🔍 Key Configuration

### Environment Variables

- `FBP_TRANSPORT=socket` - Use UNIX socket
- `FBP_SOCKET_PATH=/tmp/fbp.sock` - Socket path
- `LMSTUDIO_BASE_URL=http://localhost:1234/v1` - LM Studio URL
- `FOKS_ENV=development` - Environment
- `DATABASE_URL` - PostgreSQL connection (optional)
- `FOKS_API_KEY` - API key for authentication

### Settings (`backend/app/config.py`)

- `fbp_transport` - Transport type (socket/http)
- `fbp_socket_path` - UNIX socket path
- `lmstudio_base_url` - LM Studio base URL
- `default_timeout_seconds` - Default timeout
- `default_retry_attempts` - Retry attempts
- `cache_enabled` - Enable conversation cache
- `webhook_enabled` - Enable webhooks

---

## 📊 System Health

### Health Endpoints

- `GET /health` - Basic health check
- `GET /system/info` - System information
- `GET /system/database/stats` - Database stats
- `GET /metrics` - Application metrics

### Monitoring

- Request/response metrics
- Task execution stats
- Error rates
- Uptime tracking

---

## 🎯 Integration Points

### External Systems

1. **LM Studio** - Local LLM server (HTTP)
2. **FBP Backend** - Automation engine (UNIX socket)
3. **Database** - SQLite/PostgreSQL
4. **macOS System** - Shortcuts, AppleScript, notifications

### Client Interfaces

1. **macOS Shortcuts** - Native automation
2. **n8n/Node-RED** - Workflow automation
3. **Python Scripts** - Programmatic access
4. **Web Browser** - Swagger UI at `/docs`

---

## ✅ Project Map Status

**Status:** ✅ **COMPLETE**

**Mapped Components:**

- ✅ All routers (7 routers)
- ✅ All services (14 services)
- ✅ All models (Pydantic + DB)
- ✅ All ops scripts (17 scripts)
- ✅ All documentation (20+ docs)
- ✅ FBP integration (UNIX socket)
- ✅ Architecture rules validated

**Ready for maintenance and development.**

---

**Last Updated:** 2025-01-27
**Maintained By:** FoKS Architecture Guardian
