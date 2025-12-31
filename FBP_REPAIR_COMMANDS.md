# FBP Full Repair - macOS Terminal Commands

**System:** macOS 26 + Python 3.12 + Apple Silicon M3  
**Date:** 2025-12-10

---

## 🔧 Step-by-Step Commands

### **Step 1: Create Virtual Environment**

```bash
# Create .venvs directory if missing
mkdir -p ~/.venvs

# Create FBP virtual environment
python3.12 -m venv ~/.venvs/fbp

# Verify creation
ls -la ~/.venvs/fbp/bin/activate
```

---

### **Step 2: Install Requirements**

```bash
# Activate venv
source ~/.venvs/fbp/bin/activate

# Navigate to FBP backend
cd /Users/dnigga/Documents/FBP_Backend

# Upgrade pip
pip install --upgrade pip

# Install requirements (if requirements.txt exists)
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
elif [ -f pyproject.toml ]; then
    pip install -e .
else
    pip install uvicorn fastapi uvloop httpx pydantic
fi

# Verify key packages
python -c "import uvicorn, fastapi, uvloop; print('✓ Dependencies installed')"
```

---

### **Step 3: Fix Shell Configuration**

```bash
# Backup existing .zshrc
cp ~/.zshrc ~/.zshrc.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Append FBP configuration to .zshrc
cat >> ~/.zshrc << 'ZSHRC_EOF'

# ============================================================================
# FBP Backend Virtual Environment (Safe Activation)
# ============================================================================
FBP_VENV_PATH="$HOME/.venvs/fbp"
if [[ -d "$FBP_VENV_PATH" ]] && [[ -f "$FBP_VENV_PATH/bin/activate" ]]; then
    source "$FBP_VENV_PATH/bin/activate" 2>/dev/null || true
fi

# NFA Environment Variables
export NFA_USERNAME="${NFA_USERNAME:-}"
export NFA_PASSWORD="${NFA_PASSWORD:-}"
export NFA_EMITENTE_CNPJ="${NFA_EMITENTE_CNPJ:-}"
# ============================================================================
ZSHRC_EOF

# Reload shell configuration
source ~/.zshrc

# Verify activation (should show venv path)
echo "VIRTUAL_ENV: ${VIRTUAL_ENV:-not set}"
```

---

### **Step 4: Start Services**

```bash
# Navigate to FoKS project
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence

# Option A: Use auto-repair script (recommended)
bash ops/scripts/fbp_auto_repair.sh

# OR Option B: Manual start
# bash ops/scripts/fbp_boot.sh

# Wait for socket creation (up to 15 seconds)
for i in {1..15}; do
    if [ -S /tmp/fbp.sock ]; then
        echo "✓ Socket created: /tmp/fbp.sock"
        break
    fi
    sleep 1
done

# Verify FBP is running
if [ -S /tmp/fbp.sock ]; then
    curl --unix-socket /tmp/fbp.sock --max-time 2 http://localhost/health 2>&1 | head -3
else
    echo "⚠ Socket not created - check logs: ops/logs/fbp_auto_repair.log"
fi
```

---

### **Step 5: Validate with curl and FoKS Endpoints**

```bash
# Start FoKS backend (if not running)
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend
source .venv_foks/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/foks_backend.log 2>&1 &
FOKS_PID=$!
echo "FoKS backend starting (PID: $FOKS_PID)"

# Wait for FoKS to be ready
sleep 3

# Test 1: FoKS health check
echo "=== Test 1: FoKS Health ==="
curl -s http://localhost:8000/health | python3 -m json.tool

# Test 2: FBP socket direct check
echo -e "\n=== Test 2: FBP Socket Direct ==="
if [ -S /tmp/fbp.sock ]; then
    curl --unix-socket /tmp/fbp.sock --max-time 2 http://localhost/health 2>&1 | python3 -m json.tool || echo "⚠ FBP not responding"
else
    echo "✗ Socket not found"
fi

# Test 3: FoKS NFA Readiness
echo -e "\n=== Test 3: FoKS NFA Readiness ==="
curl -s http://localhost:8000/system/nfa-readiness | python3 -m json.tool

# Test 4: FoKS FBP Diagnostics
echo -e "\n=== Test 4: FoKS FBP Diagnostics ==="
curl -s -X POST http://localhost:8000/fbp/diagnostics/run | python3 -m json.tool

# Summary
echo -e "\n=== Validation Summary ==="
echo "FoKS PID: $FOKS_PID"
echo "Socket exists: $([ -S /tmp/fbp.sock ] && echo 'YES' || echo 'NO')"
echo "FoKS health: $(curl -s http://localhost:8000/health >/dev/null 2>&1 && echo 'OK' || echo 'FAILED')"
```

---

## 🚀 **One-Liner Full Repair** (All Steps Combined)

```bash
# Full repair in one command block
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence && \
mkdir -p ~/.venvs && \
python3.12 -m venv ~/.venvs/fbp && \
source ~/.venvs/fbp/bin/activate && \
cd /Users/dnigga/Documents/FBP_Backend && \
pip install --upgrade pip && \
([ -f requirements.txt ] && pip install -r requirements.txt || pip install -e . || pip install uvicorn fastapi uvloop httpx pydantic) && \
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence && \
bash ops/scripts/fbp_auto_repair.sh && \
sleep 5 && \
curl --unix-socket /tmp/fbp.sock --max-time 2 http://localhost/health 2>&1 | head -3
```

---

## ✅ **Quick Validation** (After Repair)

```bash
# Quick validation script
echo "=== FBP Repair Validation ===" && \
echo "Venv: $([ -d ~/.venvs/fbp ] && echo '✓' || echo '✗')" && \
echo "Socket: $([ -S /tmp/fbp.sock ] && echo '✓' || echo '✗')" && \
echo "FBP Health: $(curl --unix-socket /tmp/fbp.sock --max-time 1 http://localhost/health >/dev/null 2>&1 && echo '✓' || echo '✗')" && \
echo "FoKS Health: $(curl -s http://localhost:8000/health >/dev/null 2>&1 && echo '✓' || echo '✗')" && \
echo "Diagnostics: $(curl -s -X POST http://localhost:8000/fbp/diagnostics/run >/dev/null 2>&1 && echo '✓' || echo '✗')"
```

---

## 📋 **Troubleshooting Commands**

```bash
# Check FBP process
ps aux | grep -E "uvicorn.*fbp|fbp.*uvicorn" | grep -v grep

# Check socket
ls -la /tmp/fbp.sock && lsof /tmp/fbp.sock 2>/dev/null

# Check FoKS process
ps aux | grep "uvicorn.*app.main:app" | grep -v grep

# View FBP logs
tail -f /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/logs/fbp_auto_repair.log

# View FoKS logs
tail -f /tmp/foks_backend.log

# Kill all services (clean restart)
pkill -f "uvicorn.*app.main:app" && pkill -f "uvicorn.*fbp" && rm -f /tmp/fbp.sock
```

---

**End of Commands**
