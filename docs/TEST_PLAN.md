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
