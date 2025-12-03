#!/usr/bin/env bash
# Script de teste completo para FoKS Intelligence

set -e

BASE_URL="http://localhost:8001"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  FoKS Intelligence - Test Suite"
echo "=========================================="
echo

# Test 1: Health Check
echo -e "${YELLOW}[TEST 1]${NC} Health Check"
response=$(curl -s "$BASE_URL/health")
if echo "$response" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✅ PASS${NC}"
    echo "$response" | python3 -m json.tool
else
    echo -e "${RED}❌ FAIL${NC}"
    echo "$response"
fi
echo

# Test 2: Chat Endpoint
echo -e "${YELLOW}[TEST 2]${NC} Chat Endpoint"
response=$(curl -s -X POST "$BASE_URL/chat/" \
    -H "Content-Type: application/json" \
    -d '{
        "message": "Responda apenas: OK, funcionando!",
        "source": "test_script",
        "input_type": "text"
    }')

if echo "$response" | grep -q '"reply"'; then
    echo -e "${GREEN}✅ PASS${NC}"
    echo "$response" | python3 -m json.tool | head -10
else
    echo -e "${RED}❌ FAIL${NC}"
    echo "$response"
fi
echo

# Test 3: Vision Endpoint (Placeholder)
echo -e "${YELLOW}[TEST 3]${NC} Vision Endpoint"
response=$(curl -s -X POST "$BASE_URL/vision/analyze" \
    -H "Content-Type: application/json" \
    -d '{
        "description": "Test image description",
        "source": "test_script"
    }')

if echo "$response" | grep -q '"summary"'; then
    echo -e "${GREEN}✅ PASS${NC}"
    echo "$response" | python3 -m json.tool
else
    echo -e "${RED}❌ FAIL${NC}"
    echo "$response"
fi
echo

# Test 4: Tasks Endpoint - Say
echo -e "${YELLOW}[TEST 4]${NC} Tasks Endpoint - Say"
response=$(curl -s -X POST "$BASE_URL/tasks/run" \
    -H "Content-Type: application/json" \
    -d '{
        "task_name": "say",
        "params": {"text": "Teste de voz"},
        "source": "test_script"
    }')

if echo "$response" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ PASS${NC}"
    echo "$response" | python3 -m json.tool
else
    echo -e "${RED}❌ FAIL${NC}"
    echo "$response"
fi
echo

# Test 5: Tasks Endpoint - Open URL
echo -e "${YELLOW}[TEST 5]${NC} Tasks Endpoint - Open URL"
response=$(curl -s -X POST "$BASE_URL/tasks/run" \
    -H "Content-Type: application/json" \
    -d '{
        "task_name": "open_url",
        "params": {"url": "https://www.apple.com"},
        "source": "test_script"
    }')

if echo "$response" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ PASS${NC}"
    echo "$response" | python3 -m json.tool
else
    echo -e "${RED}❌ FAIL${NC}"
    echo "$response"
fi
echo

# Test 6: Invalid Task
echo -e "${YELLOW}[TEST 6]${NC} Invalid Task (should fail gracefully)"
response=$(curl -s -X POST "$BASE_URL/tasks/run" \
    -H "Content-Type: application/json" \
    -d '{
        "task_name": "invalid_task",
        "params": {},
        "source": "test_script"
    }')

if echo "$response" | grep -q '"success":false'; then
    echo -e "${GREEN}✅ PASS${NC} (failed as expected)"
    echo "$response" | python3 -m json.tool
else
    echo -e "${RED}❌ FAIL${NC}"
    echo "$response"
fi
echo

echo "=========================================="
echo -e "${GREEN}Test Suite Complete!${NC}"
echo "=========================================="

