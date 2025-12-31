#!/bin/bash
# NFA Trigger Batch Commands
# Execute these commands after starting the FoKS server

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "NFA TRIGGER BATCH COMMANDS"
echo "=========================================="
echo ""
echo "Make sure FoKS server is running:"
echo "  cd backend && uvicorn app.main:app --reload"
echo ""
echo "Then execute these commands:"
echo ""

# Item 1
echo "# 1. SP228 - CPF: 228.240.248-01"
echo "curl -X POST ${BASE_URL}/tasks/nfa \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"cpf\": \"228.240.248-01\", \"test\": false}'"
echo ""

# Item 2
echo "# 2. SP233 - CPF: 113.684.248.99"
echo "# ⚠️  Note: Format might be incorrect, should be 113.684.248-99"
echo "curl -X POST ${BASE_URL}/tasks/nfa \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"cpf\": \"113.684.248.99\", \"test\": false}'"
echo ""

# Item 3
echo "# 3. SP242 - CPF: 512.810.178-92"
echo "curl -X POST ${BASE_URL}/tasks/nfa \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"cpf\": \"512.810.178-92\", \"test\": false}'"
echo ""

echo "=========================================="
echo "Or use the batch script:"
echo "  bash ops/scripts/execute_nfa_batch.sh"
echo "=========================================="
