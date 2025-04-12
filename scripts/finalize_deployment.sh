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
TIMESTAMP=$(date +%Y%m%d%H%M%S)
SERVER_ID=""
DEPLOYMENT_NAME=""
LOG_FILE="deployment_${TIMESTAMP}.log"

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

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --server-id)
        SERVER_ID="$2"
        shift
        shift
        ;;
        --deployment-name)
        DEPLOYMENT_NAME="$2"
        shift
        shift
        ;;
        --values-file)
        VALUES_FILE="$2"
        shift
        shift
        ;;
        --check-only)
        CHECK_ONLY=true
        shift
        ;;
        *)
        # Unknown option
        echo -e "${RED}Unknown option: $key${NC}"
        exit 1
        ;;
    esac
done

# Create deployment identifier if server ID is provided
if [ -n "$SERVER_ID" ]; then
    if [ -z "$DEPLOYMENT_NAME" ]; then
        DEPLOYMENT_NAME="sno"
    fi
    DEPLOYMENT_ID="r630-${SERVER_ID}-${DEPLOYMENT_NAME}-${TIMESTAMP}"
    
    # Update log file name with deployment ID
    LOG_FILE="deployment_${DEPLOYMENT_ID}.log"
    echo -e "${BLUE}Using deployment ID: ${DEPLOYMENT_ID}${NC}"
    echo -e "${BLUE}Log file: ${LOG_FILE}${NC}"
fi

# Ask to run in check-only mode if not specified via command line
if [ -z "$CHECK_ONLY" ]; then
    CHECK_ONLY=false
    if confirm "Run in check-only mode (no actual changes)?"; then
        CHECK_ONLY=true
        echo -e "${YELLOW}Running in check-only mode. No changes will be made.${NC}"
        echo "Running in check-only mode" >> "$LOG_FILE"
    fi
else
    echo -e "${YELLOW}Running in check-only mode (specified via command line). No changes will be made.${NC}"
    echo "Running in check-only mode" >> "$LOG_FILE"
fi

# Step 1: Generate OpenShift ISOs
print_header "Step 1: Generate OpenShift ISOs"

# Check for local GitHub runner status
echo -e "${BLUE}Checking for local GitHub runner...${NC}"
LOCAL_RUNNER_ACTIVE=false
if pgrep -f "actions-runner" > /dev/null; then
    echo -e "${GREEN}✓ Local x86_64 GitHub runner detected and active${NC}"
    LOCAL_RUNNER_ACTIVE=true
else
    echo -e "${YELLOW}! No local GitHub runner detected. ISO generation will use GitHub-hosted runners.${NC}"
    echo -e "${YELLOW}  This may be slower and subject to GitHub-hosted runner constraints.${NC}"
fi

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
    
    # Base workflow parameters
    WORKFLOW_PARAMS=(
        "-f" "version=$VERSION"
        "-f" "rendezvous_ip=$SERVER_IP"
        "-f" "truenas_ip=$TRUENAS_IP"
    )
    
    # Add deployment tracking parameters if server ID is provided
    if [ -n "$SERVER_ID" ]; then
        WORKFLOW_PARAMS+=(
            "-f" "server_id=$SERVER_ID"
            "-f" "timestamp=$TIMESTAMP"
        )
        
        if [ -n "$DEPLOYMENT_NAME" ]; then
            WORKFLOW_PARAMS+=("-f" "deployment_name=$DEPLOYMENT_NAME")
        fi
        
        # If values file was provided
        if [ -n "$VALUES_FILE" ]; then
            WORKFLOW_PARAMS+=("-f" "values_file=$VALUES_FILE")
        fi
        
        echo -e "${BLUE}Using deployment tracking with ID: ${DEPLOYMENT_ID}${NC}"
    fi
    
    # Run the workflow with all parameters
    WORKFLOW_URL=$(gh workflow run generate_iso.yml -R "$REPO_NAME" "${WORKFLOW_PARAMS[@]}" --json url -q .url)
    
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

# Step 4: Run integration tests via GitHub Actions
print_header "Step 4: Run Integration Tests"

if [ "$CHECK_ONLY" == "true" ]; then
    echo -e "${YELLOW}Check-only mode: Would trigger GitHub workflow for integration tests${NC}"
else
    echo -e "${GREEN}Triggering GitHub workflow for system integration tests...${NC}"
    
    # Base integration test workflow parameters
    WORKFLOW_PARAMS=(
        "-f" "server_ip=$SERVER_IP"
        "-f" "truenas_ip=$TRUENAS_IP"
    )
    
    # Add deployment tracking parameters if server ID is provided
    if [ -n "$SERVER_ID" ]; then
        WORKFLOW_PARAMS+=(
            "-f" "server_id=$SERVER_ID"
            "-f" "timestamp=$TIMESTAMP"
        )
        
        if [ -n "$DEPLOYMENT_NAME" ]; then
            WORKFLOW_PARAMS+=("-f" "deployment_name=$DEPLOYMENT_NAME")
        fi
        
        echo -e "${BLUE}Using deployment tracking with ID: ${DEPLOYMENT_ID}${NC}"
    fi
    
    # Run the workflow with all parameters
    WORKFLOW_URL=$(gh workflow run test_integration.yml -R "$REPO_NAME" "${WORKFLOW_PARAMS[@]}" --json url -q .url)
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to trigger integration test workflow${NC}"
        if ! confirm "Continue with deployment?"; then
            echo "Deployment aborted by user"
            exit 1
        fi
    else
        echo -e "${GREEN}Integration test workflow triggered: $WORKFLOW_URL${NC}"
        echo -e "${BLUE}Waiting for tests to complete...${NC}"
        
        # Get the run ID
        RUN_ID=$(echo "$WORKFLOW_URL" | grep -o '[0-9]\+$')
        
        # Poll for workflow completion
        while true; do
            STATUS=$(gh run view "$RUN_ID" -R "$REPO_NAME" --json status -q .status)
            
            if [ "$STATUS" == "completed" ]; then
                CONCLUSION=$(gh run view "$RUN_ID" -R "$REPO_NAME" --json conclusion -q .conclusion)
                if [ "$CONCLUSION" == "success" ]; then
                    echo -e "${GREEN}Integration tests completed successfully!${NC}"
                    break
                else
                    echo -e "${RED}Integration tests failed with conclusion: $CONCLUSION${NC}"
                    echo -e "${YELLOW}Review the workflow logs for details: $WORKFLOW_URL${NC}"
                    if ! confirm "Continue with deployment?"; then
                        echo "Deployment aborted by user"
                        exit 1
                    fi
                    break
                fi
            fi
            
            echo -e "${BLUE}Still running... (current status: $STATUS)${NC}"
            sleep 15
        done
    fi
fi

# Step 5: Run local validation tests
print_header "Step 5: Run Local Validation Tests"
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

# Upload deployment artifacts to TrueNAS if server ID is provided
if [ -n "$SERVER_ID" ] && [ "$CHECK_ONLY" != "true" ]; then
    print_header "Uploading Deployment Artifacts to TrueNAS"
    
    # Prepare artifact upload parameters
    ARTIFACT_PARAMS=(
        "--server-id" "$SERVER_ID"
        "--log-file" "$LOG_FILE"
        "--truenas-ip" "$TRUENAS_IP"
    )
    
    # Add deployment name if provided
    if [ -n "$DEPLOYMENT_NAME" ]; then
        ARTIFACT_PARAMS+=("--deployment-name" "$DEPLOYMENT_NAME")
    fi
    
    # Add timestamp
    ARTIFACT_PARAMS+=("--timestamp" "$TIMESTAMP")
    
    # Add any kubeconfig file if found (assuming standard OpenShift location)
    KUBECONFIG_DIR="./auth"
    if [ -f "${KUBECONFIG_DIR}/kubeconfig" ]; then
        ARTIFACT_PARAMS+=("--kubeconfig" "${KUBECONFIG_DIR}/kubeconfig")
    fi
    
    # Add custom metadata
    ARTIFACT_PARAMS+=(
        "--metadata" "openshift_version=${VERSION:-unknown}"
        "--metadata" "status=${COMPLETION_STATUS}"
    )
    
    if [ $FAILURES -gt 0 ]; then
        ARTIFACT_PARAMS+=("--metadata" "failures=${FAILURES}")
    fi
    
    # Execute the upload command
    run_command "Uploading deployment artifacts to TrueNAS" \
        "./scripts/upload_deployment_artifacts.sh ${ARTIFACT_PARAMS[*]}" \
        false
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Successfully uploaded deployment artifacts to TrueNAS${NC}"
    else
        echo -e "${RED}Failed to upload deployment artifacts${NC}"
    fi
fi
