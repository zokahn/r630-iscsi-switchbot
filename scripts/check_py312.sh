#!/bin/bash
# Simple wrapper to run the Python 3.12 verification script in Docker
# This helps users who don't have Python 3.12 installed locally

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}R630 iSCSI SwitchBot - Python 3.12 Migration Checker${NC}"
echo -e "${BLUE}${BOLD}=================================================${NC}\n"

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Error: docker compose not found${NC}"
    echo -e "${YELLOW}Please install Docker Compose V2 to run this check${NC}"
    exit 1
fi

# Check if the Docker Compose file exists
if [ ! -f "docker-compose.python312.yml" ]; then
    echo -e "${RED}Error: docker-compose.python312.yml not found${NC}"
    echo -e "${YELLOW}Please run this script from the project root directory${NC}"
    exit 1
fi

echo -e "${BLUE}Starting Python 3.12 verification in Docker environment...${NC}\n"

# Run the verification script in Docker with required dependencies
docker compose -f docker-compose.python312.yml run --rm python312 bash scripts/docker_verify_py312.sh

# Capture the exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}${BOLD}Verification completed successfully!${NC}"
    echo -e "${BLUE}You can now commit the Python 3.12 migration changes.${NC}"
else
    echo -e "\n${YELLOW}${BOLD}Verification completed with some issues.${NC}"
    echo -e "${BLUE}Please fix the reported issues before committing.${NC}"
fi

# Return the exit code from the verification script
exit $EXIT_CODE
