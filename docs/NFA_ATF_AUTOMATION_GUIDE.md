# NFA ATF Automation Guide

Complete guide for running NFA ATF automation workflows with customizable parameters.

---

## 📋 Quick Reference

### Workflow 1: DANFE (Imprimir) - First Run
Downloads DANFE PDFs for selected NFAs.

### Workflow 2: Taxa Serviço (Emitir Taxa Serviço) - Second Run
Downloads Taxa Serviço PDFs for selected NFAs.

---

## 🚀 Exact Scripts to Run

### 1. DANFE Workflow (Imprimir)

```bash
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "type": "nfa_atf",
    "args": {
      "from_date": "08/12/2025",
      "to_date": "08/12/2025",
      "matricula": "1595504",
      "max_nfas": 10,
      "download_dar": false
    }
  }'
```

**What it does:**
- Logs into ATF portal
- Navigates to FIS_308
- Applies date range and matrícula filters
- Selects first 10 NFAs
- Clicks "Imprimir" for each NFA
- Waits 10 seconds per NFA for manual download
- Browser stays open after completion

---

### 2. Taxa Serviço Workflow (Emitir Taxa Serviço)

```bash
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "type": "nfa_atf",
    "args": {
      "from_date": "08/12/2025",
      "to_date": "08/12/2025",
      "matricula": "1595504",
      "max_nfas": 10,
      "download_dar": true
    }
  }'
```

**What it does:**
- Logs into ATF portal (fresh login)
- Navigates to FIS_308
- Applies date range and matrícula filters
- Selects first 10 NFAs
- Clicks "Gerar/Emitir Taxa Serviço" for each NFA
- Waits 10 seconds per NFA for manual download
- Browser stays open after completion

---

## ⚙️ How to Customize Parameters

### 1. Change Date Range

**Format:** `dd/mm/yyyy` (day/month/year)

**Example - Single Day:**
```json
"from_date": "08/12/2025",
"to_date": "08/12/2025"
```

**Example - Date Range (Multiple Days):**
```json
"from_date": "01/12/2025",
"to_date": "31/12/2025"
```

**Example - Last Week:**
```json
"from_date": "05/12/2025",
"to_date": "12/12/2025"
```

---

### 2. Change Matrícula

**Format:** Numeric string (no dashes or dots)

**Current:**
```json
"matricula": "1595504"
```

**To change:** Replace with your matrícula number
```json
"matricula": "1234567"
```

---

### 3. Change Number of NFAs

**Format:** Integer (number of NFAs to process)

**Current:**
```json
"max_nfas": 10
```

**Examples:**
```json
"max_nfas": 1      // Process only first NFA
"max_nfas": 5      // Process first 5 NFAs
"max_nfas": 20     // Process first 20 NFAs
"max_nfas": 100    // Process first 100 NFAs (if available)
```

**Note:** The script will process up to the number specified, but won't exceed the total available NFAs in the search results.

---

### 4. Change Workflow Type

**DANFE Only (Imprimir):**
```json
"download_dar": false
```

**Taxa Serviço Only (Emitir Taxa Serviço):**
```json
"download_dar": true
```

---

## 📝 Complete Customizable Template

```bash
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "type": "nfa_atf",
    "args": {
      "from_date": "DD/MM/YYYY",      # ⬅️ CHANGE START DATE
      "to_date": "DD/MM/YYYY",        # ⬅️ CHANGE END DATE
      "matricula": "1234567",         # ⬅️ CHANGE MATRÍCULA
      "max_nfas": 10,                 # ⬅️ CHANGE NUMBER OF NFAs
      "download_dar": false           # ⬅️ false = DANFE, true = Taxa Serviço
    }
  }'
```

---

## 🎯 Common Use Cases

### Process All NFAs from Last Month

```bash
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "type": "nfa_atf",
    "args": {
      "from_date": "01/11/2025",
      "to_date": "30/11/2025",
      "matricula": "1595504",
      "max_nfas": 100,
      "download_dar": false
    }
  }'
```

### Process Single NFA (Quick Test)

```bash
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "type": "nfa_atf",
    "args": {
      "from_date": "08/12/2025",
      "to_date": "08/12/2025",
      "matricula": "1595504",
      "max_nfas": 1,
      "download_dar": false
    }
  }'
```

### Process Specific NFA by Number

```bash
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "type": "nfa_atf",
    "args": {
      "from_date": "08/12/2025",
      "to_date": "08/12/2025",
      "matricula": "1595504",
      "nfa_number": "900501884",
      "max_nfas": 1,
      "download_dar": false
    }
  }'
```

---

## ⏱️ Timing Information

- **Per NFA:** ~10-15 seconds (10s wait + processing time)
- **10 NFAs:** ~2-3 minutes
- **50 NFAs:** ~8-12 minutes
- **100 NFAs:** ~15-25 minutes

**Note:** Times include the 10-second manual download wait per NFA.

---

## 🔍 Response Format

### Success Response

```json
{
  "task": "nfa_atf",
  "success": true,
  "duration_ms": 124271,
  "payload": {
    "status": "success",
    "nfa_number": "786463388",
    "danfe_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_786463388_DANFE.pdf",
    "dar_path": null,
    "processed_count": 10,
    "all_results": [
      {
        "nfa_number": "786463388",
        "danfe_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_786463388_DANFE.pdf",
        "dar_path": null
      },
      // ... more results
    ]
  }
}
```

### Error Response

```json
{
  "task": "nfa_atf",
  "success": false,
  "duration_ms": 5000,
  "payload": {
    "status": "error",
    "message": "Login failed"
  }
}
```

---

## 📁 Output Location

All PDFs are saved to:
```
/Users/dnigga/Downloads/NFA_Outputs/
```

**File naming:**
- DANFE: `NFA_<NUMERO>_DANFE.pdf`
- Taxa Serviço: `NFA_<NUMERO>_DAR.pdf`

---

## 🔧 Environment Variables Required

Make sure these are set in your environment:

```bash
export NFA_USERNAME="your_username"
export NFA_PASSWORD="your_password"
```

---

## 🐛 Troubleshooting

### Browser Not Opening
- Check if backend is running: `curl http://localhost:8000/health`
- Verify Playwright is installed: `playwright --version`

### Login Fails
- Verify `NFA_USERNAME` and `NFA_PASSWORD` are set correctly
- Check credentials are valid

### No Results Found
- Verify date range is correct (format: `dd/mm/yyyy`)
- Check matrícula number is correct
- Ensure NFAs exist for the specified date range

### Timeout Errors
- Increase timeout in `task_runner.py` (currently 900s = 15 minutes)
- Process fewer NFAs per run (reduce `max_nfas`)

---

## 📚 Related Files

- **Script:** `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/nfa/nfa_atf.py`
- **Task Runner:** `/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/app/services/task_runner.py`
- **API Endpoint:** `http://localhost:8000/tasks/run`

---

## ✅ Quick Checklist

Before running:
- [ ] Backend is running (`http://localhost:8000`)
- [ ] Environment variables set (`NFA_USERNAME`, `NFA_PASSWORD`)
- [ ] Date format is correct (`dd/mm/yyyy`)
- [ ] Matrícula number is correct
- [ ] `max_nfas` is set appropriately
- [ ] `download_dar` flag matches desired workflow

---

**Last Updated:** 2025-12-12
**Version:** 1.0
