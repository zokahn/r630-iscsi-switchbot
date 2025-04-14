#!/bin/bash
# Script to verify Python 3.12 migration with all required dependencies
# This script runs inside the Docker container

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Installing required dependencies...${NC}"

# Install boto3 and other required packages
pip install boto3 requests urllib3 hvac pytest mypy-boto3-s3

echo -e "${GREEN}Dependencies installed successfully${NC}"
echo -e "${BLUE}Starting verification...${NC}"

# Run the verification script
python scripts/verify_py312_migration.py

# Return the exit code from the verification script
exit $?
