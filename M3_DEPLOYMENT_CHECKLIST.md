# M3 Optimization Deployment Checklist

## ✅ Pre-Deployment (Verify Everything Exists)

### Boot Scripts
- [ ] `ops/scripts/foks_boot_optimized.sh` exists and is readable
- [ ] `ops/scripts/fbp_boot_optimized.sh` exists and is readable
- [ ] `ops/scripts/apply_m3_optimizations.sh` exists and is readable

### LaunchD Plists
- [ ] `ops/launchd/com.foks.bootstrap.optimized.plist` exists
- [ ] `ops/launchd/com.fbp.bootstrap.optimized.plist` exists

### Configuration
- [ ] `ops/config/.m3_optimization.env` exists

### Documentation
- [ ] `docs/M3_OPTIMIZATION_GUIDE.md` exists
- [ ] `docs/M3_OPTIMIZATION_SUMMARY.md` exists

### Directory Structure
Run this to verify:
```bash
tree -L 2 /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/
```
Should show:
```
ops/
├── config/
│   └── .m3_optimization.env
├── launchd/
│   ├── com.foks.bootstrap.optimized.plist
│   └── com.fbp.bootstrap.optimized.plist
└── scripts/
    ├── apply_m3_optimizations.sh
    ├── foks_boot_optimized.sh
    └── fbp_boot_optimized.sh
```

---

## ✅ Step 1: Backup Current Setup (5 minutes)

```bash
# Backup current launchd agents (if any exist)
mkdir -p ~/Library/LaunchAgents/backup_$(date +%Y%m%d_%H%M%S)
cp ~/Library/LaunchAgents/com.foks.* ~/Library/LaunchAgents/backup_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true
cp ~/Library/LaunchAgents/com.fbp.* ~/Library/LaunchAgents/backup_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true
cp ~/Library/LaunchAgents/com.lmstudio.* ~/Library/LaunchAgents/backup_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true

echo "✅ Backup created"
```

- [ ] Backup completed
- [ ] Backup directory path noted: `~/Library/LaunchAgents/backup_YYYYMMDD_HHMMSS`

---

## ✅ Step 2: Run Automated Deployment Script (5 minutes)

```bash
# Make script executable
chmod +x /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/apply_m3_optimizations.sh

# Run the deployment script
bash /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/apply_m3_optimizations.sh
```

The script will:
1. Create log directory `~/Library/Logs/FoKS`
2. Unload old agents (if any)
3. Make boot scripts executable
4. Install optimized plists
5. Load new agents
6. Verify they're running
7. Show health status

- [ ] Script ran successfully
- [ ] No errors in output
- [ ] Both FoKS and FBP agents loaded

---

## ✅ Step 3: Verify Services Are Running (5 minutes)

### Check LaunchD Status
```bash
launchctl list | grep -E "com\.foks|com\.fbp"
```

Expected output:
```
<PID>  0  com.foks.bootstrap
<PID>  0  com.fbp.bootstrap
```

- [ ] FoKS agent shows a PID (not "-")
- [ ] FBP agent shows a PID (not "-")

### Check Ports are Listening
```bash
lsof -i :8000
lsof -i :8001
```

Expected: Should show Python processes listening on ports.

- [ ] Port 8000 is listening (FoKS or FBP)
- [ ] Port 8001 is listening (FBP, if different port)

### Test Health Endpoints
```bash
curl -s http://127.0.0.1:8000/health | jq .
```

Expected: JSON response with status.

- [ ] FoKS health endpoint responds
- [ ] Response is valid JSON
- [ ] Status is "ok" or "healthy"

### Check Log Files
```bash
ls -lh ~/Library/Logs/FoKS/
head -20 ~/Library/Logs/FoKS/com.foks.bootstrap.out.log
```

Expected: Log files exist and contain startup messages.

- [ ] Log directory exists: `~/Library/Logs/FoKS`
- [ ] `com.foks.bootstrap.out.log` exists
- [ ] `com.foks.bootstrap.err.log` exists
- [ ] `com.fbp.bootstrap.out.log` exists (if FBP on separate port)
- [ ] Logs contain no error messages

---

## ✅ Step 4: Verify Configuration (5 minutes)

### Check Environment File
```bash
cat /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/config/.m3_optimization.env | head -20
```

- [ ] File exists and is readable
- [ ] Contains key settings (LMSTUDIO_BASE_URL, UVICORN_WORKERS, etc.)

### Verify Key Settings
```bash
grep "UVICORN_WORKERS" /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/config/.m3_optimization.env
grep "LMSTUDIO_MAX_CONCURRENT" /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/config/.m3_optimization.env
grep "LMSTUDIO_DEFAULT_MODEL" /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/config/.m3_optimization.env
```

Expected: Settings should show optimized values.

- [ ] UVICORN_WORKERS=1
- [ ] LMSTUDIO_MAX_CONCURRENT_GENERATIONS=2
- [ ] LMSTUDIO_DEFAULT_MODEL is set to a 7-8B model

---

## ✅ Step 5: LM Studio Configuration (5 minutes)

### Verify MLX Backend
1. Open LM Studio app
2. Load a model
3. Check the "Settings" or "Model Info" section
4. Verify "Engine" or "Backend" is set to **MLX** (not CPU, NNPACK, etc.)

- [ ] LM Studio app is running
- [ ] A model is loaded
- [ ] Backend/Engine is MLX
- [ ] Model is 7-8B, 4-bit quantization (e.g., `mistral-7b-instruct-4bit`)

### Test LM Studio Endpoint
```bash
curl -s http://127.0.0.1:1234/v1/models | jq .
```

Expected: JSON with model list.

- [ ] LM Studio endpoint responds
- [ ] Response shows a loaded model

---

## ✅ Step 6: Monitor Resources (15 minutes)

### Watch Memory Usage
```bash
# Terminal 1: Watch memory
while true; do top -l 1 | grep PhysMem; sleep 5; done

# Terminal 2: Send a chat request to FoKS
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?"}'
```

- [ ] Memory usage remains < 13 GB during testing
- [ ] No sudden jumps > 14 GB
- [ ] Chat request completes successfully

### Check CPU Usage
```bash
top  # Press Q to exit
```

Look for:
- Python processes should not show > 100% CPU constantly
- Efficiency cores may be < 50%, performance cores may spike but shouldn't max out

- [ ] No runaway CPU usage
- [ ] System is responsive (can open apps, switch windows)

### Monitor Logs
```bash
tail -f ~/Library/Logs/FoKS/com.foks.bootstrap.out.log
```

In another terminal, send requests and verify logs show them.

- [ ] Logs show incoming requests
- [ ] No error messages appearing
- [ ] Access log shows responses (200, 201, etc.)

---

## ✅ Step 7: Test Critical Paths (10 minutes)

### Test 1: FoKS Health
```bash
curl -v http://127.0.0.1:8000/health
```

- [ ] HTTP 200 response
- [ ] JSON response with status

### Test 2: FoKS Chat (Basic)
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, say hello back"}'
```

- [ ] HTTP 200 response
- [ ] Response contains a message from LM Studio

### Test 3: FoKS Chat (Longer Context)
```bash
# This should work but may be slower
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze this code: def hello():\n    print("hello")", "max_tokens": 256}'
```

- [ ] Request completes without hanging
- [ ] Response is reasonable

### Test 4: FBP Health (if using)
```bash
curl -v http://127.0.0.1:8000/health
# Or if FBP is on different port:
curl -v http://127.0.0.1:8001/health
```

- [ ] HTTP 200 response
- [ ] FBP backend is accessible

### Test 5: Concurrency Limiting
```bash
# Send 3 concurrent requests to LM Studio (should queue internally)
for i in {1..3}; do
  curl -X POST http://127.0.0.1:8000/chat \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Request $i\"}" &
done
wait
```

- [ ] All 3 requests complete (don't hang or crash)
- [ ] System remains responsive
- [ ] Logs show requests being queued

---

## ✅ Step 8: Verify Boot on Restart (5 minutes + Restart Time)

### Test: Restart the Services
```bash
# Stop services
launchctl unload ~/Library/LaunchAgents/com.foks.bootstrap.plist
launchctl unload ~/Library/LaunchAgents/com.fbp.bootstrap.plist

# Wait a moment
sleep 2

# Reload
launchctl load ~/Library/LaunchAgents/com.foks.bootstrap.plist
launchctl load ~/Library/LaunchAgents/com.fbp.bootstrap.plist

# Wait for startup
sleep 5

# Verify
launchctl list | grep -E "com\.foks|com\.fbp"
curl http://127.0.0.1:8000/health
```

- [ ] Services start successfully after reload
- [ ] Health endpoint responds within 10 seconds

### Full Restart (Optional, for extra confidence)
```bash
# Note: This will restart your Mac
sudo reboot

# After reboot:
launchctl list | grep -E "com\.foks|com\.fbp"  # Should show running
curl http://127.0.0.1:8000/health              # Should respond
```

- [ ] Services auto-start on login
- [ ] Health endpoints respond immediately after boot

---

## ✅ Step 9: Documentation & Rollback Plan (5 minutes)

### Document Your Setup
```bash
# Create a setup summary for future reference
cat > /tmp/m3_setup_summary.txt << 'EOF'
Date Deployed: $(date)
Machine: iMac M3 (8 cores: 4P+4E, 16 GB RAM)
macOS: $(sw_vers -productVersion)

Services:
- FoKS Bootstrap: ~/Library/LaunchAgents/com.foks.bootstrap.plist
- FBP Bootstrap: ~/Library/LaunchAgents/com.fbp.bootstrap.plist

Boot Scripts:
- FoKS: /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/foks_boot_optimized.sh
- FBP: /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/fbp_boot_optimized.sh

Config:
- /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/config/.m3_optimization.env

Logs:
- ~/Library/Logs/FoKS/

Backup:
- ~/Library/LaunchAgents/backup_YYYYMMDD_HHMMSS/
EOF
cat /tmp/m3_setup_summary.txt
```

- [ ] Setup documented
- [ ] Backup location noted

### Rollback Plan (If Needed)
```bash
# If things go wrong, rollback is simple:
launchctl unload ~/Library/LaunchAgents/com.foks.bootstrap.plist
launchctl unload ~/Library/LaunchAgents/com.fbp.bootstrap.plist

# Restore old plists from backup
cp ~/Library/LaunchAgents/backup_YYYYMMDD_HHMMSS/com.foks.* ~/Library/LaunchAgents/
cp ~/Library/LaunchAgents/backup_YYYYMMDD_HHMMSS/com.fbp.* ~/Library/LaunchAgents/

# Reload old agents
launchctl load ~/Library/LaunchAgents/com.foks.bootstrap.plist
launchctl load ~/Library/LaunchAgents/com.fbp.bootstrap.plist
```

- [ ] Rollback plan written down
- [ ] Backup paths verified

---

## ✅ Step 10: Ongoing Monitoring (Daily/Weekly)

### Daily (5 minutes)
```bash
# Check services are still running
launchctl list | grep -E "com\.foks|com\.fbp"

# Quick health check
curl -s http://127.0.0.1:8000/health | jq .status
```

- [ ] Check launchd status
- [ ] Check health endpoints

### Weekly (15 minutes)
```bash
# Check for errors in logs
grep -i error ~/Library/Logs/FoKS/com.foks.bootstrap.out.log | tail -20
grep -i error ~/Library/Logs/FoKS/com.fbp.bootstrap.out.log | tail -20

# Check memory trend
ps aux | grep python

# Check for restarts (high PID = recent restart)
ps aux | grep python
```

- [ ] No error logs accumulating
- [ ] Memory usage stable
- [ ] No frequent restarts

### Monthly (30 minutes)
```bash
# Rotate logs (optional, prevents huge files)
# Create a log rotation script or use logrotate

# Review performance metrics
# - LLM latency
# - Memory usage patterns
# - CPU usage patterns
# - Restart count

# Update documentation if needed
```

- [ ] Logs are manageable size
- [ ] Performance is acceptable

---

## ✅ Final Sign-Off

When all steps are complete and verified:

```
✅ Pre-deployment verified
✅ Backup completed
✅ Deployment script ran
✅ Services running and responding
✅ Configuration verified
✅ LM Studio optimized
✅ Resources monitored
✅ Critical paths tested
✅ Restart recovery tested
✅ Documentation completed
✅ Rollback plan in place
✅ Ongoing monitoring established

🎉 Deployment Complete!
```

---

## Quick Reference Commands

```bash
# Check status
launchctl list | grep -E "com\.foks|com\.fbp"

# View logs
tail -f ~/Library/Logs/FoKS/com.foks.bootstrap.out.log

# Health check
curl http://127.0.0.1:8000/health

# Restart services
launchctl unload ~/Library/LaunchAgents/com.foks.bootstrap.plist
launchctl load ~/Library/LaunchAgents/com.foks.bootstrap.plist

# Monitor resources
top
Activity Monitor.app

# Emergency restart (nuclear option)
killall -9 python3
```

---

**Created:** December 8, 2025  
**Status:** Ready to Deploy  
**Estimated Time:** 1.5 hours (including monitoring)  
**Difficulty:** Medium (most steps are automated)
