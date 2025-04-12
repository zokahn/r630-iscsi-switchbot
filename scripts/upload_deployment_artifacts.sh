#!/bin/bash
# upload_deployment_artifacts.sh - Collects and uploads deployment artifacts to TrueNAS
# This script gathers logs, credentials, and metadata from an OpenShift deployment 
# and stores them in an organized directory structure on TrueNAS

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
TRUENAS_IP="192.168.2.245"
TRUENAS_USER="root"
REMOTE_BASE_PATH="/mnt/tank/deployment_artifacts"
LOCAL_ARTIFACTS_DIR="/tmp/deployment_artifacts"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
MOCK_MODE=false  # For testing without actually connecting to TrueNAS

# Print usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --server-id ID        Server identifier (e.g., 01, 02) (required)"
    echo "  --deployment-name NAME Type of deployment (e.g., sno, ha) (default: sno)"
    echo "  --timestamp TIME      Deployment timestamp (default: current time)"
    echo "  --log-file PATH       Path to deployment log file"
    echo "  --kubeconfig PATH     Path to kubeconfig file"
    echo "  --artifacts-dir PATH  Path to additional artifacts directory"
    echo "  --truenas-ip IP       TrueNAS IP address (default: $TRUENAS_IP)"
    echo "  --truenas-user USER   TrueNAS SSH username (default: $TRUENAS_USER)"
    echo "  --ssh-key PATH        Path to SSH private key for TrueNAS"
    echo "  --metadata KEY=VALUE  Add custom metadata (can be specified multiple times)"
    echo "  --mock-mode BOOL      Test mode - don't connect to TrueNAS (default: false)"
    echo ""
    echo "Example:"
    echo "  $0 --server-id 01 --deployment-name sno --log-file ./deployment.log"
}

# Parse command line arguments
SERVER_ID=""
DEPLOYMENT_NAME="sno"
LOG_FILE=""
KUBECONFIG_FILE=""
ARTIFACTS_DIR=""
SSH_KEY=""
METADATA_KEYS=()
METADATA_VALUES=()

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
        --timestamp)
        TIMESTAMP="$2"
        shift
        shift
        ;;
        --log-file)
        LOG_FILE="$2"
        shift
        shift
        ;;
        --kubeconfig)
        KUBECONFIG_FILE="$2"
        shift
        shift
        ;;
        --artifacts-dir)
        ARTIFACTS_DIR="$2"
        shift
        shift
        ;;
        --truenas-ip)
        TRUENAS_IP="$2"
        shift
        shift
        ;;
        --truenas-user)
        TRUENAS_USER="$2"
        shift
        shift
        ;;
        --ssh-key)
        SSH_KEY="$2"
        shift
        shift
        ;;
        --metadata)
        # Parse KEY=VALUE format and store in parallel arrays
        IFS='=' read -r -a meta_parts <<< "$2"
        if [ ${#meta_parts[@]} -ge 2 ]; then
            METADATA_KEYS+=("${meta_parts[0]}")
            METADATA_VALUES+=("${meta_parts[1]}")
        else
            echo -e "${RED}Error: Metadata must be in KEY=VALUE format${NC}"
            exit 1
        fi
        shift
        shift
        ;;
        --mock-mode)
        MOCK_MODE="$2"
        shift
        shift
        ;;
        -h|--help)
        usage
        exit 0
        ;;
        *)
        # Unknown option
        echo -e "${RED}Unknown option: $key${NC}"
        usage
        exit 1
        ;;
    esac
done

# Validate required parameters
if [ -z "$SERVER_ID" ]; then
    echo -e "${RED}Error: Server ID is required${NC}"
    usage
    exit 1
fi

# Create deployment ID
DEPLOYMENT_ID="r630-${SERVER_ID}-${DEPLOYMENT_NAME}-${TIMESTAMP}"
echo -e "${BLUE}Using deployment ID: ${DEPLOYMENT_ID}${NC}"

# Create local directory structure for artifacts
LOCAL_DEPLOYMENT_DIR="${LOCAL_ARTIFACTS_DIR}/${DEPLOYMENT_ID}"
mkdir -p "${LOCAL_DEPLOYMENT_DIR}/logs"
mkdir -p "${LOCAL_DEPLOYMENT_DIR}/auth"
mkdir -p "${LOCAL_DEPLOYMENT_DIR}/metadata"
echo -e "${GREEN}Created local artifact directory: ${LOCAL_DEPLOYMENT_DIR}${NC}"

# Copy deployment log if provided
if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
    cp "$LOG_FILE" "${LOCAL_DEPLOYMENT_DIR}/logs/"
    echo -e "${GREEN}Copied deployment log: ${LOG_FILE}${NC}"
else
    echo -e "${YELLOW}No deployment log provided or file not found${NC}"
fi

# Copy kubeconfig if provided
if [ -n "$KUBECONFIG_FILE" ] && [ -f "$KUBECONFIG_FILE" ]; then
    cp "$KUBECONFIG_FILE" "${LOCAL_DEPLOYMENT_DIR}/auth/kubeconfig"
    echo -e "${GREEN}Copied kubeconfig: ${KUBECONFIG_FILE}${NC}"
else
    echo -e "${YELLOW}No kubeconfig provided or file not found${NC}"
fi

# Copy additional artifacts if provided
if [ -n "$ARTIFACTS_DIR" ] && [ -d "$ARTIFACTS_DIR" ]; then
    cp -r "$ARTIFACTS_DIR"/* "${LOCAL_DEPLOYMENT_DIR}/"
    echo -e "${GREEN}Copied additional artifacts from: ${ARTIFACTS_DIR}${NC}"
else
    echo -e "${YELLOW}No additional artifacts directory provided or directory not found${NC}"
fi

# Generate metadata.json
echo -e "${BLUE}Generating metadata...${NC}"
metadata_file="${LOCAL_DEPLOYMENT_DIR}/metadata.json"

# Start with basic metadata
cat > "$metadata_file" << EOF
{
  "deployment_id": "${DEPLOYMENT_ID}",
  "server_id": "${SERVER_ID}",
  "deployment_name": "${DEPLOYMENT_NAME}",
  "timestamp": "${TIMESTAMP}",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
EOF

# Add custom metadata if any
if [ ${#METADATA_KEYS[@]} -gt 0 ]; then
    for i in "${!METADATA_KEYS[@]}"; do
        key="${METADATA_KEYS[$i]}"
        value="${METADATA_VALUES[$i]}"
        # Append to metadata file, properly handling commas
        sed -i '' -e '$s/}$/,/' "$metadata_file"
        echo "  \"$key\": \"$value\"" >> "$metadata_file"
    done
fi

# Close the JSON object
echo "}" >> "$metadata_file"

echo -e "${GREEN}Generated metadata file: ${metadata_file}${NC}"

# If in mock mode, skip actual TrueNAS interaction
if [ "$MOCK_MODE" = "true" ]; then
    echo -e "${YELLOW}Running in mock mode - skipping TrueNAS upload${NC}"
    echo -e "${GREEN}Would upload to: ${REMOTE_BASE_PATH}/r630-${SERVER_ID}/${DEPLOYMENT_ID}/${NC}"
    echo -e "${BLUE}Local artifacts are available at: ${LOCAL_DEPLOYMENT_DIR}${NC}"
    exit 0
fi

# Create remote directory structure on TrueNAS
echo -e "${BLUE}Creating remote directory structure on TrueNAS...${NC}"

ssh_cmd="ssh"
if [ -n "$SSH_KEY" ]; then
    ssh_cmd="ssh -i $SSH_KEY"
fi

server_dir="${REMOTE_BASE_PATH}/r630-${SERVER_ID}"
deployment_dir="${server_dir}/${DEPLOYMENT_ID}"

# Create directories on TrueNAS
$ssh_cmd ${TRUENAS_USER}@${TRUENAS_IP} "mkdir -p ${server_dir} ${deployment_dir}/logs ${deployment_dir}/auth ${deployment_dir}/metadata"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create remote directories on TrueNAS${NC}"
    exit 1
fi

echo -e "${GREEN}Created remote directories on TrueNAS${NC}"

# Upload artifacts to TrueNAS
echo -e "${BLUE}Uploading artifacts to TrueNAS...${NC}"

scp_cmd="scp"
if [ -n "$SSH_KEY" ]; then
    scp_cmd="scp -i $SSH_KEY"
fi

# Upload the entire artifacts directory
$scp_cmd -r "${LOCAL_DEPLOYMENT_DIR}"/* "${TRUENAS_USER}@${TRUENAS_IP}:${deployment_dir}/"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to upload artifacts to TrueNAS${NC}"
    exit 1
fi

echo -e "${GREEN}Successfully uploaded artifacts to TrueNAS${NC}"
echo -e "${GREEN}Artifacts location: ${deployment_dir}${NC}"

# Clean up local artifacts
echo -e "${BLUE}Cleaning up local artifacts...${NC}"
rm -rf "${LOCAL_ARTIFACTS_DIR}"

echo -e "${GREEN}Deployment artifacts successfully uploaded to TrueNAS${NC}"
echo -e "${GREEN}Server directory: ${server_dir}${NC}"
echo -e "${GREEN}Deployment directory: ${deployment_dir}${NC}"
