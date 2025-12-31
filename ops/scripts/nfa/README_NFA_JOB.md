# NFA Job CLI - Guia de Uso

Script CLI robusto para automação de download de NFAs do portal SEFAZ-PB ATF.

---

## 🚀 Setup Inicial

### 1. Instalar Dependências

```bash
# Executar script de setup
./ops/scripts/nfa/setup_nfa_job.sh
```

Ou manualmente:

```bash
cd backend
source .venv_foks/bin/activate
pip install playwright>=1.40.0
playwright install chromium
```

### 2. Configurar Credenciais

```bash
export NFA_USERNAME="seu_usuario"
export NFA_PASSWORD="sua_senha"
```

---

## 📖 Uso Básico

### Executar Job

```bash
python3 ops/scripts/nfa/nfa_job.py \
  --data-inicial 08/12/2025 \
  --data-final 10/12/2025 \
  --matricula 1595504
```

### Opções Disponíveis

- `--data-inicial` (obrigatório): Data inicial no formato `dd/mm/yyyy`
- `--data-final` (obrigatório): Data final no formato `dd/mm/yyyy`
- `--matricula` (opcional): Matrícula do funcionário (padrão: `1595504`)
- `--username` (opcional): Username ATF (padrão: variável `NFA_USERNAME`)
- `--password` (opcional): Password ATF (padrão: variável `NFA_PASSWORD`)
- `--headless` (padrão): Executar browser em modo headless
- `--no-headless`: Executar browser com interface visível (útil para debug)

---

## 📊 Saída

### Formato JSON

O script imprime um JSON estruturado no stdout:

```json
{
  "status": "ok",
  "nfa_numero": "900501884",
  "danfe_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_DANFE.pdf",
  "dar_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_DAR.pdf",
  "started_at": "2025-12-11T04:22:02.123456",
  "finished_at": "2025-12-11T04:22:45.789012",
  "error": null
}
```

### Log JSONL

Cada execução é logada em:
```
/Users/dnigga/Downloads/NFA_Outputs/nfa_runs.jsonl
```

Formato: uma linha JSON por execução.

---

## 🔧 Integração com FoKS

### Via TaskRunner

O script pode ser chamado via TaskRunner:

```bash
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "run_shell",
    "params": {
      "cmd": "python3 /path/to/nfa_job.py --data-inicial 08/12/2025 --data-final 10/12/2025"
    }
  }'
```

### Via NFA Intelligence Layer

Use o endpoint de batch processing:

```bash
curl -X POST http://localhost:8000/nfa/intelligence/run \
  -H "Content-Type: application/json" \
  -d '{
    "from_date": "08/12/2025",
    "to_date": "10/12/2025",
    "employees": "auto",
    "headless": true
  }'
```

---

## 🐛 Troubleshooting

### Browser não encontrado

```bash
playwright install chromium
```

### Credenciais inválidas

Verifique as variáveis de ambiente:
```bash
echo $NFA_USERNAME
echo $NFA_PASSWORD
```

### Timeout errors

Aumente os timeouts no código ou verifique conexão de rede.

### Downloads não funcionam

- Verifique se `accept_downloads=True` está configurado
- Verifique permissões do diretório `/Users/dnigga/Downloads/NFA_Outputs`
- Tente executar com `--no-headless` para ver o que acontece

---

## 📚 Documentação Completa

Veja `docs/NFA_Automation_Spec.md` para:
- Especificação completa do fluxo
- Seletores CSS detalhados
- Tratamento de iframes
- Estratégias de retry
- Formato de logs

---

## ✅ Checklist de Teste

- [ ] Playwright instalado e browsers baixados
- [ ] Credenciais configuradas (env vars)
- [ ] Diretório de output existe e é gravável
- [ ] Teste com `--no-headless` para debug visual
- [ ] Verificar logs JSONL após execução
- [ ] Validar PDFs baixados

---

**Status:** ✅ Pronto para uso  
**Última atualização:** 2025-12-11
