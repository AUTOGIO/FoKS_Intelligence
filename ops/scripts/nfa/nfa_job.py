#!/usr/bin/env python3
"""
NFA Job CLI - Robust Playwright automation for SEFAZ-PB ATF Portal.

This script implements the complete NFA automation flow as specified in:
docs/NFA_Automation_Spec.md

Features:
- Login to ATF portal
- Navigate to FIS_308
- Fill consultation form
- Select NFA result
- Download DANFE and DAR PDFs
- Retry logic for transient failures
- JSONL logging
- Structured JSON output

Usage:
    python3 nfa_job.py --data-inicial 08/12/2025 --data-final 10/12/2025 --matricula 1595504
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page

# Add project root to path for logging utils
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

try:
    from app.services.logging_utils import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        return logger

logger = get_logger(__name__)

# Constants
OUTPUT_DIR = Path("/Users/dnigga/Downloads/NFA_Outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = OUTPUT_DIR / "nfa_runs.jsonl"

# ATF Portal URL
ATF_BASE_URL = "https://www4.sefaz.pb.gov.br/atf/"

# Retry configuration
MAX_RETRIES = 2
RETRY_DELAYS = [1.0, 2.0]  # seconds


async def _retry_operation(
    operation, *args, max_retries: int = MAX_RETRIES, delays: list[float] = RETRY_DELAYS, **kwargs
):
    """
    Retry an async operation with exponential backoff.

    Args:
        operation: Async function to retry
        *args: Positional arguments for operation
        max_retries: Maximum number of retries
        delays: List of delay seconds between retries
        **kwargs: Keyword arguments for operation

    Returns:
        Result of operation

    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = delays[min(attempt, len(delays) - 1)]
                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay}s",
                    extra={"payload": {"error": str(e), "attempt": attempt + 1}},
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Operation failed after all retries",
                    exc_info=True,
                    extra={"payload": {"error": str(e), "attempts": attempt + 1}},
                )
    raise last_exception


async def _login(page: Page, username: str, password: str) -> None:
    """
    Login to ATF portal.

    Maps to: NFA_Automation_Spec.md - Authentication section
    """
    logger.info("Navigating to ATF login page", extra={"payload": {"url": ATF_BASE_URL}})
    await page.goto(ATF_BASE_URL, wait_until="networkidle", timeout=30000)

    logger.info("Waiting for login form")
    # Try multiple selectors for username field
    username_selectors = [
        'input[name="edtNoLogin"]',
        'input[name="username"]',
        'input[type="text"][name*="login"]',
        'input[type="text"][name*="user"]',
        'input[id*="login"]',
        'input[id*="user"]',
    ]

    username_field = None
    for selector in username_selectors:
        try:
            await page.wait_for_selector(selector, timeout=5000)
            username_field = selector
            logger.info(f"Found username field: {selector}")
            break
        except Exception:
            continue

    if not username_field:
        # Take screenshot for debugging
        screenshot_path = OUTPUT_DIR / f"login_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await page.screenshot(path=str(screenshot_path))
        logger.error(f"Login form not found. Screenshot saved: {screenshot_path}")
        raise RuntimeError("Could not find login form. Check screenshot for details.")

    # Find password field
    password_selectors = [
        'input[name="edtDsSenha"]',
        'input[name="password"]',
        'input[type="password"]',
    ]

    password_field = None
    for selector in password_selectors:
        try:
            if await page.locator(selector).count() > 0:
                password_field = selector
                logger.info(f"Found password field: {selector}")
                break
        except Exception:
            continue

    if not password_field:
        raise RuntimeError("Could not find password field")

    logger.info("Filling login credentials")
    await page.fill(username_field, username)
    await page.fill(password_field, password)

    # Find submit button
    submit_selectors = [
        'button[name="btnAvancar"]',
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Entrar")',
        'button:has-text("Login")',
        'button:has-text("Avançar")',
    ]

    submit_button = None
    for selector in submit_selectors:
        try:
            if await page.locator(selector).count() > 0:
                submit_button = selector
                logger.info(f"Found submit button: {selector}")
                break
        except Exception:
            continue

    if not submit_button:
        raise RuntimeError("Could not find submit button")

    logger.info("Submitting login form")
    async with page.expect_navigation(timeout=30000):
        await page.click(submit_button)

    logger.info("Login completed")


async def _get_main_frame(page: Page) -> Page:
    """
    Get main content frame (may be in iframe).

    Maps to: NFA_Automation_Spec.md - Iframe Handling section
    """
    # Wait a bit for frames to load
    await page.wait_for_timeout(1000)

    # Check all frames for FIS_308 content
    for frame in page.frames:
        frame_url = frame.url or ""
        if "FIS_" in frame_url or "FISf_ConsultarNotasFiscaisAvulsas" in frame_url:
            logger.info("Found main frame with FIS_308 content", extra={"payload": {"url": frame_url}})
            return frame

    # Fallback to main page
    logger.info("Using main page (no iframe found)")
    return page


async def _navigate_to_fis308(page: Page) -> None:
    """
    Navigate to FIS_308 function.

    Maps to: NFA_Automation_Spec.md - Navigation to FIS_308 section
    """
    logger.info("Navigating to FIS_308")
    await page.wait_for_selector('input[name="edtFuncao"]', timeout=10000)
    await page.fill('input[name="edtFuncao"]', "fis_308")
    await page.keyboard.press("Enter")
    await page.wait_for_load_state("networkidle", timeout=15000)
    logger.info("FIS_308 navigation completed")


async def _fill_consulta_form(
    frame: Page, data_inicial: str, data_final: str, matricula: str
) -> None:
    """
    Fill consultation form with date range and matrícula.

    Maps to: NFA_Automation_Spec.md - Consultation Form section
    """
    logger.info(
        "Filling consultation form",
        extra={"payload": {"data_inicial": data_inicial, "data_final": data_final, "matricula": matricula}},
    )

    # Wait for form to be ready
    await frame.wait_for_selector('input[name="edtDtEmissaoNfaeInicial"]', timeout=10000)

    # Fill dates
    await frame.fill('input[name="edtDtEmissaoNfaeInicial"]', data_inicial)
    await frame.fill('input[name="edtDtEmissaoNfaeFinal"]', data_final)

    # Fill matrícula - try hidden field first
    try:
        await frame.fill('input[name="hidnrMatriculacmpFuncEmitente"]', matricula)
        logger.info("Matrícula set via hidden field")
    except Exception:
        # Fallback: try component iframe
        logger.info("Trying component iframe for matrícula")
        try:
            # Look for component iframe
            component_frames = [f for f in frame.child_frames if "cmpFuncEmitente" in (f.url or "")]
            if component_frames:
                cmp_frame = component_frames[0]
                await cmp_frame.fill("input[type='text']", matricula)
                try:
                    await cmp_frame.click("input[type='submit'][value='Pesquisar']")
                except Exception:
                    pass  # Submit may not be needed
                logger.info("Matrícula set via component iframe")
        except Exception as e:
            logger.warning("Could not set matrícula via component iframe", extra={"payload": {"error": str(e)}})

    # Submit consultation
    logger.info("Submitting consultation form")
    async with frame.expect_navigation(wait_until="load"):
        await frame.click('input[name="btnConsultar"]')

    logger.info("Consultation form submitted")


async def _select_first_nfa(frame: Page) -> str | None:
    """
    Select first NFA result and extract NFA number.

    Maps to: NFA_Automation_Spec.md - Results Selection section

    Returns:
        NFA number as string, or None if not found
    """
    logger.info("Selecting first NFA result")

    # Wait for radio buttons
    count = await frame.locator("input[type='radio']").count()
    if count == 0:
        logger.error("No NFA results found")
        return None

    # Select first radio
    first_radio = frame.locator("input[type='radio']").first
    await first_radio.click()
    logger.info("First NFA radio selected")

    # Try to extract NFA number from the row
    numero = None
    try:
        row = await first_radio.evaluate_handle("el => el.closest('tr')")
        if row:
            textos = await row.evaluate(
                "el => Array.from(el.querySelectorAll('td')).map(td => td.innerText.trim())"
            )
            # Heuristic: find text that looks like a number (>= 6 digits)
            for t in textos:
                if t.isdigit() and len(t) >= 6:
                    numero = t
                    break
    except Exception as e:
        logger.warning("Could not extract NFA number from row", extra={"payload": {"error": str(e)}})

    if numero:
        logger.info("NFA number extracted", extra={"payload": {"nfa_numero": numero}})
    else:
        logger.warning("NFA number not found, will use UNKNOWN in filename")

    return numero


async def _download_action(
    frame: Page, button_selector: str, filename: str, context: BrowserContext
) -> Path:
    """
    Click download button and save PDF.

    Maps to: NFA_Automation_Spec.md - PDF Downloads section

    Args:
        frame: Page or Frame to interact with
        button_selector: CSS selector for download button
        filename: Output filename
        context: Browser context (for download events)

    Returns:
        Path to saved PDF file
    """
    logger.info("Setting up download handler", extra={"payload": {"button": button_selector, "filename": filename}})

    download = None
    try:
        async with context.expect_event("download", timeout=30000) as dl_info:
            await frame.click(button_selector)
        download = await dl_info.value
    except Exception as e:
        logger.error("Download failed", exc_info=True, extra={"payload": {"error": str(e)}})
        # Fallback: if download opens in new page instead, handle here if needed
        raise

    out_path = OUTPUT_DIR / filename
    await download.save_as(str(out_path))
    logger.info("PDF downloaded", extra={"payload": {"path": str(out_path)}})

    return out_path


async def run_nfa_job(
    username: str | None = None,
    password: str | None = None,
    data_inicial: str = "08/12/2025",
    data_final: str = "10/12/2025",
    matricula: str = "1595504",
    headless: bool = True,
) -> dict:
    """
    Execute complete NFA automation job.

    Maps to: NFA_Automation_Spec.md - Complete Flow

    Args:
        username: ATF username (defaults to NFA_USERNAME env var)
        password: ATF password (defaults to NFA_PASSWORD env var)
        data_inicial: Start date in dd/mm/yyyy format
        data_final: End date in dd/mm/yyyy format
        matricula: Matrícula number
        headless: Run browser in headless mode

    Returns:
        Dictionary with status, nfa_numero, danfe_path, dar_path, timestamps, error
    """
    username = username or os.getenv("NFA_USERNAME")
    password = password or os.getenv("NFA_PASSWORD")

    if not username or not password:
        raise RuntimeError("NFA_USERNAME / NFA_PASSWORD must be set or passed explicitly")

    result: dict = {
        "status": "error",
        "nfa_numero": None,
        "danfe_path": None,
        "dar_path": None,
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "error": None,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            # Step 1: Login (with retry)
            await _retry_operation(_login, page, username, password)

            # Step 2: Navigate to FIS_308 (with retry)
            await _retry_operation(_navigate_to_fis308, page)

            # Step 3: Get main frame (may be iframe)
            frame = await _get_main_frame(page)

            # Step 4: Fill consultation form (with retry)
            await _retry_operation(_fill_consulta_form, frame, data_inicial, data_final, matricula)

            # Step 5: Select first NFA (with retry)
            nfa_numero = await _retry_operation(_select_first_nfa, frame)
            if not nfa_numero:
                raise RuntimeError("Nenhuma NFA encontrada para o filtro informado")

            result["nfa_numero"] = nfa_numero or "UNKNOWN"

            # Step 6: Download DANFE
            danfe_name = f"NFA_{nfa_numero or 'UNKNOWN'}_DANFE.pdf"
            danfe_path = await _download_action(
                frame,
                "input[type='button'][value='Imprimir']",
                danfe_name,
                context,
            )

            # Step 7: Download DAR
            dar_name = f"NFA_{nfa_numero or 'UNKNOWN'}_DAR.pdf"
            # Try primary selector first, then fallback
            try:
                dar_path = await _download_action(
                    frame,
                    "input[type='button'][value*='Emitir DAR']",
                    dar_name,
                    context,
                )
            except Exception:
                # Fallback to alternative selector
                logger.info("Trying alternative DAR button selector")
                dar_path = await _download_action(
                    frame,
                    "input[type='button'][value*='Taxa Serviço']",
                    dar_name,
                    context,
                )

            result["status"] = "ok"
            result["danfe_path"] = str(danfe_path)
            result["dar_path"] = str(dar_path)

        except Exception as e:
            result["error"] = str(e)
            logger.error("NFA job failed", exc_info=True, extra={"payload": {"error": str(e)}})
        finally:
            result["finished_at"] = datetime.utcnow().isoformat()
            await context.close()
            await browser.close()

    # Log to JSONL
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Logging failure should not break the job

    return result


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NFA Job CLI - Download NFA PDFs from SEFAZ-PB ATF Portal"
    )
    parser.add_argument(
        "--data-inicial",
        required=True,
        help="Data inicial no formato dd/mm/yyyy (ex: 08/12/2025)",
    )
    parser.add_argument(
        "--data-final",
        required=True,
        help="Data final no formato dd/mm/yyyy (ex: 10/12/2025)",
    )
    parser.add_argument(
        "--matricula",
        default="1595504",
        help="Matrícula do funcionário (padrão: 1595504)",
    )
    parser.add_argument(
        "--username",
        help="Username ATF (padrão: variável NFA_USERNAME)",
    )
    parser.add_argument(
        "--password",
        help="Password ATF (padrão: variável NFA_PASSWORD)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Executar browser em modo headless (padrão: True)",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Executar browser com interface visível",
    )

    args = parser.parse_args()

    try:
        result = asyncio.run(
            run_nfa_job(
                username=args.username,
                password=args.password,
                data_inicial=args.data_inicial,
                data_final=args.data_final,
                matricula=args.matricula,
                headless=args.headless,
            )
        )

        # Print JSON result
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Return exit code
        return 0 if result["status"] == "ok" else 1

    except Exception as e:
        error_result = {
            "status": "error",
            "nfa_numero": None,
            "danfe_path": None,
            "dar_path": None,
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
