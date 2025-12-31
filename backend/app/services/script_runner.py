"""Script runner service for executing external Python scripts."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.logging_utils import get_logger

# Calculate project root: backend/app/services/script_runner.py -> backend -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "ops" / "scripts"

logger = get_logger(__name__)


@dataclass
class ScriptResult:
    """Result from script execution."""

    status: str  # "success" | "error"
    exit_code: int
    output: dict[str, Any] | str  # JSON dict or text
    errors: str  # stderr output
    stdout: str  # Full stdout
    stderr: str  # Full stderr

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "exit_code": self.exit_code,
            "output": self.output,
            "errors": self.errors,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


async def run_local_script(
    script: str,
    args: dict[str, Any],
    *,
    timeout: int = 900,
    script_dir: Path | None = None,
) -> ScriptResult:
    """
    Run a local Python script and capture its output.

    Args:
        script: Script filename (e.g., "nfa_atf.py")
        args: Dictionary of arguments to pass as CLI args
        timeout: Maximum execution time in seconds (default: 900)
        script_dir: Directory containing the script (default: ops/scripts/nfa/)

    Returns:
        ScriptResult with parsed JSON output or error details

    Raises:
        FileNotFoundError: If script file doesn't exist
        RuntimeError: If script execution fails critically
    """
    if script_dir is None:
        script_dir = SCRIPTS_DIR / "nfa"

    script_path = script_dir / script
    if not script_path.exists():
        error_msg = f"Script not found: {script_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Build command
    command = [sys.executable, str(script_path)]

    # Convert args dict to CLI arguments
    # Format: --key value for each arg, or --key for boolean True flags
    for key, value in args.items():
        if value is None:
            continue
        # Convert snake_case to kebab-case for CLI
        cli_key = key.replace("_", "-")
        # Handle boolean flags: if True, just add flag; if False, skip
        if isinstance(value, bool):
            if value is True:
                command.append(f"--{cli_key}")
            # If False, skip (don't add flag)
        else:
            command.extend([f"--{cli_key}", str(value)])

    logger.info(
        "Executing script",
        extra={
            "payload": {
                "script": script,
                "script_path": str(script_path),
                "args": args,
                "timeout": timeout,
            }
        },
    )

    # Execute script
    start_time = asyncio.get_event_loop().time()
    try:
        # Prepare environment variables (inherit current env and ensure NFA credentials are available)
        import os
        env = os.environ.copy()

        # Try to load NFA credentials from FBP config if not in environment
        if "NFA_USERNAME" not in env or "NFA_PASSWORD" not in env:
            try:
                # Try to load from FBP .env file directly
                fbp_env_path = Path("/Users/dnigga/Documents/FBP_Backend/.env")
                if fbp_env_path.exists():
                    try:
                        from dotenv import dotenv_values
                        fbp_env = dotenv_values(fbp_env_path)
                        if not env.get("NFA_USERNAME") and fbp_env.get("NFA_USERNAME"):
                            env["NFA_USERNAME"] = fbp_env["NFA_USERNAME"]
                            logger.info("Loaded NFA_USERNAME from FBP .env file")
                        if not env.get("NFA_PASSWORD") and fbp_env.get("NFA_PASSWORD"):
                            env["NFA_PASSWORD"] = fbp_env["NFA_PASSWORD"]
                            logger.info("Loaded NFA_PASSWORD from FBP .env file")
                    except ImportError:
                        # Fallback: try to parse .env manually
                        try:
                            with open(fbp_env_path, encoding="utf-8") as f:
                                for line in f:
                                    line = line.strip()
                                    if line and not line.startswith("#") and "=" in line:
                                        key, value = line.split("=", 1)
                                        key = key.strip()
                                        value = value.strip().strip('"').strip("'")
                                        if key == "NFA_USERNAME" and not env.get("NFA_USERNAME"):
                                            env["NFA_USERNAME"] = value
                                            logger.info("Loaded NFA_USERNAME from FBP .env file (manual parse)")
                                        elif key == "NFA_PASSWORD" and not env.get("NFA_PASSWORD"):
                                            env["NFA_PASSWORD"] = value
                                            logger.info("Loaded NFA_PASSWORD from FBP .env file (manual parse)")
                        except Exception as parse_error:
                            logger.warning(f"Failed to parse FBP .env file: {parse_error}")
                    except Exception as e:
                        logger.warning(f"Failed to load NFA credentials from FBP .env: {e}")
            except Exception as e:
                logger.warning(f"Failed to load NFA credentials from FBP: {e}")

        # Warn if credentials are still missing
        if "NFA_USERNAME" not in env or not env.get("NFA_USERNAME"):
            logger.warning("NFA_USERNAME not found in environment or FBP config")
        if "NFA_PASSWORD" not in env or not env.get("NFA_PASSWORD"):
            logger.warning("NFA_PASSWORD not found in environment or FBP config")

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(script_dir),
            env=env,  # Pass environment variables to subprocess
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            elapsed = int(
                (asyncio.get_event_loop().time() - start_time) * 1000
            )
            error_msg = f"Script timed out after {timeout}s"
            logger.error(
                error_msg,
                extra={"payload": {"script": script, "elapsed_ms": elapsed}},
            )
            return ScriptResult(
                status="error",
                exit_code=-1,
                output={"error": error_msg, "error_type": "timeout"},
                errors=error_msg,
                stdout="",
                stderr=error_msg,
            )

        exit_code = process.returncode or 0
        stdout = (stdout_bytes or b"").decode("utf-8", errors="replace").strip()
        stderr = (stderr_bytes or b"").decode("utf-8", errors="replace").strip()

        elapsed = int(
            (asyncio.get_event_loop().time() - start_time) * 1000
        )
        logger.info(
            "Script execution completed",
            extra={
                "payload": {
                    "script": script,
                    "exit_code": exit_code,
                    "elapsed_ms": elapsed,
                    "stdout_length": len(stdout),
                    "stderr_length": len(stderr),
                }
            },
        )

        # Parse JSON from stdout
        output: dict[str, Any] | str
        status = "success" if exit_code == 0 else "error"

        if stdout:
            try:
                # Try to extract JSON from stdout (may have log lines before/after)
                json_start = stdout.find("{")
                json_end = stdout.rfind("}") + 1

                if json_start != -1 and json_end > 0:
                    json_str = stdout[json_start:json_end]
                    output = json.loads(json_str)
                    # Use status from JSON if available
                    if isinstance(output, dict) and "status" in output:
                        status = output["status"]
                else:
                    # No JSON found, use stdout as text output
                    output = stdout
                    if exit_code != 0:
                        status = "error"
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse JSON from stdout",
                    extra={
                        "payload": {
                            "script": script,
                            "error": str(e),
                            "stdout_preview": stdout[:500],
                        }
                    },
                )
                output = stdout
                if exit_code != 0:
                    status = "error"
        else:
            # No stdout, create error output
            output = {"error": "Script produced no output", "error_type": "no_output"}
            status = "error"

        # If exit code is non-zero and we don't have error details
        if exit_code != 0 and isinstance(output, dict) and "error" not in output:
            output["error"] = stderr or "Script exited with non-zero code"
            output["error_type"] = "script_error"

        return ScriptResult(
            status=status,
            exit_code=exit_code,
            output=output,
            errors=stderr,
            stdout=stdout,
            stderr=stderr,
        )

    except FileNotFoundError:
        error_msg = f"Python interpreter not found: {sys.executable}"
        logger.error(error_msg)
        return ScriptResult(
            status="error",
            exit_code=-1,
            output={"error": error_msg, "error_type": "python_not_found"},
            errors=error_msg,
            stdout="",
            stderr=error_msg,
        )
    except Exception as e:
        error_msg = f"Failed to execute script: {str(e)}"
        logger.error(
            error_msg, exc_info=True, extra={"payload": {"script": script}}
        )
        return ScriptResult(
            status="error",
            exit_code=-1,
            output={"error": error_msg, "error_type": "execution_error"},
            errors=str(e),
            stdout="",
            stderr=str(e),
        )
