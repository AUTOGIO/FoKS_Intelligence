#!/usr/bin/env python3
"""
NFA ATF Automation Script for FoKS Intelligence.

This script automates the process of:
1. Logging into ATF (https://www4.sefaz.pb.gov.br/atf/)
2. Navigating to FIS_308
3. Filling filters (date range, matricula)
4. Selecting NFA result
5. Generating and downloading DANFE and DAR PDFs

Returns structured JSON output for FoKS TaskRunner integration.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Add parent directory to path for logging utils
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

try:
    from app.services.logging_utils import get_logger
except ImportError:
    # Fallback if logging_utils not available
    import logging

    def get_logger(name: str):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        # Output to stderr only (not stdout)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
        return logger

logger = get_logger(__name__)

# Keychain integration (read-only). We avoid writing secrets into terminal history.
DEFAULT_KEYCHAIN_SERVICE = "FoKS_NFA_ATF"

# Load default config
CONFIG_PATH = SCRIPT_DIR / "config.json"
DEFAULT_CONFIG: Dict[str, Any] = {
    "default_matricula": "1595504",
    "default_output_dir": "/Users/dnigga/Downloads/NFA_Outputs",
    "atf_base_url": "https://www4.sefaz.pb.gov.br/atf/",
    "timeout_seconds": 600,
    "wait_timeout_ms": 30000,
}

# Ensure output directory is always the required path
OUTPUT_DIR = "/Users/dnigga/Downloads/NFA_Outputs"

if CONFIG_PATH.exists():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            DEFAULT_CONFIG.update(json.load(f))
    except Exception as e:
        logger.warning(f"Failed to load config.json: {e}. Using defaults.")


class NFAATFAutomation:
    """Playwright automation for NFA ATF operations."""

    def __init__(
        self,
        username: str,
        password: str,
        from_date: str,
        to_date: str,
        matricula: str,
        output_dir: str,
        headless: bool = True,
    ):
        """
        Initialize NFA ATF automation.

        Args:
            username: ATF username (from NFA_USERNAME env var)
            password: ATF password (from NFA_PASSWORD env var)
            from_date: Start date in dd/mm/yyyy format
            to_date: End date in dd/mm/yyyy format
            matricula: Matricula number
            output_dir: Directory to save PDFs
            headless: Run browser in headless mode
        """
        self.username = username
        self.password = password
        self.from_date = from_date
        self.to_date = to_date
        self.matricula = matricula
        self.output_dir = Path(output_dir)
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.main_page: Optional[Page] = None  # Store main page reference for iframe navigation
        self.nfa_number: Optional[str] = None
        self.danfe_path: Optional[str] = None
        self.dar_path: Optional[str] = None
        self.current_nfa_dir: Optional[Path] = None
        self._cdp_sessions: Dict[int, Any] = {}
        self._user_data_dir: Optional[Path] = None

    async def _capture_next_pdf_bytes(
        self,
        *,
        trigger: Callable[[], Awaitable[None]],
        timeout_ms: int = 30000,
    ) -> bytes:
        """
        Capture the next PDF response bytes after a trigger action.

        This avoids relying on Chromium's PDF viewer download button (which can open
        a macOS Save dialog and won't emit Playwright download events).
        """
        if not self.context:
            raise RuntimeError("Browser context not initialized.")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[bytes] = loop.create_future()
        captured_meta: Dict[str, Any] = {"url": None, "content_type": None}

        def _on_response(response) -> None:  # type: ignore[no-untyped-def]
            # We must not block the response handler; read body async.
            async def _probe() -> None:
                if future.done():
                    return
                try:
                    body = await response.body()
                    if body.startswith(b"%PDF") and not future.done():
                        captured_meta["url"] = getattr(response, "url", None)
                        captured_meta["content_type"] = response.headers.get("content-type")
                        future.set_result(body)
                except Exception:
                    return

            try:
                asyncio.create_task(_probe())
            except Exception:
                return

        self.context.on("response", _on_response)
        try:
            await trigger()
            pdf_bytes = await asyncio.wait_for(future, timeout=timeout_ms / 1000)
            logger.info(
                "Captured PDF bytes from network",
                extra={"payload": {"url": captured_meta["url"], "content_type": captured_meta["content_type"], "bytes": len(pdf_bytes)}},
            )
            return pdf_bytes
        finally:
            try:
                self.context.off("response", _on_response)  # type: ignore[attr-defined]
            except Exception:
                pass

    async def _set_download_dir(self, page: Page, download_dir: Path) -> None:
        """
        Force Chromium downloads into `download_dir` and disable any OS save prompt.

        Uses Chrome DevTools Protocol via Playwright. This is the most reliable way
        to avoid the macOS Save dialog from the built-in PDF viewer.
        """
        download_dir.mkdir(parents=True, exist_ok=True)

        key = id(page)
        session = self._cdp_sessions.get(key)
        if session is None:
            session = await self.context.new_cdp_session(page)  # type: ignore[union-attr]
            self._cdp_sessions[key] = session

        payload = {"behavior": "allow", "downloadPath": str(download_dir)}
        # Try Browser.* first (newer), fallback to Page.* (older).
        try:
            await session.send("Browser.setDownloadBehavior", payload)
        except Exception:
            await session.send("Page.setDownloadBehavior", payload)

    @staticmethod
    def _save_dialog_to_path(target_path: Path, *, timeout_s: int = 30) -> None:
        """
        Use macOS UI automation (System Events) to save the currently-open Save dialog
        to the requested folder+filename.

        Requires Accessibility permission for the host app (Cursor/Terminal) and System Events.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        folder = str(target_path.parent)
        filename = target_path.name

        applescript = f"""
tell application "System Events"
  set frontApp to name of first application process whose frontmost is true
  tell process frontApp
    -- Focus is typically on the Save As field already, but we re-type the name.
    delay 0.2
    keystroke "g" using {{command down, shift down}}
    delay 0.2
    keystroke "{folder}"
    key code 36
    delay 0.2
    -- Ensure name field is active; type filename and confirm Save
    keystroke "{filename}"
    key code 36
  end tell
end tell
"""

        start = time.time()
        while True:
            try:
                subprocess.run(
                    ["osascript", "-e", applescript],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except Exception:
                if time.time() - start > timeout_s:
                    raise RuntimeError(
                        "Failed to control macOS Save dialog. "
                        "Grant Accessibility permissions to your terminal/app and retry."
                    )
                time.sleep(0.5)

    @staticmethod
    def _wait_for_file(path: Path, *, timeout_s: int = 60, min_bytes: int = 1024) -> None:
        """Wait until a file exists and has at least min_bytes."""
        start = time.time()
        while True:
            try:
                if path.exists() and path.stat().st_size >= min_bytes:
                    return
            except Exception:
                pass
            if time.time() - start > timeout_s:
                raise TimeoutError(f"Timed out waiting for file to be saved: {path}")
            time.sleep(0.25)

    @staticmethod
    def _unique_path(target: Path) -> Path:
        """Return a non-colliding path by suffixing _2, _3... if needed."""
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        for i in range(2, 10_000):
            candidate = parent / f"{stem}_{i}{suffix}"
            if not candidate.exists():
                return candidate
        raise RuntimeError(f"Could not create unique filename for {target}")

    async def setup(self) -> None:
        """Initialize Playwright browser and context."""
        playwright = await async_playwright().start()
        # Use a TEMPORARY Chromium profile so we don't touch user settings.
        # Key pref: always download PDFs (avoid Chrome PDF viewer + macOS Save dialog).
        profile_root = Path("/tmp") / f"foks_atf_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        default_dir = profile_root / "Default"
        default_dir.mkdir(parents=True, exist_ok=True)
        preferences_path = default_dir / "Preferences"

        preferences = {
            "download": {
                "prompt_for_download": False,
                "directory_upgrade": True,
            },
            "plugins": {
                # Critical: force PDFs to download instead of opening in the viewer.
                "always_open_pdf_externally": True,
            },
        }
        preferences_path.write_text(json.dumps(preferences), encoding="utf-8")
        self._user_data_dir = profile_root

        # Persistent context lets us control download behavior reliably.
        self.browser = None
        self.context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_root),
            headless=self.headless,
            accept_downloads=True,
            viewport={"width": 1920, "height": 1080},
            downloads_path=str(self.output_dir),
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Persistent contexts usually start with one blank page.
        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()
        self.main_page = self.page

        # Set longer timeout for slow ATF pages
        self.page.set_default_timeout(DEFAULT_CONFIG.get("wait_timeout_ms", 30000))

        logger.info("Browser initialized", extra={"payload": {"headless": self.headless}})

    async def login(self) -> None:
        """Log into ATF system."""
        if not self.page:
            raise RuntimeError("Page not initialized. Call setup() first.")

        url = DEFAULT_CONFIG.get("atf_base_url", "https://www4.sefaz.pb.gov.br/atf/")
        logger.info("Navigating to ATF login", extra={"payload": {"url": url}})

        # Navigate and wait for page to load
        response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        logger.info("Page navigation started", extra={"payload": {"status": response.status if response else None}})
        
        # Wait for page to be fully interactive
        await self.page.wait_for_load_state("networkidle", timeout=20000)
        # Additional wait for JavaScript to render the form (Bootstrap 5 forms need time)
        await self.page.wait_for_timeout(5000)

        # Debug: Log page title and URL to verify we're on the right page
        page_title = await self.page.title()
        page_url = self.page.url
        logger.info("Page loaded", extra={"payload": {"title": page_title, "url": page_url}})

        # Check if login form is in an iframe (ATF uses iframe for login)
        iframe_selector = 'iframe[name="contents"], iframe#contents, iframe[src*="Login"]'
        frame = None
        
        try:
            # Wait for iframe to load
            iframe_element = await self.page.wait_for_selector(iframe_selector, timeout=10000)
            if iframe_element:
                frame = await iframe_element.content_frame()
                if frame:
                    logger.info("Login form is in iframe, switched to iframe context")
        except Exception:
            logger.info("No iframe found, checking main page for login form")
            frame = self.page  # Use main page if no iframe

        # Wait for login form to be present (try multiple selectors)
        form_selectors = [
            'form[name="FormLogin"]',
            'form#loginForm',
            'form',
            'input[name="edtNoLogin"]',  # If form not found, try input directly
            'input[id="login"]',
        ]
        
        form_found = False
        for form_selector in form_selectors:
            try:
                await frame.wait_for_selector(form_selector, timeout=5000)
                logger.info("Form/input element found", extra={"payload": {"selector": form_selector}})
                form_found = True
                break
            except Exception:
                continue
        
        if not form_found:
            # Try to get page content for debugging
            page_content = await self.page.content()
            logger.error(
                "Login form/input not found",
                extra={"payload": {"url": page_url, "title": page_title, "content_preview": page_content[:1000]}},
            )
            raise RuntimeError(f"Login form not found on page: {page_url}")
        
        # Use frame context for all subsequent operations
        self.page = frame

        # Wait for login form inputs (ATF specific selectors)
        # Based on actual ATF page: name="edtNoLogin" id="login" for username
        # name="edtDsSenha" id="senha" for password
        username_selectors = [
            'input[name="edtNoLogin"]',
            'input[id="login"]',
            'input[placeholder*="Usuário"], input[placeholder*="usuário"]',
            'input[type="text"]',
        ]
        password_selector = 'input[name="edtDsSenha"], input[id="senha"], input[type="password"]'

        username_selector = None
        try:
            # Try each selector in order
            for selector in username_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    username_selector = selector
                    logger.info("Username field found", extra={"payload": {"selector": selector}})
                    break
                except Exception:
                    continue
            
            if not username_selector:
                raise RuntimeError("Could not find username field with any selector")
            # Fill username and password (using frame context)
            await self.page.fill(username_selector, self.username)
            await self.page.fill(password_selector, self.password)
            logger.info("Credentials filled")

            # Find and click login button (ATF uses name="btnAvancar")
            login_button = self.page.locator('button[name="btnAvancar"], button[type="submit"]:has-text("Avançar"), button[type="submit"], input[type="submit"], button:has-text("Entrar"), button:has-text("Login")').first
            await login_button.click()
            logger.info("Login button clicked")

            # Wait for navigation after login
            await self.page.wait_for_load_state("networkidle", timeout=15000)

            # Verify login success (check for error messages or dashboard)
            error_selectors = [
                'text="Usuário ou senha inválidos"',
                'text="Login inválido"',
                'text="Erro"',
            ]
            for error_selector in error_selectors:
                if await self.page.locator(error_selector).count() > 0:
                    raise ValueError("Login failed: Invalid credentials")

            logger.info("Login successful")
            
            # After login, wait for navigation and check for new iframe or main page update
            await self.page.wait_for_timeout(3000)
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            
            # After login, the main page iframe might be updated with the menu
            # Check if main page has a new iframe with the menu
            try:
                # Wait for main page to update (login redirects main page)
                await self.main_page.wait_for_load_state("networkidle", timeout=10000)
                
                # Check for menu iframe in main page
                menu_iframe_selector = 'iframe[name="contents"], iframe#contents'
                menu_iframe = await self.main_page.wait_for_selector(menu_iframe_selector, timeout=5000)
                if menu_iframe:
                    menu_frame = await menu_iframe.content_frame()
                    if menu_frame:
                        logger.info("Menu iframe found after login, switching to menu frame")
                        self.page = menu_frame
                        await self.page.wait_for_load_state("networkidle", timeout=10000)
                    else:
                        # Use main page directly
                        self.page = self.main_page
                else:
                    # No iframe, use main page
                    self.page = self.main_page
                    logger.info("Switched to main page after login")
            except Exception as e:
                logger.warning("Could not switch to menu frame, staying in current context", extra={"payload": {"error": str(e)}})
                # Stay in current context
                pass
        except Exception as e:
            logger.error("Login failed", exc_info=True, extra={"payload": {"error": str(e)}})
            raise RuntimeError(f"Login failed: {str(e)}") from e

    async def navigate_to_fis_308(self) -> None:
        """Navigate to FIS_308 function using direct URL."""
        if not self.page:
            raise RuntimeError("Page not initialized.")

        logger.info("Navigating to FIS_308 via direct URL")

        # After login, ensure we're using the main page context
        # Wait for login navigation to complete and session to be established
        await self.main_page.wait_for_load_state("networkidle", timeout=15000)
        await self.page.wait_for_timeout(3000)  # Increased wait to ensure session is ready

        # Navigate directly to FIS_308 URL
        fis_308_url = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_ConsultarNotasFiscaisAvulsas.do?limparSessao=true"
        logger.info("Navigating to FIS_308 URL", extra={"payload": {"url": fis_308_url}})
        
        response = await self.main_page.goto(
            fis_308_url,
            wait_until="domcontentloaded",
            timeout=30000,
        )
        
        if response:
            logger.info("FIS_308 page navigation started", extra={"payload": {"status": response.status}})
        
        # Wait for page to load
        await self.main_page.wait_for_load_state("networkidle", timeout=20000)
        await self.main_page.wait_for_timeout(3000)
        
        # Check if we got redirected to an error page
        current_url = self.main_page.url
        if "SEGf_EmitirMensagemTelaCheia" in current_url or "codigo=27" in current_url:
            logger.warning("Redirected to error page, waiting longer and retrying navigation")
            await self.main_page.wait_for_timeout(5000)  # Wait longer for session
            # Try navigating again without limparSessao (might be causing the issue)
            fis_308_url_retry = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_ConsultarNotasFiscaisAvulsas.do"
            logger.info("Retrying FIS_308 navigation without limparSessao", extra={"payload": {"url": fis_308_url_retry}})
            response = await self.main_page.goto(
                fis_308_url_retry,
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await self.main_page.wait_for_load_state("networkidle", timeout=20000)
            await self.main_page.wait_for_timeout(3000)

        # Check if the form is in an iframe (principal iframe)
        try:
            principal_iframe = await self.main_page.wait_for_selector('iframe[name="principal"], iframe#principal', timeout=10000)
            if principal_iframe:
                principal_frame = await principal_iframe.content_frame()
                if principal_frame:
                    logger.info("Switched to principal iframe for FIS_308 form")
                    self.page = principal_frame
                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                    await self.page.wait_for_timeout(2000)
                else:
                    # Use main page if iframe content not available
                    self.page = self.main_page
            else:
                # No iframe, use main page directly
                self.page = self.main_page
                logger.info("Using main page directly (no principal iframe found)")
        except Exception as e:
            logger.warning(f"Could not switch to principal iframe: {e}, using main page")
            self.page = self.main_page

        # Verify we're on the correct page
        page_text = await self.page.text_content("body") or ""
        form_found = await self.page.locator('form[name="frmConsultar"]').count() > 0
        
        if not form_found and "Consultar Notas Fiscais Avulsas" not in page_text:
            logger.error(
                "FIS_308 page verification failed",
                extra={
                    "payload": {
                        "url": self.page.url,
                        "form_found": form_found,
                        "body_preview": page_text[:500],
                    }
                },
            )
            raise RuntimeError("Failed to load FIS_308 page: form or expected text not found")

        logger.info("FIS_308 page loaded and verified", extra={"payload": {"form_found": form_found, "url": self.page.url}})

    async def fill_filters(self) -> None:
        """Fill date range and matricula filters."""
        if not self.page:
            raise RuntimeError("Page not initialized.")

        logger.info(
            "Filling filters",
            extra={
                "payload": {
                    "from_date": self.from_date,
                    "to_date": self.to_date,
                    "matricula": self.matricula,
                }
            },
        )

        # We should already be in the principal iframe from navigate_to_fis_308
        # But ensure we're in the right context
        if "principal" not in str(self.page.url) and "FISf_ConsultarNotas" not in str(self.page.url):
            try:
                principal_iframe = await self.main_page.wait_for_selector('iframe[name="principal"], iframe#principal', timeout=5000)
                if principal_iframe:
                    principal_frame = await principal_iframe.content_frame()
                    if principal_frame:
                        logger.info("Switched to principal iframe for filter form")
                        self.page = principal_frame
            except Exception as e:
                logger.warning(f"Could not switch to principal iframe: {e}")

        # Wait for filter form to be ready (reduced wait)
        await self.page.wait_for_load_state("networkidle", timeout=8000)
        await self.page.wait_for_timeout(1000)  # Medium speed wait for form readiness

        # Fill from_date - based on image, selector is edtDtEmissaoNfaeInicial
        from_date_input = self.page.locator('input[name="edtDtEmissaoNfaeInicial"]').first
        if await from_date_input.count() > 0:
            await from_date_input.clear()
            await from_date_input.fill(self.from_date)
            logger.info("From date filled", extra={"payload": {"date": self.from_date}})
        else:
            logger.warning("Could not find from_date input (edtDtEmissaoNfaeInicial)")

        # Fill to_date - based on image, selector is edtDtEmissaoNfaeFinal
        to_date_input = self.page.locator('input[name="edtDtEmissaoNfaeFinal"]').first
        if await to_date_input.count() > 0:
            await to_date_input.clear()
            await to_date_input.fill(self.to_date)
            logger.info("To date filled", extra={"payload": {"date": self.to_date}})
        else:
            logger.warning("Could not find to_date input (edtDtEmissaoNfaeFinal)")

        # Fill matricula - try in iframe cmpFuncEmitente first (based on images)
        matricula_filled = False
        matricula_frame_context = None
        try:
            # Try in iframe cmpFuncEmitente (nested in principal iframe)
            matricula_iframe = await self.page.wait_for_selector('iframe[name="cmpFuncEmitente"]', timeout=5000)
            if matricula_iframe:
                matricula_frame = await matricula_iframe.content_frame()
                if matricula_frame:
                    matricula_frame_context = matricula_frame
                    # Look for the visible input field (not hidden)
                    matricula_input = matricula_frame.locator('input[type="text"][name*="matricula"]:not([type="hidden"])').first
                    if await matricula_input.count() == 0:
                        # Try any text input in the iframe
                        matricula_input = matricula_frame.locator('input[type="text"]').first
                    if await matricula_input.count() > 0:
                        await matricula_input.clear()
                        await matricula_input.fill(self.matricula)
                        matricula_filled = True
                        logger.info("Matricula filled in cmpFuncEmitente iframe")
        except Exception as e:
            logger.warning(f"Could not fill matricula in iframe: {e}")

        # Fallback: try in current page context
        if not matricula_filled:
            try:
                matricula_input = self.page.locator('input[name*="matricula"]:not([type="hidden"])').first
                if await matricula_input.count() > 0:
                    await matricula_input.clear()
                    await matricula_input.fill(self.matricula)
                    matricula_filled = True
                    matricula_frame_context = self.page
                    logger.info("Matricula filled in main context")
            except Exception:
                pass

        if not matricula_filled:
            logger.warning("Could not find matricula input")
        else:
            # After filling matricula, click "Pesquisar" button first
            if matricula_frame_context:
                try:
                    pesquisar_button = matricula_frame_context.locator('input[type="submit"][value="Pesquisar"], button:has-text("Pesquisar"), input[value*="Pesquisar"]').first
                    if await pesquisar_button.count() > 0:
                        await pesquisar_button.click()
                        logger.info("Pesquisar button clicked after matricula")
                        await self.page.wait_for_timeout(2000)  # Wait for search to complete
                        await self.page.wait_for_load_state("networkidle", timeout=10000)
                    else:
                        logger.warning("Could not find Pesquisar button")
                except Exception as e:
                    logger.warning(f"Could not click Pesquisar button: {e}")

        # Now click "Consultar" button to search for NFAs
        await self.page.wait_for_timeout(1000)  # Medium speed before Consultar
        consultar_button = self.page.locator('input[name="btnConsultar"]').first
        if await consultar_button.count() == 0:
            # Try alternative selectors
            consultar_button = self.page.locator('button:has-text("Consultar"), input[type="submit"][value="Consultar"]').first
        
        if await consultar_button.count() > 0:
            await consultar_button.click()
            logger.info("Consultar button clicked")
            await self.page.wait_for_load_state("networkidle", timeout=15000)  # Reduced timeout
            await self.page.wait_for_timeout(3000)  # Reduced from 5000ms
        else:
            logger.warning("Could not find Consultar button")

        logger.info("Filters filled and search executed")

    async def select_nfa_result(self, nfa_number: Optional[str] = None, index: int = 0) -> None:
        """
        Select NFA result from the list.

        Args:
            nfa_number: Optional specific NFA number to select. If None, selects by index.
            index: Index of NFA to select (0-based, default 0 for first)
        """
        if not self.page:
            raise RuntimeError("Page not initialized.")

        logger.info("Selecting NFA result", extra={"payload": {"nfa_number": nfa_number, "index": index}})

        # Ensure we're still in the principal iframe (results are in the same iframe)
        await self.page.wait_for_load_state("networkidle", timeout=10000)
        await self.page.wait_for_timeout(3000)

        # Based on images, radio buttons have name="rdNFAE" or "rdbNFAe"
        if nfa_number:
            # Try to find specific NFA by number in table
            nfa_row = self.page.locator(f'table tbody tr:has-text("{nfa_number}")').first
            if await nfa_row.count() > 0:
                radio = nfa_row.locator('input[type="radio"][name="rdNFAE"]').first
                if await radio.count() > 0:
                    await radio.click()
                    self.nfa_number = nfa_number
                    logger.info("Selected NFA by number", extra={"payload": {"nfa_number": nfa_number}})
                else:
                    logger.warning(f"NFA {nfa_number} found but radio button not found")
                    nfa_number = None
            else:
                logger.warning(f"NFA {nfa_number} not found in results")
                nfa_number = None

        if not nfa_number:
            # Prefer selecting by table row to avoid "always first row" extraction issues.
            rows = self.page.locator(
                'table tbody tr:has(input[type="radio"][name="rdNFAE"]), '
                'table tbody tr:has(input[type="radio"][name="rdbNFAe"])'
            )
            count = await rows.count()
            
            if count == 0:
                # Try waiting a bit more for table to load
                await self.page.wait_for_timeout(2000)
                count = await rows.count()
                
            if count == 0:
                # Debug: check if table exists
                table = self.page.locator('table').first
                if await table.count() > 0:
                    table_text = await table.text_content()
                    logger.error("No radio buttons found but table exists", extra={"payload": {"table_preview": (table_text or "")[:500]}})
                raise RuntimeError("Could not find any NFA results (no radio buttons found)")
            
            if index >= count:
                logger.warning(f"Index {index} out of range, selecting last available (index {count-1})")
                index = count - 1

            row = rows.nth(index)
            radio = row.locator(
                'input[type="radio"][name="rdNFAE"], input[type="radio"][name="rdbNFAe"]'
            ).first
            await radio.click()
            logger.info("Selected NFA row", extra={"payload": {"index": index}})

            # Extract NFA number from the selected row
            try:
                row_text = await row.text_content()
                if row_text:
                    # Extract NFA number (typically 9 digits)
                    import re
                    numbers = re.findall(r"\d{9,}", row_text)
                    if numbers:
                        # Use the first number that looks like an NFA number (9+ digits)
                        self.nfa_number = numbers[0]
                        logger.info("Extracted NFA number from row", extra={"payload": {"nfa_number": self.nfa_number}})
            except Exception as e:
                logger.warning(f"Could not extract NFA number from row: {e}")
                # Try to get it from the radio button value attribute
                try:
                    radio_value = await radio.get_attribute("value")
                    if radio_value:
                        self.nfa_number = radio_value
                        logger.info("Extracted NFA number from radio value", extra={"payload": {"nfa_number": self.nfa_number}})
                except Exception:
                    pass

        # Prepare per-NFA output directory to keep each "couple" grouped.
        nfa_key = self.nfa_number or f"IDX_{index + 1:03d}"
        self.current_nfa_dir = self.output_dir / f"NFA_{nfa_key}"
        self.current_nfa_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Prepared NFA output folder",
            extra={"payload": {"nfa_key": nfa_key, "dir": str(self.current_nfa_dir)}},
        )

        await self.page.wait_for_load_state("networkidle", timeout=5000)  # Reduced timeout
        await self.page.wait_for_timeout(225)  # Reduced by 25% from 300ms
        logger.info("NFA result selected", extra={"payload": {"nfa_number": self.nfa_number}})

    async def download_danfe(self) -> str:
        """
        Download DANFE by capturing the generated PDF response.

        Returns:
            Path to downloaded PDF file
        """
        if not self.page:
            raise RuntimeError("Page not initialized.")

        logger.info("Clicking Imprimir button for DANFE PDF")

        # Based on images, button is input[name="btnImprimirEletronica"]
        imprimir_button = self.page.locator('input[name="btnImprimirEletronica"]').first
        if await imprimir_button.count() == 0:
            # Try alternative selectors
            imprimir_button = self.page.locator('button:has-text("Imprimir"), input[value="Imprimir"]').first
            if await imprimir_button.count() == 0:
                raise RuntimeError("Could not find 'Imprimir' button")

        # Generate filename
        # Generate filename
        nfa_id = self.nfa_number or datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = self.current_nfa_dir or self.output_dir
        filename = f"NFA_{nfa_id}_DANFE.pdf"
        file_path = self._unique_path(target_dir / filename)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # With always_open_pdf_externally=True, clicking Imprimir should trigger a direct download.
        logger.info("Imprimir button clicked - waiting for download event (DANFE)")
        async with self.page.expect_download(timeout=60000) as download_info:
            await imprimir_button.click()
        download = await download_info.value
        await download.save_as(file_path)

        # Validate file looks like a PDF (avoid 345-byte HTML).
        self._wait_for_file(file_path, timeout_s=90, min_bytes=1024)
        if not file_path.read_bytes().startswith(b"%PDF"):
            raise RuntimeError(f"DANFE file saved but is not a PDF: {file_path}")

        # Ensure we are back on the main page
        self.page = self.main_page
        await self.page.wait_for_load_state("networkidle", timeout=5000)
        
        self.danfe_path = str(file_path)
        return self.danfe_path

    async def download_dar(self) -> str:
        """
        Download Taxa Serviço by capturing the generated PDF response.

        Returns:
            Path to downloaded PDF file
        """
        if not self.page:
            raise RuntimeError("Page not initialized.")

        logger.info("Clicking Gerar/Emitir Taxa Serviço button")

        # Based on image, button is input[name="btnGerarTaxaServicoEletronica"]
        emitir_taxa_button = self.page.locator('input[name="btnGerarTaxaServicoEletronica"]').first
        if await emitir_taxa_button.count() == 0:
            # Try alternative selectors
            emitir_taxa_button = self.page.locator('input[value*="Taxa Serviço"], input[value*="Emitir Taxa"], button:has-text("Taxa Serviço")').first
            if await emitir_taxa_button.count() == 0:
                raise RuntimeError("Could not find 'Gerar/Emitir Taxa Serviço' button")

        # Generate filename
        nfa_id = self.nfa_number or datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = self.current_nfa_dir or self.output_dir
        filename = f"NFA_{nfa_id}_TAXA_SERVICO.pdf"
        file_path = self._unique_path(target_dir / filename)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Taxa Serviço button clicked - waiting for download event")
        async with self.page.expect_download(timeout=60000) as download_info:
            await emitir_taxa_button.click()
        download = await download_info.value
        await download.save_as(file_path)

        self._wait_for_file(file_path, timeout_s=90, min_bytes=1024)
        if not file_path.read_bytes().startswith(b"%PDF"):
            raise RuntimeError(f"Taxa Serviço file saved but is not a PDF: {file_path}")

        # Switch back to main page
        self.page = self.main_page
        await self.page.wait_for_load_state("networkidle", timeout=5000)
        
        self.dar_path = str(file_path)
        return self.dar_path

    async def run(self, nfa_number: Optional[str] = None, max_nfas: int = 3, download_dar: bool = False) -> Dict[str, Any]:
        """
        Execute full automation workflow - processes first N NFAs (default: 3).

        Both DANFE (Imprimir) and Taxa Serviço downloads are executed in sequence for each NFA.
        The download_dar parameter is kept for backward compatibility but is now ignored.

        Args:
            nfa_number: Optional specific NFA number to select (if provided, only processes that one)
            max_nfas: Maximum number of NFAs to process (default: 3)
            download_dar: Deprecated - kept for backward compatibility. Both downloads always execute.

        Returns:
            Dictionary with status, nfa_number, danfe_path, and dar_path (for last processed NFA)
            or list of results if processing multiple
        """
        try:
            await self.setup()
            await self.login()
            await self.navigate_to_fis_308()
            await self.fill_filters()
            
            # After fill_filters (which clicked Consultar), wait for results to load (reduced waits)
            # The results appear in the principal iframe after the page reloads
            await self.main_page.wait_for_load_state("networkidle", timeout=15000)  # Reduced timeout
            await self.page.wait_for_timeout(3000)  # Reduced from 5000ms
            
            # Wait for principal iframe to reload with results
            principal_frame = None
            try:
                principal_iframe = await self.main_page.wait_for_selector('iframe[name="principal"], iframe#principal', timeout=15000)
                if principal_iframe:
                    principal_frame = await principal_iframe.content_frame()
                    if principal_frame:
                        # Wait for the iframe to load results (reduced waits)
                        await principal_frame.wait_for_load_state("networkidle", timeout=10000)  # Reduced timeout
                        await principal_frame.wait_for_timeout(2000)  # Reduced from 5000ms
                        logger.info("Principal iframe loaded, checking for results")
            except Exception as e:
                logger.warning(f"Could not wait for principal iframe: {e}")
            
            # Check all frames for radio buttons (results are in principal iframe)
            nfa_count = 0
            radio_buttons = None
            best_frame = self.page  # Default to current page
            
            # First, try principal iframe (most likely location)
            if principal_frame:
                try:
                    logger.info("Checking principal iframe for results")
                    test_radios = principal_frame.locator('input[type="radio"][name="rdbNFAe"], input[type="radio"][name="rdNFAE"]')
                    test_count = await test_radios.count()
                    if test_count > 0:
                        logger.info(f"Found {test_count} radio buttons in principal iframe")
                        self.page = principal_frame
                        radio_buttons = test_radios
                        nfa_count = test_count
                        best_frame = principal_frame
                except Exception as e:
                    logger.warning(f"Error checking principal iframe: {e}")
            
            # If not found, check main page
            if nfa_count == 0:
                logger.info("Checking main page for results")
                main_page_radios = self.main_page.locator('input[type="radio"][name="rdbNFAe"], input[type="radio"][name="rdNFAE"]')
                main_count = await main_page_radios.count()
                if main_count > 0:
                    logger.info(f"Found {main_count} radio buttons in main page")
                    self.page = self.main_page
                    radio_buttons = main_page_radios
                    nfa_count = main_count
                    best_frame = self.main_page
            
            # If still not found, check all frames recursively
            if nfa_count == 0:
                logger.info("Checking all frames for results")
                for frame in self.main_page.frames:
                    try:
                        frame_radios = frame.locator('input[type="radio"][name="rdbNFAe"], input[type="radio"][name="rdNFAE"]')
                        frame_count = await frame_radios.count()
                        if frame_count > 0:
                            logger.info(f"Found {frame_count} radio buttons in frame: {frame.url}")
                            self.page = frame
                            radio_buttons = frame_radios
                            nfa_count = frame_count
                            best_frame = frame
                            break
                    except Exception:
                        continue
            
            # Final wait and retry if still no results - wait for table to appear
            if nfa_count == 0:
                logger.warning("No radio buttons found, waiting for table to appear...")
                try:
                    # Wait for table element to appear
                    if principal_frame:
                        await principal_frame.wait_for_selector('table', timeout=10000)
                        await principal_frame.wait_for_timeout(3000)
                    else:
                        await self.main_page.wait_for_selector('table', timeout=10000)
                        await self.main_page.wait_for_timeout(3000)
                    
                    # Try one more time in the best frame
                    if best_frame:
                        final_radios = best_frame.locator('input[type="radio"][name="rdbNFAe"], input[type="radio"][name="rdNFAE"]')
                        nfa_count = await final_radios.count()
                        if nfa_count > 0:
                            self.page = best_frame
                            logger.info(f"Found {nfa_count} radio buttons after waiting for table")
                except Exception as e:
                    logger.warning(f"Table wait failed: {e}")
            
            if nfa_count == 0:
                # Debug: log page content
                try:
                    page_text = await self.page.text_content("body") or ""
                    logger.error(
                        "No NFA results found",
                        extra={"payload": {"url": self.page.url, "body_preview": page_text[:1000]}}
                    )
                except Exception:
                    pass
                raise RuntimeError("No NFA results found")
            
            # Determine how many to process
            if nfa_number:
                # Process specific NFA only
                process_count = 1
            else:
                # Process first N NFAs (up to available count)
                process_count = min(max_nfas, nfa_count)
            
            logger.info(f"Processing {process_count} NFA(s)", extra={"payload": {"total_available": nfa_count, "processing": process_count}})
            
            results = []
            
            for i in range(process_count):
                logger.info(f"Processing NFA {i+1} of {process_count}")
                
                # Ensure we're in the correct frame context (principal iframe with results)
                if best_frame and self.page != best_frame:
                    logger.info("Switching back to results frame")
                    self.page = best_frame
                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                    await self.page.wait_for_timeout(2000)
                
                # Select NFA at index i
                if nfa_number and i == 0:
                    # First iteration with specific NFA number
                    await self.select_nfa_result(nfa_number=nfa_number, index=0)
                else:
                    # Select by index
                    await self.select_nfa_result(nfa_number=None, index=i)
                
                # Always download DANFE (Imprimir) first
                logger.info("Downloading DANFE (Imprimir) for NFA")
                danfe_path = await self.download_danfe()
                
                # Ensure we're back on results page after DANFE download
                if best_frame and self.page != best_frame:
                    self.page = best_frame
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                    await self.page.wait_for_timeout(500)  # Medium speed after DANFE download
                    logger.info("Switched back to results frame after DANFE download")
                
                # Always download Taxa Serviço second
                logger.info("Downloading Taxa Serviço for NFA")
                await self.page.wait_for_timeout(500)  # Medium speed before Taxa Serviço download
                dar_path = await self.download_dar()
                
                # Ensure we're back on results page after Taxa Serviço download
                if best_frame and self.page != best_frame:
                    self.page = best_frame
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                    await self.page.wait_for_timeout(500)  # Medium speed after Taxa Serviço download
                    logger.info("Switched back to results frame after Taxa Serviço download")
                
                nfa_result = {
                    "nfa_number": self.nfa_number or "UNKNOWN",
                    "danfe_path": danfe_path,
                    "dar_path": dar_path,
                }
                results.append(nfa_result)
                logger.info(f"NFA {i+1} processed", extra={"payload": nfa_result})
                
                # If processing multiple and not the last one, minimal wait and ensure we're back on results page
                if i < process_count - 1:
                    await self.page.wait_for_timeout(500)  # Medium speed between NFAs
                    # Ensure we're still in the results frame after downloads
                    if best_frame:
                        try:
                            # Re-check if we're still in the right frame
                            if self.page != best_frame:
                                self.page = best_frame
                            await self.page.wait_for_load_state("networkidle", timeout=5000)  # Reduced timeout
                            await self.page.wait_for_timeout(500)  # Medium speed ready for next selection
                            logger.info("Ready for next NFA selection")
                        except Exception as e:
                            logger.warning(f"Could not ensure frame context: {e}")
            
            # Return result for last processed NFA (maintaining backward compatibility)
            result = {
                "status": "success",
                "nfa_number": results[-1]["nfa_number"],
                "danfe_path": results[-1]["danfe_path"],
                "dar_path": results[-1]["dar_path"],
                "processed_count": len(results),
                "all_results": results if len(results) > 1 else None,
            }

            logger.info("Automation completed successfully", extra={"payload": result})
            return result

        except ValueError as e:
            # Login failed
            error_msg = str(e)
            logger.error("Automation failed", exc_info=True, extra={"payload": {"error": error_msg}})
            return {
                "status": "error",
                "message": error_msg,
            }
        except RuntimeError as e:
            error_msg = str(e)
            logger.error("Automation failed", exc_info=True, extra={"payload": {"error": error_msg}})
            return {
                "status": "error",
                "message": error_msg,
            }
        except Exception as e:
            error_msg = str(e)
            logger.error("Automation failed", exc_info=True, extra={"payload": {"error": error_msg}})
            return {
                "status": "error",
                "message": error_msg,
            }
        finally:
            # DO NOT close browser - keep it open for inspection
            # await self.cleanup()
            logger.info("Automation completed - browser left open for inspection")

    async def cleanup(self) -> None:
        """Close browser and cleanup resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Browser closed")


async def main() -> None:
    """Main entry point for script execution."""
    parser = argparse.ArgumentParser(description="NFA ATF Automation Script")
    # Support both --from/--to and --from-date/--to-date for compatibility
    parser.add_argument("--from", "--from-date", dest="from_date", required=True, help="Start date (dd/mm/yyyy)")
    parser.add_argument("--to", "--to-date", dest="to_date", required=True, help="End date (dd/mm/yyyy)")
    parser.add_argument("--matricula", default=DEFAULT_CONFIG.get("default_matricula"), help="Matricula number")
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="Output directory for PDFs",
    )
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run browser with UI")
    parser.add_argument("--nfa-number", help="Specific NFA number to select (optional)")
    parser.add_argument("--max-nfas", type=int, default=3, help="Maximum number of NFAs to process (default: 3)")
    parser.add_argument("--download-dar", action="store_true", default=False, help="Also download DAR (emitir taxa servico). Default: only DANFE (imprimir)")
    parser.add_argument(
        "--use-keychain",
        action="store_true",
        default=True,
        help="If env vars are missing, try reading password from macOS Keychain (default: true).",
    )
    parser.add_argument(
        "--keychain-service",
        type=str,
        default=DEFAULT_KEYCHAIN_SERVICE,
        help=f"Keychain service name (default: {DEFAULT_KEYCHAIN_SERVICE})",
    )
    parser.add_argument(
        "--keychain-account",
        type=str,
        default=None,
        help="Keychain account (defaults to NFA_USERNAME if set).",
    )

    args = parser.parse_args()

    def _keychain_get_password(*, service: str, account: str) -> Optional[str]:
        try:
            proc = subprocess.run(
                ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
                check=False,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                return None
            value = (proc.stdout or "").strip()
            return value or None
        except Exception:
            return None

    # Get credentials from environment
    username = os.getenv("NFA_USERNAME")
    password = os.getenv("NFA_PASSWORD")

    # If password missing, try Keychain (read-only).
    if (not password) and args.use_keychain:
        account = args.keychain_account or username
        if account:
            password = _keychain_get_password(service=args.keychain_service, account=account)
            if password:
                username = username or account

    if not username or not password:
        error_msg = (
            "Missing credentials. Set NFA_USERNAME and NFA_PASSWORD environment variables, "
            "or store the password in Keychain and pass --keychain-account."
        )
        logger.error(error_msg)
        result = {"status": "error", "message": error_msg}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # Create automation instance
    automation = NFAATFAutomation(
        username=username,
        password=password,
        from_date=args.from_date,
        to_date=args.to_date,
        matricula=args.matricula,
        output_dir=args.output_dir,
        headless=args.headless,
    )

    # Run automation - processes first N NFAs (default: 3, configurable via --max-nfas)
    result = await automation.run(nfa_number=args.nfa_number, max_nfas=args.max_nfas, download_dar=args.download_dar)

    # Output JSON result to stdout ONLY (no extra prints, no indentation)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

