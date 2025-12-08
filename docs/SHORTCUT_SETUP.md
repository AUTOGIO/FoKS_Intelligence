# 🎯 Guia: Criar Atalho "FoKS Intelligence" no macOS

Este guia mostra como criar o atalho macOS que conecta com o backend FoKS Intelligence.

## 📋 Pré-requisitos

- ✅ Backend FoKS rodando em `http://localhost:8000`
- ✅ LM Studio ativo e servidor OpenAI-compatible rodando
- ✅ App **Atalhos** (Shortcuts) instalado no macOS

---

## 🔹 Passo 1: Criar Novo Atalho

1. Abra o app **Atalhos** (Shortcuts)
2. Clique em **"+"** (canto superior direito) para criar novo atalho
3. Nomeie como: **"FoKS Intelligence"**

---

## 🔹 Passo 2: Adicionar Ação "Perguntar"

1. Na barra de busca, digite: **"Perguntar"** ou **"Ask for Input"**
2. Selecione a ação **"Perguntar"** (Ask for Input)
3. Configure:
   - **Pergunta**: `FoKS: o que você quer fazer?`
   - **Tipo de entrada**: Texto
   - **Permitir múltiplas linhas**: Sim (opcional)
4. A variável será salva automaticamente como **"Texto Perguntado"** (ou "Ask for Input")

---

## 🔹 Passo 3: Criar Dicionário JSON

1. Busque a ação: **"Dicionário"** (Dictionary)
2. Adicione os seguintes campos:

| Chave | Valor | Tipo |
|-------|-------|------|
| `message` | `Texto Perguntado` (variável do passo anterior) | Texto |
| `input_type` | `text` | Texto |
| `source` | `shortcuts` | Texto |
| `metadata` | (criar outro dicionário) | Dicionário |

### 3.1 Criar sub-dicionário "metadata"

Dentro do campo `metadata`, crie outro dicionário com:

| Chave | Valor |
|-------|-------|
| `device` | `iMac_M3` |
| `shortcut_name` | `FoKS Intelligence` |

3. Salve o dicionário completo em uma variável chamada: **Payload**

---

## 🔹 Passo 4: Fazer Requisição HTTP POST

1. Busque a ação: **"Obter Conteúdo de URL"** (Get Contents of URL)
2. Configure:
   - **URL**: `http://localhost:8000/chat/`
   - **Método**: `POST`
   - **Cabeçalhos**: Adicionar novo cabeçalho
     - **Nome**: `Content-Type`
     - **Valor**: `application/json`
   - **Corpo da Requisição**: `JSON`
   - **Corpo**: Selecionar variável **Payload** (do passo anterior)
3. Salvar resultado em variável: **Response**

---

## 🔹 Passo 5: Extrair Resposta

1. Busque a ação: **"Obter valor para chave"** (Get Dictionary Value)
2. Configure:
   - **Dicionário**: `Response` (variável do passo anterior)
   - **Chave**: `reply`
3. Salvar em variável: **ReplyText**

---

## 🔹 Passo 6: Mostrar Resultado

1. Busque a ação: **"Mostrar Notificação"** (Show Notification)
2. Configure:
   - **Título**: `FoKS Intelligence`
   - **Corpo**: `ReplyText` (variável do passo anterior)
   - **Som**: Opcional

**OU**

1. Busque a ação: **"Mostrar Resultado"** (Show Result)
2. Configure:
   - **Resultado**: `ReplyText`

---

## 🔹 Passo 7 (Opcional): Falar Resposta

1. Busque a ação: **"Falar Texto"** (Speak Text)
2. Configure:
   - **Texto**: `ReplyText`
   - **Voz**: Escolha sua voz preferida
   - **Taxa de fala**: Ajuste conforme preferência

---

## 📸 Estrutura Final do Atalho

```
FoKS Intelligence
├── Perguntar
│   └── "FoKS: o que você quer fazer?"
├── Dicionário (Payload)
│   ├── message → Texto Perguntado
│   ├── input_type → "text"
│   ├── source → "shortcuts"
│   └── metadata
│       ├── device → "iMac_M3"
│       └── shortcut_name → "FoKS Intelligence"
├── Obter Conteúdo de URL
│   ├── URL: http://localhost:8000/chat/
│   ├── Método: POST
│   ├── Cabeçalho: Content-Type: application/json
│   └── Corpo: Payload (JSON)
├── Obter valor para chave
│   ├── Dicionário: Response
│   └── Chave: "reply"
├── Mostrar Notificação
│   └── Corpo: ReplyText
└── (Opcional) Falar Texto
    └── Texto: ReplyText
```

---

## 🧪 Testar o Atalho

1. Execute o atalho "FoKS Intelligence"
2. Quando perguntado, digite: `Explique em uma frase o que é inteligência artificial`
3. Aguarde a resposta do LM Studio
4. Verifique a notificação com a resposta

---

## 🔧 Troubleshooting

### Erro: "Não foi possível conectar"
- Verifique se o backend está rodando: `curl http://localhost:8000/health`
- Confirme que a porta está correta (8000)

### Erro: "400 Bad Request"
- Verifique se o JSON está correto
- Confirme que o campo `message` não está vazio

### Erro: "500 Internal Server Error"
- Verifique os logs: `tail -f /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/logs/app.log`
- Confirme que o LM Studio está rodando

---

## 🚀 Próximas Melhorias

- [ ] Adicionar menu de opções (Texto / Voz / Screenshot)
- [ ] Suporte a entrada por voz (Siri)
- [ ] Histórico de conversas
- [ ] Integração com Clipboard para screenshots

