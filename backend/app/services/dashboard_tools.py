"""Dashboard tools service for engineering briefings and analytics."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict

import httpx

from app.config import PROJECT_ROOT, settings
from app.services.fbp_client import FBPClient
from app.services.lmstudio_client import LMStudioClient, LMStudioClientError
from app.services.logging_utils import get_logger
from app.services.monitoring import monitoring

logger = get_logger(__name__)


class HealthStatus(TypedDict, total=False):
    """Health status response structure."""
    status: str  # "ok" or "error"
    data: dict[str, Any]  # Optional data payload
    error: str  # Optional error message


class BriefingResult(TypedDict):
    """Result structure for briefing generation."""
    markdown: str


async def _run_git_command(
    repo_path: Path,
    command: list[str],
    timeout: int = 10,
) -> str | None:
    """
    Run a git command and return stdout, or None on error.

    Args:
        repo_path: Path to git repository
        command: Git command arguments (without 'git' prefix)
        timeout: Command timeout in seconds

    Returns:
        Command stdout as string, or None if command failed or timed out
    """
    try:
        result = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                "git",
                *command,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=timeout,
        )
        stdout, stderr = await result.communicate()
        if result.returncode == 0:
            return stdout.decode("utf-8").strip()
        logger.warning(
            "Git command failed",
            extra={
                "payload": {
                    "command": " ".join(command),
                    "repo_path": str(repo_path),
                    "stderr": stderr.decode("utf-8")[:200],  # noqa: E501
                }
            },
        )
        return None
    except TimeoutError:
        logger.warning(
            "Git command timed out",
            extra={"payload": {"command": " ".join(command)}},
        )
        return None
    except Exception:
        logger.error(
            "Git command error",
            exc_info=True,
            extra={"payload": {"command": " ".join(command)}},
        )
        return None


async def _get_recent_commits(
    repo_path: Path, hours: int = 24
) -> list[dict[str, Any]]:
    """
    Get recent commits from the last N hours.

    Args:
        repo_path: Path to git repository
        hours: Number of hours to look back (default: 24)

    Returns:
        List of commit dictionaries with keys: hash, author, email,
        date, message
    """
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    output = await _run_git_command(
        repo_path,
        [
            "log",
            f"--since={since}",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso",
        ],
    )
    if not output:
        return []

    commits = []
    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 4)
        if len(parts) == 5:
            commits.append(
                {
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "message": parts[4],
                }
            )
    return commits


async def _get_open_pr_branches(
    repo_path: Path,
) -> list[dict[str, Any]]:
    """
    Get local branches matching feature/* or fix/* patterns.

    Args:
        repo_path: Path to git repository

    Returns:
        List of branch dictionaries with keys: name, last_commit
        (hash, author, date, message)
    """
    output = await _run_git_command(
        repo_path, ["branch", "--list", "feature/*", "fix/*"]
    )
    if not output:
        return []

    branches = []
    for line in output.split("\n"):
        branch_name = line.strip().lstrip("*").strip()
        if not branch_name:
            continue

        # Get last commit on branch
        last_commit = await _run_git_command(
            repo_path,
            [
                "log",
                "-1",
                "--pretty=format:%H|%an|%ad|%s",
                "--date=iso",
                branch_name,
            ],
        )
        if last_commit:
            parts = last_commit.split("|", 3)
            if len(parts) == 4:
                branches.append(
                    {
                        "name": branch_name,
                        "last_commit": {
                            "hash": parts[0][:8],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3],
                        },
                    }
                )
    return branches


async def _get_directory_changes(
    repo_path: Path,
    directories: list[str],
    hours: int = 24,
) -> dict[str, list[str]]:
    """
    Get changed files in specified directories.

    Args:
        repo_path: Path to git repository
        directories: List of directory paths to check
        hours: Number of hours to look back (default: 24)

    Returns:
        Dictionary mapping directory paths to lists of changed file paths
    """
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    changes: dict[str, list[str]] = {}

    for directory in directories:
        rel_path = Path(directory)
        if not (repo_path / rel_path).exists():
            continue

        output = await _run_git_command(
            repo_path,
            [
                "log",
                f"--since={since}",
                "--name-only",
                "--pretty=format:",
                "--",
                str(rel_path),
            ],
        )
        if output:
            files = [
                f.strip()
                for f in output.split("\n")
                if f.strip() and not f.startswith("commit")
            ]
            if files:
                changes[directory] = list(set(files))  # Deduplicate

    return changes


async def _get_foks_health() -> HealthStatus:
    """
    Get FoKS system health from monitoring service.

    Returns:
        HealthStatus with status "ok" and data payload, or status "error" with error message
    """
    try:
        stats = monitoring.get_stats()
        return {
            "status": "ok",
            "data": {
                "uptime_seconds": stats.get("uptime_seconds", 0),
                "uptime_formatted": stats.get("uptime_formatted", "0s"),
                "requests": {
                    "total": stats.get("requests", {}).get("total", 0),
                    "success": stats.get("requests", {}).get("success", 0),
                    "failures": stats.get("requests", {}).get("failures", 0),
                    "avg_response_time_ms": stats.get("requests", {}).get("avg_response_time_ms", 0),
                },
                "tasks": {
                    "total": stats.get("tasks", {}).get("total", 0),
                    "success": stats.get("tasks", {}).get("success", 0),
                    "failures": stats.get("tasks", {}).get("failures", 0),
                },
            },
        }
    except Exception as exc:
        logger.warning("FoKS health check failed", exc_info=True)
        return {"status": "error", "error": str(exc)}


async def _get_fbp_health() -> HealthStatus | None:
    """
    Get FBP backend health via UNIX socket.

    Returns:
        HealthStatus with status "ok" and data payload, or status "error"
        with error message. Returns None if FBP health check is disabled
        or unavailable.
    """
    try:
        client = FBPClient()
        result = await client.health()
        await client.close()
        return {"status": "ok", "data": result.get("payload", {})}
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "FBP health check failed",
            exc_info=True,
            extra={"payload": {"error_type": type(exc).__name__}},
        )
        return {"status": "error", "error": str(exc)}


async def _get_lmstudio_health() -> HealthStatus:
    """
    Get LM Studio health by checking available models.

    Returns:
        HealthStatus with status "ok" and models data, or status "error" with error message
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            base_url = settings.lmstudio_base_url.rstrip("/v1").rstrip("/")
            response = await client.get(f"{base_url}/v1/models")
            if response.status_code == 200:
                models = response.json()
                return {
                    "status": "ok",
                    "data": {
                    "models_count": len(models.get("data", [])),
                    "models": [m.get("id", "") for m in models.get("data", [])[:5]],
                    },
                }
            return {"status": "error", "error": f"HTTP {response.status_code}"}
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "LM Studio health check failed",
            exc_info=True,
            extra={"payload": {"error_type": type(exc).__name__}},
        )
        return {"status": "error", "error": str(exc)}


async def _get_nfa_stats() -> dict[str, Any]:
    """
    Get NFA/ATF statistics from recent reports.

    Returns:
        Dictionary with NFA stats: processed_today, failures_today, last_run, last_report_path
    """
    from app.config import PROJECT_ROOT

    reports_dir = PROJECT_ROOT / "reports"
    if not reports_dir.exists():
        return {
            "processed_today": 0,
            "failures_today": 0,
            "last_run": None,
            "last_report_path": None,
        }

    try:
        # Find all NFA reports
        nfa_reports = sorted(
            reports_dir.glob("NFA_ATF_RUN_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not nfa_reports:
            return {
                "processed_today": 0,
                "failures_today": 0,
                "last_run": None,
                "last_report_path": None,
            }

        # Get today's reports
        today = datetime.now().date()
        today_reports = [
            r
            for r in nfa_reports
            if datetime.fromtimestamp(r.stat().st_mtime).date() == today
        ]

        # Calculate today's stats
        processed_today = 0
        failures_today = 0

        for report_path in today_reports:
            try:
                with open(report_path, encoding="utf-8") as f:
                    report_data = json.load(f)
                    summary = report_data.get("summary", {})
                    processed_today += summary.get("total_items", 0)
                    failures_today += summary.get("failure_count", 0)
            except Exception:
                # Skip corrupted reports
                continue

        # Get last run info from most recent report
        last_report = nfa_reports[0]
        last_run_time = datetime.fromtimestamp(last_report.stat().st_mtime)

        return {
            "processed_today": processed_today,
            "failures_today": failures_today,
            "last_run": last_run_time.isoformat(),
            "last_report_path": str(last_report),
        }

    except Exception:
        logger.warning("Failed to get NFA stats", exc_info=True)
        return {
            "processed_today": 0,
            "failures_today": 0,
            "last_run": None,
            "last_report_path": None,
        }


async def _get_obsidian_notes(
    obsidian_path: str | None,
) -> list[dict[str, Any]]:
    """
    Get recent Obsidian notes if path is provided.

    Args:
        obsidian_path: Optional path to Obsidian vault directory

    Returns:
        List of note dictionaries with keys: path, modified (ISO timestamp).
        Returns empty list if path is None, doesn't exist, or on error.
    """
    if not obsidian_path:
        return []

    notes_path = Path(obsidian_path)
    if not notes_path.exists():
        logger.warning(
            "Obsidian path does not exist",
            extra={"payload": {"path": obsidian_path}},
        )
        return []

    try:
        # Find markdown files modified in last 24h
        cutoff = datetime.now() - timedelta(hours=24)
        recent_notes = []

        for md_file in notes_path.rglob("*.md"):
            if md_file.stat().st_mtime >= cutoff.timestamp():
                recent_notes.append(
                    {
                        "path": str(md_file.relative_to(notes_path)),
                        "modified": datetime.fromtimestamp(
                            md_file.stat().st_mtime
                        ).isoformat(),
                    }
                )

        # Sort by modification time, most recent first
        recent_notes.sort(key=lambda x: x["modified"], reverse=True)
        return recent_notes[:10]  # Top 10 most recent
    except Exception:
        logger.warning(
            "Failed to read Obsidian notes",
            exc_info=True,
            extra={"payload": {"path": obsidian_path}},
        )
        return []


async def build_daily_engineering_briefing(
    repo_path: str | None = None,
    obsidian_path: str | None = None,
    include_fbp_health: bool = True,
) -> BriefingResult:
    """
    Build a daily engineering briefing from git, health checks, and optional
    Obsidian notes.

    Collects data in parallel, then generates markdown via LM Studio.
    Falls back to template-based markdown if LM Studio is unavailable.

    Args:
        repo_path: Path to git repository (defaults to PROJECT_ROOT)
        obsidian_path: Optional path to Obsidian vault for recent notes
        include_fbp_health: Whether to include FBP backend health check

    Returns:
        BriefingResult with "markdown" key containing the formatted briefing.
        Always returns a valid markdown string (either from LM Studio or
        fallback template).

    Raises:
        RuntimeError: If fallback template generation fails
            (should never happen)
    """
    logger.info(
        "Building daily engineering briefing",
        extra={"payload": {"repo_path": repo_path}},
    )

    # Determine repository path
    if repo_path:
        repo_path_obj = Path(repo_path).resolve()
    else:
        repo_path_obj = PROJECT_ROOT

    if not (repo_path_obj / ".git").exists():
        logger.warning(
            "Not a git repository",
            extra={"payload": {"path": str(repo_path_obj)}},
        )
        repo_path_obj = PROJECT_ROOT  # Fallback to project root

    # Collect data in parallel
    commits_task = _get_recent_commits(repo_path_obj, hours=24)
    branches_task = _get_open_pr_branches(repo_path_obj)
    changes_task = _get_directory_changes(
        repo_path_obj,
        ["backend/app", "ops/scripts"],
        hours=24,
    )
    foks_health_task = _get_foks_health()
    lmstudio_health_task = _get_lmstudio_health()
    obsidian_task = _get_obsidian_notes(obsidian_path)

    (
        commits,
        branches,
        changes,
        foks_health,
        lmstudio_health,
        obsidian_notes,
    ) = await asyncio.gather(
        commits_task,
        branches_task,
        changes_task,
        foks_health_task,
        lmstudio_health_task,
        obsidian_task,
    )

    # Optionally get FBP health
    fbp_health = None
    if include_fbp_health:
        fbp_health = await _get_fbp_health()

    # Get NFA/ATF statistics
    nfa_stats = await _get_nfa_stats()

    # Build structured payload for LM Studio
    briefing_data = {
        "timestamp": datetime.now().isoformat(),
        "repository": {
            "path": str(repo_path_obj),
            "recent_commits": commits,
            "open_branches": branches,
            "directory_changes": changes,
        },
        "system_health": {
            "foks": foks_health,
            "lmstudio": lmstudio_health,
        },
    }

    if fbp_health:
        system_health = briefing_data["system_health"]
        if isinstance(system_health, dict):
            system_health["fbp"] = fbp_health

    # Add NFA/ATF stats to system_health
    system_health = briefing_data["system_health"]
    if isinstance(system_health, dict):
        system_health["nfa_atf"] = nfa_stats

    if obsidian_notes:
        briefing_data["obsidian_notes"] = obsidian_notes

    # Create user prompt with instructions for LM Studio
    user_prompt = f"""You are an engineering briefing assistant. Generate a \
clear, concise daily engineering briefing in markdown format.

Structure the briefing as follows:
1. **Executive Summary** - Brief overview of the day's activity
2. **Recent Commits** - List of commits from the last 24 hours
3. **Active Branches** - Open feature/fix branches and their status
4. **Key Changes** - Notable changes in backend/app and ops/scripts
5. **System Health** - Status of FoKS, FBP (if available), LM Studio, and NFA/ATF
6. **Recent Notes** - Recent Obsidian notes (if available)

Use clear markdown formatting with headers, lists, and code blocks where \
appropriate. Keep it professional and actionable.

Generate a daily engineering briefing based on the following data:

{json.dumps(briefing_data, indent=2)}

Provide a well-formatted markdown briefing that summarizes the engineering \
activity and system status."""

    # Send to LM Studio with robust fallback
    markdown: str
    try:
        lm_client = LMStudioClient()
        result = await lm_client.chat(
            user_prompt,
            model_name=None,  # Use default model
            task_type="chat",
            tools_required=False,
        )
        markdown = result.get("response", "")
        if not markdown or not markdown.strip():
            logger.warning(
                "LM Studio returned empty response, using fallback",
                extra={"payload": {"result_keys": list(result.keys())}},
            )
            markdown = _generate_fallback_briefing(briefing_data)
        else:
            logger.info(
                "Daily engineering briefing generated successfully via "
                "LM Studio",
                extra={"payload": {"markdown_length": len(markdown)}},
            )
    except (LMStudioClientError, Exception) as exc:  # noqa: BLE001
        logger.warning(
            "Failed to generate briefing via LM Studio, using fallback "
            "template",
            exc_info=True,
            extra={
                "payload": {
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            },
        )
        # Fallback: generate a simple markdown template
        markdown = _generate_fallback_briefing(briefing_data)

    return {"markdown": markdown}


def _generate_fallback_briefing(data: dict[str, Any]) -> str:
    """
    Generate a simple markdown briefing as fallback if LM Studio fails.

    This function always returns valid markdown, even if data is incomplete.

    Args:
        data: Briefing data dictionary with timestamp, repository, system_health, etc.

    Returns:
        Valid markdown string with briefing content
    """
    timestamp = data.get("timestamp", datetime.now().isoformat())
    lines = ["# Daily Engineering Briefing", "", f"**Generated:** {timestamp}", ""]

    # Commits
    commits = data.get("repository", {}).get("recent_commits", [])
    if commits:
        lines.append("## Recent Commits (Last 24h)")
        for commit in commits[:10]:
            lines.append(f"- `{commit['hash']}` {commit['message']} ({commit['author']})")
        lines.append("")

    # Branches
    branches = data.get("repository", {}).get("open_branches", [])
    if branches:
        lines.append("## Active Branches")
        for branch in branches:
            lines.append(f"- **{branch['name']}**: {branch['last_commit']['message']}")
        lines.append("")

    # System Health
    health = data.get("system_health", {})
    if health:
        lines.append("## System Health")
        for service, status in health.items():
            if isinstance(status, dict):
                if status.get("status") == "ok":
                    status_str = "✅ OK"
                else:
                    error_msg = status.get("error", "Unknown")
                    status_str = f"❌ Error: {error_msg}"
                lines.append(f"- **{service.upper()}**: {status_str}")
        lines.append("")

    # Obsidian Notes
    obsidian_notes = data.get("obsidian_notes", [])
    if obsidian_notes:
        lines.append("## Recent Notes")
        for note in obsidian_notes[:5]:  # Top 5 most recent
            note_path = note.get("path", "Unknown")
            lines.append(f"- `{note_path}`")
        lines.append("")

    # Ensure we always return valid markdown
    if len(lines) <= 3:  # Only header and timestamp
        lines.append("_No recent activity to report._")

    return "\n".join(lines)
