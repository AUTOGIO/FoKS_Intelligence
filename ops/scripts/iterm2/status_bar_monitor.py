#!/usr/bin/env python3
"""iTerm2 Status Bar Component - FoKS Automation Monitor
Displays real-time status of FoKS and FBP backends in status bar.
"""

import asyncio
import json
import iterm2
import subprocess


async def check_foks_status():
    """Check FoKS backend status."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "2", "http://localhost:8000/health"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return f"✅ FoKS:{data.get('environment', 'OK')}"
        return "❌ FoKS:Down"
    except Exception:
        return "❌ FoKS:Down"


async def check_fbp_status():
    """Check FBP backend status on Unix socket."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "2", "--unix-socket", "/tmp/fbp.sock", 
             "http://localhost/socket-health"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return f"✅ FBP:{data.get('via', 'OK')}"
        return "❌ FBP:Down"
    except Exception:
        return "❌ FBP:Down"


async def check_nfa_jobs():
    """Check recent NFA job count."""
    try:
        result = subprocess.run(
            ["bash", "-c", 
             "wc -l < /Users/dnigga/Downloads/NFA_Outputs/nfa_runs.jsonl 2>/dev/null || echo 0"],
            capture_output=True,
            text=True,
            timeout=2
        )
        count = result.stdout.strip()
        return f"📋 NFAs:{count}"
    except Exception:
        return "📋 NFAs:0"


async def status_monitor(knobs):
    """Status bar component coroutine."""
    while True:
        # Check all statuses
        foks_status, fbp_status, nfa_count = await asyncio.gather(
            check_foks_status(),
            check_fbp_status(),
            check_nfa_jobs()
        )
        
        # Combine status
        status_text = f"{foks_status} | {fbp_status} | {nfa_count}"
        
        # Update status bar
        await knobs.async_set_state(status_text)
        
        # Update every 5 seconds
        await asyncio.sleep(5)


async def main(connection: iterm2.Connection):
    """Register status bar component."""
    component = iterm2.StatusBarComponent(
        short_description="FoKS Monitor",
        detailed_description="Real-time FoKS and FBP backend status",
        knobs=[],
        exemplar="✅ FoKS:prod | ✅ FBP:unix | 📋 NFAs:42",
        update_cadence=5.0,
        identifier="com.foks.automation.monitor"
    )
    
    @iterm2.StatusBarRPC
    async def status_coroutine(knobs):
        await status_monitor(knobs)
    
    await component.async_register(connection, status_coroutine)


iterm2.run_forever(main)
