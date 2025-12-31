# NFA ATF Automation Scripts

Scripts to run NFA ATF automation workflows for downloading PDFs.

## Available Scripts

### 1. `run_nfa_danfe.sh` - DANFE Only (Imprimir)
Downloads DANFE PDFs by clicking "Imprimir" button.

**Usage:**
```bash
# Default: 10 NFAs, date 08/12/2025, matrícula 1595504
./ops/scripts/run_nfa_danfe.sh

# Custom number of NFAs
./ops/scripts/run_nfa_danfe.sh 20

# Custom parameters: max_nfas from_date to_date matricula
./ops/scripts/run_nfa_danfe.sh 10 "08/12/2025" "08/12/2025" "1595504"
```

**What it does:**
- Logs in to ATF
- Navigates to FIS_308
- Fills filters and searches
- For each NFA: clicks "Imprimir" → waits 10 seconds for manual download → continues

---

### 2. `run_nfa_taxa_servico.sh` - Taxa Serviço Only (Gerar/Emitir Taxa Serviço)
Downloads Taxa Serviço PDFs by clicking "Gerar/Emitir Taxa Serviço" button.

**Usage:**
```bash
# Default: 10 NFAs, date 08/12/2025, matrícula 1595504
./ops/scripts/run_nfa_taxa_servico.sh

# Custom number of NFAs
./ops/scripts/run_nfa_taxa_servico.sh 20

# Custom parameters: max_nfas from_date to_date matricula
./ops/scripts/run_nfa_taxa_servico.sh 10 "08/12/2025" "08/12/2025" "1595504"
```

**What it does:**
- Logs in to ATF
- Navigates to FIS_308
- Fills filters and searches
- For each NFA: clicks "Gerar/Emitir Taxa Serviço" → waits 10 seconds for manual download → continues
- **Skips DANFE (Imprimir)**

---

### 3. `run_nfa_dar.sh` - DAR Only (Emitir DAR)
Downloads DAR PDFs by clicking "Emitir DAR" button.

**Usage:**
```bash
# Default: 10 NFAs, date 08/12/2025, matrícula 1595504
./ops/scripts/run_nfa_dar.sh

# Custom number of NFAs
./ops/scripts/run_nfa_dar.sh 20

# Custom parameters: max_nfas from_date to_date matricula
./ops/scripts/run_nfa_dar.sh 10 "08/12/2025" "08/12/2025" "1595504"
```

**What it does:**
- Logs in to ATF
- Navigates to FIS_308
- Fills filters and searches
- For each NFA: clicks "Emitir DAR" → waits 10 seconds for manual download → continues
- **Skips DANFE (Imprimir)**

---

## Workflow

### Typical Two-Step Process:

**Step 1: Download DANFE**
```bash
./ops/scripts/run_nfa_danfe.sh 10
```
- Clicks "Imprimir" for first 10 NFAs
- You manually click download in each PDF viewer tab (10 seconds per NFA)

**Step 2: Download Taxa Serviço**
```bash
./ops/scripts/run_nfa_taxa_servico.sh 10
```
- Logs in again
- Clicks "Gerar/Emitir Taxa Serviço" for first 10 NFAs
- You manually click download in each PDF viewer tab (10 seconds per NFA)

---

## Parameters

All scripts accept the same parameters (in order):

1. **max_nfas** (default: 10) - Number of NFAs to process
2. **from_date** (default: "08/12/2025") - Start date in dd/mm/yyyy format
3. **to_date** (default: "08/12/2025") - End date in dd/mm/yyyy format
4. **matricula** (default: "1595504") - Matrícula number

---

## Requirements

- FoKS backend running on `http://localhost:8000`
- Environment variables set:
  - `NFA_USERNAME` - ATF login username
  - `NFA_PASSWORD` - ATF login password
- `jq` installed (for JSON formatting in output)

---

## Notes

- Browser runs in **visual mode** (headless=false) so you can see and interact
- Each PDF download has a **10-second wait** for manual download click
- Browser stays open after completion for inspection
- All PDFs are saved to `/Users/dnigga/Downloads/NFA_Outputs/`

---

## Quick Reference

```bash
# DANFE only (10 NFAs)
./ops/scripts/run_nfa_danfe.sh

# Taxa Serviço only (10 NFAs)
./ops/scripts/run_nfa_taxa_servico.sh

# DAR only (10 NFAs)
./ops/scripts/run_nfa_dar.sh

# Custom: 20 NFAs, different date
./ops/scripts/run_nfa_danfe.sh 20 "01/12/2025" "31/12/2025" "1595504"
```
