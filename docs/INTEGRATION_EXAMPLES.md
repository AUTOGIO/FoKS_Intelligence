# 🔗 FoKS Intelligence - Exemplos de Integração

Guia de integração com ferramentas de automação e workflow.

---

## 🔹 Integração com n8n

### Webhook para Chat

1. Crie um novo workflow no n8n
2. Adicione um nó **Webhook** (trigger)
3. Configure:
   - **HTTP Method**: POST
   - **Path**: `foks-chat`
   - **Response Mode**: Respond to Webhook

4. Adicione um nó **HTTP Request**
5. Configure:
   - **Method**: POST
   - **URL**: `http://localhost:8001/chat/`
   - **Headers**:
     - `Content-Type`: `application/json`
   - **Body**:
   ```json
   {
     "message": "{{ $json.body.message }}",
     "source": "n8n",
     "input_type": "text"
   }
   ```

6. Adicione um nó **Respond to Webhook**
7. Configure:
   - **Response Body**: `{{ $json.reply }}`

### Exemplo de Payload n8n

```json
{
  "message": "Explique o que é inteligência artificial",
  "source": "n8n_workflow",
  "metadata": {
    "workflow_id": "workflow_123",
    "node_id": "node_456"
  }
}
```

---

## 🔹 Integração com Node-RED

### Flow de Chat

1. Adicione um nó **http in**
   - **Method**: POST
   - **URL**: `/foks/chat`

2. Adicione um nó **function** com código:
   ```javascript
   const payload = {
     message: msg.payload.message || msg.payload,
     source: "node-red",
     input_type: "text"
   };

   msg.payload = payload;
   return msg;
   ```

3. Adicione um nó **http request**
   - **Method**: POST
   - **URL**: `http://localhost:8001/chat/`
   - **Headers**: `Content-Type: application/json`

4. Adicione um nó **function** para extrair resposta:
   ```javascript
   msg.payload = msg.payload.reply;
   return msg;
   ```

5. Adicione um nó **http response**

---

## 🔹 Integração com Apple Shortcuts (Avançado)

### Shortcut com Menu de Opções

1. **Escolher do Menu**
   - Opções:
     - `Texto`
     - `Voz`
     - `Screenshot`
     - `Clipboard`

2. **Se** (If) - baseado na escolha

   **Caso "Texto":**
   - Perguntar por texto
   - Chamar `/chat/` com `input_type: "text"`

   **Caso "Voz":**
   - Reconhecer fala
   - Chamar `/chat/` com `input_type: "voice"`

   **Caso "Screenshot":**
   - Tirar screenshot
   - Converter para base64
   - Chamar `/vision/analyze` com `image_base64`

   **Caso "Clipboard":**
   - Obter clipboard
   - Chamar `/chat/` com mensagem do clipboard

---

## 🔹 Integração via cURL

### Chat Simples

```bash
curl -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Olá!",
    "source": "curl"
  }'
```

### Chat com Histórico

```bash
curl -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Continue nossa conversa",
    "history": [
      {"role": "user", "content": "Meu nome é João"},
      {"role": "assistant", "content": "Prazer em conhecê-lo, João!"}
    ],
    "source": "curl"
  }'
```

### Task - Notificação

```bash
curl -X POST http://localhost:8001/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "notification",
    "params": {
      "title": "FoKS",
      "message": "Tarefa concluída!",
      "subtitle": "Sucesso"
    },
    "source": "curl"
  }'
```

### Task - Screenshot

```bash
curl -X POST http://localhost:8001/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "screenshot",
    "params": {
      "type": "full",
      "format": "png"
    },
    "source": "curl"
  }'
```

---

## 🔹 Integração com Python

### Cliente Simples

```python
import requests

BASE_URL = "http://localhost:8001"

def chat(message: str, history=None):
    payload = {
        "message": message,
        "source": "python_client",
        "input_type": "text"
    }
    if history:
        payload["history"] = history

    response = requests.post(f"{BASE_URL}/chat/", json=payload)
    return response.json()["reply"]

# Uso
reply = chat("Olá!")
print(reply)
```

### Cliente com Tasks

```python
import requests

BASE_URL = "http://localhost:8001"

def run_task(task_name: str, params: dict):
    payload = {
        "task_name": task_name,
        "params": params,
        "source": "python_client"
    }
    response = requests.post(f"{BASE_URL}/tasks/run", json=payload)
    return response.json()

# Exemplos
run_task("say", {"text": "Olá do Python!"})
run_task("notification", {
    "title": "Python",
    "message": "Tarefa executada"
})
```

---

## 🔹 Integração com JavaScript/Node.js

### Cliente Node.js

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8001';

async function chat(message, history = null) {
  const payload = {
    message,
    source: 'nodejs_client',
    input_type: 'text'
  };

  if (history) {
    payload.history = history;
  }

  const response = await axios.post(`${BASE_URL}/chat/`, payload);
  return response.data.reply;
}

// Uso
chat('Olá!').then(reply => console.log(reply));
```

---

## 🔹 Webhook para Automações Externas

### Exemplo: Trigger via HTTP

Crie um endpoint que recebe webhooks e processa:

```python
from fastapi import APIRouter
import httpx

router = APIRouter()

@router.post("/webhook/process")
async def webhook_handler(payload: dict):
    # Extrair dados do webhook
    message = payload.get("message")

    # Chamar FoKS Intelligence
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/chat/",
            json={
                "message": message,
                "source": "webhook",
                "metadata": payload
            }
        )
        result = response.json()

    # Processar resposta
    return {"reply": result["reply"]}
```

---

## 🔹 Integração com Obsidian

### Plugin ou Script

Crie um script que envia notas do Obsidian para o FoKS:

```javascript
// Obsidian plugin example
async function sendToFoKS(content) {
  const response = await fetch('http://localhost:8001/chat/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: content,
      source: 'obsidian',
      input_type: 'text',
      metadata: {
        vault: app.vault.getName(),
        file: this.app.workspace.getActiveFile()?.name
      }
    })
  });

  const data = await response.json();
  return data.reply;
}
```

---

## 🔹 Exemplo de Workflow Completo

### Fluxo: Screenshot → Análise → Ação

1. **Tirar Screenshot** (via task)
2. **Analisar Imagem** (via vision endpoint)
3. **Processar Resposta** (via chat)
4. **Executar Ação** (via task)

```bash
# 1. Screenshot
SCREENSHOT=$(curl -s -X POST http://localhost:8001/tasks/run \
  -H "Content-Type: application/json" \
  -d '{"task_name": "screenshot", "params": {"type": "full"}}' \
  | jq -r '.data.image_base64')

# 2. Analisar
ANALYSIS=$(curl -s -X POST http://localhost:8001/vision/analyze \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$SCREENSHOT\", \"description\": \"O que há nesta imagem?\"}")

# 3. Chat com resultado
REPLY=$(curl -s -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Analise esta imagem e sugira uma ação\", \"source\": \"workflow\"}")

# 4. Notificar
curl -X POST http://localhost:8001/tasks/run \
  -H "Content-Type: application/json" \
  -d "{\"task_name\": \"notification\", \"params\": {\"message\": \"$REPLY\"}}"
```

---

## 📝 Notas

- Todas as integrações usam `http://localhost:8001` como base URL
- Para produção, configure CORS adequadamente
- Use variáveis de ambiente para URLs em diferentes ambientes
- Logs estão disponíveis em `logs/app.log`

