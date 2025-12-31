"""Tests for dashboard tools service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import dashboard_tools
from app.services.fbp_client import FBPClient, FBPClientError
from app.services.lmstudio_client import LMStudioClient


@pytest.fixture
def mock_repo_path(tmp_path: Path) -> Path:
    """Create a temporary git repository for testing."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    return repo


@pytest.fixture
def mock_git_output():
    """Mock git command outputs."""
    return {
        "commits": """abc12345|John Doe|john@example.com|2024-01-15T10:00:00|Fix bug in dashboard
def67890|Jane Smith|jane@example.com|2024-01-15T09:00:00|Add new feature""",
        "branches": """  feature/new-dashboard
* fix/bug-123""",
        "branch_commit": """xyz98765|John Doe|2024-01-15T11:00:00|WIP: implementing feature""",
        "changes": """backend/app/services/dashboard_tools.py
backend/app/routers/tools_dashboard.py
ops/scripts/test.sh""",
    }


@pytest.mark.asyncio
async def test_get_recent_commits(mock_repo_path: Path, mock_git_output):
    """Test getting recent commits."""
    with patch("app.services.dashboard_tools._run_git_command") as mock_git:
        mock_git.return_value = mock_git_output["commits"]
        commits = await dashboard_tools._get_recent_commits(mock_repo_path, hours=24)
        assert len(commits) == 2
        assert commits[0]["hash"] == "abc12345"
        assert commits[0]["author"] == "John Doe"
        assert commits[0]["message"] == "Fix bug in dashboard"


@pytest.mark.asyncio
async def test_get_recent_commits_empty(mock_repo_path: Path):
    """Test getting recent commits when none exist."""
    with patch("app.services.dashboard_tools._run_git_command") as mock_git:
        mock_git.return_value = None
        commits = await dashboard_tools._get_recent_commits(mock_repo_path, hours=24)
        assert commits == []


@pytest.mark.asyncio
async def test_get_open_pr_branches(mock_repo_path: Path, mock_git_output):
    """Test getting open PR branches."""
    with patch("app.services.dashboard_tools._run_git_command") as mock_git:
        # First call returns branch list, second call returns commit for each branch
        mock_git.side_effect = [
            mock_git_output["branches"],
            mock_git_output["branch_commit"],
            mock_git_output["branch_commit"],
        ]
        branches = await dashboard_tools._get_open_pr_branches(mock_repo_path)
        assert len(branches) == 2
        assert "feature/new-dashboard" in [b["name"] for b in branches]
        assert "fix/bug-123" in [b["name"] for b in branches]


@pytest.mark.asyncio
async def test_get_directory_changes(mock_repo_path: Path, mock_git_output):
    """Test getting directory changes."""
    with patch("app.services.dashboard_tools._run_git_command") as mock_git:
        mock_git.return_value = mock_git_output["changes"]
        changes = await dashboard_tools._get_directory_changes(
            mock_repo_path,
            ["backend/app", "ops/scripts"],
            hours=24,
        )
        assert "backend/app" in changes or "ops/scripts" in changes


@pytest.mark.asyncio
async def test_get_foks_health_success():
    """Test FoKS health check success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "app": "FoKS Intelligence"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        health = await dashboard_tools._get_foks_health()
        assert health["status"] == "ok"
        assert "data" in health


@pytest.mark.asyncio
async def test_get_foks_health_failure():
    """Test FoKS health check failure."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.RequestError("Connection failed")
        health = await dashboard_tools._get_foks_health()
        assert health["status"] == "error"
        assert "error" in health


@pytest.mark.asyncio
async def test_get_fbp_health_success():
    """Test FBP health check success."""
    mock_client = AsyncMock(spec=FBPClient)
    mock_client.health = AsyncMock(
        return_value={
            "endpoint": "/health",
            "payload": {"status": "ok"},
            "status": 200,
        }
    )
    mock_client.close = AsyncMock()

    with patch("app.services.dashboard_tools.FBPClient", return_value=mock_client):
        health = await dashboard_tools._get_fbp_health()
        assert health is not None
        assert health["status"] == "ok"
        assert "data" in health


@pytest.mark.asyncio
async def test_get_fbp_health_failure():
    """Test FBP health check failure."""
    mock_client = AsyncMock(spec=FBPClient)
    mock_client.health = AsyncMock(side_effect=FBPClientError("Connection failed"))
    mock_client.close = AsyncMock()

    with patch("app.services.dashboard_tools.FBPClient", return_value=mock_client):
        health = await dashboard_tools._get_fbp_health()
        assert health is not None
        assert health["status"] == "error"
        assert "error" in health


@pytest.mark.asyncio
async def test_get_lmstudio_health_success():
    """Test LM Studio health check success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "model1"},
            {"id": "model2"},
        ]
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        health = await dashboard_tools._get_lmstudio_health()
        assert health["status"] == "ok"
        assert health["models_count"] == 2


@pytest.mark.asyncio
async def test_get_lmstudio_health_failure():
    """Test LM Studio health check failure."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.RequestError("Connection failed")
        health = await dashboard_tools._get_lmstudio_health()
        assert health["status"] == "error"
        assert "error" in health


@pytest.mark.asyncio
async def test_get_obsidian_notes_success(tmp_path: Path):
    """Test getting Obsidian notes."""
    obsidian_path = tmp_path / "obsidian"
    obsidian_path.mkdir()
    (obsidian_path / "note1.md").write_text("# Note 1")
    (obsidian_path / "note2.md").write_text("# Note 2")

    # Mock file modification times to be recent
    import time
    recent_time = time.time()
    (obsidian_path / "note1.md").touch()
    (obsidian_path / "note2.md").touch()

    notes = await dashboard_tools._get_obsidian_notes(str(obsidian_path))
    assert len(notes) >= 2


@pytest.mark.asyncio
async def test_get_obsidian_notes_none():
    """Test getting Obsidian notes when path is None."""
    notes = await dashboard_tools._get_obsidian_notes(None)
    assert notes == []


@pytest.mark.asyncio
async def test_build_daily_engineering_briefing_success(mock_repo_path: Path, mock_git_output):
    """Test building daily engineering briefing successfully."""
    # Mock all the data collection functions
    with patch("app.services.dashboard_tools._get_recent_commits") as mock_commits, \
         patch("app.services.dashboard_tools._get_open_pr_branches") as mock_branches, \
         patch("app.services.dashboard_tools._get_directory_changes") as mock_changes, \
         patch("app.services.dashboard_tools._get_foks_health") as mock_foks, \
         patch("app.services.dashboard_tools._get_lmstudio_health") as mock_lmstudio, \
         patch("app.services.dashboard_tools._get_obsidian_notes") as mock_obsidian, \
         patch("app.services.dashboard_tools._get_fbp_health") as mock_fbp, \
         patch("app.services.dashboard_tools.LMStudioClient") as mock_lm_client:

        # Setup mocks
        mock_commits.return_value = [
            {"hash": "abc123", "author": "John", "message": "Fix bug", "email": "john@example.com", "date": "2024-01-15"}
        ]
        mock_branches.return_value = [
            {"name": "feature/test", "last_commit": {"hash": "xyz", "author": "Jane", "date": "2024-01-15", "message": "WIP"}}
        ]
        mock_changes.return_value = {"backend/app": ["file1.py"]}
        mock_foks.return_value = {"status": "ok", "data": {"status": "ok"}}
        mock_lmstudio.return_value = {"status": "ok", "models_count": 2}
        mock_obsidian.return_value = []
        mock_fbp.return_value = None

        # Mock LM Studio client
        mock_client_instance = AsyncMock()
        mock_client_instance.chat = AsyncMock(
            return_value={"response": "# Daily Engineering Briefing\n\nTest briefing content."}
        )
        mock_lm_client.return_value = mock_client_instance

        # Mock PROJECT_ROOT
        with patch("app.services.dashboard_tools.PROJECT_ROOT", mock_repo_path):
            result = await dashboard_tools.build_daily_engineering_briefing(
                repo_path=str(mock_repo_path),
                include_fbp_health=False,
            )

        assert "markdown" in result
        assert "Daily Engineering Briefing" in result["markdown"]


@pytest.mark.asyncio
async def test_build_daily_engineering_briefing_lmstudio_fallback(mock_repo_path: Path):
    """Test building briefing with LM Studio failure (fallback)."""
    with patch("app.services.dashboard_tools._get_recent_commits") as mock_commits, \
         patch("app.services.dashboard_tools._get_open_pr_branches") as mock_branches, \
         patch("app.services.dashboard_tools._get_directory_changes") as mock_changes, \
         patch("app.services.dashboard_tools._get_foks_health") as mock_foks, \
         patch("app.services.dashboard_tools._get_lmstudio_health") as mock_lmstudio, \
         patch("app.services.dashboard_tools._get_obsidian_notes") as mock_obsidian, \
         patch("app.services.dashboard_tools.LMStudioClient") as mock_lm_client:

        # Setup mocks
        mock_commits.return_value = []
        mock_branches.return_value = []
        mock_changes.return_value = {}
        mock_foks.return_value = {"status": "ok", "data": {}}
        mock_lmstudio.return_value = {"status": "ok", "models_count": 1}
        mock_obsidian.return_value = []

        # Mock LM Studio client to fail
        mock_client_instance = AsyncMock()
        mock_client_instance.chat = AsyncMock(side_effect=Exception("LM Studio unavailable"))
        mock_lm_client.return_value = mock_client_instance

        with patch("app.services.dashboard_tools.PROJECT_ROOT", mock_repo_path):
            result = await dashboard_tools.build_daily_engineering_briefing(
                repo_path=str(mock_repo_path),
                include_fbp_health=False,
            )

        # Should return fallback markdown
        assert "markdown" in result
        assert "Daily Engineering Briefing" in result["markdown"]


@pytest.mark.asyncio
async def test_build_daily_engineering_briefing_with_fbp(mock_repo_path: Path):
    """Test building briefing with FBP health included."""
    with patch("app.services.dashboard_tools._get_recent_commits") as mock_commits, \
         patch("app.services.dashboard_tools._get_open_pr_branches") as mock_branches, \
         patch("app.services.dashboard_tools._get_directory_changes") as mock_changes, \
         patch("app.services.dashboard_tools._get_foks_health") as mock_foks, \
         patch("app.services.dashboard_tools._get_lmstudio_health") as mock_lmstudio, \
         patch("app.services.dashboard_tools._get_obsidian_notes") as mock_obsidian, \
         patch("app.services.dashboard_tools._get_fbp_health") as mock_fbp, \
         patch("app.services.dashboard_tools.LMStudioClient") as mock_lm_client:

        # Setup mocks
        mock_commits.return_value = []
        mock_branches.return_value = []
        mock_changes.return_value = {}
        mock_foks.return_value = {"status": "ok", "data": {}}
        mock_lmstudio.return_value = {"status": "ok", "models_count": 1}
        mock_obsidian.return_value = []
        mock_fbp.return_value = {"status": "ok", "data": {"status": "ok"}}

        # Mock LM Studio client
        mock_client_instance = AsyncMock()
        mock_client_instance.chat = AsyncMock(
            return_value={"response": "# Briefing\n\nContent"}
        )
        mock_lm_client.return_value = mock_client_instance

        with patch("app.services.dashboard_tools.PROJECT_ROOT", mock_repo_path):
            result = await dashboard_tools.build_daily_engineering_briefing(
                repo_path=str(mock_repo_path),
                include_fbp_health=True,
            )

        assert "markdown" in result
        # Verify FBP health was checked
        mock_fbp.assert_awaited_once()
