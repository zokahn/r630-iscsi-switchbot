#!/bin/bash
# test_github_actions.sh - Verify GitHub Actions setup for local runner
# Checks the status of the local runner and validates workflow configurations

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}== GitHub Actions Test Setup${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo -e "${RED}ERROR: jq is not installed. This is required for JSON parsing:${NC}"
    echo -e "${YELLOW}macOS: brew install jq${NC}"
    echo -e "${YELLOW}Linux: sudo apt install jq${NC}"
    exit 1
fi

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}ERROR: GitHub CLI (gh) is not installed. Please install it first:${NC}"
    echo -e "${YELLOW}https://cli.github.com/manual/installation${NC}"
    exit 1
fi

# Check GitHub authentication
if ! gh auth status &> /dev/null; then
    echo -e "${RED}ERROR: GitHub CLI is not authenticated. Please run:${NC}"
    echo -e "${YELLOW}gh auth login${NC}"
    exit 1
fi

echo -e "${GREEN}✓ GitHub CLI is installed and authenticated${NC}"

# Get repo information
REPO_NAME=$(git remote get-url origin | sed -n 's/.*github.com[:/]\(.*\).git/\1/p')

if [ -z "$REPO_NAME" ]; then
    echo -e "${RED}ERROR: Failed to determine GitHub repository name.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Repository identified: $REPO_NAME${NC}"

# Check if we are in the correct repository
SCRIPT_DIR=$(dirname "$(realpath "$0")")
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)

if [ "$REPO_ROOT" != "$(pwd)" ]; then
    echo -e "${YELLOW}Warning: This script is being run from outside the repository root.${NC}"
    echo -e "${YELLOW}Current directory: $(pwd)${NC}"
    echo -e "${YELLOW}Repository root: $REPO_ROOT${NC}"
fi

# Check for workflow files
if [ -f ".github/workflows/generate_iso.yml" ]; then
    echo -e "${GREEN}✓ Found generate_iso.yml workflow${NC}"
else
    echo -e "${RED}ERROR: Missing .github/workflows/generate_iso.yml${NC}"
    exit 1
fi

if [ -f ".github/workflows/test_integration.yml" ]; then
    echo -e "${GREEN}✓ Found test_integration.yml workflow${NC}"
else
    echo -e "${RED}ERROR: Missing .github/workflows/test_integration.yml${NC}"
    exit 1
fi

# Check for GitHub runner
RUNNER_ACTIVE=false
EXPECTED_RUNNER_NAME="r630-switchbot-runner"

echo -e "\n${BLUE}Checking GitHub for runner named '$EXPECTED_RUNNER_NAME'...${NC}"

# Directly check GitHub API for runner existence and status
RUNNERS_JSON=$(gh api "/repos/$REPO_NAME/actions/runners" 2>/dev/null || echo '{"runners":[]}')
RUNNER_STATUS=$(echo "$RUNNERS_JSON" | jq -r '.runners[] | select(.name=="'"$EXPECTED_RUNNER_NAME"'") | .status' 2>/dev/null)

if [ "$RUNNER_STATUS" = "online" ]; then
    echo -e "${GREEN}✓ Runner '$EXPECTED_RUNNER_NAME' is registered and ONLINE${NC}"
    RUNNER_ACTIVE=true
elif [ "$RUNNER_STATUS" = "offline" ]; then
    echo -e "${YELLOW}! Runner '$EXPECTED_RUNNER_NAME' is registered but OFFLINE${NC}"
    echo -e "${YELLOW}  Please start the runner service${NC}"
elif [ -n "$RUNNER_STATUS" ]; then
    echo -e "${YELLOW}! Runner '$EXPECTED_RUNNER_NAME' is registered but status is: $RUNNER_STATUS${NC}"
else
    echo -e "${YELLOW}! Runner '$EXPECTED_RUNNER_NAME' is not registered with this repository${NC}"
fi

# Also check local process (this might not be accurate if runner is on another machine)
if pgrep -f "actions-runner" > /dev/null || pgrep -f "$EXPECTED_RUNNER_NAME" > /dev/null; then
    echo -e "${GREEN}✓ Actions runner process detected on this machine${NC}"
    
    # Try to get runner info from process
    RUNNER_PROC_INFO=$(ps aux | grep -E "[a]ctions-runner" | head -1)
    if [ -n "$RUNNER_PROC_INFO" ]; then
        echo -e "${BLUE}  Process info: $RUNNER_PROC_INFO${NC}"
    fi
else
    echo -e "${YELLOW}! No actions runner process detected on this machine${NC}"
    if [ "$RUNNER_STATUS" = "online" ]; then
        echo -e "${BLUE}  Runner is likely running on another machine${NC}"
    fi
fi

# Check required secrets
echo -e "\n${BLUE}Checking for required secrets...${NC}"
SECRETS=$(gh secret list -R "$REPO_NAME" 2>/dev/null)
SECRET_STATUS=0

if echo "$SECRETS" | grep -q "OPENSHIFT_PULL_SECRET"; then
    echo -e "${GREEN}✓ OPENSHIFT_PULL_SECRET is set${NC}"
else
    echo -e "${RED}✗ OPENSHIFT_PULL_SECRET is missing${NC}"
    SECRET_STATUS=1
fi

if echo "$SECRETS" | grep -q "TRUENAS_SSH_KEY"; then
    echo -e "${GREEN}✓ TRUENAS_SSH_KEY is set${NC}"
else
    echo -e "${RED}✗ TRUENAS_SSH_KEY is missing${NC}"
    SECRET_STATUS=1
fi

if echo "$SECRETS" | grep -q "TRUENAS_KNOWN_HOSTS"; then
    echo -e "${GREEN}✓ TRUENAS_KNOWN_HOSTS is set${NC}"
else
    echo -e "${RED}✗ TRUENAS_KNOWN_HOSTS is missing${NC}"
    SECRET_STATUS=1
fi

# List available workflows
echo -e "\n${BLUE}Available workflows:${NC}"
gh workflow list -R "$REPO_NAME"

# Final summary
echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${BLUE}== Summary${NC}"
echo -e "${BLUE}======================================================================${NC}"

if [ "$RUNNER_ACTIVE" = "true" ]; then
    echo -e "${GREEN}✓ Local GitHub runner is active and will be used for workflows${NC}"
else
    echo -e "${YELLOW}! No local GitHub runner detected. GitHub-hosted runners will be used.${NC}"
    echo -e "${YELLOW}  This may be slower and subject to GitHub-hosted runner constraints.${NC}"
    echo -e "${YELLOW}  Consider setting up a local runner for optimal performance:${NC}"
    echo -e "${YELLOW}  https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners${NC}"
fi

if [ $SECRET_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ All required secrets are configured${NC}"
else
    echo -e "${RED}✗ Some required secrets are missing. Please set them up before running workflows.${NC}"
    echo -e "${YELLOW}  See docs/GITHUB_ACTIONS_USAGE.md for instructions${NC}"
fi

echo -e "\n${GREEN}Testing workflow configuration:${NC}"
echo -e "${YELLOW}To test the generate_iso workflow:${NC}"
echo -e "  gh workflow run generate_iso.yml -R \"$REPO_NAME\" \\"
echo -e "    -f version=\"4.18\" \\"
echo -e "    -f rendezvous_ip=\"192.168.2.230\" \\"
echo -e "    -f truenas_ip=\"192.168.2.245\" \\"
echo -e "    -f skip_upload=\"true\""

echo -e "\n${YELLOW}To test the integration test workflow:${NC}"
echo -e "  gh workflow run test_integration.yml -R \"$REPO_NAME\" \\"
echo -e "    -f server_ip=\"192.168.2.230\" \\"
echo -e "    -f truenas_ip=\"192.168.2.245\""

echo -e "\n${BLUE}For full deployment with all tests, use:${NC}"
echo -e "  ./scripts/finalize_deployment.sh"
