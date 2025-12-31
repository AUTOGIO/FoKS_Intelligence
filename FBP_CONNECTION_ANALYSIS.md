# FBP Connection Analysis Report

**Date:** 2025-12-10  
**Scope:** FoKS_Intelligence repository only  
**Focus:** UNIX socket connection, hard-coded paths, failure points

---

## 🔍 Executive Summary

FoKS connects to FBP via UNIX socket (`/tmp/fbp.sock`) using `httpx.AsyncHTTPTransport(uds=...)`. The connection layer is **architecturally sound**, but there are **critical hard-coded paths** and **assumptions** that will cause failures in non-standard environments.

---

## 📋 Problem Categories

### 1. **Hard-Coded Paths to FBP Backend**

#### ❌ **CRITICAL: `ops/scripts/start_fbp_m3.sh`**
**Line 9:**
```bash
FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
```
**Problem:** Absolute hard-coded path with username `dnigga`  
**Impact:** Script fails on any other machine or user  
**Severity:** 🔴 **CRITICAL**

#### ⚠️ **HIGH: `ops/scripts/setup_m3_modern.sh`**
**Line 74:**
```bash
FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
```
**Problem:** Same hard-coded path  
**Impact:** Setup script fails for other users  
**Severity:** 🔴 **CRITICAL**

#### ⚠️ **HIGH: `ops/scripts/nfa_runner.sh`**
**Line 11:**
```bash
FBP_DIR="/Users/dnigga/Documents/FBP_Backend"
```
**Problem:** Hard-coded path  
**Impact:** NFA runner fails on other systems  
**Severity:** 🔴 **CRITICAL**

#### ✅ **GOOD: `ops/scripts/fbp_boot.sh`**
**Line 17:**
```bash
FBP_ROOT="${FBP_ROOT:-"$HOME/Documents/FBP_Backend"}"
```
**Status:** Uses environment variable with fallback ✅

#### ✅ **GOOD: `ops/scripts/fbp_boot_optimized.sh`**
**Line 16:**
```bash
FBP_ROOT="${FBP_ROOT:-"$HOME/Documents/FBP_Backend"}"
```
**Status:** Uses environment variable with fallback ✅

#### ⚠️ **MEDIUM: `backend/app/services/fbp_bootstrap.py`**
**Line 15:**
```python
DEFAULT_FBP_ROOT = os.path.expanduser("~/Documents/FBP_Backend")
```
**Problem:** Hard-coded default path (though uses `expanduser`)  
**Line 16:**
```python
FBP_ROOT_ENV = os.getenv("FBP_ROOT", DEFAULT_FBP_ROOT)
```
**Status:** ✅ Respects `FBP_ROOT` env var, but default is still hard-coded

**Line 42:**
```python
centralized_venv = Path.home() / "Documents" / ".venvs" / "fbp"
```
**Problem:** Hard-coded venv path assumption  
**Impact:** Won't find venv if user uses different location  
**Severity:** 🟡 **MEDIUM**

---

### 2. **Hard-Coded Virtual Environment Assumptions**

#### ❌ **CRITICAL: `ops/scripts/fbp_boot.sh`**
**Line 49:**
```bash
VENV_PATH="$HOME/Documents/.venvs/fbp"
```
**Problem:** Assumes centralized venv at fixed location  
**Line 51-52:**
```bash
if [[ ! -d "$VENV_PATH" ]]; then
  log "ERROR" "FBP virtualenv not found at $VENV_PATH"
```
**Impact:** Script exits with error if venv is in project directory (`FBP_ROOT/venv` or `FBP_ROOT/.venv`)  
**Severity:** 🔴 **CRITICAL**

#### ❌ **CRITICAL: `ops/scripts/fbp_boot_optimized.sh`**
**Line 49:**
```bash
VENV_PATH="$HOME/Documents/.venvs/fbp"
```
**Same problem as above**  
**Severity:** 🔴 **CRITICAL**

#### ✅ **GOOD: `ops/scripts/start_fbp_m3.sh`**
**Lines 37-63:** Checks multiple venv locations:
- `$HOME/Documents/.venvs/fbp` (centralized)
- `$FBP_ROOT/venv` (project)
- `$FBP_ROOT/.venv` (project alt)

**Status:** ✅ Handles multiple venv patterns correctly

#### ⚠️ **MEDIUM: `backend/app/services/fbp_bootstrap.py`**
**Lines 42-85:** Checks multiple venv locations, but:
- Hard-coded `Path.home() / "Documents" / ".venvs" / "fbp"` path
- Doesn't check for `FBP_VENV` environment variable

**Severity:** 🟡 **MEDIUM**

---

### 3. **Failure Points When FBP Is Not Running**

#### ✅ **GOOD: Connection Error Handling**
**File:** `backend/app/services/fbp_client.py`

**Lines 84-115:** `_execute_with_retry()` method:
- ✅ Retries on connection errors (3 attempts by default)
- ✅ Exponential backoff
- ✅ Raises `FBPClientError` with clear messages
- ✅ Logs warnings for retries

**Status:** ✅ **Robust error handling**

#### ⚠️ **MEDIUM: No Graceful Degradation**
**File:** `backend/app/services/fbp_service.py`

**Line 98:**
```python
result = await _CLIENT.nfa(payload)
```
**Problem:** If FBP is not running, this raises `FBPClientError`  
**Impact:** All NFA requests fail with 502 error  
**Current behavior:** Error propagates to router → HTTP 502 response

**Recommendation:** Consider optional fallback mode (e.g., queue requests, return "FBP unavailable" status)

**Severity:** 🟡 **MEDIUM** (by design, but could be improved)

#### ✅ **GOOD: Readiness Checks**
**File:** `backend/app/services/nfa_readiness.py`

**Lines 35-88:** Comprehensive checks:
- ✅ Socket existence check
- ✅ Health ping with 1-second timeout
- ✅ Environment variable validation
- ✅ Returns structured "READY" / "BLOCKED" status

**Status:** ✅ **Good diagnostic capability**

---

### 4. **Broken Activation Commands**

#### ❌ **CRITICAL: `ops/scripts/fbp_boot.sh`**
**Line 57:**
```bash
source "$VENV_PATH/bin/activate"
```
**Problem:** If `$VENV_PATH` doesn't exist (line 51 check fails), script exits before this line. But if venv exists but `activate` script is missing/corrupted, this will fail silently or with cryptic error.

**Line 120:**
```bash
"$VENV_PATH/bin/python" -m uvicorn ...
```
**Problem:** Uses hard-coded venv path. If venv is in project directory, this fails.

**Severity:** 🔴 **CRITICAL**

#### ❌ **CRITICAL: `ops/scripts/fbp_boot_optimized.sh`**
**Line 57:**
```bash
source "$VENV_PATH/bin/activate"
```
**Same issue as above**  
**Severity:** 🔴 **CRITICAL**

#### ✅ **GOOD: `ops/scripts/start_fbp_m3.sh`**
**Lines 37-63:** Uses conditional activation based on detected venv location:
```bash
elif [ -d "$HOME/Documents/.venvs/fbp" ]; then
    source "$HOME/Documents/.venvs/fbp/bin/activate"
elif [ -d "$FBP_ROOT/venv" ]; then
    source "$FBP_ROOT/venv/bin/activate"
```
**Status:** ✅ Handles multiple venv patterns

#### ⚠️ **MEDIUM: Missing Error Handling**
**All scripts:** If `source activate` fails, script continues and may use wrong Python interpreter.

**Recommendation:** Add error check after activation:
```bash
source "$VENV_PATH/bin/activate" || {
    log "ERROR" "Failed to activate venv at $VENV_PATH"
    exit 1
}
```

**Severity:** 🟡 **MEDIUM**

---

## 🔧 Recommended Code Patches

### **Patch 1: Fix Hard-Coded Paths in `start_fbp_m3.sh`**

**File:** `ops/scripts/start_fbp_m3.sh`

**Change:**
```diff
--- a/ops/scripts/start_fbp_m3.sh
+++ b/ops/scripts/start_fbp_m3.sh
@@ -6,7 +6,7 @@ set -euo pipefail
 
 SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
-FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
+FBP_ROOT="${FBP_ROOT:-"$HOME/Documents/FBP_Backend"}"
 SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"
```

**Impact:** Script works on any user's machine

---

### **Patch 2: Fix Hard-Coded Paths in `setup_m3_modern.sh`**

**File:** `ops/scripts/setup_m3_modern.sh`

**Change:**
```diff
--- a/ops/scripts/setup_m3_modern.sh
+++ b/ops/scripts/setup_m3_modern.sh
@@ -71,7 +71,7 @@ echo -e "${GREEN}✓ FoKS backend ready${NC}"
 echo ""
 
 # 4. Setup FBP backend with uv (modern approach)
-FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
+FBP_ROOT="${FBP_ROOT:-"$HOME/Documents/FBP_Backend"}"
 FBP_VENV="$HOME/.local/share/uv/projects/fbp"  # uv managed project
```

**Also fix line 47:**
```diff
-FOKS_ROOT="/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence"
+FOKS_ROOT="${FOKS_ROOT:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"}"
```

**Impact:** Setup script is portable

---

### **Patch 3: Fix Hard-Coded Path in `nfa_runner.sh`**

**File:** `ops/scripts/nfa_runner.sh`

**Change:**
```diff
--- a/ops/scripts/nfa_runner.sh
+++ b/ops/scripts/nfa_runner.sh
@@ -8,7 +8,7 @@ set -euo pipefail
 BACKEND_DIR="$(cd "$SCRIPT_DIR/../../backend" && pwd)"
 VENV_DIR="$BACKEND_DIR/.venv_foks"
 
-FBP_DIR="/Users/dnigga/Documents/FBP_Backend"
+FBP_DIR="${FBP_DIR:-"$HOME/Documents/FBP_Backend"}"
 FBP_SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"
 FBP_PORT="${FBP_PORT:-8000}"
```

**Impact:** NFA runner works on any system

---

### **Patch 4: Fix Venv Detection in `fbp_boot.sh`**

**File:** `ops/scripts/fbp_boot.sh`

**Change:**
```diff
--- a/ops/scripts/fbp_boot.sh
+++ b/ops/scripts/fbp_boot.sh
@@ -46,8 +46,20 @@ if [[ ! -d "$FBP_ROOT" ]]; then
   exit 1
 fi
 
-VENV_PATH="$HOME/Documents/.venvs/fbp"
-if [[ ! -d "$VENV_PATH" ]]; then
+# Try multiple venv locations (in order of preference)
+if [[ -d "$HOME/Documents/.venvs/fbp" ]]; then
+  VENV_PATH="$HOME/Documents/.venvs/fbp"
+elif [[ -d "$FBP_ROOT/venv" ]]; then
+  VENV_PATH="$FBP_ROOT/venv"
+elif [[ -d "$FBP_ROOT/.venv" ]]; then
+  VENV_PATH="$FBP_ROOT/.venv"
+elif [[ -n "${FBP_VENV:-}" ]] && [[ -d "$FBP_VENV" ]]; then
+  VENV_PATH="$FBP_VENV"
+else
+  VENV_PATH=""
+fi
+
+if [[ -z "$VENV_PATH" ]] || [[ ! -d "$VENV_PATH" ]]; then
   log "ERROR" "FBP virtualenv not found at $VENV_PATH"
-  log "HINT" "Create it with: python3 -m venv \"$VENV_PATH\" && \"$VENV_PATH/bin/pip\" install -e '.[dev]' (run inside $FBP_ROOT)"
+  log "HINT" "Checked locations:"
+  log "HINT" "  - $HOME/Documents/.venvs/fbp (centralized)"
+  log "HINT" "  - $FBP_ROOT/venv (project)"
+  log "HINT" "  - $FBP_ROOT/.venv (project alt)"
+  log "HINT" "  - \$FBP_VENV (environment variable)"
   exit 1
 fi
 
 # shellcheck disable=SC1090
-source "$VENV_PATH/bin/activate"
+source "$VENV_PATH/bin/activate" || {
+  log "ERROR" "Failed to activate venv at $VENV_PATH"
+  exit 1
+}
```

**Impact:** Script finds venv in project directory or respects `FBP_VENV` env var

---

### **Patch 5: Fix Venv Detection in `fbp_boot_optimized.sh`**

**File:** `ops/scripts/fbp_boot_optimized.sh`

**Apply same changes as Patch 4** (identical logic)

---

### **Patch 6: Enhance `fbp_bootstrap.py` to Support `FBP_VENV`**

**File:** `backend/app/services/fbp_bootstrap.py`

**Change:**
```diff
--- a/backend/app/services/fbp_bootstrap.py
+++ b/backend/app/services/fbp_bootstrap.py
@@ -14,6 +14,7 @@ logger = get_logger(__name__)
 # Standard FBP paths
 DEFAULT_FBP_ROOT = os.path.expanduser("~/Documents/FBP_Backend")
 FBP_ROOT_ENV = os.getenv("FBP_ROOT", DEFAULT_FBP_ROOT)
+FBP_VENV_ENV = os.getenv("FBP_VENV")
 
 def check_fbp_venv() -> Dict[str, Any]:
@@ -34,6 +35,14 @@ def check_fbp_venv() -> Dict[str, Any]:
         "type": "none",
     }
 
+    # Check FBP_VENV environment variable first (highest priority)
+    if FBP_VENV_ENV:
+        custom_venv = Path(FBP_VENV_ENV)
+        if custom_venv.exists() and custom_venv.is_dir():
+            if (custom_venv / "bin" / "activate").exists() or (
+                custom_venv / "Scripts" / "activate"
+            ).exists():
+                checks["exists"] = True
+                checks["path"] = str(custom_venv)
+                checks["type"] = "custom"
+                return checks
+
     # Check centralized venv
     centralized_venv = Path.home() / "Documents" / ".venvs" / "fbp"
```

**Impact:** Respects `FBP_VENV` environment variable for custom venv locations

---

### **Patch 7: Add Graceful Degradation for FBP Unavailable**

**File:** `backend/app/services/fbp_service.py`

**Optional enhancement:**
```python
async def run_nfa(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run NFA automation and log to Obsidian.
    
    If FBP is unavailable, returns error response instead of raising exception.
    """
    cpf = payload.get("cpf", "unknown")
    timestamp = datetime.now().isoformat()
    
    try:
        result = await _CLIENT.nfa(payload)
    except FBPClientError as exc:
        # Log error but return structured error response
        logger.error(
            "FBP NFA request failed",
            exc_info=True,
            extra={"payload": {"cpf": cpf, "error": str(exc)}},
        )
        # Return error response instead of raising
        return {
            "status": 503,
            "payload": {
                "success": False,
                "error": f"FBP backend unavailable: {str(exc)}",
                "message": "FBP backend is not responding. Please check if FBP is running.",
            },
        }
    
    # ... rest of function
```

**Impact:** Better error messages, optional queueing capability

**Note:** This is **optional** - current behavior (raising exception) is acceptable for API design.

---

## 📊 Summary Table

| File | Issue | Severity | Patch |
|------|-------|----------|-------|
| `ops/scripts/start_fbp_m3.sh` | Hard-coded `FBP_ROOT` | 🔴 CRITICAL | Patch 1 |
| `ops/scripts/setup_m3_modern.sh` | Hard-coded `FBP_ROOT`, `FOKS_ROOT` | 🔴 CRITICAL | Patch 2 |
| `ops/scripts/nfa_runner.sh` | Hard-coded `FBP_DIR` | 🔴 CRITICAL | Patch 3 |
| `ops/scripts/fbp_boot.sh` | Hard-coded venv path, no fallback | 🔴 CRITICAL | Patch 4 |
| `ops/scripts/fbp_boot_optimized.sh` | Hard-coded venv path, no fallback | 🔴 CRITICAL | Patch 5 |
| `backend/app/services/fbp_bootstrap.py` | No `FBP_VENV` support | 🟡 MEDIUM | Patch 6 |
| `backend/app/services/fbp_service.py` | No graceful degradation | 🟡 MEDIUM | Patch 7 (optional) |

---

## ✅ What's Working Well

1. **Socket Connection:** `fbp_client.py` correctly uses `httpx.AsyncHTTPTransport(uds=...)`
2. **Error Handling:** Retry logic with exponential backoff
3. **Readiness Checks:** Comprehensive diagnostic endpoint
4. **Config Flexibility:** `FBP_ROOT`, `FBP_SOCKET_PATH`, `FBP_TRANSPORT` env vars supported
5. **Multiple Venv Detection:** `start_fbp_m3.sh` and `fbp_bootstrap.py` check multiple locations

---

## 🎯 Priority Actions

1. **IMMEDIATE:** Apply Patches 1-5 (fix hard-coded paths)
2. **HIGH:** Apply Patch 6 (support `FBP_VENV` env var)
3. **OPTIONAL:** Consider Patch 7 (graceful degradation)

---

## 📝 Testing Checklist

After applying patches:

- [ ] `start_fbp_m3.sh` works with `FBP_ROOT` env var
- [ ] `fbp_boot.sh` finds venv in project directory
- [ ] `fbp_bootstrap.py` respects `FBP_VENV` env var
- [ ] All scripts work on different user accounts
- [ ] Error messages are clear when FBP is not running

---

**End of Report**
