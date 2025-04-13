# iSCSI and OpenShift Integration Guide

This document describes how to use the integrated workflow for creating iSCSI targets and deploying OpenShift on Dell R630 servers. The integration streamlines the process by automatically coordinating iSCSI target creation, iSCSI boot configuration, and OpenShift agent-based installation.

## Overview

The integration process addresses several challenges:

1. **Device Path Consistency**: Ensures that iSCSI targets are consistently mapped to expected device paths
2. **Configuration Coordination**: Automatically generates matching iSCSI and OpenShift configurations
3. **Reduced Manual Steps**: Integrates multiple scripts into a single workflow

## Prerequisites

- TrueNAS server (192.168.2.245) with iSCSI service enabled
- Dell R630 server with iDRAC access
- Network connectivity between all components
- OpenShift pull secret in `~/.openshift/pull-secret`

## Integration Script

The `integrate_iscsi_openshift.py` script ties together iSCSI target creation, iSCSI boot configuration, and OpenShift ISO generation.

### Basic Usage

```bash
./scripts/integrate_iscsi_openshift.py \
  --server-id 01 \
  --hostname humpty \
  --node-ip 192.168.2.90 \
  --mac-address e4:43:4b:44:5b:10 \
  --base-domain omnisack.nl \
  --openshift-version stable
```

This command will:

1. Create an iSCSI target on TrueNAS
2. Configure iSCSI boot on the Dell R630 server via iDRAC
3. Generate OpenShift configuration values with the correct device path
4. Create an OpenShift agent-based installation ISO

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--server-id` | Server ID (e.g., 01) | *Required* |
| `--hostname` | Server hostname | *Required* |
| `--node-ip` | Server IP address | *Required* |
| `--mac-address` | Server MAC address for primary NIC | *Required* |
| `--base-domain` | Base domain for the cluster | example.com |
| `--openshift-version` | OpenShift version | stable |
| `--idrac-ip` | iDRAC IP address | 192.168.2.230 |
| `--idrac-user` | iDRAC username | root |
| `--idrac-password` | iDRAC password | calvin |
| `--truenas-ip` | TrueNAS IP address | 192.168.2.245 |
| `--truenas-user` | TrueNAS username | root |
| `--device-path` | Override iSCSI device path | /dev/sda |
| `--output-dir` | Output directory for generated files | ./test_run_[hostname] |

### Selective Execution

The script supports skipping certain steps if needed:

```bash
./scripts/integrate_iscsi_openshift.py \
  --server-id 01 \
  --hostname humpty \
  --node-ip 192.168.2.90 \
  --mac-address e4:43:4b:44:5b:10 \
  --skip-target-creation \
  --skip-iscsi-config
```

Available skip options:
- `--skip-target-creation`: Skip TrueNAS iSCSI target creation
- `--skip-iscsi-config`: Skip iSCSI boot configuration
- `--skip-iso-generation`: Skip OpenShift ISO generation

## iSCSI Device Mapping

The script maintains a mapping between iSCSI targets and device paths in `config/iscsi_device_mapping.json`. This ensures consistent device paths across reboots and reinstallations.

Example mapping:
```json
{
  "targets": {
    "iqn.2005-10.org.freenas.ctl:iscsi.r630-01.openshift4_18": {
      "server_id": "01",
      "hostname": "humpty",
      "device_path": "/dev/sda",
      "zvol_path": "/dev/zvol/tank/openshift_installations/r630_01_4_18"
    }
  }
}
```

## OpenShift Configuration for iSCSI Boot

The script automatically generates the correct OpenShift agent-based installation configuration with the proper device paths:

1. In `install-config.yaml`:
   ```yaml
   bootstrapInPlace:
     installationDisk: "/dev/sda"  # From device mapping
   ```

2. In `agent-config.yaml`:
   ```yaml
   rootDeviceHints:
     deviceName: "/dev/sda"  # From device mapping
   ```

## Troubleshooting

### Device Path Issues

If the iSCSI device doesn't appear at the expected path:

1. Boot from the OpenShift ISO
2. From the CoreOS live environment, check the actual device path:
   ```bash
   lsblk -f
   ls -l /dev/disk/by-path/*iscsi*
   ```
3. Re-run the integration script with the correct device path:
   ```bash
   ./scripts/integrate_iscsi_openshift.py --device-path /dev/sdX ...
   ```

### iSCSI Boot Issues

If the server doesn't boot from iSCSI:

1. Verify that iSCSI initiator is enabled in the BIOS
2. Verify iSCSI target connectivity:
   ```bash
   iscsiadm -m discovery -t sendtargets -p 192.168.2.245
   ```
3. Check target configuration on TrueNAS

## Examples

### Complete Setup for a New Server

```bash
# Create iSCSI target, configure iSCSI boot, and generate OpenShift ISO
./scripts/integrate_iscsi_openshift.py \
  --server-id 01 \
  --hostname humpty \
  --node-ip 192.168.2.90 \
  --mac-address e4:43:4b:44:5b:10 \
  --base-domain omnisack.nl \
  --openshift-version stable
```

### Regenerate ISO with Existing iSCSI Target

```bash
# Skip target creation and iSCSI boot configuration
./scripts/integrate_iscsi_openshift.py \
  --server-id 01 \
  --hostname humpty \
  --node-ip 192.168.2.90 \
  --mac-address e4:43:4b:44:5b:10 \
  --skip-target-creation \
  --skip-iscsi-config
```

## References

- [OpenShift Agent-Based ISO Generation](OPENSHIFT_ISO_GENERATION.md)
- [R630 iSCSI Boot Guide](R630_ISCSI_BOOT_GUIDE.md)
- [TrueNAS iSCSI Finding Block Devices with OpenShift Agent-Based Installer](TRUENAS_ISCSI_FINDING_BLOCK_DEVICES_USE_OCP_AGENT_BASED.md)
