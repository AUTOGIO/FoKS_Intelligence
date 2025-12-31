# NFA ATF Automation Script

This script automates the process of downloading NFA (Nota Fiscal Avulsa) documents from the ATF (Ambiente de Testes Fiscais) system.

## Overview

The script performs the following steps:
1. Logs into ATF (https://www4.sefaz.pb.gov.br/atf/)
2. Navigates to FIS_308 function
3. Fills filters (date range, matricula)
4. Selects NFA result
5. Downloads DANFE PDF (clicks "Imprimir" button) - **First action**
6. Downloads Taxa Serviço PDF (clicks "Taxa Serviço" button) - **Second action**

Both downloads execute in sequence for each NFA.

## Prerequisites

### Environment Variables

The script requires the following environment variables:

```bash
export NFA_USERNAME="your_username"
export NFA_PASSWORD="your_password"
```

### Dependencies

The script requires:
- Python 3.9+
- Playwright (`pip install playwright`)
- Playwright browsers (`playwright install chromium`)

## Usage

### Manual Execution

Run the script directly from the command line:

```bash
python3 /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/nfa/nfa_atf.py \
  --from-date "01/01/2024" \
  --to-date "31/01/2024" \
  --matricula "1595504" \
  --output-dir "/Users/dnigga/Downloads/NFA_Outputs"
```

### Arguments

- `--from-date` (required): Start date in `dd/mm/yyyy` format
- `--to-date` (required): End date in `dd/mm/yyyy` format
- `--matricula` (optional): Matricula number (defaults to value in `config.json`)
- `--output-dir` (optional): Output directory for PDFs (defaults to `/Users/dnigga/Downloads/NFA_Outputs`)
- `--headless` (default): Run browser in headless mode
- `--no-headless`: Run browser with visible UI (useful for debugging)
- `--nfa-number` (optional): Specific NFA number to select

### Output

The script outputs JSON to stdout:

```json
{
  "status": "success",
  "nfa_number": "900501884",
  "danfe_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_DANFE.pdf",
  "dar_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_TAXA_SERVICO.pdf"
}
```

**Note**: Both downloads (DANFE and Taxa Serviço) always execute in sequence for each NFA.

On error:

```json
{
  "status": "error",
  "error": "Error message here",
  "nfa_number": null,
  "danfe_path": null,
  "dar_path": null
}
```

## FoKS Integration

### Via TaskRunner

The script is integrated with FoKS TaskRunner. You can call it via the `/tasks/run` endpoint:

```bash
curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "nfa_atf",
    "params": {
      "from_date": "01/01/2024",
      "to_date": "31/01/2024",
      "matricula": "1595504",
      "output_dir": "/Users/dnigga/Downloads/NFA_Outputs"
    },
    "source": "shortcuts"
  }'
```

### Via Direct Router Endpoint

Alternatively, use the dedicated endpoint:

```bash
curl -X POST http://localhost:8000/tasks/nfa_atf/run \
  -H "Content-Type: application/json" \
  -d '{
    "from_date": "01/01/2024",
    "to_date": "31/01/2024",
    "matricula": "1595504",
    "output_dir": "/Users/dnigga/Downloads/NFA_Outputs"
  }'
```

## Configuration

Default settings can be modified in `config.json`:

```json
{
  "default_matricula": "1595504",
  "default_output_dir": "/Users/dnigga/Downloads/NFA_Outputs",
  "atf_base_url": "https://www4.sefaz.pb.gov.br/atf/",
  "timeout_seconds": 600,
  "wait_timeout_ms": 30000
}
```

## Troubleshooting

### Login Fails

- Verify `NFA_USERNAME` and `NFA_PASSWORD` environment variables are set
- Check if credentials are correct
- Try running with `--no-headless` to see what's happening

### Cannot Find Elements

- The ATF website may have changed its structure
- Run with `--no-headless` to inspect the page
- Check browser console for JavaScript errors

### Downloads Fail

- Ensure output directory exists and is writable
- Check disk space
- Verify browser download permissions

### Timeout Errors

- ATF can be slow; increase timeout in `config.json`
- Check network connection
- Try running during off-peak hours

## Architecture

This script follows **Architecture C**:

```
FoKS TaskRunner → executes nfa_atf.py → downloads PDFs → returns JSON
```

**Workflow**: For each NFA, the script:
1. Clicks "Imprimir" button → opens DANFE PDF viewer → waits for manual download
2. Clicks "Taxa Serviço" button → opens Taxa Serviço PDF viewer → waits for manual download

Both downloads execute in sequence automatically.

The script is:
- **Standalone**: Can run independently without FoKS
- **Async**: Uses Playwright async API
- **Type-safe**: Full type hints
- **Logged**: Uses FoKS logging_utils format
- **Error-handled**: Graceful error handling with clear messages

## Testing

Run tests:

```bash
pytest backend/tests/test_nfa_task_runner.py
pytest backend/tests/test_nfa_router.py
```

## Notes

- The script does NOT modify user settings
- The script does NOT require FBP backend
- All PDFs are saved to the specified output directory
- The script uses Playwright's `acceptDownloads=True` for reliable downloads

