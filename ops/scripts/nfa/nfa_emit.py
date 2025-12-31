#!/usr/bin/env python3
"""
NFA Emission Automation Script for FoKS Intelligence.

This script automates the process of:
1. Logging into ATF (https://www4.sefaz.pb.gov.br/atf/)
2. Navigating to FISf_EmitirNFAeReparticao.do (emit page)
3. Filling CPF in destinatario_block field
4. Submitting form and emitting NFA
5. Extracting NFA number from result

Returns structured JSON output for FoKS TaskRunner integration.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    "atf_base_url": "https://www4.sefaz.pb.gov.br/atf/",
    "timeout_seconds": 600,
    "wait_timeout_ms": 30000,
}

if CONFIG_PATH.exists():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            DEFAULT_CONFIG.update(json.load(f))
    except Exception as e:
        logger.warning(f"Failed to load config.json: {e}. Using defaults.")

# Load Informações Adicionais mapping
INFO_ADICIONAIS_MAPPING_PATH = SCRIPT_DIR / "first_second_columns_INFO_ADICIONAIS.json"
INFO_ADICIONAIS_MAPPING: Dict[str, str] = {}
INFO_ADICIONAIS_DEFAULT: str = "RN13 Remessa por conta de contrato de locação"

if INFO_ADICIONAIS_MAPPING_PATH.exists():
    try:
        with open(INFO_ADICIONAIS_MAPPING_PATH, "r", encoding="utf-8") as f:
            mapping_data = json.load(f)
            INFO_ADICIONAIS_MAPPING = mapping_data.get("mapping", {})
            INFO_ADICIONAIS_DEFAULT = mapping_data.get("default", INFO_ADICIONAIS_DEFAULT)
            logger.info(f"Loaded {len(INFO_ADICIONAIS_MAPPING)} LOJA mappings for Informações Adicionais")
    except Exception as e:
        logger.warning(f"Failed to load Informações Adicionais mapping: {e}. Using default.")
else:
    logger.warning(f"Informações Adicionais mapping file not found: {INFO_ADICIONAIS_MAPPING_PATH}. Using default.")


def get_informacoes_adicionais(loja_code: Optional[str] = None) -> str:
    """
    Get Informações Adicionais text based on LOJA code.
    
    Args:
        loja_code: LOJA code (e.g., "RN13", "RO03"). If None, returns default.
    
    Returns:
        Informações Adicionais text string
    """
    if loja_code and loja_code in INFO_ADICIONAIS_MAPPING:
        return INFO_ADICIONAIS_MAPPING[loja_code]
    return INFO_ADICIONAIS_DEFAULT


def clean_cpf(cpf: str) -> str:
    """Remove formatting from CPF (dots and dashes)."""
    return re.sub(r"[.\-]", "", cpf.strip())


def validate_cpf(cpf: str) -> bool:
    """Validate CPF format (11 digits)."""
    cleaned = clean_cpf(cpf)
    return len(cleaned) == 11 and cleaned.isdigit()


class NFAEmitAutomation:
    """Playwright automation for NFA emission operations."""

    def __init__(
        self,
        username: str,
        password: str,
        cpf: Optional[str] = None,
        loja_code: Optional[str] = None,
        test_mode: bool = False,
        headless: bool = True,
        output_dir: str = "/Users/dnigga/Downloads/NFA_Outputs",
        keep_open: bool = True,
    ):
        """
        Initialize NFA emission automation.

        Args:
            username: ATF username (from NFA_USERNAME env var)
            password: ATF password (from NFA_PASSWORD env var)
            cpf: CPF number (formatted or unformatted)
            loja_code: LOJA code for Informações Adicionais mapping (e.g., "RN13", "RO03")
            test_mode: If True, validate form but don't submit
            headless: Run browser in headless mode
            output_dir: Directory to save emitted PDFs (when available)
            keep_open: Keep browser open when visual mode is used
        """
        self.username = username
        self.password = password
        self.cpf: Optional[str] = clean_cpf(cpf) if cpf else None
        self.loja_code: Optional[str] = loja_code
        self.test_mode = test_mode
        self.headless = headless
        self.output_dir = Path(output_dir)
        self.keep_open = keep_open
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.main_page: Optional[Page] = None
        self.nfa_number: Optional[str] = None
        self._user_data_dir: Optional[Path] = None

        # Validate CPF if provided at init
        if self.cpf and not validate_cpf(self.cpf):
            raise ValueError(f"Invalid CPF format: {cpf} (must be 11 digits)")

    async def setup(self) -> None:
        """Initialize Playwright browser and context."""
        playwright = await async_playwright().start()
        # Use a TEMPORARY Chromium profile
        profile_root = Path("/tmp") / f"foks_nfa_emit_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        default_dir = profile_root / "Default"
        default_dir.mkdir(parents=True, exist_ok=True)
        preferences_path = default_dir / "Preferences"

        preferences = {
            "download": {
                "prompt_for_download": False,
                "directory_upgrade": True,
            },
            "plugins": {
                # Force PDFs to download instead of opening the built-in viewer.
                "always_open_pdf_externally": True,
            },
        }
        preferences_path.write_text(json.dumps(preferences), encoding="utf-8")
        self._user_data_dir = profile_root

        # Persistent context
        self.browser = None
        self.context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_root),
            headless=self.headless,
            accept_downloads=True,
            viewport={"width": 1920, "height": 1080},
            downloads_path=str(self.output_dir),
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Persistent contexts usually start with one blank page
        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()
        self.main_page = self.page

        # Set longer timeout for slow ATF pages
        self.page.set_default_timeout(DEFAULT_CONFIG.get("wait_timeout_ms", 30000))

        logger.info("Browser initialized", extra={"payload": {"headless": self.headless}})

    async def login(self) -> None:
        """Log into ATF system (reuse logic from nfa_atf.py)."""
        if not self.page:
            raise RuntimeError("Page not initialized. Call setup() first.")

        url = DEFAULT_CONFIG.get("atf_base_url", "https://www4.sefaz.pb.gov.br/atf/")
        logger.info("Navigating to ATF login", extra={"payload": {"url": url}})

        # Navigate and wait for page to load
        response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        logger.info("Page navigation started", extra={"payload": {"status": response.status if response else None}})

        # Wait for page to be fully interactive
        await self.page.wait_for_load_state("networkidle", timeout=20000)
        await self.page.wait_for_timeout(5000)

        # Debug: Log page title and URL
        page_title = await self.page.title()
        page_url = self.page.url
        logger.info("Page loaded", extra={"payload": {"title": page_title, "url": page_url}})

        # Check if login form is in an iframe
        iframe_selector = 'iframe[name="contents"], iframe#contents, iframe[src*="Login"]'
        frame = None

        try:
            iframe_element = await self.page.wait_for_selector(iframe_selector, timeout=10000)
            if iframe_element:
                frame = await iframe_element.content_frame()
                if frame:
                    logger.info("Login form is in iframe, switched to iframe context")
        except Exception:
            logger.info("No iframe found, checking main page for login form")
            frame = self.page

        # Wait for login form
        form_selectors = [
            'form[name="FormLogin"]',
            'form#loginForm',
            'form',
            'input[name="edtNoLogin"]',
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
            raise RuntimeError(f"Login form not found on page: {page_url}")

        # Use frame context for all subsequent operations
        self.page = frame

        # Fill username and password
        username_selectors = [
            'input[name="edtNoLogin"]',
            'input[id="login"]',
            'input[placeholder*="Usuário"], input[placeholder*="usuário"]',
            'input[type="text"]',
        ]
        password_selector = 'input[name="edtDsSenha"], input[id="senha"], input[type="password"]'

        username_selector = None
        for selector in username_selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                username_selector = selector
                logger.info("Username field found", extra={"payload": {"selector": selector}})
                break
            except Exception:
                continue

        if not username_selector:
            raise RuntimeError("Could not find username field")

        await self.page.fill(username_selector, self.username)
        await self.page.fill(password_selector, self.password)
        logger.info("Credentials filled")

        # Find and click login button
        login_button = self.page.locator(
            'button[name="btnAvancar"], button[type="submit"]:has-text("Avançar"), button[type="submit"], input[type="submit"]'
        ).first
        await login_button.click()
        logger.info("Login button clicked")

        # Wait for navigation after login
        await self.page.wait_for_load_state("networkidle", timeout=15000)

        # Verify login success
        error_selectors = [
            'text="Usuário ou senha inválidos"',
            'text="Login inválido"',
            'text="Erro"',
        ]
        for error_selector in error_selectors:
            if await self.page.locator(error_selector).count() > 0:
                raise ValueError("Login failed: Invalid credentials")

        logger.info("Login successful")

        # After login, wait for navigation
        await self.page.wait_for_timeout(3000)
        await self.page.wait_for_load_state("networkidle", timeout=15000)

        # Check for menu iframe after login
        try:
            await self.main_page.wait_for_load_state("networkidle", timeout=10000)
            menu_iframe_selector = 'iframe[name="contents"], iframe#contents'
            menu_iframe = await self.main_page.wait_for_selector(menu_iframe_selector, timeout=5000)
            if menu_iframe:
                menu_frame = await menu_iframe.content_frame()
                if menu_frame:
                    logger.info("Menu iframe found after login, switching to menu frame")
                    self.page = menu_frame
        except Exception:
            logger.info("No menu iframe found, using main page")

    async def navigate_to_emit_page(self) -> None:
        """Navigate to NFA emission page."""
        if not self.page:
            raise RuntimeError("Page not initialized.")

        emit_url = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"
        logger.info("Navigating to NFA emission page", extra={"payload": {"url": emit_url}})

        # Navigate to emit page
        response = await self.main_page.goto(emit_url, wait_until="domcontentloaded", timeout=30000)
        logger.info("Emit page navigation started", extra={"payload": {"status": response.status if response else None}})

        # Wait for page to load
        await self.main_page.wait_for_load_state("networkidle", timeout=20000)
        await self.main_page.wait_for_timeout(3000)

        # Check if page is in iframe - CRITICAL: form is inside principal iframe
        # Try multiple strategies to find the principal iframe
        principal_iframe_element = None
        
        # Strategy 1: Direct selector (try attached state first, then visible)
        try:
            principal_iframe_element = await self.main_page.wait_for_selector(
                'iframe[name="principal"], iframe#principal', timeout=8000, state="attached"
            )
        except Exception:
            try:
                principal_iframe_element = await self.main_page.wait_for_selector(
                    'iframe[name="principal"], iframe#principal', timeout=8000
                )
            except Exception:
                pass
        
        # Strategy 2: Find any iframe that might contain the form
        if not principal_iframe_element:
            try:
                all_iframes = await self.main_page.locator('iframe').all()
                for ifr in all_iframes:
                    ifr_name = await ifr.get_attribute("name") or ""
                    ifr_id = await ifr.get_attribute("id") or ""
                    if "principal" in ifr_name.lower() or "principal" in ifr_id.lower():
                        principal_iframe_element = ifr
                        logger.info("Found principal iframe by name/id pattern", extra={"payload": {"name": ifr_name, "id": ifr_id}})
                        break
            except Exception:
                pass
        
        # Strategy 3: Access frame content
        if principal_iframe_element:
            try:
                frame = await principal_iframe_element.content_frame()
                if frame:
                    logger.info("Switched to principal iframe for emit page")
                    self.page = frame
                    await frame.wait_for_load_state("networkidle", timeout=15000)
                    await frame.wait_for_timeout(2000)  # Extra wait for form to render
                else:
                    self.page = self.main_page
            except Exception as e:
                logger.warning("Could not access principal iframe content", exc_info=True)
                self.page = self.main_page
        else:
            # Try to find form in main page or any available frame
            logger.info("Principal iframe not found, checking main page and available frames")
            self.page = self.main_page
            # Check if form exists in main page
            try:
                form_check = await self.main_page.locator('form, input[name*="Natureza"], select[name*="CFOP"]').first.count()
                if form_check > 0:
                    logger.info("Form found in main page")
            except Exception:
                pass

        # Verify we're on the emit page
        page_url = self.page.url
        page_text = await self.page.text_content("body") or ""

        if "Incluir Nota Fiscal Avulsa" not in page_text and "Nota Fiscal Avulsa" not in page_text and "NFA" not in page_text:
            logger.warning("Emit page verification unclear", extra={"payload": {"url": page_url, "text_preview": page_text[:500]}})

        logger.info("Emit page loaded", extra={"payload": {"url": page_url}})

    async def _fill_by_label(self, label_text: str, value: str) -> None:
        """Best-effort fill for text/select adjacent to a label cell."""
        if not self.page:
            raise RuntimeError("Page not initialized.")

        label_cell = self.page.locator(f'td:has-text("{label_text}")').first
        if await label_cell.count() == 0:
            logger.warning("Label not found", extra={"payload": {"label": label_text}})
            return
        container = label_cell.locator("xpath=..")
        input_el = container.locator("input:not([type='hidden']), select").first
        if await input_el.count() == 0:
            logger.warning("Input not found near label", extra={"payload": {"label": label_text}})
            return
        tag = await input_el.evaluate("el => el.tagName.toLowerCase()")
        if tag == "select":
            await input_el.select_option(label=value)
        else:
            await input_el.fill(value)

    def _get_frame_by_name(self, frame_name_hint: str):
        """Return frame whose name contains the hint."""
        if not self.page:
            return None
        for fr in self.page.frames:
            if frame_name_hint.lower() in (fr.name or "").lower():
                return fr
        return None

    async def _fill_first_input_and_search(self, frame_name: str, value: str) -> None:
        """Fill first visible text input in iframe and click search if present."""
        frame = self._get_frame_by_name(frame_name)
        if not frame:
            logger.warning("Frame not found", extra={"payload": {"frame": frame_name}})
            return
        txt = frame.locator("input[type='text']:not([hidden])").first
        if await txt.count() == 0:
            logger.warning("Text input not found in iframe", extra={"payload": {"frame": frame_name}})
            return
        await txt.fill(value)
        search = frame.locator("input[type='submit'], input[value*='Pesquisar']").first
        if await search.count() > 0:
            await search.click()
            await frame.wait_for_timeout(1500)

    async def _fill_simple_form_field(self, selector: str, value: str, *, by_label: bool = False) -> None:
        """Select or fill a field on the main page using a selector."""
        if not self.page:
            return
        el = self.page.locator(selector).first
        if await el.count() == 0:
            logger.warning("Main field not found", extra={"payload": {"selector": selector}})
            return
        tag = await el.evaluate("el => el.tagName.toLowerCase()")
        if tag == "select":
            try:
                await el.select_option(label=value)
            except Exception:
                await el.select_option(value=value)
        else:
            await el.fill(value)

    async def _fill_component_frame_input(self, frame_name_hint: str, value: str) -> None:
        """
        Enter value inside a component iframe (e.g., cmpEmitente, cmpDestinatario)
        and click Pesquisar if present.
        """
        if not self.page:
            raise RuntimeError("Page not initialized.")

        iframe = self._get_frame_by_name(frame_name_hint)
        if not iframe:
            logger.warning("Component iframe not found", extra={"payload": {"frame": frame_name_hint}})
            return

        # Find first visible text input (non-hidden)
        text_input = iframe.locator("input[type='text']:not([hidden])").first
        if await text_input.count() == 0:
            logger.warning("Text input not found in iframe", extra={"payload": {"frame": frame_name_hint}})
            return
        await text_input.fill(value)

        # Click Pesquisar / search button if present
        search_btn = iframe.locator("input[type='submit'], input[value*='Pesquisar']").first
        if await search_btn.count() > 0:
            await search_btn.click()
            await iframe.wait_for_timeout(1500)

    async def fill_form_fields(self, cpf_override: Optional[str] = None) -> None:
        """Fill the NFA emit form exactly as shown in images."""
        if not self.page:
            raise RuntimeError("Page not initialized.")

        # Ensure we're in the principal iframe context - CRITICAL
        try:
            if self.main_page:
                # Wait longer for principal iframe
                await self.main_page.wait_for_load_state("networkidle", timeout=20000)
                await self.main_page.wait_for_timeout(3000)
                
                principal_iframe_element = None
                # Try multiple strategies to find principal iframe
                try:
                    principal_iframe_element = await self.main_page.wait_for_selector(
                        'iframe[name="principal"], iframe#principal', timeout=10000, state="attached"
                    )
                except Exception:
                    # Try finding by iterating all iframes
                    all_iframes = await self.main_page.locator('iframe').all()
                    for ifr in all_iframes:
                        ifr_name = await ifr.get_attribute("name") or ""
                        ifr_id = await ifr.get_attribute("id") or ""
                        if "principal" in ifr_name.lower() or "principal" in ifr_id.lower():
                            principal_iframe_element = ifr
                            break
                
                if principal_iframe_element:
                    frame = await principal_iframe_element.content_frame()
                    if frame:
                        self.page = frame
                        await frame.wait_for_load_state("networkidle", timeout=15000)
                        await frame.wait_for_timeout(3000)
                        logger.info("Switched to principal iframe for form filling")
        except Exception as e:
            logger.warning("Principal iframe switch failed, using main page", exc_info=True)
            self.page = self.main_page

        # Wait for form to fully load
        await self.page.wait_for_load_state("networkidle", timeout=20000)
        await self.page.wait_for_timeout(3000)

        # Exact values from images
        reparticao_codigo = "90102008"
        municipio_codigo = "2051-6"
        emitente_cnpj = "28.842.017/0001-05"
        destinatario_cpf = cpf_override or "738.255.062-15"
        natureza_operacao = "REMESSA"
        motivo = "DESPACHO"
        tipo_operacao = "Saída"
        cfop_value = "6908"
        ncm = "0000.00.00"
        detalhamento = "1 - SID241"
        unidade = "UNIDADE"
        quantidade = "1"
        valor_unitario = "1100"
        aliquota = "0"
        cst_value = "6"  # Dropdown value for "41 - NÃO TRIBUTADA"
        receita_value = "1199"
        # Get Informações Adicionais from mapping file based on LOJA code
        informacoes_adicionais = get_informacoes_adicionais(self.loja_code)
        logger.info("Using Informações Adicionais", extra={"payload": {"loja_code": self.loja_code, "text": informacoes_adicionais}})

        logger.info("Starting form field filling", extra={"payload": {"cpf": destinatario_cpf[:3] + "***"}})

        # Step 1: Repartição Fiscal (component iframe cmpElementoOrg)
        logger.info("Step 1: Filling Repartição Fiscal")
        await self._fill_first_input_and_search("cmpElementoOrg", reparticao_codigo)
        await asyncio.sleep(2)

        # Step 2: Município (component iframe cmpMunicipioGiva)
        logger.info("Step 2: Filling Município")
        await self._fill_first_input_and_search("cmpMunicipioGiva", municipio_codigo)
        await asyncio.sleep(2)

        # Step 3: Emitente (component iframe cmpEmitente)
        logger.info("Step 3: Filling Emitente")
        emitente_frame = self._get_frame_by_name("cmpEmitente")
        if emitente_frame:
            # First, select "CNPJ" from Tipo de Identificação dropdown
            tipo_select = emitente_frame.locator('select:visible').first
            if await tipo_select.count() > 0:
                try:
                    await tipo_select.select_option(label="CNPJ")
                    logger.info("Emitente Tipo de Identificação set to CNPJ")
                    await asyncio.sleep(1)
                except Exception:
                    try:
                        await tipo_select.select_option(value="CNPJ")
                        logger.info("Emitente Tipo de Identificação set to CNPJ (by value)")
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.warning("Could not set Emitente Tipo to CNPJ", exc_info=True)
            # Then fill CNPJ number and click Pesquisar
            await self._fill_first_input_and_search("cmpEmitente", emitente_cnpj)
        else:
            logger.warning("cmpEmitente iframe not found")
        await asyncio.sleep(2)

        # Step 4: Destinatário (component iframe cmpDestinatario)
        logger.info("Step 4: Filling Destinatário")
        destinatario_frame = self._get_frame_by_name("cmpDestinatario")
        if destinatario_frame:
            # First, select "CPF" from Tipo de Identificação dropdown
            tipo_select = destinatario_frame.locator('select:visible').first
            if await tipo_select.count() > 0:
                try:
                    await tipo_select.select_option(label="CPF")
                    logger.info("Destinatário Tipo de Identificação set to CPF")
                    await asyncio.sleep(1)
                except Exception:
                    try:
                        await tipo_select.select_option(value="CPF")
                        logger.info("Destinatário Tipo de Identificação set to CPF (by value)")
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.warning("Could not set Destinatário Tipo to CPF", exc_info=True)
            # Then fill CPF number and click Pesquisar
            await self._fill_first_input_and_search("cmpDestinatario", destinatario_cpf)
        else:
            logger.warning("cmpDestinatario iframe not found")
        await asyncio.sleep(2)

        # Step 5: Informações da Nota Fiscal (in principal iframe)
        logger.info("Step 5: Filling Informações da Nota Fiscal")
        
        # Natureza da Operação
        natureza_filled = False
        for selector in [
            'select[name*="Natureza"]',
            'td:has-text("Natureza da Operação") + td select',
            'td:has-text("Natureza") + td select',
        ]:
            try:
                select = self.page.locator(selector).first
                if await select.count() > 0:
                    await select.select_option(label=natureza_operacao)
                    logger.info("Natureza filled", extra={"payload": {"selector": selector}})
                    natureza_filled = True
                    break
            except Exception:
                continue
        if not natureza_filled:
            logger.warning("Natureza da Operação not filled")
        await asyncio.sleep(1)

        # Motivo
        motivo_filled = False
        for selector in [
            'select[name*="Motivo"]',
            'td:has-text("Motivo") + td select',
        ]:
            try:
                select = self.page.locator(selector).first
                if await select.count() > 0:
                    await select.select_option(label=motivo)
                    logger.info("Motivo filled", extra={"payload": {"selector": selector}})
                    motivo_filled = True
                    break
            except Exception:
                continue
        if not motivo_filled:
            logger.warning("Motivo not filled")
        await asyncio.sleep(1)

        # Tipo de Operação
        tipo_filled = False
        for selector in [
            'select[name*="TipoOper"]',
            'select[name*="Tipo"]',
            'td:has-text("Tipo de Operação") + td select',
        ]:
            try:
                select = self.page.locator(selector).first
                if await select.count() > 0:
                    await select.select_option(label=tipo_operacao)
                    logger.info("Tipo Operação filled", extra={"payload": {"selector": selector}})
                    tipo_filled = True
                    break
            except Exception:
                continue
        if not tipo_filled:
            logger.warning("Tipo Operação not filled")
        await asyncio.sleep(1)

        # CFOP
        cfop_filled = False
        for selector in [
            'select[name*="CFOP"]',
            'select[name*="cfop"]',
            'td:has-text("CFOP") + td select',
            'td:has-text("Número CFOP") + td select',
        ]:
            try:
                select = self.page.locator(selector).first
                if await select.count() > 0:
                    try:
                        await select.select_option(value=cfop_value)
                        logger.info("CFOP filled by value", extra={"payload": {"value": cfop_value}})
                    except Exception:
                        # Try partial label match
                        options = await select.locator('option').all()
                        for opt in options:
                            opt_text = await opt.text_content() or ""
                            if "6908" in opt_text:
                                opt_value = await opt.get_attribute("value") or ""
                                await select.select_option(value=opt_value)
                                logger.info("CFOP filled by matching option")
                                break
                    cfop_filled = True
                    break
            except Exception:
                continue
        if not cfop_filled:
            logger.warning("CFOP not filled")
        await asyncio.sleep(2)

        # Step 6: Item da Nota Fiscal (in cmpProduto iframe or main page)
        logger.info("Step 6: Filling Item da Nota Fiscal in cmpProduto iframe")
        prod_iframe = self._get_frame_by_name("cmpProduto")
        
        # If iframe not found, try to find NCM field in main page
        if not prod_iframe:
            logger.warning("cmpProduto iframe not found, trying main page")
            try:
                # Try to find NCM field in main page
                ncm_input = self.page.locator('input[type="text"]:visible').first
                if await ncm_input.count() > 0:
                    await ncm_input.fill(ncm)
                    logger.info("NCM filled in main page", extra={"payload": {"ncm": ncm}})
                    await asyncio.sleep(1)
                    
                    # Click "Pesquisar" button after filling NCM
                    pesquisar_btn = self.page.locator('input[type="submit"], input[value*="Pesquisar"], button:has-text("Pesquisar")').first
                    if await pesquisar_btn.count() > 0:
                        await pesquisar_btn.click()
                        logger.info("Pesquisar clicked after NCM fill (main page)")
                        await asyncio.sleep(2)  # Wait for search results
                    else:
                        logger.warning("Pesquisar button not found after NCM field (main page)")
            except Exception as e:
                logger.warning("Could not fill NCM in main page", exc_info=True)
        
        if prod_iframe:
            try:
                await prod_iframe.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(2)
                
                # NCM Code - first visible text input
                ncm_input = prod_iframe.locator('input[type="text"]:not([hidden]):visible').first
                if await ncm_input.count() > 0:
                    await ncm_input.fill(ncm)
                    logger.info("NCM filled", extra={"payload": {"ncm": ncm}})
                    await asyncio.sleep(1)
                    
                    # Click "Pesquisar" button after filling NCM
                    pesquisar_btn = prod_iframe.locator('input[type="submit"], input[value*="Pesquisar"], button:has-text("Pesquisar")').first
                    if await pesquisar_btn.count() > 0:
                        await pesquisar_btn.click()
                        logger.info("Pesquisar clicked after NCM fill")
                        await asyncio.sleep(2)  # Wait for search results
                    else:
                        logger.warning("Pesquisar button not found after NCM field")

                # Detalhamento do Produto - try multiple strategies
                detalhamento_filled = False
                # Strategy 1: Find by label text
                try:
                    detalhamento_textarea = prod_iframe.locator('td:has-text("Detalhamento") + td textarea, td:has-text("Detalhamento do Produto") + td textarea, textarea:visible').first
                    if await detalhamento_textarea.count() > 0:
                        await detalhamento_textarea.fill(detalhamento)
                        logger.info("Detalhamento filled")
                        detalhamento_filled = True
                        await asyncio.sleep(1)
                except Exception:
                    pass
                
                # Strategy 2: First visible textarea if not found
                if not detalhamento_filled:
                    try:
                        detalhamento_textarea = prod_iframe.locator("textarea:visible").first
                        if await detalhamento_textarea.count() > 0:
                            await detalhamento_textarea.fill(detalhamento)
                            logger.info("Detalhamento filled (fallback)")
                            await asyncio.sleep(1)
                    except Exception:
                        logger.warning("Could not fill Detalhamento do Produto")

                # Unidade de Medida - first select
                unidade_select = prod_iframe.locator("select:visible").first
                if await unidade_select.count() > 0:
                    try:
                        await unidade_select.select_option(label=unidade)
                        logger.info("Unidade filled")
                    except Exception:
                        try:
                            await unidade_select.select_option(value=unidade)
                        except Exception:
                            pass
                    await asyncio.sleep(1)

                # Get all visible text inputs for valor, quantidade, aliquota
                visible_inputs = []
                for inp in await prod_iframe.locator('input[type="text"]:not([hidden]):visible').all():
                    visible_inputs.append(inp)
                
                # Fill in order: valor unitário, quantidade, aliquota (usually last 3 inputs)
                if len(visible_inputs) >= 3:
                    try:
                        # Last 3 inputs are usually: valor, quantidade, aliquota
                        await visible_inputs[-3].fill(valor_unitario)
                        await asyncio.sleep(0.5)
                        await visible_inputs[-2].fill(quantidade)
                        await asyncio.sleep(0.5)
                        await visible_inputs[-1].fill(aliquota)
                        logger.info("Valor Unitário, Quantidade, Alíquota filled")
                    except Exception as e:
                        logger.warning("Could not fill item numeric fields", exc_info=True)

                await asyncio.sleep(1)

                # Click "Adicionar/Alterar Item" button
                add_btn = prod_iframe.locator('input[value*="Adicionar"], input[value*="Alterar"], button:has-text("Adicionar"), button:has-text("Alterar")').first
                if await add_btn.count() > 0:
                    await add_btn.click()
                    logger.info("Adicionar/Alterar Item clicked")
                    # Wait for item to appear in the table
                    await asyncio.sleep(3)

            except Exception as e:
                logger.warning("Could not fully fill product iframe", exc_info=True)
        # If neither iframe nor main page worked, log error
        if not prod_iframe:
            logger.error("Could not find NCM field in either cmpProduto iframe or main page")

        # Step 7: Cálculo do Imposto - CST and Receita (in principal iframe)
        logger.info("Step 7: Filling Cálculo do Imposto")
        await asyncio.sleep(2)

        # CST dropdown - try multiple approaches
        cst_filled = False
        for selector in [
            'select[name*="CST"]',
            'select[name*="cst"]',
            'td:has-text("CST:") + td select',
            'td:has-text("CST") + td select',
        ]:
            try:
                select = self.page.locator(selector).first
                if await select.count() > 0:
                    try:
                        await select.select_option(value=cst_value)
                        logger.info("CST filled by value", extra={"payload": {"value": cst_value}})
                    except Exception:
                        # Try finding option with "41" in text
                        options = await select.locator('option').all()
                        for opt in options:
                            opt_text = await opt.text_content() or ""
                            if "41" in opt_text and "NÃO TRIBUTADA" in opt_text:
                                opt_value = await opt.get_attribute("value") or ""
                                await select.select_option(value=opt_value)
                                logger.info("CST filled by matching option")
                                break
                    cst_filled = True
                    break
            except Exception:
                continue
        if not cst_filled:
            logger.warning("CST not filled")
        await asyncio.sleep(1)

        # Receita dropdown
        receita_filled = False
        for selector in [
            'select[name*="Receita"]',
            'select[name*="receita"]',
            'td:has-text("Receita:") + td select',
            'td:has-text("Receita") + td select',
        ]:
            try:
                select = self.page.locator(selector).first
                if await select.count() > 0:
                    try:
                        await select.select_option(value=receita_value)
                        logger.info("Receita filled by value", extra={"payload": {"value": receita_value}})
                    except Exception:
                        # Try finding option with "1199" in text
                        options = await select.locator('option').all()
                        for opt in options:
                            opt_text = await opt.text_content() or ""
                            if "1199" in opt_text:
                                opt_value = await opt.get_attribute("value") or ""
                                await select.select_option(value=opt_value)
                                logger.info("Receita filled by matching option")
                                break
                    receita_filled = True
                    break
            except Exception:
                continue
        if not receita_filled:
            logger.warning("Receita not filled")

        # Step 7.5: Check checkbox to select item BEFORE clicking Calcular
        # CRITICAL: Checkbox must be checked before clicking Calcular button
        logger.info("Step 7.5: Checking checkbox to select item before Calcular")
        await asyncio.sleep(1)
        
        checkbox_checked = False
        # Try multiple strategies to find and check the checkbox in the items table
        checkbox_selectors = [
            # Checkbox in the "Itens Adicionados" table - first unchecked checkbox
            'table:has-text("Itens Adicionados") input[type="checkbox"]:not([checked])',
            'table:has-text("Itens Adicionados") input[type="checkbox"]',
            # Checkbox next to item row
            'tr:has-text("SID241") input[type="checkbox"]',
            'tr:has-text("1 - SID241") input[type="checkbox"]',
            # "Selecionar Todos" checkbox
            'input[type="checkbox"]:near(:text("Selecionar Todos"))',
            'td:has-text("Selecionar Todos") input[type="checkbox"]',
            # Any checkbox in a table row
            'table tr input[type="checkbox"]:not([checked])',
            'td input[type="checkbox"]:not([checked])',
            # Fallback: any unchecked checkbox
            'input[type="checkbox"]:not([checked])',
            'input[type="checkbox"]',
        ]
        
        for selector in checkbox_selectors:
            try:
                checkbox = self.page.locator(selector).first
                if await checkbox.count() > 0:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        # Scroll checkbox into view if needed
                        await checkbox.scroll_into_view_if_needed()
                        await checkbox.check()
                        logger.info("Checkbox checked", extra={"payload": {"selector": selector}})
                        checkbox_checked = True
                        await asyncio.sleep(1)
                        break
                    else:
                        logger.info("Checkbox already checked", extra={"payload": {"selector": selector}})
                        checkbox_checked = True
                        break
            except Exception as e:
                logger.debug(f"Checkbox selector failed: {selector}", exc_info=True)
                continue
        
        if not checkbox_checked:
            logger.warning("Could not find or check checkbox before Calcular - this may cause calculation to fail")
        else:
            logger.info("Checkbox successfully checked - ready to click Calcular")
        
        await asyncio.sleep(1)

        # Step 7.6: Click "Calcular" button (calculate tax)
        logger.info("Step 7.6: Clicking Calcular button")
        calcular_filled = False
        for selector in [
            'input[value*="Calcular"]',
            'input[value*="calcular"]',
            'button:has-text("Calcular")',
            'input[name*="calcular"]',
            'input[type="button"][value*="Calcular"]',
            'input[type="submit"][value*="Calcular"]',
        ]:
            try:
                btn = self.page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    logger.info("Calcular button clicked")
                    await asyncio.sleep(2)
                    calcular_filled = True
                    break
            except Exception:
                continue
        if not calcular_filled:
            logger.warning("Calcular button not found - tax calculation may not have been triggered")

        await asyncio.sleep(2)

        # Step 7.7: Informações Adicionais (Additional Information)
        logger.info("Step 7.7: Filling Informações Adicionais")
        informacoes_filled = False
        
        # Try multiple strategies to find the Informações Adicionais textarea
        informacoes_selectors = [
            # Find by label text
            'td:has-text("Informações Adicionais") + td textarea',
            'td:has-text("Informações Adicionais:") + td textarea',
            'label:has-text("Informações Adicionais") + textarea',
            'label:has-text("Informações Adicionais") ~ textarea',
            # Find by name attribute
            'textarea[name*="Informacoes"]',
            'textarea[name*="informacoes"]',
            'textarea[name*="Adicionais"]',
            'textarea[id*="Informacoes"]',
            'textarea[id*="informacoes"]',
            # Find textarea near "Informações" text
            'textarea:near(:text("Informações Adicionais"))',
            # Fallback: last textarea in form (often Informações Adicionais is the last field)
            'textarea:visible',
        ]
        
        for selector in informacoes_selectors:
            try:
                textarea = self.page.locator(selector).first
                if await textarea.count() > 0 and await textarea.is_visible():
                    await textarea.scroll_into_view_if_needed()
                    await textarea.fill(informacoes_adicionais)
                    logger.info("Informações Adicionais filled", extra={"payload": {"selector": selector, "value": informacoes_adicionais}})
                    informacoes_filled = True
                    await asyncio.sleep(1)
                    break
            except Exception as e:
                logger.debug(f"Informações Adicionais selector failed: {selector}", exc_info=True)
                continue
        
        if not informacoes_filled:
            logger.warning("Could not find Informações Adicionais field - this field may be missing from the form")
        else:
            logger.info("Informações Adicionais successfully filled")

        await asyncio.sleep(1)
        logger.info("Form fields filling completed")

    async def _find_cpf_field(self) -> Tuple[Any, Any]:
        """
        Find CPF input field and return (field_locator, container_locator).
        Container is used to locate nearby buttons like 'Pesquisar'.
        """
        if not self.page:
            raise RuntimeError("Page not initialized.")

        # Wait a bit more for form to fully load
        await self.page.wait_for_load_state("networkidle", timeout=10000)
        await self.page.wait_for_timeout(2000)
        
        # Try to find and click on "destinatario_block" or similar expandable section
        # This might be a tab, section header, or clickable area
        destinatario_section_selectors = [
            'text=/destinatario/i',
            '[id*="destinatario_block"]',
            '[name*="destinatario_block"]',
            '[class*="destinatario"]',
            'a:has-text("Destinatário")',
            'span:has-text("Destinatário")',
            'div:has-text("Destinatário")',
        ]
        
        for section_sel in destinatario_section_selectors:
            try:
                section = self.page.locator(section_sel).first
                if await section.count() > 0 and await section.is_visible():
                    logger.info("Found destinatario section, attempting to click/expand", extra={"payload": {"selector": section_sel}})
                    await section.click()
                    await self.page.wait_for_timeout(1000)
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                    break
            except Exception:
                continue

        # Check if we need to look in principal iframe first
        try:
            principal_iframe = await self.main_page.wait_for_selector(
                'iframe[name="principal"], iframe#principal', timeout=5000
            )
            if principal_iframe:
                frame = await principal_iframe.content_frame()
                if frame:
                    logger.info("Found principal iframe, checking for CPF field there")
                    self.page = frame
                    await frame.wait_for_load_state("networkidle", timeout=10000)
                    await frame.wait_for_timeout(1000)
        except Exception:
            logger.info("No principal iframe found or already in correct context")

        # Check for destinatario component iframe (similar to cmpFuncEmitente in consultation)
        # The form might have a component iframe for destinatario (like cmpDestinatario)
        search_page = self.page
        
        # First, try to find destinatario component iframe by name/id pattern
        destinatario_iframe_selectors = [
            'iframe[name*="destinatario"]',
            'iframe[id*="destinatario"]',
            'iframe[name*="Destinatario"]',
            'iframe[id*="Destinatario"]',
            'iframe[name*="cmpDestinatario"]',
            'iframe[id*="cmpDestinatario"]',
            'iframe[name*="cmpDestinat"]',
            'iframe[id*="cmpDestinat"]',
        ]
        
        for iframe_sel in destinatario_iframe_selectors:
            try:
                iframe_elem = self.page.locator(iframe_sel).first
                if await iframe_elem.count() > 0:
                    iframe_frame = await iframe_elem.content_frame()
                    if iframe_frame:
                        logger.info("Found destinatario component iframe", extra={"payload": {"selector": iframe_sel}})
                        await iframe_frame.wait_for_load_state("networkidle", timeout=10000)
                        await iframe_frame.wait_for_timeout(2000)
                        search_page = iframe_frame
                        break
            except Exception:
                continue
        
        # If not found, check all iframes on the page
        if search_page == self.page:
            all_iframes = self.page.locator('iframe').all()
            for iframe_elem in await all_iframes:
                try:
                    iframe_name = await iframe_elem.get_attribute("name") or ""
                    iframe_id = await iframe_elem.get_attribute("id") or ""
                    iframe_src = await iframe_elem.get_attribute("src") or ""
                    
                    logger.info("Checking iframe", extra={"payload": {"name": iframe_name, "id": iframe_id, "src": iframe_src[:100]}})
                    
                    iframe_frame = await iframe_elem.content_frame()
                    if iframe_frame:
                        await iframe_frame.wait_for_load_state("domcontentloaded", timeout=5000)
                        await iframe_frame.wait_for_timeout(1000)
                        # Check if CPF field exists in this iframe
                        test_cpf = iframe_frame.locator('input[type="text"], input[name*="cpf"], input[name*="Cpf"]').first
                        if await test_cpf.count() > 0:
                            logger.info("Found CPF field in iframe", extra={"payload": {"name": iframe_name, "id": iframe_id}})
                            search_page = iframe_frame
                            break
                except Exception as e:
                    logger.debug(f"Error checking iframe: {e}")
                    continue

        selectors = [
            'input[name="edtNrCpfCnpjDestinatario"]',
            'input[name="edtCpfCnpjDestinatario"]',
            'input[name="cpfDestinatario"]',
            'input[name*="Cpf"][type="text"]',
            'input[id*="Cpf"][type="text"]',
            'input[name*="cpf"][type="text"]',
            'input[id*="cpf"][type="text"]',
            'input[placeholder*="CPF"]',
            'input[placeholder*="cpf"]',
            'input[name*="destinatario"]',
            'input[id*="destinatario"]',
            # Additional selectors for "Remessa por conta de contrato de locação"
            'input[name*="Destinatario"]',
            'input[id*="Destinatario"]',
            'input[name*="destinatario_block"]',
            'input[id*="destinatario_block"]',
            # Generic text input in destinatario area
            'input[type="text"]',
        ]

        for sel in selectors:
            try:
                field = search_page.locator(sel).first
                if await field.count() > 0 and await field.is_visible():
                    # Verify it's likely a CPF field (not date, not other fields)
                    field_name = await field.get_attribute("name") or ""
                    field_id = await field.get_attribute("id") or ""
                    if any(keyword in (field_name + field_id).lower() for keyword in ["cpf", "cnpj", "destinatario"]):
                        logger.info("Found CPF field", extra={"payload": {"selector": sel, "name": field_name, "id": field_id}})
                        container = field.locator("xpath=ancestor::tr[1] | ancestor::div[1] | ancestor::td[1]")
                        # Update self.page to the iframe if we found it there
                        if search_page != self.page:
                            self.page = search_page
                        return field, container
            except Exception:
                continue

        # Context fallback: label text near CPF/destinatario
        label = search_page.locator('text=/destinat|cpf|cnpj/i').first
        if await label.count() > 0:
            container = label.locator("xpath=ancestor::tr[1] | ancestor::div[1] | ancestor::td[1]")
            field = container.locator('input[type="text"], input').first
            if await field.count() > 0 and await field.is_visible():
                logger.info("Found CPF field via label fallback")
                if search_page != self.page:
                    self.page = search_page
                return field, container

        # Debug: dump available form fields
        fields = await self._dump_form_fields()
        logger.error(
            "Could not find destinatario CPF field",
            extra={"payload": {"available_fields": fields[:20], "url": self.page.url}}
        )
        raise RuntimeError("Could not find destinatario CPF field")

    async def fill_destinatario_cpf(self, cpf: str) -> None:
        """Fill CPF and click Pesquisar (when present)."""
        if not self.page:
            raise RuntimeError("Page not initialized.")

        cpf_clean = clean_cpf(cpf)
        if not validate_cpf(cpf_clean):
            raise ValueError(f"Invalid CPF format: {cpf} (must be 11 digits)")

        logger.info("Filling CPF in destinatario field", extra={"payload": {"cpf": cpf_clean[:3] + "***"}})

        field, container = await self._find_cpf_field()
        await field.clear()
        await field.fill(cpf_clean)

        # If there's a Pesquisar button near the CPF field, click it.
        pesquisar_selectors = [
            'input[type="submit"][value*="Pesquisar"]',
            'input[type="button"][value*="Pesquisar"]',
            'button:has-text("Pesquisar")',
        ]
        for sel in pesquisar_selectors:
            try:
                btn = container.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    logger.info("Clicked Pesquisar for CPF lookup", extra={"payload": {"selector": sel}})
                    await self.page.wait_for_load_state("networkidle", timeout=15000)
                    break
            except Exception:
                continue

        # Wait a moment for any auto-complete or validation
        await self.page.wait_for_timeout(1000)

    async def _dump_form_fields(self) -> List[Dict[str, Any]]:
        """Best-effort dump of form fields to help identify required inputs."""
        if not self.page:
            return []

        script = """
() => {
  const out = [];
  const els = Array.from(document.querySelectorAll('input, select, textarea'));
  for (const el of els) {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    const name = el.getAttribute('name') || '';
    const id = el.getAttribute('id') || '';
    const disabled = !!el.disabled;
    const readonly = !!el.readOnly;
    const required = !!el.required || el.getAttribute('aria-required') === 'true';
    const placeholder = el.getAttribute('placeholder') || '';
    let value = '';
    if (tag === 'select') {
      const idx = el.selectedIndex;
      value = idx >= 0 ? (el.options[idx]?.value || '') : '';
    } else {
      value = el.value || '';
    }
    let labelText = '';
    if (id) {
      const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (label) labelText = (label.innerText || '').trim();
    }
    out.push({ tag, type, name, id, value, disabled, readonly, required, placeholder, labelText });
  }
  return out;
}
"""
        try:
            data = await self.page.evaluate(script)
            if isinstance(data, list):
                return data
        except Exception:
            return []
        return []

    async def _try_download_documents(self, *, nfa_number: Optional[str], cpf: str) -> Dict[str, Optional[str]]:
        """After emission, try to download DANFE/DAR if buttons are present."""
        if not self.page:
            return {"danfe_path": None, "dar_path": None}

        out_dir = self.output_dir / "NFA_Emitted" / (f"NFA_{nfa_number}" if nfa_number else f"CPF_{cpf}")
        out_dir.mkdir(parents=True, exist_ok=True)

        async def _download(selectors: List[str], filename: str) -> Optional[str]:
            for sel in selectors:
                try:
                    btn = self.page.locator(sel).first
                    if await btn.count() == 0 or not await btn.is_visible():
                        continue
                    async with self.page.expect_download(timeout=20000) as dl_info:
                        await btn.click()
                    dl = await dl_info.value
                    path = out_dir / filename
                    await dl.save_as(str(path))
                    return str(path)
                except Exception:
                    continue
            return None

        danfe = await _download(
            ['input[name="btnImprimirEletronica"]', 'input[value*="Imprimir"]', 'button:has-text("Imprimir")'],
            f"NFA_{nfa_number or cpf}_DANFE.pdf",
        )
        dar = await _download(
            [
                'input[name="btnGerarTaxaServicoEletronica"]',
                'input[value*="Taxa"]',
                'input[value*="DAR"]',
                'button:has-text("Taxa")',
                'button:has-text("DAR")',
            ],
            f"NFA_{nfa_number or cpf}_TAXA_SERVICO.pdf",
        )
        return {"danfe_path": danfe, "dar_path": dar}

    async def submit_and_emit(self) -> None:
        """Submit form and emit NFA."""
        if not self.page:
            raise RuntimeError("Page not initialized.")

        if self.test_mode:
            logger.info("Test mode: Skipping form submission")
            return

        logger.info("Submitting form to emit NFA")

        # Find submit button (try multiple selectors)
        # Based on images: "Submeter Nota" is the submit button
        submit_selectors = [
            'input[value*="Submeter Nota"]',
            'input[value*="Submeter"]',
            'input[value*="submeter"]',
            'button:has-text("Submeter Nota")',
            'button:has-text("Submeter")',
            'input[name*="submeter"]',
            'input[name*="Submeter"]',
            'input[type="submit"][value*="Submeter"]',
            'input[type="submit"]',
            'button[type="submit"]',
            'input[value*="Emitir"]',
            'input[value*="emitir"]',
            'input[value*="Incluir"]',
            'button:has-text("Incluir")',
            'button:has-text("Emitir")',
            'button:has-text("Confirmar")',
            'input[name*="emitir"]',
            'input[name*="confirmar"]',
        ]

        submit_button = None
        for selector in submit_selectors:
            try:
                button = self.page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    logger.info("Found submit button", extra={"payload": {"selector": selector}})
                    submit_button = button
                    break
            except Exception:
                continue

        if not submit_button:
            # Try to find button in principal iframe if we're in main page
            if self.main_page and self.page == self.main_page:
                try:
                    principal_iframe_element = await self.main_page.wait_for_selector(
                        'iframe[name="principal"], iframe#principal', timeout=5000, state="attached"
                    )
                    if principal_iframe_element:
                        principal_frame = await principal_iframe_element.content_frame()
                        if principal_frame:
                            for selector in submit_selectors:
                                try:
                                    button = principal_frame.locator(selector).first
                                    if await button.count() > 0 and await button.is_visible():
                                        logger.info("Found submit button in principal iframe", extra={"payload": {"selector": selector}})
                                        submit_button = button
                                        self.page = principal_frame
                                        break
                                except Exception:
                                    continue
                except Exception:
                    pass

        if not submit_button:
            raise RuntimeError("Could not find submit/emit button. Available buttons: " + 
                             str([await btn.text_content() for btn in await self.page.locator('input[type="submit"], button[type="submit"], input[type="button"]').all()][:5]))

        # Click submit button
        await submit_button.click()
        logger.info("Submit button clicked", extra={"payload": {"button_text": await submit_button.text_content() if await submit_button.count() > 0 else "unknown"}})

        # Wait for response - longer timeout for form submission
        await self.page.wait_for_load_state("networkidle", timeout=45000)
        await asyncio.sleep(3000)

        # Extract NFA number from response page
        await self.extract_nfa_number()

    async def emit_one(self, cpf: str) -> Dict[str, Any]:
        """
        Emit a single NFA for the given CPF reusing the existing browser session.
        """
        cpf_clean = clean_cpf(cpf)
        if not validate_cpf(cpf_clean):
            return {"status": "error", "cpf": cpf_clean, "message": "Invalid CPF (must be 11 digits)"}

        self.cpf = cpf_clean
        self.nfa_number = None

        await self.navigate_to_emit_page()
        # Fill full form with provided constants (includes destinatário CPF)
        await self.fill_form_fields(cpf_clean)

        if self.test_mode:
            return {
                "status": "success",
                "cpf": cpf_clean,
                "nfa_number": None,
                "emission_date": datetime.now().strftime("%d/%m/%Y"),
                "test_mode": True,
            }

        try:
            await self.submit_and_emit()
        except Exception as exc:
            fields = await self._dump_form_fields()
            return {
                "status": "error",
                "cpf": cpf_clean,
                "message": f"Emission submit failed: {type(exc).__name__}: {exc}",
                "debug": {"field_dump_count": len(fields), "field_dump": fields[:80]},
            }

        downloads = await self._try_download_documents(nfa_number=self.nfa_number, cpf=cpf_clean)
        return {
            "status": "success",
            "cpf": cpf_clean,
            "nfa_number": self.nfa_number,
            "emission_date": datetime.now().strftime("%d/%m/%Y"),
            "test_mode": False,
            **downloads,
        }

    async def extract_nfa_number(self) -> None:
        """Extract NFA number from the result page."""
        if not self.page:
            raise RuntimeError("Page not initialized.")

        logger.info("Extracting NFA number from result page")

        # Try multiple strategies to find NFA number
        # Strategy 1: Look for text patterns like "NFA: 900501884" or "Número: 900501884"
        nfa_patterns = [
            r'NFA[:\s]+(\d{9,15})',
            r'Número[:\s]+(\d{9,15})',
            r'Nota[:\s]+(\d{9,15})',
            r'(\d{9,15})',  # Any 9-15 digit number (fallback)
        ]

        page_text = await self.page.text_content("body") or ""

        for pattern in nfa_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                # Take the first match that looks like an NFA number (9-15 digits)
                for match in matches:
                    if 9 <= len(match) <= 15:
                        self.nfa_number = match
                        logger.info("Extracted NFA number from page text", extra={"payload": {"nfa_number": self.nfa_number}})
                        return

        # Strategy 2: Look in input fields or hidden fields
        try:
            nfa_inputs = self.page.locator('input[name*="nfa"], input[id*="nfa"], input[value*="9"]')
            count = await nfa_inputs.count()
            for i in range(count):
                try:
                    value = await nfa_inputs.nth(i).get_attribute("value")
                    if value and 9 <= len(value) <= 15 and value.isdigit():
                        self.nfa_number = value
                        logger.info("Extracted NFA number from input field", extra={"payload": {"nfa_number": self.nfa_number}})
                        return
                except Exception:
                    continue
        except Exception:
            pass

        # Strategy 3: Check URL for NFA number
        url = self.page.url
        url_matches = re.findall(r'(\d{9,15})', url)
        if url_matches:
            for match in url_matches:
                if 9 <= len(match) <= 15:
                    self.nfa_number = match
                    logger.info("Extracted NFA number from URL", extra={"payload": {"nfa_number": self.nfa_number}})
                    return

        logger.warning("Could not extract NFA number from result page", extra={"payload": {"url": url, "text_preview": page_text[:500]}})
        self.nfa_number = None

    async def run(self) -> Dict[str, Any]:
        """
        Execute full emission workflow.

        Returns:
            Dictionary with status, cpf, nfa_number, and emission_date
        """
        try:
            await self.setup()
            await self.login()
            # Don't navigate here - emit_one() will do it
            if not self.cpf:
                raise ValueError("Missing CPF")
            result = await self.emit_one(self.cpf)

            logger.info(
                "NFA emission completed",
                extra={"payload": {"status": result.get("status"), "cpf": (self.cpf[:3] + "***") if self.cpf else None}},
            )
            return result

        except ValueError as e:
            error_msg = str(e)
            logger.error("Emission failed (validation error)", exc_info=True, extra={"payload": {"error": error_msg}})
            return {
                "status": "error",
                "cpf": self.cpf,
                "message": error_msg,
            }
        except RuntimeError as e:
            error_msg = str(e)
            logger.error("Emission failed (runtime error)", exc_info=True, extra={"payload": {"error": error_msg}})
            return {
                "status": "error",
                "cpf": self.cpf,
                "message": error_msg,
            }
        except Exception as e:
            error_msg = str(e)
            logger.error("Emission failed (unexpected error)", exc_info=True, extra={"payload": {"error": error_msg}})
            return {
                "status": "error",
                "cpf": self.cpf,
                "message": error_msg,
            }
        finally:
            if self.keep_open and not self.headless:
                logger.info("Emission workflow completed - browser kept open", extra={"payload": {"headless": self.headless}})
                # Keep script running so browser stays open
                logger.info("Browser will remain open. Press Ctrl+C to exit.")
                try:
                    # Wait indefinitely to keep browser open
                    while True:
                        await asyncio.sleep(3600)  # Sleep for 1 hour, repeat
                except KeyboardInterrupt:
                    logger.info("Shutting down...")
                    await self.cleanup()
                return
            try:
                await self.cleanup()
            except Exception:
                pass

    async def cleanup(self) -> None:
        """Close browser and cleanup resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Browser closed")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="NFA Emission Automation")
    parser.add_argument("--cpf", required=True, help="CPF number (formatted or unformatted)")
    parser.add_argument("--loja", type=str, default=None, help="LOJA code for Informações Adicionais mapping (e.g., RN13, RO03). If not provided, uses default.")
    parser.add_argument("--test", action="store_true", default=False, help="Test mode (validate form but don't submit)")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run browser with UI")
    parser.add_argument("--output-dir", type=str, default="/Users/dnigga/Downloads/NFA_Outputs", help="Output directory for emitted PDFs")
    parser.add_argument("--keep-open", action="store_true", default=True, help="Keep browser open when visual (default: true)")
    parser.add_argument("--no-keep-open", dest="keep_open", action="store_false", help="Close browser at end")
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
        print(json.dumps(result))
        sys.exit(1)

    # Validate CPF
    if not validate_cpf(args.cpf):
        error_msg = f"Invalid CPF format: {args.cpf} (must be 11 digits)"
        logger.error(error_msg)
        result = {"status": "error", "message": error_msg}
        print(json.dumps(result))
        sys.exit(1)

    # Run automation
    automation = NFAEmitAutomation(
        username=username,
        password=password,
        cpf=args.cpf,
        loja_code=args.loja,
        test_mode=args.test,
        headless=args.headless,
        output_dir=args.output_dir,
        keep_open=args.keep_open,
    )

    result = await automation.run()
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
