# 🚀 FoKS Intelligence - Deployment Guide

Guia completo para deploy em produção.

---

## 📋 Pré-requisitos

- Python 3.9+
- LM Studio rodando (ou outro servidor OpenAI-compatible)
- macOS (para tasks nativas) ou Linux (backend apenas)

---

## 🔧 Opção 1: Deploy Local (macOS)

### Passo 1: Configurar Ambiente

```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend
cp .env.example .env
# Edite .env com suas configurações
```

### Passo 2: Instalar Dependências

```bash
python3 -m venv .venv_foks
source .venv_foks/bin/activate
pip install -r requirements.txt
```

### Passo 3: Iniciar Servidor

```bash
# Usando script
../scripts/start_backend.sh

# Ou diretamente
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Passo 4: Verificar

```bash
curl http://localhost:8000/health
```

---

## 🐳 Opção 2: Deploy com Docker

### Passo 1: Build da Imagem

```bash
cd backend
docker build -t foks-intelligence:latest .
```

### Passo 2: Rodar Container

```bash
docker run -d \
  --name foks-backend \
  -p 8000:8000 \
  -e FOKS_ENV=production \
  -e LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1/chat/completions \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  foks-intelligence:latest
```

### Passo 3: Usar docker-compose

```bash
docker-compose up -d
```

---

## 🔒 Segurança em Produção

### 1. Configurar API Key

```bash
# No .env
API_KEY=seu-token-secreto-aqui
```

### 2. Configurar CORS

```bash
# No .env
ALLOWED_ORIGINS=https://seu-dominio.com,https://app.seu-dominio.com
```

### 3. Usar HTTPS

Configure um reverse proxy (nginx, Caddy) com certificado SSL.

### 4. Rate Limiting

```bash
# No .env
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

---

## 📊 Monitoramento

### Health Checks

```bash
# Health check básico
curl http://localhost:8000/health

# Métricas
curl http://localhost:8000/metrics
```

### Logs

```bash
# Ver logs em tempo real
tail -f logs/app.log

# Filtrar erros
grep ERROR logs/app.log
```

---

## 💾 Backup

### Backup Manual

```bash
./scripts/backup_database.sh
```

### Backup Automático (cron)

```bash
# Adicionar ao crontab
0 2 * * * /path/to/scripts/backup_database.sh
```

---

## 🔄 Atualizações

### 1. Parar Servidor

```bash
# Docker
docker stop foks-backend

# Local
pkill -f "uvicorn app.main:app"
```

### 2. Backup

```bash
./scripts/backup_database.sh
```

### 3. Atualizar Código

```bash
git pull
pip install -r requirements.txt  # Se houver novas dependências
```

### 4. Restart

```bash
# Docker
docker start foks-backend

# Local
./scripts/start_backend.sh
```

---

## 🐛 Troubleshooting

### Porta já em uso

```bash
# Verificar processo
lsof -i :8000

# Matar processo
kill -9 <PID>
```

### Banco de dados travado

```bash
# SQLite pode travar em alta concorrência
# Considere migrar para PostgreSQL em produção
```

### LM Studio não responde

```bash
# Verificar se LM Studio está rodando
curl http://127.0.0.1:1234/v1/models

# Verificar logs do LM Studio
```

---

## 📈 Escalabilidade

### Para Alta Carga

1. **Migrar para PostgreSQL** (em vez de SQLite)
2. **Adicionar Redis** para cache
3. **Load Balancer** com múltiplas instâncias
4. **CDN** para assets estáticos

---

## ✅ Checklist de Deploy

- [ ] Variáveis de ambiente configuradas
- [ ] API key configurada (produção)
- [ ] CORS configurado corretamente
- [ ] Backup automático configurado
- [ ] Logs configurados
- [ ] Health checks funcionando
- [ ] Monitoramento ativo
- [ ] Documentação atualizada

---

## 📚 Próximos Passos

Veja [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) para melhorias adicionais.

