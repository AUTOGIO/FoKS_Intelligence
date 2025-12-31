# n8n Docker Bash Execution Fix

## Problem

n8n running in Docker cannot find `bash` when executing the morning brain dashboard script. Error:
```
/bin/sh: bash: not found
```

## Root Cause

n8n Docker container uses `/bin/sh` and doesn't have `bash` in PATH. The container is trying to execute a macOS bash script from the host filesystem.

## Solutions

### Solution 1: Execute Script Directly (Current Fix)

The workflow now executes the script directly, letting the shebang (`#!/usr/bin/env bash`) handle finding bash:

```json
"command": "/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/m3_system_dashboard.sh --json"
```

**If this doesn't work**, try Solution 2.

### Solution 2: Use Full Path to macOS Bash

If n8n Docker can access the host's `/bin/bash`, use the full path:

```json
"command": "/bin/bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/m3_system_dashboard.sh --json"
```

### Solution 3: Install Bash in n8n Docker Container

If n8n Docker executes commands inside the container (not on host), install bash in the container:

```bash
# In n8n Docker container
apk add bash  # Alpine Linux
# OR
apt-get update && apt-get install -y bash  # Debian/Ubuntu
```

Then update the workflow to use:
```json
"command": "bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/m3_system_dashboard.sh --json"
```

### Solution 4: Use FoKS API Endpoint (Alternative)

Instead of executing the script directly, call a FoKS API endpoint that runs the dashboard:

1. Create a FoKS endpoint: `GET /api/system/dashboard`
2. Update n8n workflow to use HTTP Request node instead of Execute Command
3. The endpoint runs the dashboard script server-side and returns JSON

**Implementation** (in FoKS):
```python
# app/routers/system_router.py
@router.get("/api/system/dashboard")
async def get_system_dashboard():
    """Return system dashboard JSON."""
    import subprocess
    script = "/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/m3_system_dashboard.sh"
    result = subprocess.run(
        [script, "--json"],
        capture_output=True,
        text=True,
        timeout=10
    )
    return json.loads(result.stdout)
```

Then in n8n:
- Replace "Execute Dashboard Script" node with "HTTP Request" node
- URL: `http://localhost:8000/api/system/dashboard`
- Method: GET

## Testing

After applying a fix, test the workflow:

1. Open n8n workflow editor
2. Click "Execute workflow" button
3. Check "Execute Dashboard Script" node output
4. Verify JSON is parsed correctly in "Parse JSON & Format Message" node

## Current Status

✅ **Solution 1 Applied**: Script executed directly (shebang handles bash)

If Solution 1 fails, try Solution 2, then Solution 3, or implement Solution 4 for a more robust approach.

