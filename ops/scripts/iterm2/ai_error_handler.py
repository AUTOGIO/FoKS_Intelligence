#!/usr/bin/env python3
"""iTerm2 AI Integration - Smart Error Handler
Automatically detects errors and offers AI-assisted debugging.
"""

import asyncio
import re
import iterm2


# Error patterns to detect
ERROR_PATTERNS = [
    r'Traceback \(most recent call last\)',
    r'ERROR:.*',
    r'CRITICAL:.*',
    r'Exception:.*',
    r'Failed to.*',
    r'Connection refused',
    r'ModuleNotFoundError',
    r'ImportError',
    r'TimeoutError',
    r'PermissionError',
    r'FileNotFoundError',
]


async def extract_error_context(session: iterm2.Session, error_line_num: int):
    """Extract error context from session."""
    screen = await session.async_get_screen_contents()
    lines = screen.lines
    
    # Get 10 lines before and 5 lines after error
    start = max(0, error_line_num - 10)
    end = min(len(lines), error_line_num + 5)
    
    context_lines = []
    for i in range(start, end):
        if i < len(lines):
            line_text = lines[i].string
            # Mark the error line
            if i == error_line_num:
                context_lines.append(f">>> {line_text}")
            else:
                context_lines.append(f"    {line_text}")
    
    return "\n".join(context_lines)


async def get_session_info(session: iterm2.Session):
    """Get session metadata."""
    profile = await session.async_get_profile()
    
    info = {
        "profile": profile.name if profile else "Unknown",
        "cwd": await session.async_get_variable("user.cwd") or "Unknown",
        "hostname": await session.async_get_variable("user.hostname") or "localhost",
        "username": await session.async_get_variable("user.username") or "Unknown",
    }
    
    return info


async def create_ai_debug_prompt(error_context: str, session_info: dict, error_type: str):
    """Create structured prompt for AI debugging."""
    prompt = f"""🔍 Error Detected in FoKS Automation

**Environment**:
- Profile: {session_info['profile']}
- Directory: {session_info['cwd']}
- Host: {session_info['hostname']}
- User: {session_info['username']}

**Error Type**: {error_type}

**Error Context**:
```
{error_context}
```

**Request**: Please analyze this error and suggest:
1. Root cause
2. Fix steps
3. Prevention tips for FoKS/NFA automation workflows

If this is a Playwright automation error, consider:
- Selector issues
- Timing/wait issues
- Frame/context problems
- Network/timeout issues
"""
    return prompt


async def show_ai_dialog(connection: iterm2.Connection, prompt: str):
    """Show AI chat with pre-filled error context."""
    # Create alert with option to open AI chat
    alert = iterm2.Alert(
        "Error Detected - AI Debug Assistant",
        "An error was detected in this session. Would you like AI assistance to debug?",
        ["Open AI Chat", "Ignore"]
    )
    
    selection = await alert.async_run(connection)
    
    if selection == 0:  # Open AI Chat
        # Note: This requires iTerm2 3.5+ with AI Chat feature
        # The prompt will be copied to clipboard for manual paste
        # (Direct AI API integration requires additional setup)
        
        # Copy prompt to clipboard
        import subprocess
        subprocess.run(
            ["pbcopy"],
            input=prompt.encode('utf-8'),
            check=True
        )
        
        # Show notification
        notice = iterm2.Alert(
            "Debug Prompt Ready",
            "Debug prompt copied to clipboard!\n\n"
            "Open AI Chat (Window → AI Chat) and paste to get assistance.",
            ["OK"]
        )
        await notice.async_run(connection)


async def monitor_for_errors(connection: iterm2.Connection):
    """Monitor all sessions for errors."""
    app = await iterm2.async_get_app(connection)
    
    # Track already-handled errors to avoid duplicates
    handled_errors = set()
    
    async with iterm2.EachSessionOnceMonitor(connection) as monitor:
        while True:
            session_id = await monitor.async_get()
            session = app.get_session_by_id(session_id)
            
            if session:
                asyncio.create_task(
                    watch_session_for_errors(
                        connection,
                        session,
                        handled_errors
                    )
                )


async def watch_session_for_errors(
    connection: iterm2.Connection,
    session: iterm2.Session,
    handled_errors: set
):
    """Watch a specific session for errors."""
    try:
        async with session.get_screen_streamer() as streamer:
            while True:
                contents = await streamer.async_get()
                lines = contents.lines
                
                for i, line in enumerate(lines):
                    line_text = line.string
                    
                    # Check each error pattern
                    for pattern in ERROR_PATTERNS:
                        if re.search(pattern, line_text, re.IGNORECASE):
                            # Create unique error signature
                            error_sig = f"{session.session_id}:{i}:{line_text[:50]}"
                            
                            if error_sig not in handled_errors:
                                handled_errors.add(error_sig)
                                
                                # Extract context
                                error_context = await extract_error_context(session, i)
                                session_info = await get_session_info(session)
                                
                                # Determine error type
                                error_type = "Unknown"
                                if "Traceback" in line_text:
                                    error_type = "Python Exception"
                                elif "ERROR" in line_text:
                                    error_type = "Application Error"
                                elif "TimeoutError" in line_text:
                                    error_type = "Timeout Error"
                                elif "Connection" in line_text:
                                    error_type = "Connection Error"
                                
                                # Create AI prompt
                                ai_prompt = await create_ai_debug_prompt(
                                    error_context,
                                    session_info,
                                    error_type
                                )
                                
                                # Show AI dialog
                                await show_ai_dialog(connection, ai_prompt)
                                
                                break  # Only handle first match per line
                
                await asyncio.sleep(0.5)  # Check twice per second
                
    except Exception as e:
        # Silently handle errors in error monitor itself
        pass


async def main(connection: iterm2.Connection):
    """Start error monitoring."""
    await monitor_for_errors(connection)


# Run the script
iterm2.run_forever(main)
