# NFA Automation Specification - SEFAZ-PB ATF Portal

**Target System:** ATF / SEFAZ-PB – Paraíba State Tax Portal  
**Main Function:** FIS_308 – Consultar Notas Fiscais Avulsas  
**Automation Tool:** Playwright for Python  
**Output Directory:** `/Users/dnigga/Downloads/NFA_Outputs`

---

## 📋 Overview

This specification defines the exact automation flow for downloading NFA (Nota Fiscal Avulsa) PDFs (DANFE + DAR) from the SEFAZ-PB ATF portal.

---

## 🔐 Authentication

### Login Form (`FormLogin`)

**URL:** `https://www4.sefaz.pb.gov.br/atf/`

**Selectors:**
- Username: `input[name="edtNoLogin"]`
- Password: `input[name="edtDsSenha"]`
- Submit: `button[name="btnAvancar"]`

**Flow:**
1. Navigate to ATF URL
2. Wait for login form (`input[name="edtNoLogin"]`)
3. Fill username
4. Fill password
5. Click submit button
6. Wait for navigation to complete

**Credentials:**
- Must come from environment variables: `NFA_USERNAME`, `NFA_PASSWORD`
- Never hard-code in repository

---

## 🧭 Navigation to FIS_308

### Function Search Field

**Selector:** `input[name="edtFuncao"]`

**Flow:**
1. Wait for function input field
2. Fill with: `fis_308`
3. Press `Enter` key
4. Wait for page load/navigation

**Expected Result:**
- Page navigates to FIS_308 function
- Main content may be in iframe (see Iframe Handling)

---

## 📝 Consultation Form

### Date Range Inputs

**Selectors:**
- Initial Date: `input[name="edtDtEmissaoNfaeInicial"]`
- Final Date: `input[name="edtDtEmissaoNfaeFinal"]`

**Format:** `dd/mm/yyyy` (e.g., `08/12/2025`)

### Funcionário Emitente (Matrícula)

**Primary Approach:**
- Hidden field: `input[name="hidnrMatriculacmpFuncEmitente"]`
- If hidden field exists, set value directly

**Fallback Approach (Component Iframe):**
- Look for iframe containing `cmpFuncEmitente` in URL
- Within component iframe:
  - Fill: `input[type="text"]` (matrícula field)
  - Click: `input[type="submit"][value="Pesquisar"]`

**Default Matrícula:** `1595504`

### Submit Consultation

**Selector:** `input[name="btnConsultar"]`

**Flow:**
1. Fill initial date
2. Fill final date
3. Fill/set matrícula
4. Click "Consultar" button
5. Wait for navigation/load
6. Wait for results table to appear

---

## 📊 Results Selection

### Radio Button Selection

**Selector:** `input[type="radio"]` (first available)

**Flow:**
1. Wait for radio buttons to appear
2. Count available radio buttons
3. If count == 0: raise error "Nenhuma NFA encontrada"
4. Select first radio button: `input[type="radio"]`.first
5. Click the radio button

### Extract NFA Number

**Heuristic:**
- After selecting radio, find closest `<tr>` element
- Extract all `<td>` innerText values
- Look for text that:
  - Is all digits
  - Has length >= 6
- Use first matching number as NFA number

**Fallback:**
- If extraction fails, use `"UNKNOWN"` in filename

---

## 📥 PDF Downloads

### Download Location

**Directory:** `/Users/dnigga/Downloads/NFA_Outputs`  
**Must exist and be writable**

### Filename Pattern

- DANFE: `NFA_{NUMERO}_DANFE.pdf`
- DAR: `NFA_{NUMERO}_DAR.pdf`
- If NFA number unknown: `NFA_UNKNOWN_DANFE.pdf`

### Download Actions

**Critical:** Always use `wait_for_event("download")` before clicking download buttons.

#### 1. DANFE Download

**Button Selector:** `input[type='button'][value='Imprimir']`

**Flow:**
1. Set up download event listener: `context.expect_event("download")`
2. Click "Imprimir" button
3. Wait for download event
4. Save download to: `NFA_{NUMERO}_DANFE.pdf`

#### 2. DAR Download

**Button Selectors:**
- Primary: `input[type='button'][value*='Emitir DAR']`
- Alternative: `input[type='button'][value*='Taxa Serviço']`

**Flow:**
1. Set up download event listener: `context.expect_event("download")`
2. Click DAR button (try primary, fallback to alternative)
3. Wait for download event
4. Save download to: `NFA_{NUMERO}_DAR.pdf`

---

## 🖼️ Iframe Handling

### Main Content Frame

**Detection:**
- Check if main content is in iframe
- Look for frame with URL containing: `FIS_` or `FISf_ConsultarNotasFiscaisAvulsas`
- If found, use frame for all interactions
- If not found, use main page

**Function:**
```python
async def _get_main_frame(page: Page) -> Page:
    # Check all frames
    for frame in page.frames:
        if "FIS_" in (frame.url or "") or "FISf_ConsultarNotasFiscaisAvulsas" in (frame.url or ""):
            return frame
    return page  # Fallback to main page
```

### Component Iframes

**Example:** `cmpFuncEmitente`

- May be in separate iframe
- Look for frame with URL containing component name
- Interact within component iframe
- Return to main frame after interaction

---

## ⚙️ Browser Configuration

### Context Settings

```python
context = await browser.new_context(
    accept_downloads=True,  # CRITICAL for PDF downloads
    viewport={"width": 1920, "height": 1080},
)
```

### Launch Options

```python
browser = await playwright.chromium.launch(
    headless=True,  # Configurable
    args=["--disable-blink-features=AutomationControlled"],
)
```

### Timeouts

- Default navigation: 30 seconds
- Download wait: 30 seconds
- Element wait: 10 seconds

---

## 🔄 Retry Logic

### Transient Failures

**Retry on:**
- Timeout errors
- Network errors
- Delayed rendering (element not found immediately)

**Strategy:**
- Max 2 retries per critical step
- Exponential backoff: 1s, 2s
- Critical steps:
  - Login
  - Form submission
  - Result selection
  - Download actions

---

## 📝 Logging

### JSONL Log File

**Location:** `/Users/dnigga/Downloads/NFA_Outputs/nfa_runs.jsonl`

**Format:** One JSON object per line

**Fields:**
```json
{
  "started_at": "2025-12-11T04:22:02.123456",
  "finished_at": "2025-12-11T04:22:45.789012",
  "status": "ok",
  "nfa_numero": "900501884",
  "danfe_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_DANFE.pdf",
  "dar_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_DAR.pdf",
  "error": null
}
```

**Error Format:**
```json
{
  "started_at": "2025-12-11T04:22:02.123456",
  "finished_at": "2025-12-11T04:22:15.789012",
  "status": "error",
  "nfa_numero": null,
  "danfe_path": null,
  "dar_path": null,
  "error": "Login failed: Invalid credentials"
}
```

---

## ✅ Return Value

### Success Response

```python
{
    "status": "ok",
    "nfa_numero": "900501884",
    "danfe_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_DANFE.pdf",
    "dar_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_DAR.pdf",
    "started_at": "2025-12-11T04:22:02.123456",
    "finished_at": "2025-12-11T04:22:45.789012",
    "error": None
}
```

### Error Response

```python
{
    "status": "error",
    "nfa_numero": None,
    "danfe_path": None,
    "dar_path": None,
    "started_at": "2025-12-11T04:22:02.123456",
    "finished_at": "2025-12-11T04:22:15.789012",
    "error": "Error message here"
}
```

---

## 🔍 Error Handling

### Common Errors

1. **Login Failed**
   - Check credentials
   - Verify network connection
   - Check for CAPTCHA (manual intervention required)

2. **No Results Found**
   - Verify date range
   - Check matrícula
   - Confirm NFA exists for period

3. **Download Timeout**
   - Increase download timeout
   - Check network connection
   - Verify button selectors

4. **Iframe Not Found**
   - Page structure may have changed
   - Fallback to main page interactions
   - Log warning for manual review

---

## 🧪 Testing Checklist

- [ ] Login with valid credentials
- [ ] Login with invalid credentials (error handling)
- [ ] Navigate to FIS_308
- [ ] Fill consultation form
- [ ] Handle no results scenario
- [ ] Select first NFA result
- [ ] Download DANFE PDF
- [ ] Download DAR PDF
- [ ] Handle iframe navigation
- [ ] Retry on transient failures
- [ ] Log to JSONL file
- [ ] Return structured JSON

---

## 📚 References

- Playwright Python API: https://playwright.dev/python/
- SEFAZ-PB ATF Portal: https://www4.sefaz.pb.gov.br/atf/
- FoKS Intelligence Architecture: `docs/ARCHITECTURE.md`

---

**Last Updated:** 2025-12-11  
**Status:** ✅ Specification Complete
