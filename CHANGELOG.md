# 📝 Changelog - FoKS Intelligence

## [1.3.0] - Monitoring & System Info

### ✨ Novas Features

#### Monitoramento
- ✅ Sistema de métricas completo (`/metrics`)
- ✅ Middleware de monitoramento automático
- ✅ Rastreamento de requests (tempo, sucesso, erros)
- ✅ Rastreamento de tasks (tempo, sucesso por tipo)
- ✅ Uptime tracking formatado

#### System Info
- ✅ Endpoint `/system/info` com informações do sistema
- ✅ Endpoint `/system/metrics` (alias para `/metrics`)
- ✅ Informações detalhadas: Python version, platform, architecture

#### Utilitários
- ✅ `app/utils/helpers.py` com funções auxiliares:
  - `generate_request_id()` - IDs únicos
  - `encode_base64_image()` - Codificação de imagens
  - `format_response_time()` - Formatação de tempo
  - `safe_get_nested()` - Acesso seguro a dicts aninhados
  - `truncate_text()` - Truncamento de texto

#### Scripts
- ✅ `scripts/check_health.sh` - Script de health check completo

### 🔧 Melhorias

- Métricas são coletadas automaticamente em todas as requisições
- Tasks registram tempo de execução
- Health check melhorado com mais informações

### 📦 Testes

- ✅ Testes para `MonitoringService` (7 testes)
- ✅ Testes para helpers (5 testes)
- ✅ Total: 38 testes (100% passando)

---

## [1.2.0] - Best Practices Implementation

### ✨ Novas Features

#### Qualidade de Código
- ✅ Testes unitários e de integração (26 testes, 100% passando)
- ✅ Type hints completos em todo o código
- ✅ Docstrings Google-style em todas as funções públicas
- ✅ Configuração de linting (Ruff) e formatação (Black)
- ✅ Type checking com MyPy
- ✅ Pre-commit hooks configurados

#### Segurança e Validação
- ✅ Validação robusta de inputs em `app/utils/validators.py`
- ✅ Sanitização de texto para prevenir injection
- ✅ Rate limiting middleware (60 req/min por IP)
- ✅ Exception handler global
- ✅ Validação de parâmetros de tasks antes da execução

#### Infraestrutura
- ✅ Makefile com comandos de desenvolvimento
- ✅ `.gitignore` completo
- ✅ `.env.example` documentado
- ✅ Health check detalhado com informações do sistema
- ✅ Documentação de melhores práticas

#### Observabilidade
- ✅ Logging estruturado melhorado
- ✅ Logs detalhados com contexto
- ✅ Exception tracking com stack traces

### 🔧 Melhorias

- Health check agora retorna versão, Python version, platform e status de configurações
- Validação de tasks retorna 400 Bad Request em vez de executar e falhar
- Compatibilidade Pydantic v2 (model_dump vs dict)
- Código formatado e lintado

### 📦 Dependências

- Adicionado: pytest, pytest-asyncio, pytest-cov
- Adicionado: black, ruff, mypy, pre-commit
- Adicionado: slowapi (para rate limiting futuro)

---

## [1.1.0] - Expansão de Funcionalidades

### ✨ Novas Features

#### Tasks Expandidas
- ✅ `notification` - Enviar notificações macOS
- ✅ `get_clipboard` - Obter conteúdo do clipboard
- ✅ `set_clipboard` - Definir conteúdo do clipboard
- ✅ `screenshot` - Tirar screenshots (full/window/selection) e retornar base64
- ✅ `open_app` - Abrir aplicativos macOS

#### Vision Endpoint Melhorado
- ✅ Suporte a processamento de imagens base64
- ✅ Extração de metadados de imagem (formato, dimensões)
- ✅ Preparado para integração com modelos vision

#### Documentação
- ✅ Guia completo de integração (n8n, Node-RED, Python, JS)
- ✅ Exemplos práticos de uso
- ✅ Scripts de teste para novas funcionalidades

### 🔧 Melhorias

- TaskRunner refatorado com arquitetura mais escalável
- Melhor tratamento de erros em todas as tasks
- Logs mais detalhados

### 📦 Dependências

- Adicionado `pillow` para processamento de imagens

---

## [1.0.0] - Versão Inicial

### ✨ Features Iniciais

- ✅ Backend FastAPI completo
- ✅ Integração com LM Studio
- ✅ Endpoints: `/chat/`, `/vision/analyze`, `/tasks/run`
- ✅ Tasks básicas: `say`, `open_url`, `run_script`
- ✅ Sistema de logging
- ✅ Scripts de inicialização
- ✅ Control Center interativo
- ✅ Documentação básica

