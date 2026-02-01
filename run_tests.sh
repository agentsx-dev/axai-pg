#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default test path - run all tests
TEST_PATH="${1:-tests/}"

# Print usage
usage() {
    echo -e "${BLUE}Usage:${NC} ./run_tests.sh [test_path]"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh                    # Run all tests"
    echo "  ./run_tests.sh tests/integration  # Run only integration tests"
    echo "  ./run_tests.sh tests/unit         # Run only unit tests"
    echo "  ./run_tests.sh tests/unit/security # Run only security tests"
    echo ""
    echo "Note: All tests require PostgreSQL database to be running."
}

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    exit 0
fi

# Start PostgreSQL
echo -e "\n${GREEN}Starting PostgreSQL container...${NC}"
docker-compose -f docker-compose.standalone-test.yml up -d postgres

# Wait for PostgreSQL to be ready
echo -e "\n${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
for i in {1..30}; do
    if docker-compose -f docker-compose.standalone-test.yml exec postgres pg_isready -U test_user -d test_db > /dev/null 2>&1; then
        echo -e "${GREEN}PostgreSQL is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}PostgreSQL failed to start within 30 seconds${NC}"
        exit 1
    fi
    sleep 1
done

# Set up trap to ensure cleanup on script exit
cleanup() {
    echo -e "\n${YELLOW}Stopping PostgreSQL container...${NC}"
    docker-compose -f docker-compose.standalone-test.yml down
}
trap cleanup EXIT

# Run tests
echo -e "\n${GREEN}Running tests from: ${TEST_PATH}${NC}"
echo -e "${BLUE}Command: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest ${TEST_PATH} -v --integration${NC}\n"

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest "${TEST_PATH}" -v --integration
TEST_STATUS=$?

# Coverage report instructions (optional)
if python -c "import pytest_cov" 2>/dev/null; then
    echo -e "\n${BLUE}To generate coverage report, run:${NC}"
    echo -e "  python -m pytest ${TEST_PATH} --cov=src --cov-report=html --cov-report=term-missing --integration"
fi

# Check test results
echo ""
if [ $TEST_STATUS -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Tests failed.${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
