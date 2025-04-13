#!/bin/bash
# test_minimal_iso.sh - Script to test the generate_minimal_iso.py script
# with the recently created configuration

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== OpenShift Minimal ISO Generator Test =====${NC}"
echo -e "${YELLOW}This script tests the minimal ISO generation with Day 1 configuration focus${NC}"
echo ""

# Check if we already have a configuration
CONFIG_FILE=$(find config/deployments/r630-01/ -name "r630-01-humpty-*.yaml" | sort -r | head -n 1)

if [ -z "$CONFIG_FILE" ]; then
    echo "No existing configuration found, generating one..."
    
    # Generate a basic configuration
    ./scripts/generate_openshift_values.py \
      --node-ip 192.168.2.90 \
      --server-id 01 \
      --cluster-name humpty \
      --base-domain omnisack.nl \
      --hostname humpty \
      --mac-address e4:43:4b:44:5b:10 \
      --installation-disk /dev/sda \
      --generate-default-dns-records
      
    # Get the newly generated config file
    CONFIG_FILE=$(find config/deployments/r630-01/ -name "r630-01-humpty-*.yaml" | sort -r | head -n 1)
else
    echo -e "${GREEN}Using existing configuration:${NC} $CONFIG_FILE"
fi

# Create a test output directory
OUTPUT_DIR="./test_iso_output"
mkdir -p $OUTPUT_DIR

echo ""
echo -e "${BLUE}Testing ISO generation with minimal Day 1 configuration${NC}"
echo -e "Configuration: ${GREEN}$CONFIG_FILE${NC}"
echo -e "Output directory: ${GREEN}$OUTPUT_DIR${NC}"
echo ""

# Run the minimal ISO generator with stable version
# Using "stable" instead of specific version to ensure download works
python3 ./scripts/generate_minimal_iso.py \
  --config $CONFIG_FILE \
  --version stable \
  --output-dir $OUTPUT_DIR \
  --skip-upload

echo ""
echo -e "${BLUE}Test complete. See $OUTPUT_DIR for generated files.${NC}"
echo -e "${YELLOW}Important: This ISO contains only Day 1 configurations.${NC}"
echo -e "${YELLOW}Day 2 operations will need to be performed post-installation.${NC}"
echo -e "${YELLOW}See docs/OPENSHIFT_ISO_GENERATION.md for more details.${NC}"
