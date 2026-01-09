# AUTOGIO Operational Baseline

**Status:** FROZEN
**Date:** 2025-01-XX
**Guardian Mode:** ACTIVE

---

## 🎯 Purpose

This document defines the **minimal "green state"** for both FoKS_Intelligence and FBP_Backend repositories.
These are the **ONE command per repo** that proves the system is healthy.

---

## ✅ FoKS Intelligence - Green State

### Health Check Command

```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence
./ops/scripts/foks_system_health.sh
```

### Expected Output

- **Exit Code:** `0` (all checks passed)
- **Summary:** `ALL HEALTH CHECKS PASSED`
- **Components Validated:**
  1. FoKS Backend Health (`GET http://localhost:8000/health`)
  2. FBP Backend Health (socket `/tmp/fbp.sock` + `/health`)
  3. FoKS → FBP Transport (`POST /fbp/diagnostics/run`)
  4. NFA Automation (`GET /tasks/nfa_atf/validate`)
  5. NFA Intelligence (`GET /nfa/intelligence/validate`)
  6. Filesystem (output dirs, reports dir)
  7. Python Environment (venv, dependencies)

### Alternative (Minimal Check)

If full health check is unavailable, use:

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

**Expected:** JSON response with `"status": "ok"`

---

## ✅ FBP Backend - Green State

### Health Check Command

```bash
curl --unix-socket /tmp/fbp.sock --max-time 2 http://localhost/health
```

### Expected Output

- **Exit Code:** `0`
- **Response:** JSON with `"status": "ok"` or similar healthy indicator

### Alternative (TCP Fallback)

If socket unavailable:

```bash
curl -s http://localhost:9500/health | python3 -m json.tool
```

**Expected:** JSON response with `"status": "ok"`

---

## 🔍 Validation Matrix

| Component | Command | Expected Exit | Success Criteria |
|-----------|---------|---------------|------------------|
| **FoKS Backend** | `curl http://localhost:8000/health` | `0` | JSON with `"status": "ok"` |
| **FBP Backend** | `curl --unix-socket /tmp/fbp.sock http://localhost/health` | `0` | JSON with `"status": "ok"` |
| **FoKS Full System** | `./ops/scripts/foks_system_health.sh` | `0` | `ALL HEALTH CHECKS PASSED` |

---

## 🚨 Red State Indicators

### FoKS Intelligence
- Health endpoint returns non-200 status
- Health endpoint unreachable
- System health script reports failures
- Missing required directories or files

### FBP Backend
- Socket `/tmp/fbp.sock` does not exist
- Health endpoint returns non-200 status
- Health endpoint unreachable (socket or TCP)

---

## 📋 Quick Validation Script

```bash
#!/bin/bash
# Quick AUTOGIO health check

echo "🔍 FoKS Intelligence:"
if curl -s --max-time 2 http://localhost:8000/health >/dev/null 2>&1; then
    echo "  ✅ OK"
else
    echo "  ❌ FAILED"
fi

echo "🔍 FBP Backend:"
if [ -S /tmp/fbp.sock ]; then
    if curl -s --unix-socket /tmp/fbp.sock --max-time 2 http://localhost/health >/dev/null 2>&1; then
        echo "  ✅ OK"
    else
        echo "  ❌ FAILED"
    fi
else
    echo "  ⚠️  Socket not found"
fi
```

---

**Last Updated:** 2025-01-XX
**Status:** FROZEN - No changes without explicit approval
