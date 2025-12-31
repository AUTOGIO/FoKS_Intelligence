#!/bin/bash
# Run NFA ATF automation - DAR only (Emitir DAR button)
# Processes first N NFAs (default: 10)
# NOTE: This skips DANFE (Imprimir) and only clicks Emitir DAR

set -e

# Default values
MAX_NFAS=${1:-10}
FROM_DATE=${2:-"08/12/2025"}
TO_DATE=${3:-"08/12/2025"}
MATRICULA=${4:-"1595504"}

echo "🔹 Running NFA ATF Automation - DAR Only (Emitir DAR)"
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
      \"download_dar\": true,
      \"download_taxa_servico\": false
    }
  }" | jq '.'

echo ""
echo "✅ Automation completed"
