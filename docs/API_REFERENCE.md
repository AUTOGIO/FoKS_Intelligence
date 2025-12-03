# 📚 FoKS Intelligence - API Reference

Documentação completa dos endpoints da API.

**Base URL**: `http://localhost:8001`

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
curl -X POST http://localhost:8001/chat/ \
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
curl -X POST http://localhost:8001/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "say",
    "params": {"text": "Teste"},
    "source": "test"
  }'
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

