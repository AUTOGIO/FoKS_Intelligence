# M3 System Optimization & Setup Guide

**Target Hardware:** iMac M3 (8 cores: 4P+4E, 16 GB RAM, macOS 26 Beta)  
**Last Updated:** 2025-12-08  
**Status:** Best Practices Implemented

---

## Executive Summary

This guide implements **2025 best practices** for running FoKS + FBP + LM Studio on your iMac M3. Key changes:

1. ✅ **FBP boot script**: refactored to use `uvloop`, single worker, proper launchd integration (no `nohup`).
2. ✅ **M3 Resource Module**: concurrency limits, model profiles (LIGHT/BALANCED/HEAVY), memory budgets.
3. ✅ **Launchd Configuration**: proper logging via `StandardOutPath` / `StandardErrorPath` to `~/Library/Logs/FoKS/`.
4. ✅ **System Dashboard**: monitors FoKS, FBP, LM Studio health + M3 resource usage.

---

## 1. Installation & Setup

### 1.1. Create Log Directory

```bash
mkdir -p ~/Library/Logs/FoKS
chmod 700 ~/Library/Logs/FoKS
```

### 1.2. Install uvloop (both backends)

```bash
# FoKS backend
cd ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend
source .venv_foks/bin/activate
pip install uvloop

# FBP backend
cd ~/Documents/FBP_Backend
source ~/.venvs/fbp/bin/activate
pip install uvloop
```

### 1.3. Update FoKS requirements.txt

Ensure both backends have uvloop in their dependency lists:

```bash
# FoKS
echo 'uvloop>=0.19.0' >> ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/requirements.txt

# FBP (add to pyproject.toml optional-dependencies or requirements if exists)
```

### 1.4. Register launchd agents

```bash
# Copy plist files to ~/Library/LaunchAgents
cp ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/launchd/com.foks.bootstrap.optimized.plist \
   ~/Library/LaunchAgents/com.foks.bootstrap.plist

cp ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/launchd/com.fbp.bootstrap.optimized.plist \
   ~/Library/LaunchAgents/com.fbp.bootstrap.plist

cp ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/launchd/com.lmstudio.watch.plist \
   ~/Library/LaunchAgents/com.lmstudio.watch.plist

# Set proper permissions
chmod 644 ~/Library/LaunchAgents/com.*.plist
```

### 1.5. Start services via launchctl

```bash
# Load agents (auto-start at login, supervise with KeepAlive)
launchctl load -w ~/Library/LaunchAgents/com.foks.bootstrap.plist
launchctl load -w ~/Library/LaunchAgents/com.fbp.bootstrap.plist
launchctl load -w ~/Library/LaunchAgents/com.lmstudio.watch.plist

# Verify
launchctl list | grep com.foks
launchctl list | grep com.fbp
```

---

## 2. Configuration & Resource Limits

### 2.1. M3 Resource Budget (from `m3_optimization.py`)

| Component | Allocated | Notes |
|-----------|-----------|-------|
| LM Studio | 4–10 GB | Model-dependent; smaller models use less |
| FoKS Backend | ~2 GB | Async concurrency, no heavy CPU |
| FBP Backend | ~2.5 GB | Playwright automation, browser contexts |
| OS + Headroom | ~3 GB | System, file cache, safety margin |
| **Total Budget** | **16 GB** | Sum of allocations on M3 |

### 2.2. LM Studio Concurrency

**Default:** 1 concurrent generation request.  
**Reasoning:** On 16 GB with model in memory, 2+ generations → RAM pressure → paging → degraded performance.

**Configuration (in FoKS `LMStudioClient`):**

```python
from app.config.m3_optimization import LMStudioConcurrencyManager

# In __init__ or setup
self.concurrency_manager = LMStudioConcurrencyManager(max_concurrent=1)

# For each request
async def chat(self, request):
    async with self.concurrency_manager.acquire():
        result = await self._http_client.post(...)
        return result
```

### 2.3. FastAPI Process Configuration

**Both FoKS and FBP:**

- **Workers:** 1 (single process)
- **Event Loop:** `uvloop` (faster than default asyncio)
- **HTTP:** `auto` (uvicorn auto-detects `httptools` for speed)
- **Async Concurrency:** High (achieved via async I/O + httpx connection pooling)

**httpx Client Settings (M3):**

```python
import httpx
from app.config.m3_optimization import HTTPX_M3_DEFAULTS

client = httpx.AsyncClient(
    **HTTPX_M3_DEFAULTS,
    # Result: 10 max connections, 5 keepalive (moderate for 16GB)
)
```

### 2.4. Launchd Logging

All output (stdout/stderr) is now captured by launchd and written to:

- **FoKS out:** `~/Library/Logs/FoKS/com.foks.bootstrap.out.log`
- **FoKS err:** `~/Library/Logs/FoKS/com.foks.bootstrap.err.log`
- **FBP out:** `~/Library/Logs/FoKS/com.fbp.bootstrap.out.log`
- **FBP err:** `~/Library/Logs/FoKS/com.fbp.bootstrap.err.log`

**View logs in real-time:**

```bash
# FoKS
tail -f ~/Library/Logs/FoKS/com.foks.bootstrap.out.log

# FBP
tail -f ~/Library/Logs/FoKS/com.fbp.bootstrap.out.log
```

---

## 3. LM Studio Optimization

### 3.1. Backend & Model Selection

✅ **Always use MLX backend** on Apple Silicon.  
MLX is 10–20% faster and more power-efficient than generic CPU backends.

**Default model profile:** `LIGHT` (7–8B, 4-bit MLX).

```python
from app.config.m3_optimization import M3_PROFILES, ModelProfile

default_config = M3_PROFILES[ModelProfile.LIGHT]
print(f"Model: {default_config.model_name}")
print(f"Max tokens: {default_config.max_tokens}")
print(f"Context: {default_config.context_window}")
```

### 3.2. Context Windows

- **Default:** 4–8k tokens (safe on 16 GB).
- **Per-request override:** Allow user to opt-in to larger contexts (e.g. 32k), but **warn about RAM impact**.
- **Quantization:** Stick to 4-bit or 5-bit; 8-bit models eat more RAM.

### 3.3. Stream vs. Full Completion

**Prefer streaming** for long outputs to:
- Reduce memory peak (token-by-token generation).
- Improve perceived latency (user sees output sooner).
- Better error recovery (stop early if needed).

---

## 4. FoKS Backend Configuration

### 4.1. Environment Variables

Set in launchd plist or `.env`:

```bash
# LM Studio
LMSTUDIO_BASE_URL=http://127.0.0.1:1234
LMSTUDIO_API_KEY=  # If LM Studio has API key, else empty

# Model profile
DEFAULT_MODEL_PROFILE=light  # light | balanced | heavy

# Concurrency
LM_MAX_CONCURRENT_REQUESTS=1

# Async client
HTPPX_MAX_CONNECTIONS=10
HTTPX_MAX_KEEPALIVE=5

# Logging
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

### 4.2. Example: LMStudioClient with M3 Concurrency

```python
# backend/app/services/lmstudio_client.py (updated)

import asyncio
from app.config.m3_optimization import LMStudioConcurrencyManager
from app.config import settings

class LMStudioClient:
    def __init__(self):
        self.base_url = settings.lmstudio_base_url
        self.concurrency_manager = LMStudioConcurrencyManager(
            max_concurrent=settings.lm_max_concurrent_requests or 1
        )
        self.http_client = None
    
    async def chat(
        self,
        messages: list,
        model: str = None,
        stream: bool = False,
        **kwargs
    ):
        """Generate chat completion with M3 concurrency control."""
        # Acquire semaphore slot
        await self.concurrency_manager.acquire()
        try:
            result = await self._do_chat(messages, model, stream, **kwargs)
            return result
        finally:
            # Always release
            await self.concurrency_manager.release()
    
    async def _do_chat(self, messages, model, stream, **kwargs):
        # Your existing chat implementation
        ...
```

---

## 5. FBP Backend Configuration

### 5.1. Boot Script Updates

The new `fbp_boot.sh` already includes:

- ✅ Proper venv activation
- ✅ uvloop installation check
- ✅ Playwright dependency validation
- ✅ Single worker + uvloop startup
- ✅ **No nohup** (launchd manages process)

### 5.2. Resource Limits (launchd)

From `com.fbp.bootstrap.optimized.plist`:

```xml
<key>SoftResourceLimits</key>
<dict>
  <key>Memory</key>
  <integer>2684354560</integer>  <!-- 2.5 GB -->
  <key>OpenFiles</key>
  <integer>2048</integer>         <!-- For Playwright FDs -->
</dict>
```

---

## 6. Monitoring & Health Checks

### 6.1. System Dashboard

Run the M3 system dashboard:

```bash
bash ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/m3_system_dashboard.sh
```

**Output example:**

```
[2025-12-08T15:30:45] === M3 System Dashboard (iMac M3, 16GB, macOS 26) ===
[2025-12-08T15:30:45] FoKS Backend:
✓ Status ✓ Metrics
[2025-12-08T15:30:45] FBP Backend:
✓ Status
[2025-12-08T15:30:45] LM Studio:
✓ Status (models available)
[2025-12-08T15:30:45] System Resources (M3 iMac):
  Total Memory: 16.0 GB
  Available Memory: 8.3 GB
  CPU Load: 1.23, 1.10, 0.95
```

### 6.2. Health Endpoints

**FoKS:**
- `GET /health` → basic health
- `GET /system/status` → detailed status
- `GET /metrics` → Prometheus-style metrics

**FBP:**
- `GET /health` → basic health (includes Playwright check)

**LM Studio:**
- `GET /v1/models` → list available models

### 6.3. Check Script (ops/health/)

```bash
# All three
python3 ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/health/check_foks.py
python3 ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/health/check_fbp.py
python3 ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/health/check_lmstudio.py
```

---

## 7. Troubleshooting

### 7.1. Services Not Starting

```bash
# Check launchctl status
launchctl list | grep com.foks
launchctl list | grep com.fbp

# Unload and reload
launchctl unload ~/Library/LaunchAgents/com.foks.bootstrap.plist
launchctl load ~/Library/LaunchAgents/com.foks.bootstrap.plist

# View logs
tail -f ~/Library/Logs/FoKS/com.foks.bootstrap.err.log
```

### 7.2. OOM or Paging (Memory Issues)

**Symptoms:** Slow response, beach-ball cursor, high disk I/O.

**Fixes:**
1. Reduce LM Studio context window (e.g., 4k → 2k).
2. Reduce model size (LIGHT profile instead of BALANCED).
3. Restart LM Studio (kill and re-launch).
4. Check if other apps are consuming RAM:
   ```bash
   ps aux --sort=-%mem | head -20
   ```

### 7.3. uvloop Not Available

```bash
# Ensure it's installed
pip install uvloop

# Test import
python -c "import uvloop; print(uvloop.__version__)"
```

If it fails on ARM64 macOS:
- Ensure using Apple Silicon Python: `python --version` should show arm64
- Try: `pip install --upgrade --force-reinstall uvloop`

---

## 8. Performance Tuning Checklist

- [ ] uvloop installed in both venvs
- [ ] LM Studio using MLX backend
- [ ] Default model profile set to LIGHT (7–8B, 4-bit)
- [ ] Max concurrent LM requests set to 1
- [ ] launchd agents loaded with `launchctl load`
- [ ] Logs writing to `~/Library/Logs/FoKS/`
- [ ] System dashboard tested
- [ ] Health endpoints responding
- [ ] No memory pressure (check `vm_stat`)
- [ ] CPU load reasonable (<50% sustained)

---

## 9. macOS 26 (Beta) Specific Notes

- ✅ Launchd plist syntax compatible with Sonoma+
- ✅ Environment constraints (SMAppService) available but not required for local setup
- ✅ StandardOutPath/StandardErrorPath fully supported
- ✅ M3 Neural Engine: no special OS-level tuning needed (handled by MLX library)

---

## 10. References & Further Reading

- **FastAPI Best Practices 2025:** https://render.com/articles/fastapi-production-deployment-best-practices
- **Apple Silicon Optimization:** https://github.com/mlx-explore/mlx (MLX framework)
- **launchd Documentation:** https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/
- **macOS 26 (Sequoia) Release Notes:** https://support.apple.com/

---

## Summary of Changes

| File | Change | Benefit |
|------|--------|----------|
| `fbp_boot.sh` | Refactored; removed nohup, added uvloop | Proper launchd integration, faster async |
| `com.fbp.bootstrap.optimized.plist` | Updated script path, logging paths | launchd manages process, logs go to ~/Library/Logs |
| `m3_optimization.py` | **NEW** | Concurrency limits, model profiles, resource budgets |
| `m3_system_dashboard.sh` | **NEW** | Monitor FoKS, FBP, LM Studio health + M3 resources |

---

**Last Verified:** 2025-12-08 on iMac M3 (8 cores, 16 GB, macOS 26 Beta)  
**Next Review:** Q1 2026 (or when major OS/library updates released)
