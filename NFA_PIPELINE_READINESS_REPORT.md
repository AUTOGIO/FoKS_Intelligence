# NFA Automation Pipeline Readiness Report
**Generated:** $(date)
**Mode:** Safeguard Mode - System Readiness Analysis

---

## 📋 EXECUTIVE SUMMARY

| Check | Status | Action Required |
|-------|--------|-----------------|
| CHECK A: FBP Socket | ❌ FAILED | Start FBP Backend |
| CHECK B: FoKS Config | ✅ PASS | None |
| CHECK C: NFA Env Vars | ❌ FAILED | Set environment variables |
| CHECK D: Modules | ✅ PASS | None |

**Overall Status:** ⚠️ **NOT READY** - Requires FBP startup and environment configuration

---

## 🔍 DETAILED CHECK RESULTS

### ✅ CHECK A: FBP Backend UNIX Socket

**Status:** ❌ Socket NOT found

**Details:**
- Expected socket: `/tmp/fbp.sock`
- Socket exists: NO
- Socket type: N/A (not present)

**ACTION REQUIRED:**
```bash
# Option 1: Using centralized venv (recommended)
source ~/.venvs/fbp/bin/activate
cd /Users/dnigga/Documents/FBP_Backend
./scripts/start.sh

# Option 2: Using project venv
cd /Users/dnigga/Documents/FBP_Backend
source venv/bin/activate
./scripts/start.sh
```

**Verification:**
```bash
# After starting, verify socket exists:
test -S /tmp/fbp.sock && echo "✓ Socket ready" || echo "✗ Socket not found"

# Test socket health:
curl --unix-socket /tmp/fbp.sock http://localhost/socket-health
```

---

### ✅ CHECK B: FoKS Configuration

**Status:** ✅ PASS

**Details:**
- Configuration loads: ✅ SUCCESS
- FBP Socket Path: `/tmp/fbp.sock`
- FBP Transport: `socket`
- FBP Base URL: `http+unix://%2Ftmp%2Ffbp.sock:`

**Architecture:**
- FoKS → FBP Client (`backend/app/services/fbp_client.py`)
- FBP Client → UNIX Socket Transport
- FBP Service → NFA delegation (`backend/app/services/fbp_service.py`)

**No action required.**

---

### ❌ CHECK C: SEFAZ/NFA Environment Variables

**Status:** ❌ FAILED - Missing all required variables

**Missing Variables:**
- `NFA_USERNAME` - SEFAZ login username
- `NFA_PASSWORD` - SEFAZ login password  
- `NFA_EMITENTE_CNPJ` - Emitente CNPJ for NFA operations

**ACTION REQUIRED:**

Set environment variables before running NFA automation:

```bash
# Option 1: Export in current shell session
export NFA_USERNAME="your_sefaz_username"
export NFA_PASSWORD="your_sefaz_password"
export NFA_EMITENTE_CNPJ="12345678000190"

# Option 2: Add to shell profile (~/.zshrc or ~/.bash_profile)
echo 'export NFA_USERNAME="your_sefaz_username"' >> ~/.zshrc
echo 'export NFA_PASSWORD="your_sefaz_password"' >> ~/.zshrc
echo 'export NFA_EMITENTE_CNPJ="12345678000190"' >> ~/.zshrc
source ~/.zshrc

# Option 3: Load from FBP .env file (if present)
cd /Users/dnigga/Documents/FBP_Backend
if [ -f .env ]; then
    source <(grep -E "^NFA_" .env | sed 's/^/export /')
fi
```

**Verification:**
```bash
env | grep -E "NFA_" | sort
# Should show:
# NFA_EMITENTE_CNPJ=...
# NFA_PASSWORD=...
# NFA_USERNAME=...
```

---

### ✅ CHECK D: Module Existence

**Status:** ✅ PASS

**FoKS Modules:**
- ✅ FBP Client: `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/app/services/fbp_client.py`
- ✅ FBP Service: `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/app/services/fbp_service.py`
- ✅ Task Runner: `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/app/services/task_runner.py`

**FBP Backend:**
- ✅ FBP Root: `/Users/dnigga/Documents/FBP_Backend`
- ✅ NFA Routers: `/app/routers/nfa.py`, `/app/routers/n8n_nfa.py`
- ✅ NFA Modules: `/app/modules/nfa/*`

**Architecture Flow:**
```
FoKS Router (/tasks/run)
  ↓
FoKS TaskRunner (delegates to FBP for "nfa" tasks)
  ↓
FoKS FBP Service (run_nfa)
  ↓
FoKS FBP Client (async httpx with UNIX socket transport)
  ↓
/tmp/fbp.sock (UNIX socket)
  ↓
FBP Backend (FastAPI)
  ↓
FBP Router (/nfa or /api/nfa/create)
  ↓
FBP NFA Service
  ↓
FBP NFA Modules (Playwright automation)
  ↓
SEFAZ Portal
```

**No action required.**

---

## 🚀 PIPELINE EXECUTION PLAN

### Phase 1: Service Startup

1. **Start FBP Backend:**
   ```bash
   source ~/.venvs/fbp/bin/activate
   cd /Users/dnigga/Documents/FBP_Backend
   ./scripts/start.sh
   ```

2. **Verify Socket:**
   ```bash
   sleep 3  # Wait for startup
   curl --unix-socket /tmp/fbp.sock http://localhost/socket-health
   ```

### Phase 2: Environment Configuration

3. **Set NFA Environment Variables** (see CHECK C above)

### Phase 3: NFA Automation Trigger

4. **Option A: Via FoKS Task Runner (Python)**
   ```bash
   cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence
   python3 -c "
   import asyncio
   from backend.app.services.task_runner import TaskRunner
   
   async def run():
       runner = TaskRunner()
       result = await runner.run_task('nfa', {
           'emitente_cnpj': '${NFA_EMITENTE_CNPJ}',
           'test': True
       })
       print(result)
   
   asyncio.run(run())
   "
   ```

5. **Option B: Via FoKS HTTP API**
   ```bash
   curl -X POST http://localhost:8000/tasks/run \
     -H "Content-Type: application/json" \
     -d '{
       "type": "nfa",
       "args": {
         "emitente_cnpj": "${NFA_EMITENTE_CNPJ}",
         "test": true
       },
       "source": "manual_test"
     }'
   ```

6. **Option C: Direct FBP Socket Call (Testing)**
   ```bash
   curl --unix-socket /tmp/fbp.sock \
     http://localhost/nfa \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"test": true}'
   ```

---

## 🔒 SAFEGUARD MODE COMPLIANCE

- ✅ No files modified (read-only analysis)
- ✅ No system paths touched outside repo
- ✅ All checks performed safely
- ✅ Clear action steps provided
- ✅ No destructive operations

---

## 📊 POST-RUN VALIDATION CHECKLIST

After automation completes, verify:

- [ ] No transport fallback triggered (should use socket, not TCP)
- [ ] FBP socket stayed active throughout execution
- [ ] FoKS returned valid results (success/failure clearly indicated)
- [ ] No unhandled exceptions in FoKS logs
- [ ] No unhandled exceptions in FBP logs
- [ ] NFA processing logs accessible at `/Users/dnigga/Documents/FBP_Backend/logs/nfa/`
- [ ] SEFAZ responses captured correctly

---

## 🐛 ERROR CATEGORIZATION GUIDE

If errors occur, categorize as:

1. **CONFIG ERROR**: Missing env vars, wrong paths, invalid settings
   - Fix: Follow CHECK C instructions above

2. **RUNTIME ERROR**: Service crashes, import failures, logic errors
   - Fix: Check logs, verify dependencies, restart services

3. **TRANSPORT ERROR**: Socket connection failures, timeout errors
   - Fix: Verify FBP is running, check socket permissions, restart FBP

4. **SEFAZ ERROR**: Login failures, form validation errors, portal timeouts
   - Fix: Verify credentials, check SEFAZ portal status, review NFA module logs

---

## 📝 NEXT STEPS

1. Review this report
2. Start FBP backend (Phase 1)
3. Set environment variables (Phase 2)
4. Execute NFA automation (Phase 3)
5. Review results and logs
6. Report any issues for categorization

---

**Report End**
