# 🚀 FoKS Intelligence - Quick Start

## ✅ Status Atual

- ✅ Backend FastAPI rodando na porta **8001**
- ✅ Integrado com LM Studio em `http://127.0.0.1:1234`
- ✅ Todos os endpoints testados e funcionando
- ✅ Documentação completa criada

## 🎯 Próximo Passo: Criar Atalho macOS

Siga o guia completo em: **[docs/SHORTCUT_SETUP.md](docs/SHORTCUT_SETUP.md)**

## 📋 Checklist Rápido

1. ✅ Backend iniciado: `./scripts/start_backend.sh`
2. ✅ LM Studio rodando e servidor ativo
3. ⏳ Criar atalho "FoKS Intelligence" no app Atalhos
4. ⏳ Testar fluxo completo: Atalho → FastAPI → LM Studio → Resposta

## 🔧 Comandos Úteis

```bash
# Iniciar backend
./scripts/start_backend.sh

# Control Center
./scripts/foks_control_center.sh

# Testar endpoints
./scripts/test_endpoints.sh

# Ver logs
tail -f logs/app.log

# Health check
curl http://localhost:8001/health
```

## 📚 Documentação

- [Guia do Atalho macOS](docs/SHORTCUT_SETUP.md)
- [Referência da API](docs/API_REFERENCE.md)
- [README Principal](README.md)
