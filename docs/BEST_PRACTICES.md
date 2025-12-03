# 🏆 FoKS Intelligence - Best Practices Guide

Este documento descreve as melhores práticas implementadas no projeto.

---

## 📋 Estrutura do Projeto

### Organização de Diretórios

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configurações
│   ├── models.py            # Modelos Pydantic
│   ├── routers/             # Endpoints da API
│   ├── services/            # Lógica de negócio
│   ├── middleware/          # Middlewares customizados
│   └── utils/               # Utilitários
├── tests/                   # Testes unitários e de integração
├── pyproject.toml          # Configuração de ferramentas
├── requirements.txt        # Dependências
└── Makefile                # Comandos de desenvolvimento
```

---

## ✅ Qualidade de Código

### Type Hints

Todos os arquivos Python usam type hints:

```python
def process_message(message: str, history: Optional[List[ChatMessage]] = None) -> Dict[str, Any]:
    ...
```

### Docstrings

Todas as funções públicas têm docstrings:

```python
def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    """
    Process chat message with LM Studio.

    Args:
        payload: Chat request with message and optional history

    Returns:
        ChatResponse: Response with model reply
    """
```

### Linting e Formatação

- **Black**: Formatação automática (line-length: 100)
- **Ruff**: Linting rápido (substitui flake8, isort, etc.)
- **MyPy**: Type checking

**Comandos:**
```bash
make format      # Formatar código
make lint        # Verificar linting
make type-check   # Verificar tipos
make dev         # Executar todos os checks
```

---

## 🧪 Testes

### Estrutura de Testes

- Testes unitários para serviços
- Testes de integração para routers
- Cobertura de código configurada

**Executar testes:**
```bash
make test                    # Com cobertura
pytest tests/ -v            # Verbose
pytest tests/ -k test_chat   # Teste específico
```

### Boas Práticas de Teste

1. **Nomes descritivos**: `test_chat_with_history_success`
2. **Arrange-Act-Assert**: Organizar testes em 3 fases
3. **Isolamento**: Cada teste é independente
4. **Mocks**: Usar mocks para dependências externas

---

## 🔒 Segurança

### Validação de Inputs

- Todos os inputs são validados usando Pydantic
- Validação customizada em `app/utils/validators.py`
- Sanitização de texto para prevenir injection

### Rate Limiting

- Middleware de rate limiting (60 req/min por IP)
- Configurável via variável de ambiente
- Health checks são excluídos do rate limit

### Tratamento de Erros

- Exception handler global
- Logs detalhados de erros (sem expor informações sensíveis)
- Mensagens de erro consistentes

---

## 📊 Logging

### Estrutura de Logs

- Logging estruturado com níveis apropriados
- Rotação automática de arquivos (5MB, 5 backups)
- Logs em arquivo e console

**Níveis:**
- `INFO`: Operações normais
- `WARNING`: Situações que requerem atenção
- `ERROR`: Erros que não impedem execução
- `CRITICAL`: Erros críticos

### Exemplo

```python
logger.info("Chat processed successfully (source=%s, length=%d)", source, len(message))
logger.error("Error in endpoint: %s", exc, exc_info=True)
```

---

## ⚙️ Configuração

### Variáveis de Ambiente

- Todas as configurações via `.env`
- Arquivo `.env.example` com documentação
- Valores padrão sensatos em `config.py`

### Health Check Detalhado

O endpoint `/health` retorna:
- Status da aplicação
- Versão
- Informações do sistema
- Status de configurações críticas

---

## 🚀 Desenvolvimento

### Pre-commit Hooks

Configurado com `.pre-commit-config.yaml`:
- Trailing whitespace
- End of file fixer
- Black formatting
- Ruff linting
- MyPy type checking

**Instalar:**
```bash
pre-commit install
```

### Makefile

Comandos úteis centralizados:

```bash
make install     # Instalar dependências
make test        # Executar testes
make lint        # Verificar linting
make format      # Formatar código
make type-check  # Verificar tipos
make clean       # Limpar cache
make run         # Rodar servidor
make dev         # Executar todos os checks
```

---

## 📝 Documentação

### Docstrings

- Google-style docstrings
- Type hints em todos os parâmetros
- Exemplos quando apropriado

### Documentação da API

- FastAPI gera automaticamente em `/docs` e `/redoc`
- Modelos Pydantic documentados
- Exemplos de requisições

---

## 🔄 Versionamento

### Changelog

- `CHANGELOG.md` mantido atualizado
- Versões seguem Semantic Versioning
- Mudanças documentadas por categoria

---

## 🎯 Próximas Melhorias

- [ ] Adicionar métricas (Prometheus)
- [ ] Implementar cache (Redis)
- [ ] Adicionar CI/CD (GitHub Actions)
- [ ] Documentação de deployment
- [ ] Performance profiling

---

## 📚 Referências

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Black Code Style](https://black.readthedocs.io/)

