#!/usr/bin/env bash
# Teste das novas tasks adicionadas

BASE_URL="http://localhost:8001"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Testando novas tasks...${NC}"
echo

# Test 1: Notification
echo -e "${YELLOW}[TEST] Notification${NC}"
curl -s -X POST "$BASE_URL/tasks/run" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "notification",
    "params": {
      "title": "FoKS Test",
      "message": "Nova funcionalidade funcionando!",
      "subtitle": "Sucesso"
    },
    "source": "test"
  }' | python3 -m json.tool
echo

# Test 2: Get Clipboard
echo -e "${YELLOW}[TEST] Get Clipboard${NC}"
curl -s -X POST "$BASE_URL/tasks/run" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "get_clipboard",
    "params": {},
    "source": "test"
  }' | python3 -m json.tool
echo

# Test 3: Set Clipboard
echo -e "${YELLOW}[TEST] Set Clipboard${NC}"
curl -s -X POST "$BASE_URL/tasks/run" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "set_clipboard",
    "params": {"text": "FoKS Intelligence test"},
    "source": "test"
  }' | python3 -m json.tool
echo

# Test 4: Open App
echo -e "${YELLOW}[TEST] Open App${NC}"
curl -s -X POST "$BASE_URL/tasks/run" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "open_app",
    "params": {"app": "Notes"},
    "source": "test"
  }' | python3 -m json.tool
echo

# Test 5: Screenshot (comentado - requer interação)
echo -e "${YELLOW}[TEST] Screenshot (skipped - requires interaction)${NC}"
echo "Para testar manualmente:"
echo 'curl -X POST http://localhost:8001/tasks/run -H "Content-Type: application/json" -d '"'"'{"task_name": "screenshot", "params": {"type": "full"}}'"'"''
echo

echo -e "${GREEN}Testes concluídos!${NC}"

