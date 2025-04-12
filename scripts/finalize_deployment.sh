#!/bin/bash
# finalize_deployment.sh - Final deployment script for OpenShift multiboot system
# Executes all required steps to complete the system deployment
# and verify functionality

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TRUENAS_IP="192.168.2.245"
SERVER_IP="192.168.2.230"
OPENSHIFT_VERSIONS=("4.16" "4.17" "4.18")
LOG_FILE="deployment_$(date +%Y%m%d_%H%M%S).log"

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}== $1${NC}"
    echo -e "${BLUE}======================================================================${NC}"
    echo -e "$(date +%Y-%m-%d' '%H:%M:%S) - $1" >> "$LOG_FILE"
}

# Function to run a command with explanations
run_command() {
    local description=$1
    local command=$2
    local check_only=${3:-false}
    
    echo -e "\n${YELLOW}$description${NC}"
    echo -e "${GREEN}> $command${NC}"
    echo -e "$(date +%Y-%m-%d' '%H:%M:%S) - COMMAND: $command" >> "$LOG_FILE"
    
    if [ "$check_only" = "true" ]; then
        echo -e "${YELLOW}Skipping execution (check-only mode)${NC}"
        echo -e "$(date +%Y-%m-%d' '%H:%M:%S) - SKIPPED (check-only mode)" >> "$LOG_FILE"
        return 0
    fi

    echo -e "${YELLOW}Executing...${NC}"
    
    # Execute the command and capture the output
    OUTPUT=$(eval "$command" 2>&1)
    STATUS=$?
    
    # Log the output
    echo -e "$OUTPUT" >> "$LOG_FILE"
    
    # Display the output
    echo -e "$OUTPUT"
    
    if [ $STATUS -eq 0 ]; then
        echo -e "${GREEN}✓ Command executed successfully${NC}"
        echo -e "$(date +%Y-%m-%d' '%H:%M:%S) - SUCCESS" >> "$LOG_FILE"
        return 0
    else
        echo -e "${RED}✗ Command failed with status $STATUS${NC}"
        echo -e "$(date +%Y-%m-%d' '%H:%M:%S) - FAILED with status $STATUS" >> "$LOG_FILE"
        return $STATUS
    fi
}

# Function to ask for confirmation
confirm() {
    local message=$1
    local default=${2:-y}
    
    local prompt
    if [ "$default" = "y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi
    
    while true; do
        read -p "$message $prompt " answer
        [ -z "$answer" ] && answer=$default
        
        case "$answer" in
            [Yy]|[Yy][Ee][Ss]) return 0 ;;
            [Nn]|[Nn][Oo]) return 1 ;;
            *) echo "Please answer yes or no." ;;
        esac
    done
}

# Initialize log file
echo "OpenShift Multiboot System - Deployment Log" > "$LOG_FILE"
echo "Started at $(date)" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"

# Print introduction
print_header "OpenShift Multiboot System - Final Deployment"
echo "This script will execute all required steps to complete the OpenShift multiboot system deployment"
echo "Log file: $LOG_FILE"

# Check if running with proper permissions
if [[ $EUID -ne 0 && "$CHECK_ONLY" != "true" ]]; then
    echo -e "${YELLOW}Note: Some operations may require elevated privileges.${NC}"
    echo -e "${YELLOW}If you encounter permission issues, consider running with sudo.${NC}"
    if confirm "Continue anyway?"; then
        echo "Proceeding with current permissions..."
    else
        echo "Deployment aborted by user"
        exit 1
    fi
fi

# Ask to run in check-only mode
CHECK_ONLY=false
if confirm "Run in check-only mode (no actual changes)?"; then
    CHECK_ONLY=true
    echo -e "${YELLOW}Running in check-only mode. No changes will be made.${NC}"
    echo "Running in check-only mode" >> "$LOG_FILE"
fi

# Step 1: Generate OpenShift ISOs
print_header "Step 1: Generate OpenShift ISOs"

# Verify GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}GitHub CLI (gh) is not installed. Please install it first:${NC}"
    echo -e "${YELLOW}https://cli.github.com/manual/installation${NC}"
    exit 1
fi

# Verify GitHub authentication
if ! gh auth status &> /dev/null; then
    echo -e "${RED}GitHub CLI is not authenticated. Please run:${NC}"
    echo -e "${YELLOW}gh auth login${NC}"
    exit 1
fi

# Get repo information
REPO_NAME=$(git remote get-url origin | sed -n 's/.*github.com[:/]\(.*\).git/\1/p')

if [ -z "$REPO_NAME" ]; then
    echo -e "${RED}Failed to determine GitHub repository name.${NC}"
    exit 1
fi

echo -e "${BLUE}Using GitHub repository: $REPO_NAME${NC}"
echo -e "${BLUE}GitHub Actions will be used to generate ISOs on x86_64 runners${NC}"

# For each OpenShift version, trigger the GitHub Actions workflow
for VERSION in "${OPENSHIFT_VERSIONS[@]}"; do
    if [ "$CHECK_ONLY" == "true" ]; then
        echo -e "${YELLOW}Check-only mode: Would trigger GitHub workflow for OpenShift $VERSION${NC}"
        continue
    fi

    echo -e "${GREEN}Triggering GitHub workflow to generate OpenShift $VERSION ISO...${NC}"
    WORKFLOW_URL=$(gh workflow run generate_iso.yml -R "$REPO_NAME" \
        -f version="$VERSION" \
        -f rendezvous_ip="$SERVER_IP" \
        -f truenas_ip="$TRUENAS_IP" \
        --json url -q .url)
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to trigger workflow for OpenShift $VERSION${NC}"
        if ! confirm "Continue with next version?"; then
            echo "Deployment aborted by user"
            exit 1
        fi
        continue
    fi
    
    echo -e "${GREEN}Workflow triggered: $WORKFLOW_URL${NC}"
    echo -e "${BLUE}Waiting for ISO generation to complete...${NC}"
    
    # Get the run ID
    RUN_ID=$(echo "$WORKFLOW_URL" | grep -o '[0-9]\+$')
    
    # Poll for workflow completion
    while true; do
        STATUS=$(gh run view "$RUN_ID" -R "$REPO_NAME" --json status -q .status)
        
        if [ "$STATUS" == "completed" ]; then
            CONCLUSION=$(gh run view "$RUN_ID" -R "$REPO_NAME" --json conclusion -q .conclusion)
            if [ "$CONCLUSION" == "success" ]; then
                echo -e "${GREEN}OpenShift $VERSION ISO generated successfully!${NC}"
                break
            else
                echo -e "${RED}OpenShift $VERSION ISO generation failed with conclusion: $CONCLUSION${NC}"
                if ! confirm "Continue with next version?"; then
                    echo "Deployment aborted by user"
                    exit 1
                fi
                break
            fi
        fi
        
        echo -e "${BLUE}Still running... (current status: $STATUS)${NC}"
        sleep 30
    done
done

# Verify ISOs exist on TrueNAS
echo -e "${BLUE}Verifying ISOs on TrueNAS...${NC}"
for VERSION in "${OPENSHIFT_VERSIONS[@]}"; do
    ISO_PATH="http://${TRUENAS_IP}/openshift_isos/${VERSION}/agent.x86_64.iso"
    
    if curl --output /dev/null --silent --head --fail "$ISO_PATH"; then
        echo -e "${GREEN}OpenShift $VERSION ISO verified at: $ISO_PATH${NC}"
    else
        echo -e "${RED}OpenShift $VERSION ISO not found at: $ISO_PATH${NC}"
        if ! confirm "Continue with deployment?"; then
            echo "Deployment aborted by user"
            exit 1
        fi
    fi
done

# Step 2: Setup netboot
print_header "Step 2: Configure Netboot Menu"
run_command "Setting up netboot menu" \
    "./scripts/setup_netboot.py --truenas-ip $TRUENAS_IP" \
    $CHECK_ONLY

if [ $? -ne 0 ] && [ "$CHECK_ONLY" != "true" ]; then
    echo -e "${RED}Failed to configure netboot menu${NC}"
    if ! confirm "Continue with deployment?"; then
        echo "Deployment aborted by user"
        exit 1
    fi
fi

# Step 3: Verify boot methods
print_header "Step 3: Verify Boot Methods"

# Verify iSCSI boot
run_command "Verifying iSCSI boot method for OpenShift 4.18" \
    "./scripts/switch_openshift.py --server $SERVER_IP --method iscsi --version 4.18 --check-only" \
    false

# Verify ISO boot
run_command "Verifying ISO boot method for OpenShift 4.18" \
    "./scripts/switch_openshift.py --server $SERVER_IP --method iso --version 4.18 --check-only" \
    false

# Verify netboot
run_command "Verifying netboot method" \
    "./scripts/switch_openshift.py --server $SERVER_IP --method netboot --check-only" \
    false

# Step 4: Run final validation tests
print_header "Step 4: Run Final Validation Tests"
run_command "Running test setup script" \
    "./scripts/test_setup.sh" \
    false

# Completion
print_header "Deployment Summary"

# Check for any failures in the log
FAILURES=$(grep -c "FAILED" "$LOG_FILE")
if [ $FAILURES -gt 0 ]; then
    echo -e "${RED}Deployment completed with $FAILURES failures${NC}"
    echo -e "${YELLOW}Review the log file at $LOG_FILE for details${NC}"
    COMPLETION_STATUS="PARTIAL"
else
    echo -e "${GREEN}Deployment completed successfully${NC}"
    COMPLETION_STATUS="COMPLETE"
fi

if [ "$CHECK_ONLY" = "true" ]; then
    echo -e "${YELLOW}Note: This was a check-only run. No actual changes were made.${NC}"
    echo -e "${YELLOW}To perform the actual deployment, run without check-only mode.${NC}"
fi

echo -e "\n${GREEN}Next Steps:${NC}"
echo -e "1. Review the PROJECT_COMPLETION.md document"
echo -e "2. Complete the Project Completion Checklist"
echo -e "3. Schedule the final demonstration with stakeholders"
echo -e "4. Complete the handover to the operations team"

# Record completion in log
echo "----------------------------------------" >> "$LOG_FILE"
echo "Deployment finished at $(date)" >> "$LOG_FILE"
echo "Status: $COMPLETION_STATUS" >> "$LOG_FILE"
if [ $FAILURES -gt 0 ]; then
    echo "Failures: $FAILURES" >> "$LOG_FILE"
fi

echo -e "\nLog file has been saved to: $LOG_FILE"
