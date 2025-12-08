# 📚 FoKS Intelligence - API Reference

Documentação completa dos endpoints da API.

**Base URL**: `http://localhost:8000`

---

## 🔹 Health Check

### `GET /health`

Verifica se o servidor está rodando.

**Resposta de Sucesso:**
```json
{
    "status": "ok",
    "app": "FoKS Intelligence Global Interface",
    "env": "development"
}
```

---

## 🔹 Chat Endpoint

### `POST /chat/`

Envia uma mensagem para o LM Studio e retorna a resposta do modelo.

**Request Body:**
```json
{
    "message": "Sua mensagem aqui",
    "history": [
        {
            "role": "user",
            "content": "Mensagem anterior"
        },
        {
            "role": "assistant",
            "content": "Resposta anterior"
        }
    ],
    "input_type": "text",
    "source": "shortcuts",
    "metadata": {
        "device": "iMac_M3",
        "shortcut_name": "FoKS Intelligence"
    }
}
```

**Campos:**
- `message` (string, obrigatório): Mensagem do usuário
- `history` (array, opcional): Histórico de conversa
- `input_type` (string, opcional): Tipo de entrada (`text`, `voice`, `screenshot`, etc.)
- `source` (string, opcional): Origem da requisição (`shortcuts`, `cli`, `obsidian`, etc.)
- `metadata` (object, opcional): Metadados adicionais

**Response:**
```json
{
    "reply": "Resposta do modelo",
    "raw": {
        "id": "chatcmpl-...",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "llama-3-8b-instruct-1048k",
        "choices": [...]
    }
}
```

**Exemplo cURL:**
```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Olá!",
    "source": "test"
  }'
```

---

## 🔹 Vision Endpoint

### `POST /vision/analyze`

Analisa uma imagem (placeholder - ainda não conectado ao modelo vision).

**Request Body:**
```json
{
    "description": "Descrição da imagem",
    "image_url": "https://example.com/image.jpg",
    "image_base64": "base64_encoded_image",
    "source": "shortcuts",
    "metadata": {}
}
```

**Campos:**
- `description` (string, obrigatório): Descrição da imagem
- `image_url` (string, opcional): URL da imagem
- `image_base64` (string, opcional): Imagem codificada em base64
- `source` (string, opcional): Origem da requisição
- `metadata` (object, opcional): Metadados adicionais

**Response:**
```json
{
    "summary": "Vision request received. Description: ...",
    "details": {
        "note": "Vision model not wired yet."
    }
}
```

---

## 🔹 Tasks Endpoint

### `POST /tasks/run`

Executa uma tarefa de automação no macOS.

**Request Body:**
```json
{
    "task_name": "say",
    "params": {
        "text": "Texto para falar"
    },
    "source": "shortcuts",
    "metadata": {}
}
```

**Campos:**
- `task_name` (string, obrigatório): Nome da tarefa
- `params` (object, obrigatório): Parâmetros da tarefa
- `source` (string, opcional): Origem da requisição
- `metadata` (object, opcional): Metadados adicionais

**Tasks Disponíveis:**

#### 1. `say`
Fala um texto usando o comando macOS `say`.

**Params:**
- `text` (string): Texto para falar

**Exemplo:**
```json
{
    "task_name": "say",
    "params": {"text": "Olá mundo"}
}
```

#### 2. `open_url`
Abre uma URL no navegador padrão.

**Params:**
- `url` (string): URL para abrir

**Exemplo:**
```json
{
    "task_name": "open_url",
    "params": {"url": "https://www.apple.com"}
}
```

#### 3. `run_script`
Executa um script bash.

**Params:**
- `path` (string): Caminho absoluto do script

**Exemplo:**
```json
{
    "task_name": "run_script",
    "params": {"path": "/path/to/script.sh"}
}
```

#### 4. `notification`
Envia notificação macOS.

**Params:**
- `title` (string, opcional): Título da notificação
- `message` (string, obrigatório): Mensagem
- `subtitle` (string, opcional): Subtítulo

**Exemplo:**
```json
{
    "task_name": "notification",
    "params": {
        "title": "FoKS",
        "message": "Tarefa concluída!",
        "subtitle": "Sucesso"
    }
}
```

#### 5. `get_clipboard`
Obtém conteúdo do clipboard.

**Params:** Nenhum

**Exemplo:**
```json
{
    "task_name": "get_clipboard",
    "params": {}
}
```

**Response:**
```json
{
    "success": true,
    "message": "Clipboard content retrieved",
    "data": {"content": "texto do clipboard"}
}
```

#### 6. `set_clipboard`
Define conteúdo do clipboard.

**Params:**
- `text` (string): Texto para copiar

**Exemplo:**
```json
{
    "task_name": "set_clipboard",
    "params": {"text": "Texto para copiar"}
}
```

#### 7. `screenshot`
Tira screenshot e retorna em base64.

**Params:**
- `type` (string, opcional): Tipo de screenshot (`full`, `window`, `selection`)
- `format` (string, opcional): Formato (`png`, `jpg`)

**Exemplo:**
```json
{
    "task_name": "screenshot",
    "params": {"type": "full", "format": "png"}
}
```

**Response:**
```json
{
    "success": true,
    "message": "Screenshot taken (full)",
    "data": {
        "image_base64": "base64_encoded_image...",
        "format": "png",
        "size_bytes": 123456
    }
}
```

#### 8. `open_app`
Abre aplicativo macOS.

**Params:**
- `app` (string): Nome do app (ex: "Safari", "Notes", "Terminal")

**Exemplo:**
```json
{
    "task_name": "open_app",
    "params": {"app": "Safari"}
}
```

**Response:**
```json
{
    "success": true,
    "message": "Spoken text via macOS 'say'",
    "data": {}
}
```

**Exemplo cURL:**
```bash
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "say",
    "params": {"text": "Teste"},
    "source": "test"
  }'
```

---

## 🔹 Conversations Endpoints

### `POST /conversations/`

Cria uma nova conversa.

**Request Body:**
```json
{
    "user_id": "user123",
    "title": "Minha Conversa",
    "source": "shortcuts"
}
```

**Campos:**
- `user_id` (string, obrigatório): Identificador do usuário
- `title` (string, opcional): Título da conversa
- `source` (string, opcional): Origem da conversa

**Response:**
```json
{
    "id": 1,
    "user_id": "user123",
    "title": "Minha Conversa",
    "source": "shortcuts",
    "created_at": "2024-01-01T12:00:00",
    "updated_at": "2024-01-01T12:00:00",
    "message_count": 0
}
```

### `GET /conversations/`

Lista conversas de um usuário.

**Query Parameters:**
- `user_id` (string, obrigatório): Identificador do usuário
- `limit` (int, opcional): Número máximo de conversas (padrão: 50, máximo: 100)
- `offset` (int, opcional): Offset para paginação (padrão: 0)

**Response:**
```json
{
    "conversations": [
        {
            "id": 1,
            "user_id": "user123",
            "title": "Minha Conversa",
            "source": "shortcuts",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:00:00",
            "message_count": 5
        }
    ],
    "total": 10,
    "limit": 50,
    "offset": 0
}
```

### `GET /conversations/{conversation_id}`

Obtém uma conversa específica por ID.

**Query Parameters:**
- `user_id` (string, opcional): Identificador do usuário para validação

**Response:**
```json
{
    "id": 1,
    "user_id": "user123",
    "title": "Minha Conversa",
    "source": "shortcuts",
    "created_at": "2024-01-01T12:00:00",
    "updated_at": "2024-01-01T12:00:00",
    "message_count": 5
}
```

### `GET /conversations/{conversation_id}/messages`

Obtém todas as mensagens de uma conversa.

**Query Parameters:**
- `user_id` (string, opcional): Identificador do usuário para validação

**Response:**
```json
[
    {
        "id": 1,
        "conversation_id": 1,
        "role": "user",
        "content": "Olá!",
        "created_at": "2024-01-01T12:00:00"
    },
    {
        "id": 2,
        "conversation_id": 1,
        "role": "assistant",
        "content": "Olá! Como posso ajudar?",
        "created_at": "2024-01-01T12:00:05"
    }
]
```

### `DELETE /conversations/{conversation_id}`

Deleta uma conversa.

**Query Parameters:**
- `user_id` (string, opcional): Identificador do usuário para validação

**Response:**
```json
{
    "success": true,
    "message": "Conversation 1 deleted"
}
```

### `PATCH /conversations/{conversation_id}/title`

Atualiza o título de uma conversa.

**Query Parameters:**
- `title` (string, obrigatório): Novo título da conversa

**Response:**
```json
{
    "success": true,
    "message": "Conversation 1 title updated"
}
```

### `GET /conversations/{conversation_id}/export`

Exporta uma conversa em formato JSON ou JSONL.

**Query Parameters:**
- `user_id` (string, opcional): Identificador do usuário para validação
- `format` (string, opcional): Formato de exportação (`json` ou `jsonl`, padrão: `json`)

**Response:**
- JSON: Retorna objeto JSON completo com conversa e mensagens
- JSONL: Retorna linhas JSONL (uma por linha)

**Exemplo cURL:**
```bash
# Criar conversa
curl -X POST http://localhost:8000/conversations/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "title": "Nova Conversa"
  }'

# Listar conversas
curl "http://localhost:8000/conversations/?user_id=user123&limit=10"

# Exportar conversa
curl "http://localhost:8000/conversations/1/export?format=json"
```

---

## 🔹 Metrics Endpoints

### `GET /metrics`

Retorna métricas resumidas da aplicação em formato JSON.

**Response:**
```json
{
    "total_requests": 150,
    "successful_requests": 145,
    "failed_requests": 5,
    "avg_response_time_ms": 250.5,
    "total_tasks": 30,
    "successful_tasks": 28,
    "failed_tasks": 2,
    "uptime_seconds": 3600,
    "uptime_formatted": "1h 0m 0s"
}
```

### `GET /metrics/prometheus`

Retorna métricas no formato Prometheus (text/plain).

**Response:**
```
# HELP foks_requests_total Total number of requests
# TYPE foks_requests_total counter
foks_requests_total 150

# HELP foks_requests_success_total Total successful requests
# TYPE foks_requests_success_total counter
foks_requests_success_total 145

# HELP foks_requests_failure_total Total failed requests
# TYPE foks_requests_failure_total counter
foks_requests_failure_total 5

# HELP foks_response_time_seconds Average response time
# TYPE foks_response_time_seconds gauge
foks_response_time_seconds 0.2505

# HELP foks_tasks_total Total tasks executed
# TYPE foks_tasks_total counter
foks_tasks_total 30

# HELP foks_tasks_success_total Total successful tasks
# TYPE foks_tasks_success_total counter
foks_tasks_success_total 28

# HELP foks_uptime_seconds Application uptime
# TYPE foks_uptime_seconds gauge
foks_uptime_seconds 3600
```

**Exemplo cURL:**
```bash
# Métricas JSON
curl http://localhost:8000/metrics

# Métricas Prometheus
curl http://localhost:8000/metrics/prometheus
```

---

## 🔹 System Endpoints

### `GET /system/info`

Retorna informações detalhadas do sistema, incluindo informações específicas do hardware M3.

**Response:**
```json
{
    "python_version": "3.11.0",
    "python_version_info": {
        "major": 3,
        "minor": 11,
        "micro": 0
    },
    "platform": "macOS-14.0-arm64",
    "system": "Darwin",
    "processor": "arm",
    "architecture": ("64bit", ""),
    "machine": "arm64",
    "app_version": "1.3.0",
    "app_name": "FoKS Intelligence Global Interface",
    "environment": "development",
    "is_apple_silicon": true,
    "is_m3": true,
    "cpu_cores": 10,
    "memory_gb": 16
}
```

### `GET /system/recommendations`

Retorna recomendações de configuração de modelo baseadas no hardware M3.

**Response:**
```json
{
    "recommended_model": "qwen2.5-14b",
    "max_tokens": 2048,
    "temperature": 0.7,
    "reason": "M3 hardware detected with 16GB memory"
}
```

### `GET /system/metrics`

Alias para `/metrics` - retorna as mesmas métricas da aplicação.

**Response:**
```json
{
    "requests": {
        "total": 150,
        "success": 145,
        "failures": 5,
        "avg_response_time_ms": 250.5
    },
    "tasks": {
        "total": 30,
        "success": 28,
        "failures": 2
    },
    "uptime_seconds": 3600,
    "uptime_formatted": "1h 0m 0s"
}
```

### `GET /system/database/stats`

Retorna estatísticas do banco de dados.

**Response:**
```json
{
    "database_type": "sqlite",
    "database_path": "/path/to/database.db",
    "size_bytes": 1048576,
    "size_formatted": "1.0 MB",
    "conversations_count": 50,
    "messages_count": 500
}
```

**Exemplo cURL:**
```bash
# Informações do sistema
curl http://localhost:8000/system/info

# Recomendações de modelo
curl http://localhost:8000/system/recommendations

# Estatísticas do banco
curl http://localhost:8000/system/database/stats
```

---

## 🔹 Códigos de Status HTTP

- `200 OK`: Requisição bem-sucedida
- `400 Bad Request`: Dados inválidos
- `500 Internal Server Error`: Erro no servidor

---

## 🔹 Logs

Os logs são salvos em:
```
/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/logs/app.log
```

Para acompanhar em tempo real:
```bash
tail -f /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/logs/app.log
```

