"""FBP bootstrap readiness checks (filesystem-only, no FBP imports)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.logging_utils import get_logger

logger = get_logger(__name__)

# Standard FBP paths
DEFAULT_FBP_ROOT = os.path.expanduser("~/Documents/FBP_Backend")
FBP_ROOT_ENV = os.getenv("FBP_ROOT", DEFAULT_FBP_ROOT)


def check_fbp_venv() -> dict[str, Any]:
    """
    Check if FBP virtual environment exists.

    Checks multiple possible venv locations:
    - Centralized: ~/Documents/.venvs/fbp
    - Project: FBP_ROOT/venv
    - Project: FBP_ROOT/.venv

    Returns:
        Dictionary with:
        - exists: bool
        - path: str (path to venv if found, empty string otherwise)
        - type: str ("centralized", "project", or "none")
    """
    fbp_root = Path(FBP_ROOT_ENV)
    checks = {
        "exists": False,
        "path": "",
        "type": "none",
    }

    # Check centralized venv
    centralized_venv = Path.home() / "Documents" / ".venvs" / "fbp"
    if centralized_venv.exists() and centralized_venv.is_dir():
        # Verify it's a valid venv (has bin/activate or Scripts/activate)
        if (centralized_venv / "bin" / "activate").exists() or (
            centralized_venv / "Scripts" / "activate"
        ).exists():
            checks["exists"] = True
            checks["path"] = str(centralized_venv)
            checks["type"] = "centralized"
            logger.debug(
                "FBP centralized venv found",
                extra={"payload": {"path": str(centralized_venv)}},
            )
            return checks

    # Check project venv (venv/)
    project_venv = fbp_root / "venv"
    if project_venv.exists() and project_venv.is_dir():
        if (project_venv / "bin" / "activate").exists() or (
            project_venv / "Scripts" / "activate"
        ).exists():
            checks["exists"] = True
            checks["path"] = str(project_venv)
            checks["type"] = "project"
            logger.debug(
                "FBP project venv found (venv/)",
                extra={"payload": {"path": str(project_venv)}},
            )
            return checks

    # Check project venv (.venv/)
    project_venv_alt = fbp_root / ".venv"
    if project_venv_alt.exists() and project_venv_alt.is_dir():
        if (project_venv_alt / "bin" / "activate").exists() or (
            project_venv_alt / "Scripts" / "activate"
        ).exists():
            checks["exists"] = True
            checks["path"] = str(project_venv_alt)
            checks["type"] = "project"
            logger.debug(
                "FBP project venv found (.venv/)",
                extra={"payload": {"path": str(project_venv_alt)}},
            )
            return checks

    logger.debug("FBP venv not found", extra={"payload": {"fbp_root": str(fbp_root)}})
    return checks


def check_fbp_backend_folder() -> dict[str, Any]:
    """
    Check if FBP backend folder exists and has expected structure.

    Expected structure:
    - FBP_ROOT/app/ (main application)
    - FBP_ROOT/pyproject.toml or requirements.txt (dependency files)

    Returns:
        Dictionary with:
        - exists: bool
        - path: str
        - has_app: bool (app/ directory exists)
        - has_deps_file: bool (pyproject.toml or requirements.txt exists)
    """
    fbp_root = Path(FBP_ROOT_ENV)
    checks = {
        "exists": False,
        "path": str(fbp_root),
        "has_app": False,
        "has_deps_file": False,
    }

    if fbp_root.exists() and fbp_root.is_dir():
        checks["exists"] = True

        # Check for app/ directory
        app_dir = fbp_root / "app"
        if app_dir.exists() and app_dir.is_dir():
            checks["has_app"] = True

        # Check for dependency files
        pyproject = fbp_root / "pyproject.toml"
        requirements = fbp_root / "requirements.txt"
        if pyproject.exists() or requirements.exists():
            checks["has_deps_file"] = True

        logger.debug(
            "FBP backend folder check",
            extra={"payload": checks},
        )
    else:
        logger.debug(
            "FBP backend folder not found",
            extra={"payload": {"path": str(fbp_root)}},
        )

    return checks


def check_fbp_start_script() -> dict[str, Any]:
    """
    Check if FBP start script exists.

    Checks common locations:
    - ops/scripts/start_fbp_m3.sh
    - ops/scripts/fbp_boot.sh
    - ops/scripts/fbp_boot_optimized.sh

    Returns:
        Dictionary with:
        - exists: bool
        - path: str (path to script if found)
        - name: str (script name if found)
    """
    checks = {
        "exists": False,
        "path": "",
        "name": "",
    }

    # Check in FoKS ops/scripts directory
    foks_root = Path(__file__).resolve().parent.parent.parent.parent
    ops_scripts = foks_root / "ops" / "scripts"

    script_names = [
        "start_fbp_m3.sh",
        "fbp_boot.sh",
        "fbp_boot_optimized.sh",
    ]

    for script_name in script_names:
        script_path = ops_scripts / script_name
        if script_path.exists() and script_path.is_file():
            # Check if executable
            is_executable = os.access(script_path, os.X_OK)
            checks["exists"] = True
            checks["path"] = str(script_path)
            checks["name"] = script_name
            checks["executable"] = is_executable
            logger.debug(
                "FBP start script found",
                extra={"payload": checks},
            )
            return checks

    logger.debug("FBP start script not found")
    return checks


def check_requirements_installed() -> dict[str, Any]:
    """
    Check if FBP requirements appear to be installed.

    Checks:
    - If venv exists, check for common FBP packages in site-packages
    - Checks for requirements.txt or pyproject.toml in FBP_ROOT
    - Does NOT import FBP code (filesystem-only check)

    Returns:
        Dictionary with:
        - has_requirements_file: bool
        - has_pyproject: bool
        - venv_has_packages: bool (if venv found, checks for key packages)
        - key_packages: list of found package names
    """
    checks = {
        "has_requirements_file": False,
        "has_pyproject": False,
        "venv_has_packages": False,
        "key_packages": [],
    }

    fbp_root = Path(FBP_ROOT_ENV)

    # Check for dependency files
    requirements = fbp_root / "requirements.txt"
    pyproject = fbp_root / "pyproject.toml"

    if requirements.exists():
        checks["has_requirements_file"] = True

    if pyproject.exists():
        checks["has_pyproject"] = True

    # Check venv for key packages (if venv exists)
    venv_check = check_fbp_venv()
    if venv_check["exists"]:
        venv_path = Path(venv_check["path"])
        site_packages = venv_path / "lib" / "python3.11" / "site-packages"
        # Also check for other Python versions
        python_versions = ["python3.11", "python3.10", "python3.9", "python3.12"]

        key_packages = [
            "fastapi",
            "uvicorn",
            "playwright",
            "httpx",
            "pydantic",
        ]

        found_packages = []
        for python_version in python_versions:
            site_packages_alt = venv_path / "lib" / python_version / "site-packages"
            if site_packages_alt.exists():
                site_packages = site_packages_alt
                break

        if site_packages.exists():
            for package in key_packages:
                # Check for package directory or .dist-info
                package_dir = site_packages / package
                dist_info = site_packages / f"{package.replace('-', '_')}-*.dist-info"
                if package_dir.exists() or list(site_packages.glob(f"{package}*.dist-info")):
                    found_packages.append(package)

        if found_packages:
            checks["venv_has_packages"] = True
            checks["key_packages"] = found_packages

    logger.debug(
        "FBP requirements check",
        extra={"payload": checks},
    )

    return checks


def check_socket() -> dict[str, Any]:
    """
    Check if FBP socket exists.

    Uses configured socket path from settings.

    Returns:
        Dictionary with:
        - exists: bool
        - path: str
        - is_socket: bool (if exists, verify it's actually a socket)
    """
    socket_path = Path(settings.fbp_socket_path)
    checks = {
        "exists": False,
        "path": str(socket_path),
        "is_socket": False,
    }

    if socket_path.exists():
        checks["exists"] = True
        # Check if it's actually a socket file
        if socket_path.is_socket():
            checks["is_socket"] = True
        logger.debug(
            "FBP socket check",
            extra={"payload": checks},
        )
    else:
        logger.debug(
            "FBP socket not found",
            extra={"payload": {"path": str(socket_path)}},
        )

    return checks


def get_fbp_bootstrap_status() -> dict[str, Any]:
    """
    Get comprehensive FBP bootstrap readiness status.

    Runs all checks and returns structured JSON.

    Returns:
        Dictionary with all check results:
        - venv: result from check_fbp_venv()
        - backend_folder: result from check_fbp_backend_folder()
        - start_script: result from check_fbp_start_script()
        - requirements: result from check_requirements_installed()
        - socket: result from check_socket()
        - overall_ready: bool (all critical checks pass)
    """
    logger.info("FBP bootstrap status check requested")

    venv_status = check_fbp_venv()
    backend_status = check_fbp_backend_folder()
    script_status = check_fbp_start_script()
    requirements_status = check_requirements_installed()
    socket_status = check_socket()

    # Determine overall readiness
    # Critical: backend folder exists, venv exists, socket exists
    overall_ready = (
        backend_status["exists"]
        and venv_status["exists"]
        and socket_status["exists"]
        and socket_status["is_socket"]
    )

    result = {
        "venv": venv_status,
        "backend_folder": backend_status,
        "start_script": script_status,
        "requirements": requirements_status,
        "socket": socket_status,
        "overall_ready": overall_ready,
    }

    logger.info(
        "FBP bootstrap status check completed",
        extra={"payload": {"overall_ready": overall_ready}},
    )

    return result
