#!/bin/bash
# test_deployment_tracking.sh - Test the deployment tracking system
# This script tests the deployment tracking functionality without performing a full deployment

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER_ID="01"
DEPLOYMENT_NAME="test"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
DEPLOYMENT_ID="r630-${SERVER_ID}-${DEPLOYMENT_NAME}-${TIMESTAMP}"
TRUENAS_IP="192.168.2.245"

# Create test directory
TEST_DIR="/tmp/test_tracking_${TIMESTAMP}"
mkdir -p "$TEST_DIR"
echo "Created test directory: $TEST_DIR"

# Function to print header
print_header() {
    echo -e "\n${BLUE}=================================================================${NC}"
    echo -e "${BLUE}== $1${NC}"
    echo -e "${BLUE}=================================================================${NC}"
}

# Function to check if a command succeeds
check_step() {
    local description=$1
    local command=$2
    
    echo -e "\n${YELLOW}$description${NC}"
    echo -e "${GREEN}> $command${NC}"
    
    # Execute command
    eval "$command"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Success${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed${NC}"
        return 1
    fi
}

# Test 1: Generate values file with server ID
print_header "Testing values file generation with server ID"

VALUES_CMD="./scripts/generate_openshift_values.py \
  --node-ip 192.168.2.230 \
  --cluster-name ${DEPLOYMENT_NAME} \
  --server-id ${SERVER_ID} \
  --base-domain test.lab \
  --output-dir ${TEST_DIR}"

if check_step "Generating values file" "$VALUES_CMD"; then
    # Check if values file was created in the expected location
    VALUES_FILE="${TEST_DIR}/deployments/r630-${SERVER_ID}/"
    if ls $VALUES_FILE/r630-*.yaml &> /dev/null; then
        echo -e "${GREEN}✓ Values file created in the expected location${NC}"
        echo -e "  $(ls $VALUES_FILE/r630-*.yaml)"
    else
        echo -e "${RED}✗ Values file not found in expected location${NC}"
        echo -e "  Expected: $VALUES_FILE/r630-*.yaml"
    fi
fi

# Test 2: Create a mock log file for artifact testing
print_header "Creating mock deployment artifacts"

LOG_FILE="${TEST_DIR}/deployment_${DEPLOYMENT_ID}.log"

# Create a mock log file
cat > "$LOG_FILE" << EOF
OpenShift Multiboot System - Deployment Log
Started at $(date)
----------------------------------------
$(date +%Y-%m-%d' '%H:%M:%S) - OpenShift Multiboot System - Final Deployment
COMMAND: ./scripts/generate_openshift_iso.py --version 4.18 --values-file ${TEST_DIR}/deployments/r630-${SERVER_ID}/r630-*.yaml
SUCCESS
COMMAND: ./scripts/setup_netboot.py --truenas-ip ${TRUENAS_IP}
SUCCESS
----------------------------------------
Deployment finished at $(date)
Status: COMPLETE
EOF

echo -e "${GREEN}✓ Created mock log file: $LOG_FILE${NC}"

# Create a mock kubeconfig
KUBECONFIG_DIR="${TEST_DIR}/auth"
mkdir -p "$KUBECONFIG_DIR"
cat > "${KUBECONFIG_DIR}/kubeconfig" << EOF
apiVersion: v1
clusters:
- cluster:
    server: https://api.test.lab:6443
  name: test-cluster
contexts:
- context:
    cluster: test-cluster
    user: admin
  name: admin
current-context: admin
kind: Config
preferences: {}
users:
- name: admin
  user:
    token: mock-token-for-testing
EOF

echo -e "${GREEN}✓ Created mock kubeconfig file: ${KUBECONFIG_DIR}/kubeconfig${NC}"

# Test 3: Test artifact upload script
print_header "Testing artifact upload (mock mode)"

# Add a --mock-mode flag to the upload script for testing
check_step "Running artifact upload script (mock mode)" "
./scripts/upload_deployment_artifacts.sh \
  --server-id ${SERVER_ID} \
  --deployment-name ${DEPLOYMENT_NAME} \
  --timestamp ${TIMESTAMP} \
  --log-file ${LOG_FILE} \
  --kubeconfig ${KUBECONFIG_DIR}/kubeconfig \
  --truenas-ip ${TRUENAS_IP} \
  --metadata status=COMPLETE \
  --metadata openshift_version=4.18 \
  --mock-mode true
"

# Test 4: Run values generation and try upload in one step
print_header "Testing end-to-end with mock mode"

# Create a small test run with just the essential steps
echo -e "${YELLOW}This test simulates what would happen in finalize_deployment.sh${NC}"

SERVER_ID="02"
DEPLOYMENT_NAME="e2e-test"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
DEPLOYMENT_ID="r630-${SERVER_ID}-${DEPLOYMENT_NAME}-${TIMESTAMP}"
LOG_FILE="${TEST_DIR}/deployment_${DEPLOYMENT_ID}.log"

# Create the log file
cat > "$LOG_FILE" << EOF
OpenShift Multiboot System - Deployment Log
Started at $(date)
----------------------------------------
$(date +%Y-%m-%d' '%H:%M:%S) - End-to-end test
----------------------------------------
Deployment finished at $(date)
Status: COMPLETE
EOF

echo -e "${GREEN}✓ Created log file for end-to-end test: $LOG_FILE${NC}"

# First, generate the values file
VALUES_CMD="./scripts/generate_openshift_values.py \
  --node-ip 192.168.2.231 \
  --cluster-name ${DEPLOYMENT_NAME} \
  --server-id ${SERVER_ID} \
  --base-domain test.lab \
  --output-dir ${TEST_DIR}"

check_step "Generating values file for end-to-end test" "$VALUES_CMD"

# Then attempt to upload artifacts
check_step "Uploading artifacts for end-to-end test" "
./scripts/upload_deployment_artifacts.sh \
  --server-id ${SERVER_ID} \
  --deployment-name ${DEPLOYMENT_NAME} \
  --timestamp ${TIMESTAMP} \
  --log-file ${LOG_FILE} \
  --truenas-ip ${TRUENAS_IP} \
  --metadata test=end-to-end \
  --mock-mode true
"

# Summary and cleanup
print_header "Test Summary"
echo -e "${GREEN}Tests completed.${NC}"
echo -e "${YELLOW}Temporary test files are in: ${TEST_DIR}${NC}"
echo -e "Run the following to clean up:"
echo -e "${YELLOW}rm -rf ${TEST_DIR}${NC}"
