#!/usr/bin/env python3
"""iTerm2 Trigger - Auto-restart on Backend Crash
Automatically restarts FoKS or FBP backends when they crash.
"""

import asyncio

try:
    import iterm2
except ImportError as e:
    raise ImportError(
        "iterm2 Python API is required to use this script. "
        "Install with: pip install iterm2 or see: https://iterm2.com/python-api/"
    ) from e


async def monitor_session_output(connection: "iterm2.Connection"):
    """
    Monitor session output and auto-restart on crash.

    Args:
        connection (iterm2.Connection): Active iTerm2 Python API connection.
    """
    app = await iterm2.async_get_app(connection)
    
    async with iterm2.EachSessionOnceMonitor(connection) as monitor:
        while True:
            session_id = await monitor.async_get()
            session = app.get_session_by_id(session_id)
            
            if session:
                # Monitor this session
                asyncio.create_task(watch_for_crashes(session))


async def watch_for_crashes(session: iterm2.Session):
    """Watch a specific session for crash indicators."""
    async with session.get_screen_streamer() as streamer:
        while True:
            contents = await streamer.async_get()
            
            # Check for crash indicators
            text = contents.string
            
            if any(indicator in text.lower() for indicator in [
                "traceback",
                "critical error",
                "connection refused",
                "address already in use",
                "port is already in use"
            ]):
                # Get session profile name
                profile = await session.async_get_profile()
                profile_name = profile.name if profile else ""
                
                # Auto-restart based on profile
                if "FoKS Intelligence" in profile_name:
                    await restart_foks_backend(session)
                elif "FBP Backend" in profile_name:
                    await restart_fbp_backend(session)


async def restart_foks_backend(session: iterm2.Session):
    """Restart FoKS backend."""
    # Send Ctrl+C to stop current process
    await session.async_send_text("\x03")
    await asyncio.sleep(1)
    
    # Restart command
    restart_cmd = (
        "cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend && "
        "source /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/.venv_foks/bin/activate && "
        "echo '🔄 Auto-restarting FoKS backend...' && "
        "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload\n"
    )
    await session.async_send_text(restart_cmd)


async def restart_fbp_backend(session: iterm2.Session):
    """Restart FBP backend."""
    # Send Ctrl+C to stop current process
    await session.async_send_text("\x03")
    await asyncio.sleep(1)
    
    # Clean up socket
    cleanup_cmd = "rm -f /tmp/fbp.sock\n"
    await session.async_send_text(cleanup_cmd)
    await asyncio.sleep(0.5)
    
    # Restart command
    restart_cmd = (
        "cd /Users/dnigga/Documents/FBP_Backend && "
        "source ~/.venvs/fbp/bin/activate && "
        "echo '🔄 Auto-restarting FBP backend...' && "
        "uvicorn app.main:app --uds /tmp/fbp.sock --loop uvloop --http httptools\n"
    )
    await session.async_send_text(restart_cmd)


async def main(connection: iterm2.Connection):
    """Monitor all sessions for crashes."""
    await monitor_session_output(connection)


iterm2.run_forever(main)
