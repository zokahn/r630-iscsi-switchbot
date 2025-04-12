#!/bin/bash
# validate_openshift_config.sh - Script to validate OpenShift install configurations
# This script validates OpenShift configurations for SNO deployments using multiple methods

set -e

# Default values
CONFIG_FILE=""
VERBOSE=false
INSTALLER_CHECK=true
POLICY_CHECK=true
TEMP_DIR=""
LOG_FILE=""
BASIC_CHECK=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Help message
function show_help() {
    echo "Usage: $0 [options] --config <config-file>"
    echo ""
    echo "This script validates OpenShift configuration files using multiple methods."
    echo ""
    echo "Options:"
    echo "  -c, --config FILE         Configuration file to validate (required)"
    echo "  -l, --log FILE            Log file for validation output"
    echo "  -v, --verbose             Display detailed validation output"
    echo "  --skip-installer          Skip OpenShift installer validation"
    echo "  --skip-policy             Skip OPA/Conftest policy validation"
    echo "  --skip-basic              Skip basic YAML and field validation"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --config config/deployments/r630-01/r630-01-humpty-20250412223919.yaml"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -l|--log)
            LOG_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --skip-installer)
            INSTALLER_CHECK=false
            shift
            ;;
        --skip-policy)
            POLICY_CHECK=false
            shift
            ;;
        --skip-basic)
            BASIC_CHECK=false
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

# Check if config file is provided
if [ -z "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Configuration file not specified${NC}"
    show_help
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Configuration file '$CONFIG_FILE' not found${NC}"
    exit 1
fi

# Setup logging
if [ -z "$LOG_FILE" ]; then
    TIMESTAMP=$(date +"%Y%m%d%H%M%S")
    LOG_FILE="validation_${TIMESTAMP}.log"
fi

log() {
    echo "$@" | tee -a "$LOG_FILE"
    if [ "$VERBOSE" = true ]; then
        echo "$@"
    fi
}

log_header() {
    echo -e "\n----- $1 -----" | tee -a "$LOG_FILE"
    if [ "$VERBOSE" = true ]; then
        echo -e "\n----- $1 -----"
    fi
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗ $1${NC}" | tee -a "$LOG_FILE"
}

# Create temp directory
create_temp_dir() {
    TEMP_DIR=$(mktemp -d)
    log "Created temporary directory: $TEMP_DIR"
}

# Clean up temp directory
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        log "Removed temporary directory: $TEMP_DIR"
    fi
}

# Set up cleanup on exit
trap cleanup EXIT

# Basic YAML syntax and field validation using simple grep checks
validate_basic() {
    log_header "Basic YAML and Field Validation"
    
    # Check if file is valid YAML by trying to parse it
    if ! grep -q "apiVersion: v1" "$CONFIG_FILE"; then
        log_error "Missing required field: apiVersion"
        return 1
    fi
    
    # Essential field checks for SNO deployment
    ERRORS=0
    WARNINGS=0
    
    # Required fields
    if ! grep -q "baseDomain:" "$CONFIG_FILE"; then
        log_error "Missing required field: baseDomain"
        ERRORS=$((ERRORS + 1))
    fi
    
    if ! grep -q "metadata:" "$CONFIG_FILE"; then
        log_error "Missing required field: metadata"
        ERRORS=$((ERRORS + 1))
    fi
    
    if ! grep -q "networking:" "$CONFIG_FILE"; then
        log_error "Missing required field: networking"
        ERRORS=$((ERRORS + 1))
    fi
    
    if ! grep -q "networkType: OVNKubernetes" "$CONFIG_FILE"; then
        log_error "Missing or incorrect required field: networking.networkType"
        log_error "Required value: 'OVNKubernetes'"
        ERRORS=$((ERRORS + 1))
    fi
    
    if ! grep -q "platform:" "$CONFIG_FILE"; then
        log_error "Missing required field: platform"
        ERRORS=$((ERRORS + 1))
    fi
    
    # SNO specific fields
    if ! grep -q "sno:" "$CONFIG_FILE"; then
        log_error "Missing required field: sno"
        ERRORS=$((ERRORS + 1))
    else
        # Check sno required fields
        if ! grep -q "nodeIP:" "$CONFIG_FILE"; then
            log_error "Missing required field: sno.nodeIP"
            ERRORS=$((ERRORS + 1))
        fi
        
        if ! grep -q "apiVIP:" "$CONFIG_FILE"; then
            log_error "Missing required field: sno.apiVIP"
            ERRORS=$((ERRORS + 1))
        fi
        
        if ! grep -q "ingressVIP:" "$CONFIG_FILE"; then
            log_error "Missing required field: sno.ingressVIP"
            ERRORS=$((ERRORS + 1))
        fi
        
        if ! grep -q "domain:" "$CONFIG_FILE"; then
            log_error "Missing required field: sno.domain"
            ERRORS=$((ERRORS + 1))
        fi
        
        if ! grep -q "hostname:" "$CONFIG_FILE"; then
            log_error "Missing required field: sno.hostname"
            ERRORS=$((ERRORS + 1))
        fi
        
        # Check for MAC address
        if ! grep -q "macAddress:" "$CONFIG_FILE"; then
            log_warning "Missing field: sno.macAddress"
            WARNINGS=$((WARNINGS + 1))
        fi
        
        # Check for DNS records
        if ! grep -q "dnsRecords:" "$CONFIG_FILE"; then
            log_warning "Missing field: sno.dnsRecords"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
    
    # Check for installation disk
    if ! grep -q "bootstrapInPlace:" "$CONFIG_FILE"; then
        log_warning "Missing field: bootstrapInPlace"
        WARNINGS=$((WARNINGS + 1))
    else
        if ! grep -q "installationDisk:" "$CONFIG_FILE"; then
            log_warning "Missing field: bootstrapInPlace.installationDisk"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
    
    # Check controlPlane replicas (should be 1 for SNO)
    if grep -q "controlPlane:" "$CONFIG_FILE"; then
        if ! grep -q "replicas: 1" "$CONFIG_FILE"; then
            log_warning "controlPlane replicas should be 1 for SNO deployments"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
    
    # Display validation results
    if [ $ERRORS -eq 0 ]; then
        log_success "Basic validation passed"
        
        if [ $WARNINGS -gt 0 ]; then
            log_warning "Found $WARNINGS warnings"
        fi
        
        return 0
    else
        log_error "Basic validation failed with $ERRORS errors"
        return 1
    fi
}

# OpenShift installer validation
validate_installer() {
    log_header "OpenShift Installer Validation"
    
    # Check if openshift-install is available
    if ! command -v openshift-install &> /dev/null; then
        log_warning "openshift-install not found, skipping installer validation"
        return 0
    fi
    
    mkdir -p "$TEMP_DIR/installer"
    cp "$CONFIG_FILE" "$TEMP_DIR/installer/install-config.yaml"
    
    log "Running openshift-install validation"
    if openshift-install agent create --dir="$TEMP_DIR/installer" --log-level=debug; then
        log_success "OpenShift installer validation passed"
        return 0
    else
        log_error "OpenShift installer validation failed"
        return 1
    fi
}

# OPA/Conftest policy validation
validate_policy() {
    log_header "Policy-Based Validation (OPA/Conftest)"
    
    # Check if conftest is available
    if ! command -v conftest &> /dev/null; then
        log_warning "conftest not found, skipping policy validation"
        return 0
    fi
    
    # Create policies for SNO validation
    mkdir -p "$TEMP_DIR/policy"
    cat > "$TEMP_DIR/policy/sno.rego" << 'EOF'
package main

# SNO networking must use OVNKubernetes
deny[msg] {
    input.networking.networkType != "OVNKubernetes"
    msg = "networkType must be OVNKubernetes for SNO deployments"
}

# ControlPlane replicas must be 1
deny[msg] {
    input.controlPlane.replicas != 1
    msg = "controlPlane.replicas must be 1 for SNO deployments"
}

# Compute replicas should be 0
deny[msg] {
    count(input.compute) > 0
    input.compute[0].replicas != 0
    msg = "compute replicas should be 0 for SNO deployments"
}

# SNO configuration must include nodeIP
deny[msg] {
    not input.sno.nodeIP
    msg = "sno.nodeIP must be specified"
}

# Installation disk should be specified
warn[msg] {
    not input.bootstrapInPlace.installationDisk
    msg = "Installation disk should be specified in bootstrapInPlace.installationDisk"
}

# MAC address should be specified
warn[msg] {
    not input.sno.macAddress
    msg = "MAC address should be specified in sno.macAddress"
}

# DNS records should be specified
warn[msg] {
    not input.sno.dnsRecords
    msg = "DNS records should be specified in sno.dnsRecords"
}
EOF

    log "Running conftest policy validation"
    if conftest test "$CONFIG_FILE" --policy "$TEMP_DIR/policy" --no-color; then
        log_success "Policy validation passed"
        return 0
    else
        log_warning "Policy validation found issues"
        return 1
    fi
}

# Main validation function
run_validation() {
    local basic_result=0
    local installer_result=0
    local policy_result=0
    local overall_result=0
    
    log_header "Starting OpenShift Configuration Validation"
    log "Configuration file: $CONFIG_FILE"
    log "Log file: $LOG_FILE"
    log "Date: $(date)"
    log ""
    
    # Create temp directory
    create_temp_dir
    
    # Run validations
    if [ "$BASIC_CHECK" = true ]; then
        validate_basic
        basic_result=$?
    else
        log_warning "Skipping basic validation"
    fi
    
    if [ "$INSTALLER_CHECK" = true ]; then
        validate_installer
        installer_result=$?
    else
        log_warning "Skipping installer validation"
    fi
    
    if [ "$POLICY_CHECK" = true ]; then
        validate_policy
        policy_result=$?
    else
        log_warning "Skipping policy validation"
    fi
    
    # Calculate overall result
    overall_result=$((basic_result + installer_result))
    
    log_header "Validation Summary"
    if [ "$BASIC_CHECK" = true ]; then
        if [ $basic_result -eq 0 ]; then
            log_success "Basic validation: Passed"
        else
            log_error "Basic validation: Failed"
        fi
    fi
    
    if [ "$INSTALLER_CHECK" = true ]; then
        if [ $installer_result -eq 0 ]; then
            log_success "Installer validation: Passed"
        else
            log_error "Installer validation: Failed"
        fi
    fi
    
    if [ "$POLICY_CHECK" = true ]; then
        if [ $policy_result -eq 0 ]; then
            log_success "Policy validation: Passed"
        else
            log_warning "Policy validation: Warnings found"
        fi
    fi
    
    if [ $overall_result -eq 0 ]; then
        log_success "Overall validation: Passed"
        echo -e "${GREEN}Configuration validation successful${NC}"
        return 0
    else
        log_error "Overall validation: Failed"
        echo -e "${RED}Configuration validation failed${NC}"
        return 1
    fi
}

# Run the validation
run_validation
