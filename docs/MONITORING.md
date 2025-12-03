# 📊 FoKS Intelligence - Monitoring & Metrics

Guia sobre o sistema de monitoramento e métricas do FoKS Intelligence.

---

## 🔹 Endpoints de Monitoramento

### `GET /metrics`

Retorna métricas detalhadas da aplicação.

**Response:**
```json
{
    "uptime_seconds": 3600.5,
    "uptime_formatted": "1h 0m 0s",
    "requests": {
        "total": 150,
        "successful": 145,
        "failed": 5,
        "success_rate": 0.9667,
        "avg_response_time_ms": 125.5,
        "endpoint_counts": {
            "/chat/": 100,
            "/tasks/run": 30,
            "/health": 20
        },
        "error_counts": {
            "HTTP_500": 3,
            "HTTP_400": 2
        }
    },
    "tasks": {
        "total": 50,
        "successful": 48,
        "failed": 2,
        "success_rate": 0.96,
        "avg_execution_time_ms": 45.2,
        "task_type_counts": {
            "say": 20,
            "notification": 15,
            "open_url": 10,
            "screenshot": 5
        }
    }
}
```

### `GET /system/info`

Retorna informações do sistema.

**Response:**
```json
{
    "python_version": "3.9.6",
    "python_version_info": {
        "major": 3,
        "minor": 9,
        "micro": 6
    },
    "platform": "macOS-14.0-x86_64",
    "system": "Darwin",
    "processor": "arm",
    "architecture": ["64bit"],
    "machine": "arm64",
    "app_version": "1.2.0",
    "app_name": "FoKS Intelligence Global Interface",
    "environment": "development"
}
```

### `GET /system/metrics`

Alias para `/metrics` (mesma resposta).

---

## 🔹 Como Funciona

### Middleware de Monitoramento

O `MonitoringMiddleware` rastreia automaticamente:
- Todas as requisições HTTP
- Tempo de resposta
- Status de sucesso/falha
- Endpoints acessados
- Tipos de erro

### Métricas de Tasks

O sistema rastreia:
- Execução de tasks
- Tempo de execução
- Taxa de sucesso por tipo de task
- Contadores por tipo de task

---

## 🔹 Uso Prático

### Verificar Métricas

```bash
# Via curl
curl http://localhost:8001/metrics | python3 -m json.tool

# Via script
./scripts/check_health.sh
```

### Monitorar em Tempo Real

```bash
# Watch metrics every 5 seconds
watch -n 5 'curl -s http://localhost:8001/metrics | python3 -m json.tool'
```

### Integrar com Ferramentas

#### Prometheus (futuro)

```yaml
scrape_configs:
  - job_name: 'foks_intelligence'
    static_configs:
      - targets: ['localhost:8001']
```

#### Grafana (futuro)

Criar dashboard com:
- Request rate
- Response times
- Error rates
- Task execution times
- Uptime

---

## 🔹 Métricas Disponíveis

### Requests

- `total_requests`: Total de requisições
- `successful_requests`: Requisições bem-sucedidas
- `failed_requests`: Requisições falhadas
- `success_rate`: Taxa de sucesso (0-1)
- `avg_response_time_ms`: Tempo médio de resposta em ms
- `endpoint_counts`: Contador por endpoint
- `error_counts`: Contador por tipo de erro

### Tasks

- `total_tasks`: Total de tasks executadas
- `successful_tasks`: Tasks bem-sucedidas
- `failed_tasks`: Tasks falhadas
- `success_rate`: Taxa de sucesso (0-1)
- `avg_execution_time_ms`: Tempo médio de execução em ms
- `task_type_counts`: Contador por tipo de task

### System

- `uptime_seconds`: Uptime em segundos
- `uptime_formatted`: Uptime formatado (ex: "1h 30m 15s")

---

## 🔹 Exemplos de Uso

### Script de Monitoramento

```bash
#!/bin/bash
# monitor.sh

while true; do
    clear
    echo "=== FoKS Intelligence Metrics ==="
    curl -s http://localhost:8001/metrics | \
        python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Uptime: {data['uptime_formatted']}\")
print(f\"Requests: {data['requests']['total']} ({data['requests']['success_rate']*100:.1f}% success)\")
print(f\"Tasks: {data['tasks']['total']} ({data['tasks']['success_rate']*100:.1f}% success)\")
print(f\"Avg Response Time: {data['requests']['avg_response_time_ms']:.2f}ms\")
"
    sleep 5
done
```

### Alertas Básicos

```python
import requests

def check_health():
    response = requests.get("http://localhost:8001/metrics")
    metrics = response.json()

    # Alert if error rate > 10%
    error_rate = 1 - metrics["requests"]["success_rate"]
    if error_rate > 0.1:
        print(f"⚠️ High error rate: {error_rate*100:.1f}%")

    # Alert if avg response time > 1s
    if metrics["requests"]["avg_response_time_ms"] > 1000:
        print(f"⚠️ Slow response time: {metrics['requests']['avg_response_time_ms']:.2f}ms")
```

---

## 🔹 Próximas Melhorias

- [ ] Exportar métricas em formato Prometheus
- [ ] Adicionar métricas de memória e CPU
- [ ] Histórico de métricas (time-series)
- [ ] Alertas configuráveis
- [ ] Dashboard web integrado

