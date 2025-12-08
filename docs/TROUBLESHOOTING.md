# Troubleshooting Guide

Este guia cobre problemas comuns e soluções para o FoKS Intelligence.

## Problemas Comuns

### 1. LM Studio não está conectado

**Sintomas:**
- Health check retorna `lmstudio: disconnected`
- Erros 503 ao fazer requisições de chat
- Logs mostram "LM Studio network error"

**Soluções:**
1. Verifique se o LM Studio está rodando:
   ```bash
   curl http://127.0.0.1:1234/v1/models
   ```

2. Verifique a URL configurada:
   ```bash
   echo $LMSTUDIO_BASE_URL
   ```
   Deve ser: `http://127.0.0.1:1234/v1/chat/completions`

3. Verifique se a porta está correta (padrão: 1234)

4. Reinicie o LM Studio e o backend:
   ```bash
   # No LM Studio, verifique se o servidor está ativo
   # Reinicie o backend
   cd backend
   source .venv_foks/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### 2. Erro de autenticação (401 Unauthorized)

**Sintomas:**
- Requisições retornam 401
- Mensagem: "Invalid or missing API key"

**Soluções:**
1. Se `API_KEY` estiver configurado, inclua no header:
   ```bash
   curl -H "X-API-Key: sua-chave-aqui" http://localhost:8000/chat/
   ```

2. Para desenvolvimento, remova `API_KEY` do ambiente ou não configure

3. Endpoints públicos não requerem autenticação:
   - `/health`
   - `/docs`
   - `/redoc`
   - `/openapi.json`

### 3. Erro de banco de dados

**Sintomas:**
- Health check retorna `database: error`
- Erros ao criar/listar conversas
- Mensagem: "Database error"

**Soluções:**

**SQLite:**
1. Verifique permissões do arquivo:
   ```bash
   ls -la backend/data/conversations.db
   ```

2. Verifique se o diretório existe:
   ```bash
   mkdir -p backend/data
   ```

3. Verifique espaço em disco:
   ```bash
   df -h
   ```

**PostgreSQL:**
1. Verifique se o PostgreSQL está rodando:
   ```bash
   pg_isready
   ```

2. Verifique a string de conexão:
   ```bash
   echo $DATABASE_URL
   ```
   Formato: `postgresql://user:password@host:port/database`

3. Teste a conexão:
   ```bash
   psql $DATABASE_URL -c "SELECT 1;"
   ```

4. Verifique se o banco existe:
   ```bash
   psql $DATABASE_URL -c "\l"
   ```

### 4. Rate limit excedido (429)

**Sintomas:**
- Requisições retornam 429
- Mensagem: "Rate limit exceeded"

**Soluções:**
1. Aguarde 1 minuto antes de fazer novas requisições

2. Aumente o limite (desenvolvimento):
   ```bash
   export RATE_LIMIT_REQUESTS_PER_MINUTE=120
   ```

3. Para produção, considere usar Redis para rate limiting distribuído

### 5. Erro de validação de configuração

**Sintomas:**
- Aplicação não inicia
- Mensagem: "Configuration validation failed"

**Soluções:**
1. Verifique variáveis obrigatórias:
   ```bash
   echo $LMSTUDIO_BASE_URL
   ```

2. Para produção, verifique:
   - `API_KEY` está configurado
   - `ALLOWED_ORIGINS` não inclui localhost
   - `DATABASE_URL` não usa localhost

3. Para testes, desabilite validação:
   ```bash
   export SKIP_CONFIG_VALIDATION=true
   ```

### 6. Cache não está funcionando

**Sintomas:**
- Conversas sempre vêm do banco
- Performance não melhora

**Soluções:**
1. Verifique se o cache está habilitado:
   ```bash
   echo $CACHE_ENABLED
   ```
   Deve ser `true` (padrão)

2. Verifique estatísticas do cache:
   ```bash
   # Adicione endpoint de stats do cache se necessário
   ```

3. Limpe o cache se necessário (reiniciar aplicação)

### 7. Streaming não funciona

**Sintomas:**
- Endpoint `/chat/stream` retorna erro
- Resposta não chega em chunks

**Soluções:**
1. Verifique se o LM Studio suporta streaming:
   - Alguns modelos/configurações não suportam
   - Verifique logs do LM Studio

2. Teste com curl:
   ```bash
   curl -N -H "Content-Type: application/json" \
     -d '{"message":"test"}' \
     http://localhost:8000/chat/
   ```

3. Verifique timeout:
   - Streaming pode demorar mais
   - Aumente `REQUEST_TIMEOUT_SECONDS` se necessário

## Como Debugar Erros

### 1. Verificar Logs

**Localização dos logs:**
```bash
tail -f logs/app.log
```

**Níveis de log:**
- `INFO`: Operações normais
- `WARNING`: Avisos (rate limit, cache miss, etc.)
- `ERROR`: Erros que não impedem execução
- `CRITICAL`: Erros que impedem execução

### 2. Health Check

Sempre verifique o health check primeiro:
```bash
curl http://localhost:8000/health | jq
```

Verifique:
- `status`: `ok` ou `degraded`
- `services.lmstudio`: `connected` ou `disconnected`
- `services.database`: `connected` ou `error`

### 3. Métricas

Verifique métricas para entender o comportamento:
```bash
curl http://localhost:8000/metrics | jq
```

Métricas importantes:
- `total_requests`: Total de requisições
- `total_tasks`: Total de tarefas executadas
- `error_count`: Número de erros
- `uptime_seconds`: Tempo de execução

### 4. Testar Endpoints Individualmente

```bash
# Health
curl http://localhost:8000/health

# Chat (requer LM Studio)
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}'

# Conversas
curl http://localhost:8000/conversations/?user_id=test
```

## Logs Importantes para Análise

### Erros de LM Studio
```
ERROR: LM Studio error: ... (code: LM_STUDIO_NETWORK_ERROR)
```
- Indica problema de conectividade
- Verifique se LM Studio está rodando

### Erros de Banco de Dados
```
ERROR: Database error: ...
```
- Indica problema com SQLite ou PostgreSQL
- Verifique conexão e permissões

### Rate Limit
```
WARNING: Rate limit exceeded for IP: ...
```
- Normal em produção
- Considere aumentar limite ou usar Redis

### Cache
```
DEBUG: Cache hit for conversation ...
DEBUG: Cache expired for conversation ...
```
- Indica funcionamento do cache
- Cache hits melhoram performance

## Como Reportar Bugs

Ao reportar um bug, inclua:

1. **Versão:**
   ```bash
   python --version
   # E versão do código (git commit)
   ```

2. **Configuração:**
   - Variáveis de ambiente relevantes (sem senhas)
   - Sistema operacional
   - Hardware (se relevante para M3)

3. **Logs:**
   - Últimas 50 linhas de `logs/app.log`
   - Output do health check

4. **Passos para reproduzir:**
   - Comandos exatos executados
   - Payloads de requisições

5. **Comportamento esperado vs. atual:**
   - O que deveria acontecer
   - O que realmente acontece

## Recursos Adicionais

- [Documentação da API](API_REFERENCE.md)
- [Guia de Deploy](DEPLOYMENT.md)
- [Otimizações M3](M3_OPTIMIZATION.md)
- [Monitoramento](MONITORING.md)

