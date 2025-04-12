# Test Plan for Multiboot System

This document outlines a structured approach to testing the multiboot system implementation. We'll test each component step by step to verify functionality for both OpenShift deployments and alternative OS options through netboot.xyz.

## Prerequisites

- Access to TrueNAS Scale server (192.168.2.245)
- Access to Dell R630 servers (192.168.2.230, 192.168.2.232)
- Admin credentials for TrueNAS Scale
- Red Hat account with pull secret for OpenShift

## 1. TrueNAS Authentication

### 1.1 Test truenas_wrapper.sh Setup

```bash
# Run wrapper script for first-time setup
./scripts/truenas_wrapper.sh
```

Expected result:
- Script should prompt for TrueNAS host and authentication method
- User should be guided through credentials setup
- Configuration file should be created at ~/.config/truenas/auth.json

### 1.2 Test Authentication with API Key

After generating an API key in TrueNAS UI:

```bash
# Create configuration with API key
mkdir -p ~/.config/truenas
cat > ~/.config/truenas/auth.json << EOF
{
  "host": "192.168.2.245",
  "api_key": "YOUR_ACTUAL_API_KEY"
}
EOF
chmod 600 ~/.config/truenas/auth.json

# Test wrapper with discovery command
./scripts/truenas_wrapper.sh autodiscovery --discover-only
```

Expected result:
- Script should connect to TrueNAS successfully
- Should display discovered pools, datasets, zvols, etc.

## 2. TrueNAS Configuration

### 2.1 Test TrueNAS Autodiscovery

```bash
# Run autodiscovery in discover-only mode first
./scripts/truenas_wrapper.sh autodiscovery --discover-only
```

Expected result:
- Script should analyze existing TrueNAS configuration
- Should show what changes would be made for OpenShift multiboot setup

### 2.2 Apply TrueNAS Configuration

```bash
# Apply needed changes to TrueNAS
./scripts/truenas_wrapper.sh autodiscovery --apply
```

Expected result:
- Script should create necessary datasets, zvols, and iSCSI targets
- Should report successful configuration application

## 3. OpenShift ISO Generation

### 3.1 Test ISO Generation Parameters

```bash
# Check help information
./scripts/generate_openshift_iso.py --help
```

Expected result:
- Script should display usage information and required parameters

### 3.2 Generate OpenShift ISO (Dry Run)

```bash
# Test with skip-upload to verify parameters without actually generating
./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230 --skip-upload --output-dir ./test_output
```

Expected result:
- Script should validate parameters
- Should create test_output directory with configuration files
- Should not perform the actual ISO generation (depends on pull secret)

## 4. OpenShift Boot Switching

### 4.1 Test iSCSI Target Check

```bash
# Check if OpenShift 4.18 iSCSI target is properly configured
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --check-only
```

Expected result:
- Script should check if the target exists in configuration
- Should display target information if available

### 4.2 Test ISO Boot Check

```bash
# Check if OpenShift 4.18 ISO is available
./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18 --check-only
```

Expected result:
- Script should check if the ISO is accessible
- Should display ISO status

### 4.3 Test netboot.xyz Boot Configuration

```bash
# Check if netboot.xyz configuration is available
./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --check-only
```

Expected result:
- Script should verify netboot.xyz configuration
- Should display netboot configuration status

### 4.4 Test Multi-Server Operations

```bash
# Check configuration on both servers
for server in 192.168.2.230 192.168.2.232; do
  ./scripts/switch_openshift.py --server $server --method iscsi --version 4.18 --check-only
done
```

Expected result:
- Script should check both servers
- Should display configuration status for each server

## 5. End-to-End Test (Optional)

If time and resources permit:

### 5.1 Generate Actual ISO

```bash
# Generate an actual OpenShift 4.18 ISO (requires pull secret)
./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230
```

### 5.2 Configure Server for ISO Boot

```bash
# Configure server to boot from ISO (without actual reboot)
./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18
```

### 5.3 After Installation (Future Test)

After an OpenShift instance is installed:

```bash
# Switch to iSCSI boot
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18
```

## 6. Deployment Data Testing

This section outlines the procedure for testing deployments using standardized input data sets. These tests validate the system's ability to correctly deploy using various network configurations.

### 6.1 Standardized Input Data Format

Input data for deployment tests should follow this format:

```
api.CLUSTER_NAME.DOMAIN               IP_ADDRESS
api-int.CLUSTER_NAME.DOMAIN           IP_ADDRESS
*.apps.CLUSTER_NAME.DOMAIN            IP_ADDRESS
idrac ip                              IDRAC_IP
MAC (INTERFACE)                       MAC_ADDRESS
DHCP configuration                    [details]
gateway/DNS information               [details]
```

Example:
```
api.humpty.omnisack.nl                192.168.2.90
api-int.humpty.omnisack.nl            192.168.2.90
*.apps.humpty.omnisack.nl             192.168.2.90
idrac ip                              192.168.2.230
MAC (eno2)                            e4:43:4b:44:5b:10
DHCP - fixed on mac .90 - humpty hostname
gateway 192.168.2.254, also dns
```

### 6.2 Deployment Test Procedure

#### Step 1: Generate Configuration

Create the OpenShift installation configuration file using the test data:

```bash
./scripts/generate_openshift_values.py \
  --node-ip 192.168.2.90 \
  --server-id 01 \
  --cluster-name humpty \
  --base-domain omnisack.nl \
  --hostname humpty \
  --api-vip 192.168.2.90 \
  --ingress-vip 192.168.2.90
```

#### Step 2: Verify Configuration

Examine the generated configuration file to ensure test data was correctly integrated:

```bash
# Path follows the pattern:
cat config/deployments/r630-01/r630-01-humpty-TIMESTAMP.yaml
```

Key verification points:
- DNS entries match the input data
- MAC address and interface configuration are correct
- Network settings align with provided data

#### Step 3: Configure Boot Method

Set up the server to boot using one of the available methods:

```bash
# For iSCSI boot:
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --check-only

# For ISO boot:
./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18 --check-only

# For netboot:
./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --check-only
```

#### Step 4: Initiate Deployment (Optional)

If performing actual deployment:

```bash
# Configure boot and reboot
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --reboot
```

### 6.3 Test Results Tracking

Document each deployment test in a standardized format:

| Test Date | Cluster Name | DNS Domain | Node IP | iDRAC IP | Boot Method | Status | Notes |
|-----------|--------------|------------|---------|----------|------------|--------|-------|
| 2025-04-12 | humpty | omnisack.nl | 192.168.2.90 | 192.168.2.230 | iscsi | Success | Initial test deployment |

### 6.4 Common Test Scenarios

Test deployments with different network configurations:
- Different node IPs, MAC addresses, and network interfaces
- Various DNS domain settings
- Different hostname configurations
- All three boot methods (iSCSI, ISO, netboot)

## 7. Configuration Validation

The test plan includes validation of OpenShift configurations before deployment to catch issues early.

### 7.1 Basic Configuration Validation

```bash
# Validate a configuration file with basic checks
./scripts/validate_openshift_config.sh --config config/deployments/r630-01/r630-01-humpty-TIMESTAMP.yaml
```

Expected result:
- Script should verify required fields are present
- Should check that networking is properly configured
- Should validate SNO-specific settings
- Should report any errors or warnings

### 7.2 Advanced Validation Techniques

If available, additional validation methods can be used:

```bash
# Use the OpenShift installer for validation (if available)
./scripts/validate_openshift_config.sh --config config/deployments/r630-01/r630-01-humpty-TIMESTAMP.yaml --skip-policy
```

```bash
# Use OPA/Conftest for policy validation (if available)
./scripts/validate_openshift_config.sh --config config/deployments/r630-01/r630-01-humpty-TIMESTAMP.yaml --skip-installer
```

Expected result:
- More thorough validation of configuration
- Policy-based checks for best practices
- Verification against OpenShift installer requirements

### 7.3 Automated Testing with Validation

```bash
# Run a full test with validation
./scripts/test_deployment.sh \
  --name test-cluster \
  --domain example.com \
  --node-ip 192.168.2.90 \
  --idrac-ip 192.168.2.230 \
  --mac-address e4:43:4b:44:5b:10 \
  --boot-method iscsi \
  --test-type check-only
```

Expected result:
- Automated generation of configuration
- Validation of the configuration
- Boot method verification
- Comprehensive test log

## Test Results Documentation

Document test results with the following format:

| Test # | Description | Status | Notes |
|--------|-------------|--------|-------|
| 1.1    | truenas_wrapper.sh Setup | | |
| 1.2    | API Key Authentication | | |
| 2.1    | TrueNAS Autodiscovery | | |
| 2.2    | TrueNAS Configuration | | |
| 3.1    | ISO Gen Parameters | | |
| 3.2    | ISO Generation | | |
| 4.1    | iSCSI Target Check | | |
| 4.2    | ISO Boot Check | | |
| 4.3    | netboot.xyz Config | | |
| 4.4    | Multi-Server Ops | | |
| 5.1    | Actual ISO Generation | | |
| 5.2    | ISO Boot Config | | |
| 5.3    | iSCSI Boot Switch | | |
| 5.4    | Netboot Boot Test | | |
| 7.1    | Basic Config Validation | | |
| 7.2    | Installer Validation | | |
| 7.3    | Policy Validation | | |
