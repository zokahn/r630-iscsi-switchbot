#!/bin/bash
# test_setup.sh - Test script for OpenShift multiboot functionality
# This script runs different commands in test/dry-run mode to verify functionality

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}== $1${NC}"
    echo -e "${BLUE}======================================================================${NC}"
}

# Function to run a command with explanations
run_test_command() {
    local description=$1
    local command=$2
    
    echo -e "\n${YELLOW}$description${NC}"
    echo -e "${GREEN}> $command${NC}"
    echo -e "${YELLOW}Executing...${NC}"
    
    eval "$command"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Command executed successfully${NC}"
    else
        echo -e "${RED}✗ Command failed${NC}"
    fi
}

# Introduction
print_header "OpenShift Multiboot System Test Script"
echo "This script will run various commands in test/dry-run mode to verify the"
echo "functionality of the OpenShift multiboot system without making actual changes."

# Test TrueNAS autodiscovery
print_header "Testing TrueNAS Autodiscovery"
run_test_command "Discovering TrueNAS configuration without making changes:" \
    "./scripts/truenas_autodiscovery.py --discover-only --host 192.168.2.245 --port 444"

# Test iSCSI target configuration check
print_header "Testing iSCSI Target Configuration"
run_test_command "Checking if OpenShift 4.18 iSCSI target is properly configured:" \
    "./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --check-only"

# Test ISO availability check
print_header "Testing ISO Availability"
run_test_command "Checking if OpenShift 4.18 ISO is available (note: this will likely fail unless the ISO exists):" \
    "./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18 --check-only"

# Test generate_openshift_iso.py (with --skip-upload to avoid actual uploads)
print_header "Testing OpenShift ISO Generation"
echo -e "${YELLOW}Note: The following command will not be executed automatically as it requires a pull secret.${NC}"
echo -e "${GREEN}> ./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230 --skip-upload --output-dir ./test_output${NC}"
echo -e "${YELLOW}To run this test, execute the above command manually with your pull secret.${NC}"

# Testing switch_openshift.py with dry run
print_header "Testing OpenShift Version Switching"
echo -e "${YELLOW}The following commands demonstrate how to switch OpenShift versions.${NC}"
echo -e "${YELLOW}They are shown for reference but not executed to avoid actual system changes.${NC}"
echo -e "${GREEN}# Configure for ISO boot:${NC}"
echo -e "${GREEN}./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18${NC}"
echo -e "${GREEN}# Switch to OpenShift 4.18 via iSCSI:${NC}"
echo -e "${GREEN}./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18${NC}"
echo -e "${GREEN}# Switch to OpenShift 4.17 via iSCSI:${NC}"
echo -e "${GREEN}./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.17${NC}"
echo -e "${GREEN}# Boot using netboot:${NC}"
echo -e "${GREEN}./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --reboot${NC}"

# Summary and next steps
print_header "Testing Summary and Next Steps"
echo -e "The OpenShift multiboot system has been installed and initial tests have been performed."
echo -e "\n${GREEN}Next steps:${NC}"
echo -e "1. Run the TrueNAS autodiscovery script to set up your TrueNAS Scale server:"
echo -e "   ${GREEN}./scripts/truenas_autodiscovery.py --host 192.168.2.245 --port 444${NC}"
echo -e "2. Generate an OpenShift ISO for installation:"
echo -e "   ${GREEN}./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230${NC}"
echo -e "3. Configure your R630 server to boot from the ISO:"
echo -e "   ${GREEN}./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18 --reboot${NC}"
echo -e "4. After installation, create a snapshot or clone of the installation in TrueNAS"
echo -e "5. Set up netboot custom menu:"
echo -e "   ${GREEN}./scripts/setup_netboot.py --truenas-ip 192.168.2.245${NC}"
echo -e "6. Switch between different OpenShift versions or boot methods using the switch_openshift.py script"
