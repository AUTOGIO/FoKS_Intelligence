# FoKS Intelligence - Plano de Disaster Recovery

## Objetivo

Documentar procedimentos para recuperação após falhas críticas do sistema.

## Cenários de Desastre

### 1. Perda de Banco de Dados

**Sintomas:**
- Erros de conexão com banco
- Arquivo de banco corrompido ou ausente
- Health check retorna `database: error`

**Procedimento de Recuperação:**

1. **Verificar backups disponíveis:**
   ```bash
   ls -lh backups/conversations_*.db
   ```

2. **Restaurar backup mais recente:**
   ```bash
   BACKUP_FILE="backups/conversations_YYYYMMDD_HHMMSS.db"
   cp "$BACKUP_FILE" backend/data/conversations.db
   ```

3. **Verificar integridade:**
   ```bash
   sqlite3 backend/data/conversations.db "PRAGMA integrity_check;"
   ```

4. **Reiniciar serviço:**
   ```bash
   ./scripts/deploy.sh
   ```

5. **Verificar funcionamento:**
   ```bash
   curl http://localhost:8001/health
   ```

**Prevenção:**
- Backups automáticos diários (cron)
- Verificação de integridade periódica
- Múltiplos backups (local + remoto)

### 2. Perda de Logs

**Sintomas:**
- Logs não estão sendo escritos
- Diretório de logs corrompido

**Procedimento de Recuperação:**

1. **Restaurar logs de backup:**
   ```bash
   ./scripts/backup_logs.sh  # Se ainda não foi executado
   tar -xzf backups/logs/history_TIMESTAMP.tar.gz -C logs/
   ```

2. **Recriar estrutura de logs:**
   ```bash
   mkdir -p logs/history
   touch logs/app.log
   ```

3. **Verificar permissões:**
   ```bash
   chmod 644 logs/app.log
   ```

**Prevenção:**
- Backup automático de logs
- Rotação configurada corretamente
- Monitoramento de espaço em disco

### 3. Falha do LM Studio

**Sintomas:**
- Health check retorna `lmstudio: disconnected`
- Erros 503 em endpoints de chat
- Circuit breaker aberto

**Procedimento de Recuperação:**

1. **Verificar status do LM Studio:**
   ```bash
   curl http://127.0.0.1:1234/v1/models
   ```

2. **Reiniciar LM Studio:**
   - Abrir LM Studio
   - Verificar se servidor está rodando
   - Reiniciar servidor se necessário

3. **Resetar circuit breaker (se necessário):**
   ```python
   # Via endpoint ou código
   from app.utils.circuit_breaker import lmstudio_circuit_breaker
   lmstudio_circuit_breaker.reset()
   ```

4. **Verificar health check:**
   ```bash
   curl http://localhost:8001/health
   ```

**Prevenção:**
- Monitoramento do LM Studio
- Alertas quando desconectado
- Circuit breaker para prevenir cascading failures

### 4. Corrupção de Configuração

**Sintomas:**
- Aplicação não inicia
- Erros de validação de configuração
- Variáveis de ambiente incorretas

**Procedimento de Recuperação:**

1. **Verificar variáveis de ambiente:**
   ```bash
   env | grep FOKS
   env | grep LMSTUDIO
   ```

2. **Restaurar de .env.example:**
   ```bash
   cp backend/.env.example backend/.env
   # Editar .env com valores corretos
   ```

3. **Validar configuração:**
   ```bash
   cd backend
   source .venv_foks/bin/activate
   python -c "from app.config import validate_settings; validate_settings()"
   ```

4. **Reiniciar serviço:**
   ```bash
   ./scripts/deploy.sh
   ```

**Prevenção:**
- `.env.example` sempre atualizado
- Documentação de variáveis
- Validação no startup

### 5. Falha Completa do Sistema

**Sintomas:**
- Serviço não responde
- Múltiplos componentes falhando
- Sistema inacessível

**Procedimento de Recuperação:**

1. **Diagnóstico inicial:**
   ```bash
   # Verificar processos
   ps aux | grep uvicorn
   ps aux | grep python

   # Verificar logs
   tail -100 logs/app.log

   # Verificar recursos
   df -h
   free -h
   ```

2. **Parar todos os processos:**
   ```bash
   pkill -f "uvicorn app.main:app"
   pkill -f "foks"
   ```

3. **Backup de estado atual:**
   ```bash
   ./scripts/backup_database.sh
   ./scripts/backup_logs.sh
   ```

4. **Verificar integridade:**
   ```bash
   # Database
   sqlite3 backend/data/conversations.db "PRAGMA integrity_check;"

   # Dependências
   cd backend
   source .venv_foks/bin/activate
   pip check
   ```

5. **Recuperação completa:**
   ```bash
   ./scripts/deploy.sh
   ```

6. **Verificação pós-recuperação:**
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8001/metrics
   ```

## Testes de Restore

### Teste Mensal de Restore

1. **Criar ambiente de teste:**
   ```bash
   mkdir -p test_restore
   cd test_restore
   ```

2. **Restaurar backup de teste:**
   ```bash
   cp ../backups/conversations_*.db test.db
   ```

3. **Verificar dados:**
   ```bash
   sqlite3 test.db "SELECT COUNT(*) FROM conversations;"
   sqlite3 test.db "SELECT COUNT(*) FROM messages;"
   ```

4. **Testar queries:**
   ```bash
   sqlite3 test.db "SELECT * FROM conversations LIMIT 5;"
   ```

5. **Limpar ambiente de teste:**
   ```bash
   rm -rf test_restore
   ```

## RTO e RPO

### Recovery Time Objective (RTO)
- **Crítico:** < 15 minutos
- **Importante:** < 1 hora
- **Normal:** < 4 horas

### Recovery Point Objective (RPO)
- **Backup de banco:** Diário (2 AM)
- **Backup de logs:** Semanal
- **Configuração:** Versionada no Git

## Checklist de Recuperação

- [ ] Identificar tipo de desastre
- [ ] Verificar backups disponíveis
- [ ] Parar serviços afetados
- [ ] Fazer backup de estado atual (se possível)
- [ ] Restaurar de backup
- [ ] Verificar integridade dos dados
- [ ] Reiniciar serviços
- [ ] Verificar funcionamento
- [ ] Documentar incidente
- [ ] Atualizar procedimentos se necessário

## Contatos de Emergência

- **Desenvolvedor:** [Seu contato]
- **Infraestrutura:** [Contato infra]
- **Suporte:** [Contato suporte]

## Documentação Relacionada

- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Deployment Guide](DEPLOYMENT.md)
- [PostgreSQL Setup](POSTGRESQL_SETUP.md)

