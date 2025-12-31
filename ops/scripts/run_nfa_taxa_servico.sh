#!/bin/bash
# Run NFA ATF automation - Taxa Serviço only (Gerar/Emitir Taxa Serviço button)
# Processes first N NFAs (default: 10)
# NOTE: This skips DANFE (Imprimir) and only clicks Taxa Serviço

set -e

# Default values
MAX_NFAS=${1:-10}
FROM_DATE=${2:-"08/12/2025"}
TO_DATE=${3:-"08/12/2025"}
MATRICULA=${4:-"1595504"}

echo "🔹 Running NFA ATF Automation - Taxa Serviço Only (Gerar/Emitir Taxa Serviço)"
echo "   Max NFAs: $MAX_NFAS"
echo "   Date Range: $FROM_DATE to $TO_DATE"
echo "   Matrícula: $MATRICULA"
echo ""

curl -X POST http://localhost:8000/tasks/run \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"nfa_atf\",
    \"args\": {
      \"from_date\": \"$FROM_DATE\",
      \"to_date\": \"$TO_DATE\",
      \"matricula\": \"$MATRICULA\",
      \"max_nfas\": $MAX_NFAS,
      \"download_dar\": false,
      \"download_taxa_servico\": true
    }
  }" | jq '.'

echo ""
echo "✅ Automation completed"
