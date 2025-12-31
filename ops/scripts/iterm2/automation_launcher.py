#!/usr/bin/env python3
"""iTerm2 Python API - Automation Launcher
Automatically creates optimized window layouts for FoKS automation workflows.
"""

import asyncio
import iterm2


async def create_foks_workspace(connection: iterm2.Connection):
    """Create complete FoKS automation workspace with split panes."""
    app = await iterm2.async_get_app(connection)
    
    # Create new window with FoKS Backend profile
    window = await iterm2.Window.async_create(connection)
    
    # Main tab - Backend Services
    tab1 = window.current_tab
    await tab1.async_set_title("Backend Services")
    
    # Split horizontally - FoKS Backend (top) and FBP Backend (bottom)
    session1 = tab1.current_session
    await session1.async_set_profile("FoKS Intelligence - Backend")
    
    session2 = await session1.async_split_pane(vertical=False)
    await session2.async_set_profile("FBP Backend - Socket Server")
    
    # Create second tab - NFA Automation
    tab2 = await window.async_create_tab(profile="NFA Automation - Batch Runner")
    await tab2.async_set_title("NFA Automation")
    
    # Split into 3 panes: Batch Runner | Intelligence | Logs
    nfa_session1 = tab2.current_session
    nfa_session2 = await nfa_session1.async_split_pane(vertical=True, profile="NFA Intelligence - Reporting")
    nfa_session3 = await nfa_session2.async_split_pane(vertical=False, profile="Logs Monitor - Live Tail")
    
    # Create third tab - Operations & Monitoring
    tab3 = await window.async_create_tab(profile="M3 Operations Dashboard")
    await tab3.async_set_title("Operations")
    
    ops_session1 = tab3.current_session
    ops_session2 = await ops_session1.async_split_pane(vertical=True, profile="Quick Test Runner")
    
    # Create fourth tab - Development
    tab4 = await window.async_create_tab(profile="Playwright Browser Console")
    await tab4.async_set_title("Development")
    
    dev_session1 = tab4.current_session
    dev_session2 = await dev_session1.async_split_pane(vertical=True, profile="API Client - cURL Interactive")
    
    # Focus first tab
    await tab1.async_select()
    
    print("✅ FoKS Automation workspace created successfully!")
    return window


async def start_backends(connection: iterm2.Connection):
    """Start both FoKS and FBP backends automatically."""
    app = await iterm2.async_get_app(connection)
    
    # Find or create window
    if app.current_terminal_window:
        window = app.current_terminal_window
    else:
        window = await iterm2.Window.async_create(connection)
    
    # Create tab for FoKS backend
    foks_tab = await window.async_create_tab(profile="FoKS Intelligence - Backend")
    await foks_tab.async_set_title("FoKS Backend")
    foks_session = foks_tab.current_session
    
    # Start FoKS backend
    await foks_session.async_send_text(
        "cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend && "
        "source /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/.venv_foks/bin/activate && "
        "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload\n"
    )
    
    await asyncio.sleep(2)  # Wait for FoKS to start
    
    # Create tab for FBP backend
    fbp_tab = await window.async_create_tab(profile="FBP Backend - Socket Server")
    await fbp_tab.async_set_title("FBP Socket")
    fbp_session = fbp_tab.current_session
    
    # Start FBP backend on Unix socket
    await fbp_session.async_send_text(
        "cd /Users/dnigga/Documents/FBP_Backend && "
        "source ~/.venvs/fbp/bin/activate && "
        "uvicorn app.main:app --uds /tmp/fbp.sock --loop uvloop --http httptools\n"
    )
    
    print("✅ Both backends started!")


async def run_nfa_batch_visual(connection: iterm2.Connection):
    """Run NFA batch processing with visual monitoring."""
    app = await iterm2.async_get_app(connection)
    
    window = app.current_terminal_window or await iterm2.Window.async_create(connection)
    
    # Create monitoring layout
    monitor_tab = await window.async_create_tab(profile="NFA Automation - Batch Runner")
    await monitor_tab.async_set_title("NFA Batch Processing")
    
    # Main batch runner
    runner_session = monitor_tab.current_session
    
    # Split for live logs
    log_session = await runner_session.async_split_pane(
        vertical=False, 
        profile="Logs Monitor - Live Tail"
    )
    
    # Split for browser console
    browser_session = await runner_session.async_split_pane(
        vertical=True,
        profile="Playwright Browser Console"
    )
    
    # Start log monitoring in background
    await log_session.async_send_text(
        "tail -f /Users/dnigga/Downloads/NFA_Outputs/nfa_runs.jsonl\n"
    )
    
    # Start batch processing
    await runner_session.async_send_text(
        "python run_rental_nfa_batch.py\n"
    )
    
    print("✅ NFA batch processing started with monitoring!")


async def health_check_dashboard(connection: iterm2.Connection):
    """Create health monitoring dashboard."""
    app = await iterm2.async_get_app(connection)
    
    window = app.current_terminal_window or await iterm2.Window.async_create(connection)
    
    health_tab = await window.async_create_tab(profile="M3 Operations Dashboard")
    await health_tab.async_set_title("Health Monitor")
    
    dashboard_session = health_tab.current_session
    
    # Split for continuous monitoring
    test_session = await dashboard_session.async_split_pane(
        vertical=True,
        profile="Quick Test Runner"
    )
    
    # Run continuous health checks
    health_check_script = """
while true; do
    clear
    echo "🏥 System Health Check - $(date)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "FoKS Backend:"
    curl -s http://localhost:8000/health | jq . || echo "❌ Down"
    echo ""
    echo "FBP Socket:"
    curl -s --unix-socket /tmp/fbp.sock http://localhost/socket-health | jq . || echo "❌ Down"
    echo ""
    sleep 10
done
"""
    await test_session.async_send_text(health_check_script + "\n")
    
    print("✅ Health monitoring dashboard created!")


async def main(connection: iterm2.Connection):
    """Main automation entry point - interactive menu."""
    app = await iterm2.async_get_app(connection)
    
    # Create a selection menu
    menu = """
🚀 FoKS Automation Launcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select an action:
1. Create Full Workspace
2. Start Both Backends
3. Run NFA Batch (Visual)
4. Health Dashboard
5. Exit

Choice: """
    
    # For now, create full workspace by default
    await create_foks_workspace(connection)


# Register the script
iterm2.run_until_complete(main)
