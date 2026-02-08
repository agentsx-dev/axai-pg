#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track if any check fails
FAILED=0

# Print header
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Running CI Checks Locally${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Function to run a check and track failures
run_check() {
    local name="$1"
    local command="$2"
    
    echo -e "\n${YELLOW}[1/4] Running: ${name}${NC}"
    echo -e "${BLUE}Command: ${command}${NC}\n"
    
    eval "$command"
    local status=$?
    
    if [ $status -eq 0 ]; then
        echo -e "\n${GREEN}✓ ${name} passed${NC}"
    else
        echo -e "\n${RED}✗ ${name} failed${NC}"
        FAILED=1
    fi
    
    return $status
}

# Check if hatch is available
if ! command -v hatch &> /dev/null; then
    echo -e "${RED}Error: hatch is not installed${NC}"
    echo -e "${YELLOW}Install with: pip install hatch${NC}"
    exit 1
fi

# Ensure hatch environment is created
echo -e "${BLUE}Ensuring hatch environment is set up...${NC}"
hatch env create > /dev/null 2>&1

# Run formatting check (black --check)
run_check "Formatting Check (black)" "hatch run lint:check"

# Run type checking
run_check "Type Checking (mypy)" "hatch run types:check"

# Check if PostgreSQL is needed for tests
if docker-compose -f docker-compose.standalone-test.yml ps postgres 2>/dev/null | grep -q "Up"; then
    echo -e "\n${GREEN}PostgreSQL container is running${NC}"
    DB_RUNNING=1
else
    echo -e "\n${YELLOW}PostgreSQL container is not running${NC}"
    echo -e "${BLUE}Starting PostgreSQL container...${NC}"
    docker-compose -f docker-compose.standalone-test.yml up -d postgres
    
    # Wait for PostgreSQL to be ready
    echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
    for i in {1..30}; do
        if docker-compose -f docker-compose.standalone-test.yml exec postgres pg_isready -U test_user -d test_db > /dev/null 2>&1; then
            echo -e "${GREEN}PostgreSQL is ready!${NC}"
            DB_RUNNING=1
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}PostgreSQL failed to start within 30 seconds${NC}"
            FAILED=1
            DB_RUNNING=0
        fi
        sleep 1
    done
fi

# Run tests if DB is available
if [ $DB_RUNNING -eq 1 ]; then
    echo -e "\n${YELLOW}[3/4] Running: Tests${NC}"
    echo -e "${BLUE}Command: hatch run test${NC}\n"
    
    export TEST_DATABASE_URL="postgresql://test_user:test_password@localhost:5432/test_db"
    export POSTGRES_HOST=localhost
    export POSTGRES_PORT=5432
    export POSTGRES_DB=test_db
    export POSTGRES_USER=test_user
    export POSTGRES_PASSWORD=test_password
    export POSTGRES_SCHEMA=public
    
    hatch run test
    TEST_STATUS=$?
    
    if [ $TEST_STATUS -eq 0 ]; then
        echo -e "\n${GREEN}✓ Tests passed${NC}"
    else
        echo -e "\n${RED}✗ Tests failed${NC}"
        FAILED=1
    fi
else
    echo -e "\n${YELLOW}[3/4] Skipping: Tests (PostgreSQL not available)${NC}"
fi

# Summary
echo -e "\n${BLUE}========================================${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed! ✓${NC}"
    echo -e "${BLUE}========================================${NC}\n"
    exit 0
else
    echo -e "${RED}Some checks failed ✗${NC}"
    echo -e "${BLUE}========================================${NC}\n"
    echo -e "${YELLOW}To fix formatting issues, run:${NC}"
    echo -e "  ${BLUE}hatch run lint:fmt${NC}"
    echo -e "\n${YELLOW}To run individual checks:${NC}"
    echo -e "  ${BLUE}hatch run lint:check${NC}    # Formatting check"
    echo -e "  ${BLUE}hatch run lint:fmt${NC}       # Auto-format code"
    echo -e "  ${BLUE}hatch run types:check${NC}    # Type checking"
    echo -e "  ${BLUE}hatch run test${NC}           # Run tests"
    echo ""
    exit 1
fi
