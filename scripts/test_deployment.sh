#!/bin/bash
# test_deployment.sh - Script to run deployment tests with predefined data
# This script simplifies the process of testing deployments with sample data

set -e

# Default values
CLUSTER_NAME="test-cluster"
BASE_DOMAIN="example.com"
NODE_IP="192.168.1.100"
IDRAC_IP="192.168.1.200"
MAC_ADDRESS=""
SERVER_ID="01"
REBOOT="false"
TEST_TYPE="config-only"  # config-only, check-only, full-deployment
BOOT_METHOD="iscsi"
OCP_VERSION="4.18"

# Help message
function show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "This script simplifies testing OpenShift deployments with sample data."
    echo ""
    echo "Options:"
    echo "  -n, --name NAME             Cluster name (default: test-cluster)"
    echo "  -d, --domain DOMAIN         Base domain (default: example.com)"
    echo "  -i, --node-ip IP            Node IP address (default: 192.168.1.100)"
    echo "  -r, --idrac-ip IP           iDRAC IP address (default: 192.168.1.200)"
    echo "  -m, --mac-address MAC       MAC address for primary interface"
    echo "  -s, --server-id ID          Server identifier (default: 01)"
    echo "  -b, --boot-method METHOD    Boot method: iscsi, iso, netboot (default: iscsi)"
    echo "  -v, --ocp-version VERSION   OpenShift version (default: 4.18)"
    echo "  -t, --test-type TYPE        Test type: config-only, check-only, full-deployment (default: config-only)"
    echo "  -R, --reboot                Reboot the server after configuration (default: false)"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --name humpty --domain omnisack.nl --node-ip 192.168.2.90 --idrac-ip 192.168.2.230 --mac-address e4:43:4b:44:5b:10"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -n|--name)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        -d|--domain)
            BASE_DOMAIN="$2"
            shift 2
            ;;
        -i|--node-ip)
            NODE_IP="$2"
            shift 2
            ;;
        -r|--idrac-ip)
            IDRAC_IP="$2"
            shift 2
            ;;
        -m|--mac-address)
            MAC_ADDRESS="$2"
            shift 2
            ;;
        -s|--server-id)
            SERVER_ID="$2"
            shift 2
            ;;
        -b|--boot-method)
            BOOT_METHOD="$2"
            shift 2
            ;;
        -v|--ocp-version)
            OCP_VERSION="$2"
            shift 2
            ;;
        -t|--test-type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -R|--reboot)
            REBOOT="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Create log file
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
LOG_FILE="deployment_test_${CLUSTER_NAME}_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Echo to both console and log file
log() {
    echo "$@" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✓ $@${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗ $@${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠ $@${NC}" | tee -a "$LOG_FILE"
}

log "--- OpenShift Multiboot System Test Deployment Log ---"
log "Date: $(date +"%Y-%m-%d %H:%M:%S")"
log "Test ID: TDEP${TIMESTAMP}"
log "Configuration:"
log "  - Cluster name: ${CLUSTER_NAME}"
log "  - Base domain: ${BASE_DOMAIN}"
log "  - Node IP: ${NODE_IP}"
log "  - iDRAC IP: ${IDRAC_IP}"
if [ -n "$MAC_ADDRESS" ]; then
    log "  - MAC address: ${MAC_ADDRESS}"
fi
log "  - Server ID: ${SERVER_ID}"
log "  - OpenShift version: ${OCP_VERSION}"
log "  - Boot method: ${BOOT_METHOD}"
log "  - Test type: ${TEST_TYPE}"
log ""

# Generate configuration
log "Step 1: Generating configuration..."

CMD="./scripts/generate_openshift_values.py \
  --node-ip ${NODE_IP} \
  --server-id ${SERVER_ID} \
  --cluster-name ${CLUSTER_NAME} \
  --base-domain ${BASE_DOMAIN} \
  --hostname ${CLUSTER_NAME} \
  --api-vip ${NODE_IP} \
  --ingress-vip ${NODE_IP}"

if [ -n "$MAC_ADDRESS" ]; then
    CMD="${CMD} --mac-address ${MAC_ADDRESS}"
fi

CMD="${CMD} --installation-disk /dev/sda"
CMD="${CMD} --generate-default-dns-records"

log "Running command: ${CMD}"
if ! eval $CMD 2>&1 | tee -a "$LOG_FILE"; then
    log_error "Configuration generation failed. See the output above for details."
    log "Test failed at: $(date +"%Y-%m-%d %H:%M:%S")"
    log "Results saved to: ${LOG_FILE}"
    echo ""
    echo "⛔ Test failed. Log file saved to: ${LOG_FILE}"
    exit 1
fi

# Get the generated config file
CONFIG_FILE=$(find config/deployments/r630-${SERVER_ID}/ -name "r630-${SERVER_ID}-${CLUSTER_NAME}-*.yaml" | sort -r | head -n 1)
if [ -z "$CONFIG_FILE" ]; then
    log_error "Could not find generated configuration file."
    log "Test failed at: $(date +"%Y-%m-%d %H:%M:%S")"
    log "Results saved to: ${LOG_FILE}"
    echo ""
    echo "⛔ Test failed. Log file saved to: ${LOG_FILE}"
    exit 1
fi
log "Generated configuration file: ${CONFIG_FILE}"
log ""

# Validate configuration
log "Step 2: Validating configuration..."
CMD="./scripts/validate_openshift_config.sh --config ${CONFIG_FILE} --skip-installer"
if [ "$VERBOSE" = "true" ]; then
    CMD="${CMD} --verbose"
fi

log "Running command: ${CMD}"
if eval $CMD 2>&1 | tee -a "$LOG_FILE"; then
    log_success "Configuration validation passed"
else
    log_warning "Configuration validation found issues, see validation log for details"
    if [ "$TEST_TYPE" = "full-deployment" ]; then
        log_warning "Proceeding with deployment despite validation issues"
    fi
fi
log ""

# Check boot method availability
if [ "$TEST_TYPE" = "check-only" ] || [ "$TEST_TYPE" = "full-deployment" ]; then
    log "Step 3: Checking boot method availability..."
    CMD="./scripts/switch_openshift.py \
      --server ${IDRAC_IP} \
      --method ${BOOT_METHOD} \
      --version ${OCP_VERSION} \
      --check-only"
      
    log "Running command: ${CMD}"
    eval $CMD 2>&1 | tee -a "$LOG_FILE"
    log ""
fi

# Execute deployment if requested
if [ "$TEST_TYPE" = "full-deployment" ]; then
    log "Step 4: Executing deployment..."
    CMD="./scripts/switch_openshift.py \
      --server ${IDRAC_IP} \
      --method ${BOOT_METHOD} \
      --version ${OCP_VERSION}"
      
    if [ "$REBOOT" = "true" ]; then
        CMD="${CMD} --reboot"
    fi
    
    log "Running command: ${CMD}"
    eval $CMD 2>&1 | tee -a "$LOG_FILE"
    log ""
fi

log "Test completed at: $(date +"%Y-%m-%d %H:%M:%S")"
log "Results saved to: ${LOG_FILE}"
echo ""
echo -e "${GREEN}✓ Test completed successfully.${NC} Log file saved to: ${LOG_FILE}"
