#!/bin/bash
# Execute NFA trigger workflow for multiple CPFs from CSV
# Usage: ./execute_nfa_batch.sh [csv_file]

BASE_URL="${FOKS_BASE_URL:-http://localhost:8000}"
ENDPOINT="${BASE_URL}/tasks/nfa"

# CSV file path (default or from argument)
CSV_FILE="${1:-/Volumes/MICRO/downloads_MICRO/CADASTRO GERAL ATUALIZADO ENDEREÇOS DOSADORAS.csv}"

echo "=========================================="
echo "NFA TRIGGER BATCH EXECUTION"
echo "=========================================="
echo "Endpoint: ${ENDPOINT}"
echo "CSV File: ${CSV_FILE}"
echo ""

# Check if CSV file exists
if [ ! -f "$CSV_FILE" ]; then
    echo "❌ ERROR: CSV file not found: ${CSV_FILE}"
    exit 1
fi

# Check if server is running
if ! curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
    echo "❌ ERROR: FoKS server is not running at ${BASE_URL}"
    echo "   Please start the server first:"
    echo "   cd backend && uvicorn app.main:app --reload"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Extract CPF and LOJA from CSV (column 2 = LOJA, column 4 = CPF)
# Skip header and empty lines
declare -a items=()
while IFS=',' read -r col1 loja desc cpf rest; do
    # Skip empty lines and header
    if [ -z "$cpf" ] || [[ "$cpf" =~ ^[^0-9] ]]; then
        continue
    fi
    
    # Clean CPF (remove spaces, ensure proper format)
    cpf_clean=$(echo "$cpf" | tr -d ' ' | tr -d '"')
    
    # Validate CPF format (should have dots and dash)
    if [[ "$cpf_clean" =~ ^[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}$ ]]; then
        loja_clean=$(echo "$loja" | tr -d ' ' | tr -d '"')
        items+=("${loja_clean}|${cpf_clean}")
    fi
done < "$CSV_FILE"

total_items=${#items[@]}
echo "📊 Found ${total_items} valid CPF entries in CSV"
echo ""

if [ $total_items -eq 0 ]; then
    echo "❌ ERROR: No valid CPF entries found in CSV"
    exit 1
fi

# Show first 5 entries as preview
echo "Preview (first 5 entries):"
for i in "${!items[@]}"; do
    if [ $i -lt 5 ]; then
        IFS='|' read -r loja cpf <<< "${items[$i]}"
        echo "  ${i}: LOJA=${loja}, CPF=${cpf}"
    fi
done
if [ $total_items -gt 5 ]; then
    echo "  ... and $((total_items - 5)) more"
fi
echo ""

# Ask for confirmation if more than 10 items (skip if --yes flag provided)
if [ "$2" != "--yes" ] && [ "$2" != "-y" ]; then
    if [ $total_items -gt 10 ]; then
        read -p "Process ${total_items} items? (y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
    fi
else
    echo "⏩ Auto-confirmed (--yes flag provided)"
fi

results_file=$(mktemp)
success_count=0
fail_count=0

echo "=========================================="
echo "PROCESSING ${total_items} ITEMS"
echo "=========================================="
echo ""

for i in "${!items[@]}"; do
    IFS='|' read -r loja cpf <<< "${items[$i]}"
    
    item_num=$((i + 1))
    echo "[${item_num}/${total_items}] Processing: ${loja}"
    echo "  CPF: ${cpf}"
    
    # Make POST request
    response=$(curl -s -w "\n%{http_code}" -X POST "${ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{\"cpf\": \"${cpf}\", \"test\": false}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    # Parse response
    success=$(echo "$body" | grep -o '"success":[^,}]*' | cut -d':' -f2 | tr -d ' ' || echo "false")
    message=$(echo "$body" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 || echo "No message")
    
    if [ "$http_code" = "200" ] && [ "$success" = "true" ]; then
        echo "  ✅ SUCCESS: ${message}"
        ((success_count++))
    else
        echo "  ❌ FAILED: ${message:-HTTP ${http_code}}"
        if [ "$http_code" != "200" ]; then
            echo "  Response body: ${body:0:200}"
        fi
        ((fail_count++))
    fi
    
    # Save result
    echo "{\"loja\": \"${loja}\", \"cpf\": \"${cpf}\", \"http_code\": ${http_code}, \"success\": ${success}, \"message\": \"${message}\"}" >> "$results_file"
    
    echo ""
    
    # Small delay between requests to avoid overwhelming the server
    sleep 1
done

echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo "✅ Successful: ${success_count}"
echo "❌ Failed: ${fail_count}"
echo "📊 Total: ${total_items}"
echo ""

# Output JSON results
echo "Detailed Results (JSON):"
if command -v jq &> /dev/null; then
    cat "$results_file" | jq -s '.'
else
    cat "$results_file"
fi

# Save results to file
results_output="/Users/dnigga/Downloads/nfa_batch_results_$(date +%Y%m%d_%H%M%S).json"
cat "$results_file" | jq -s '.' > "$results_output" 2>/dev/null || cat "$results_file" > "$results_output"
echo ""
echo "📁 Results saved to: ${results_output}"

rm -f "$results_file"
