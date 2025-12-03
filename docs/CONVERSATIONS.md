# 💬 FoKS Intelligence - Sistema de Conversas

Documentação do sistema de histórico de conversas persistente.

---

## Visão Geral

O sistema de conversas permite:
- Armazenar histórico de conversas
- Continuar conversas existentes
- Gerenciar múltiplas conversas
- Acessar histórico completo de mensagens

---

## Endpoints

### Criar Conversa

**POST** `/conversations/`

```json
{
  "user_id": "user123",
  "title": "Minha Conversa",
  "source": "shortcuts"
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": "user123",
  "title": "Minha Conversa",
  "source": "shortcuts",
  "created_at": "2025-11-29T10:00:00",
  "updated_at": "2025-11-29T10:00:00",
  "message_count": 0
}
```

### Listar Conversas

**GET** `/conversations/?user_id=user123&limit=50&offset=0`

**Response:**
```json
{
  "conversations": [...],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

### Obter Conversa

**GET** `/conversations/{conversation_id}?user_id=user123`

### Obter Mensagens

**GET** `/conversations/{conversation_id}/messages?user_id=user123`

### Deletar Conversa

**DELETE** `/conversations/{conversation_id}?user_id=user123`

### Atualizar Título

**PATCH** `/conversations/{conversation_id}/title?title=Novo Título`

---

## Integração com Chat

### Continuar Conversa Existente

```bash
curl -X POST "http://localhost:8001/chat/?conversation_id=1&user_id=user123" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Continue nossa conversa",
    "source": "shortcuts"
  }'
```

O histórico será carregado automaticamente da conversa.

### Nova Conversa

Se não fornecer `conversation_id`, será uma nova conversa sem histórico.

---

## Banco de Dados

### Schema

**Conversations:**
- `id` (PK)
- `user_id` (indexed)
- `title`
- `source`
- `created_at`
- `updated_at`

**Messages:**
- `id` (PK)
- `conversation_id` (FK)
- `role` (user/assistant/system)
- `content`
- `created_at`

### Localização

Banco SQLite em:
```
/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/data/conversations.db
```

---

## Exemplos de Uso

### Fluxo Completo

```python
import requests

BASE_URL = "http://localhost:8001"

# 1. Criar conversa
conv = requests.post(f"{BASE_URL}/conversations/", json={
    "user_id": "user123",
    "title": "Minha Conversa"
}).json()

conv_id = conv["id"]

# 2. Enviar mensagem com histórico
response = requests.post(
    f"{BASE_URL}/chat/?conversation_id={conv_id}&user_id=user123",
    json={"message": "Olá!", "source": "python"}
).json()

# 3. Ver mensagens
messages = requests.get(
    f"{BASE_URL}/conversations/{conv_id}/messages"
).json()
```

---

## Limpeza Automática

Para limpar conversas antigas (opcional):

```python
from app.services.conversation_store import conversation_store

# Deletar conversas com mais de 30 dias
deleted = conversation_store.cleanup_old_conversations(days=30)
```

