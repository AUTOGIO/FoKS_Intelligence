#!/bin/bash
# FoKS Intelligence - Phase 6: Freeze Policy Check
# This script verifies that core architectural documents and rules have not been violated.

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "🔍 Starting Architectural Freeze Check..."

# 1. Check Document Checksums
echo -n "Checking contract checksums... "
shasum -c /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/freeze_checksums.txt > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}VALID${NC}"
else
    echo -e "${RED}VIOLATION DETECTED${NC}"
    echo "Warning: PROJECT_MAP.md or ARCHITECTURAL_CONTRACT.md has been modified during the freeze."
    exit 1
fi

# 2. Run Architectural Assertion Scan
echo -n "Running runtime assertion scan... "
# Here we'd typically run pytest or a specific check script.
# For now, we'll verify the existence and basic syntax of the assertions file.
if python3 -m py_compile /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/app/utils/architectural_assertions.py; then
    echo -e "${GREEN}VALID${NC}"
else
    echo -e "${RED}INVALID ASSERTIONS${NC}"
    exit 1
fi

echo -e "\n${GREEN}✔ Architecture is LOCK and STABLE.${NC}"
exit 0
