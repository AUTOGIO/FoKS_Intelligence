#!/bin/bash
# NFA ATF Automation - Taxa Serviço (Gerar/Emitir Taxa Serviço) Workflow
# Downloads Taxa Serviço PDFs for NFAs

curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "type": "nfa_atf",
    "args": {
      "from_date": "08/12/2025",
      "to_date": "08/12/2025",
      "matricula": "1595504",
      "max_nfas": 10,
      "download_dar": false,
      "download_taxa_servico": true,
      "headless": false
    }
  }'
