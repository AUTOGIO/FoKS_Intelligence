# 🍎 FoKS Intelligence - M3 Optimization Guide

Guia de otimizações específicas para Apple M3 (iMac Mac15,5).

---

## 🔹 Hardware Overview

**Seu Hardware:**
- **Modelo**: iMac (Mac15,5)
- **Chip**: Apple M3 (8 cores: 4 performance + 4 efficiency)
- **Memória**: 16 GB
- **OS**: macOS 26.0 Beta

---

## 🔹 Otimizações Aplicadas Automaticamente

### 1. Detecção Automática de Hardware

O sistema detecta automaticamente:
- ✅ Apple Silicon (arm64)
- ✅ Chip M3 específico
- ✅ Número de cores (8)
- ✅ Memória disponível (16GB)

### 2. Configuração de Workers

**Otimizado para M3:**
- **Workers**: 4 (usando performance cores)
- **Max Concurrent Tasks**: ~120 (baseado em 16GB RAM)
- **Thread Pool**: Otimizado para 4 performance cores

### 3. Neural Engine

- ✅ Detecção automática de Neural Engine disponível
- ✅ Configuração para uso quando disponível
- ✅ Otimizações MLX quando usando modelos MLX

### 4. Limites de Memória

**Baseado em 16GB RAM:**
- **Max Request Size**: 10MB (configurável)
- **Memory Buffer**: 4GB reservado para sistema
- **Available for Tasks**: ~12GB

---

## 🔹 Endpoints Específicos

### `GET /system/info`

Retorna informações detalhadas do hardware M3:

```json
{
    "hardware": {
        "model": "arm64",
        "is_apple_silicon": true,
        "is_m3": true,
        "cpu_cores": 8,
        "memory_gb": 16,
        "platform": "macOS-26.0...",
        "processor": "arm"
    },
    "optimizations": {
        "optimal_workers": 4,
        "max_concurrent_tasks": 120,
        "neural_engine_enabled": true,
        "max_request_size_mb": 10
    }
}
```

### `GET /system/recommendations`

Recomendações de modelos baseadas no hardware M3:

```json
{
    "preferred_format": "MLX",
    "quantization": "4-bit",
    "max_model_size_gb": 8,
    "use_neural_engine": true,
    "optimal_batch_size": 4,
    "preferred_models": [
        "qwen2.5-14b",
        "llama-3-8b-instruct",
        "phi-4-mini"
    ]
}
```

---

## 🔹 Variáveis de Ambiente M3-Specific

```bash
# Neural Engine
ENABLE_NEURAL_ENGINE=true

# Request limits (16GB RAM)
MAX_REQUEST_SIZE_MB=10
REQUEST_TIMEOUT_SECONDS=120

# Workers (4 performance cores)
OPTIMAL_WORKERS=4
```

---

## 🔹 Modelos Recomendados para M3

### MLX Format (Recomendado)

- ✅ `qwen2.5-14b` (4-bit) - Balanceado
- ✅ `llama-3-8b-instruct` (4-bit) - Eficiente
- ✅ `phi-4-mini` (4-bit) - Leve

### GGUF Format (Alternativa)

- ✅ `qwen2.5-14b-Q4_K_M` - Boa performance
- ✅ `llama-3-8b-instruct-Q4_K_M` - Rápido

### Quantização

**Para 16GB RAM:**
- **4-bit**: Ideal para modelos até 14B
- **8-bit**: Para modelos maiores (se necessário)

---

## 🔹 Performance Tips

### 1. Use MLX quando possível

MLX é otimizado especificamente para Apple Silicon:

```python
# Models em /Volumes/MICRO/LM_STUDIO_MODELS
# Prefira modelos MLX para melhor performance
```

### 2. Batch Processing

Com 4 performance cores, processe em batches de 4:

```python
# Otimizado para 4 performance cores
batch_size = 4
```

### 3. Memory Management

Com 16GB:
- ✅ Use modelos quantizados (4-bit)
- ✅ Limite modelos simultâneos
- ✅ Monitore uso de memória via `/metrics`

---

## 🔹 Monitoramento M3-Specific

### Verificar Otimizações

```bash
curl http://localhost:8001/system/info | python3 -m json.tool
```

### Ver Recomendações

```bash
curl http://localhost:8001/system/recommendations | python3 -m json.tool
```

### Verificar Health com Info M3

```bash
curl http://localhost:8001/health | python3 -m json.tool
# Inclui informações de hardware M3
```

---

## 🔹 Troubleshooting M3

### Neural Engine não detectado

```bash
# Verificar disponibilidade
sysctl hw.optional.arm64

# Se retornar 1, Neural Engine está disponível
```

### Performance abaixo do esperado

1. Verifique se está usando modelos MLX
2. Confirme quantização (4-bit recomendado)
3. Verifique uso de memória via `/metrics`
4. Ajuste `max_concurrent_tasks` se necessário

### Memória insuficiente

Com 16GB:
- Reduza `max_concurrent_tasks`
- Use modelos menores ou mais quantizados
- Feche outros aplicativos pesados

---

## 🔹 Próximas Otimizações

- [ ] Suporte direto para MLX models
- [ ] Cache inteligente usando Neural Engine
- [ ] Otimização de batch processing para 4 cores
- [ ] Monitoramento de temperatura e throttling

---

## 📚 Referências

- [MLX Documentation](https://ml-explore.github.io/mlx/)
- [Apple Neural Engine](https://developer.apple.com/machine-learning/)
- [Core ML Optimization](https://developer.apple.com/documentation/coreml)

