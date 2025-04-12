#!/bin/bash
# cleanup_for_public.sh - Script to clean up temporary files and logs before making repository public

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==== Cleaning Up Repository for Public Release ====${NC}"

# 1. Remove deployment logs
echo -e "\n${YELLOW}Removing deployment logs...${NC}"
find . -name "deployment_*.log" -type f -print -delete
find . -name "*.log" -type f -print -delete
echo -e "${GREEN}✓ Deployment logs removed${NC}"

# 2. Remove any temp files
echo -e "\n${YELLOW}Removing temporary files...${NC}"
find . -name "*.tmp" -type f -print -delete
find . -name "*.temp" -type f -print -delete
find . -name "temp_*" -type f -print -delete
echo -e "${GREEN}✓ Temporary files removed${NC}"

# 3. Remove python cache files
echo -e "\n${YELLOW}Removing Python cache files...${NC}"
find . -type d -name "__pycache__" -print -exec rm -rf {} +
find . -name "*.pyc" -type f -print -delete
find . -name "*.pyo" -type f -print -delete
find . -name "*.pyd" -type f -print -delete
echo -e "${GREEN}✓ Python cache files removed${NC}"

# 4. Remove MkDocs build directory if it exists
if [ -d "site" ]; then
    echo -e "\n${YELLOW}Removing MkDocs build directory...${NC}"
    rm -rf site/
    echo -e "${GREEN}✓ MkDocs build directory removed${NC}"
fi

# 5. Check for any remaining potential sensitive files
echo -e "\n${YELLOW}Checking for potentially sensitive files...${NC}"
SENSITIVE_PATTERNS=(
    "*password*"
    "*secret*"
    "*credential*"
    "*api_key*"
    "*apikey*"
    "*.key"
    "*.pem"
    "pull-secret.txt"
    ".truenas_auth"
    ".truenas_config"
)

# Build find command for sensitive files
FIND_CMD="find . -type f"
for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    # Add exception for our explicitly allowed files
    if [[ "$pattern" == "*secret*" ]]; then
        FIND_CMD="$FIND_CMD -name \"$pattern\" ! -path \"*/scripts/secrets_provider.py\" ! -path \"*/docs/SECRETS_PROVIDER.md\" ! -path \"*/docs_mkdocs/docs/SECRETS_PROVIDER.md\""
    else
        FIND_CMD="$FIND_CMD -name \"$pattern\""
    fi
    if [[ "$pattern" != "${SENSITIVE_PATTERNS[-1]}" ]]; then
        FIND_CMD="$FIND_CMD -o"
    fi
done

# Execute the find command and capture output
SENSITIVE_FILES=$(eval $FIND_CMD)

if [ -n "$SENSITIVE_FILES" ]; then
    echo -e "${RED}Potentially sensitive files found:${NC}"
    echo "$SENSITIVE_FILES"
    echo -e "\n${YELLOW}Please review these files manually or delete them if they contain sensitive information.${NC}"
else
    echo -e "${GREEN}✓ No potentially sensitive files found${NC}"
fi

# 6. Test files in root directory
TEST_FILES=$(find . -maxdepth 1 -name "test_*.py" -type f)
if [ -n "$TEST_FILES" ]; then
    echo -e "\n${YELLOW}Test files found in root directory:${NC}"
    echo "$TEST_FILES"
    echo -e "${YELLOW}Consider moving these to a 'tests' directory or removing if not needed.${NC}"
fi

echo -e "\n${GREEN}Repository cleanup complete.${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Run ./scripts/organize_repo_structure.py to organize markdown files"
echo -e "2. Run ./scripts/create_public_repo.sh to create a new public repository"
