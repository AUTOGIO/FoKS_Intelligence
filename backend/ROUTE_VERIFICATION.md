# FastAPI Router Table Verification

## Router Registration Analysis

### System Router Registration
- **Location**: `app/main.py` line 71
- **Registration**: `app.include_router(system.router)`
- **Frequency**: ✅ **Registered exactly once**

### System Router Definition
- **Location**: `app/routers/system.py` line 19
- **Prefix**: `/system`
- **Tag**: `["system"]`

## All Routes in System Router

Based on code analysis of `app/routers/system.py`:

| Method | Route Path | Line | Endpoint Function |
|--------|------------|------|-------------------|
| GET | `/system/info` | 35 | `system_info()` |
| GET | `/system/recommendations` | 68 | `get_recommendations()` |
| GET | `/system/metrics` | 80 | `get_metrics()` |
| GET | `/system/database/stats` | 91 | `database_stats()` |
| GET | `/system/models` | 103 | `get_locked_models()` ✅ |
| GET | `/system/identity-guard/status` | 127 | `identity_guard_status()` ✅ |

## Critical Endpoint Verification

### ✅ `/system/models`
- **Router**: `system.router`
- **Prefix**: `/system`
- **Route Decorator**: `@router.get("/models")`
- **Final Path**: `/system/models`
- **Registration Count**: **1** (registered once in `main.py` line 71)
- **Status**: ✅ **VERIFIED - Appears exactly once**

### ✅ `/system/identity-guard/status`
- **Router**: `system.router`
- **Prefix**: `/system`
- **Route Decorator**: `@router.get("/identity-guard/status")`
- **Final Path**: `/system/identity-guard/status`
- **Registration Count**: **1** (registered once in `main.py` line 71)
- **Status**: ✅ **VERIFIED - Appears exactly once**

## Other Routers with `/system` Prefix

### System Readiness Router
- **Location**: `app/routers/system_readiness.py` line 11
- **Prefix**: `/system` (shared with system.router)
- **Registration**: `app.include_router(system_readiness.router)` (line 72)
- **Routes**:
  - GET `/system/nfa-readiness`

**Note**: FastAPI allows multiple routers to share the same prefix as long as their route paths don't conflict. The system_readiness router has no conflicts with the system router endpoints.

## Complete Router Registration List

From `app/main.py` (lines 63-74):

1. `app.include_router(chat.router)` - prefix: `/chat`
2. `app.include_router(vision.router)` - prefix: `/vision`
3. `app.include_router(tasks.router)` - prefix: `/tasks`
4. `app.include_router(nfa_atf.router)` - prefix: `/tasks/nfa_atf`
5. `app.include_router(nfa_intelligence.router)` - prefix: `/nfa/intelligence`
6. `app.include_router(nfa_trigger.router)` - prefix: `/tasks`
7. `app.include_router(fbp_diagnostics.router)` - prefix: `/fbp/diagnostics`
8. `app.include_router(metrics.router)` - prefix: `/metrics`
9. `app.include_router(system.router)` - prefix: `/system` ✅
10. `app.include_router(system_readiness.router)` - prefix: `/system`
11. `app.include_router(conversations.router)` - prefix: `/conversations`
12. `app.include_router(tools_dashboard.router)` - prefix: `/tools/dashboard`

## Verification Summary

✅ **Both critical endpoints registered exactly once**:
- `/system/models` - ✅ Single registration
- `/system/identity-guard/status` - ✅ Single registration

✅ **No duplicate registrations found**

✅ **No route conflicts detected**

✅ **Router structure is correct and follows FastAPI best practices**

