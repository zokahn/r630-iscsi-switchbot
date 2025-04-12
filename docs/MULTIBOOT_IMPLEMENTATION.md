# Multiboot System Implementation Plan

This document outlines the detailed implementation plan for a flexible multiboot system using TrueNAS Scale as the storage backend. The system focuses on OpenShift deployment but can be extended to other operating systems through netboot.xyz integration.

## System Overview

The multiboot system will leverage the existing TrueNAS Scale server (192.168.2.245) to provide storage for both installation ISOs and boot disk images. The Dell R630 servers (192.168.2.230, 192.168.2.232) will be configured to boot from various sources:

1. **iSCSI targets** for persistent OpenShift installations
2. **ISO images** for fresh installations
3. **netboot.xyz** for alternative OS options

```
┌───────────────────┐     ┌──────────────────────────────────────┐
│ Dell R630 Servers │     │         TrueNAS Scale Server         │
│  192.168.2.230    │◄────┤             192.168.2.245            │
│  192.168.2.232    │     │                                      │
└───────────────────┘     │ ┌────────────┐  ┌─────────────────┐  │
         │                │ │ iSCSI      │  │ Installation    │  │
         │                │ │ Boot       │  │ ISOs            │  │
         └───────────────►│ │ Targets    │  │                 │  │
                          │ └────────────┘  └─────────────────┘  │
                          │                                      │
                          │ ┌──────────────────────────────────┐ │
                          │ │ netboot.xyz (Network Boot)       │ │
                          │ └──────────────────────────────────┘ │
                          └──────────────────────────────────────┘
```

## TrueNAS Scale Configuration

Based on the discovery performed on TrueNAS Scale (192.168.2.245), we have identified the following:

- TrueNAS Scale version: 24.10.2.1
- Available ZFS pool: "test" (~9TB)
- Existing NFS share for ISOs: /mnt/test/iso
- iSCSI service is running with 2 existing targets

### Storage Structure

We will create the following storage structure:

1. **For OpenShift ISOs**
   - Leverage the existing `test/iso` dataset
   - Create a subdirectory structure for OpenShift versions
   ```
   /mnt/test/iso/openshift/
   ├── 4.16/
   ├── 4.17/
   └── 4.18/
   ```

2. **For OpenShift Boot Disks**
   - Create new zvols for each OpenShift version:
   ```
   test/openshift_installations/
   ├── 4_16_complete  (500GB)
   ├── 4_17_complete  (500GB)
   └── 4_18_complete  (500GB)
   ```

### iSCSI Configuration

For each OpenShift version, we will create:

1. An iSCSI extent pointing to the corresponding zvol
2. An iSCSI target with a unique IQN
3. A target-extent mapping to connect them

```
Targets:
- iqn.2005-10.org.freenas.ctl:iscsi.r630.openshift4_16
- iqn.2005-10.org.freenas.ctl:iscsi.r630.openshift4_17
- iqn.2005-10.org.freenas.ctl:iscsi.r630.openshift4_18

Extents:
- openshift_4_16_extent -> zvol/test/openshift_installations/4_16_complete
- openshift_4_17_extent -> zvol/test/openshift_installations/4_17_complete
- openshift_4_18_extent -> zvol/test/openshift_installations/4_18_complete
```

## Implementation Steps

### 1. TrueNAS Scale Configuration

#### a. Create OpenShift Installation Storage

1. Create the OpenShift installations dataset:
   ```bash
   ./scripts/truenas_wrapper.sh autodiscovery --apply
   ```
   This will create the necessary datasets and zvols based on the analysis.

2. Verify the created storage structure:
   ```bash
   ./scripts/truenas_wrapper.sh autodiscovery --discover-only
   ```

#### b. Set Up NFS Sharing for ISOs

1. Create the directory structure for OpenShift ISOs:
   ```bash
   ./scripts/truenas_wrapper.sh setup
   ```
   This will SSH into TrueNAS and set up the directory structure.

### 2. OpenShift ISO Preparation

#### a. Generate Agent-Based ISOs

1. For each OpenShift version (4.16, 4.17, 4.18), generate an agent-based ISO:
   ```bash
   ./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230
   ```

2. Upload the generated ISOs to TrueNAS:
   - This is handled automatically by the generate_openshift_iso.py script
   - ISOs will be placed in /mnt/test/iso/openshift/{version}/

### 3. Dell R630 Server Configuration

#### a. Configure iSCSI Initiator

1. Set up the iSCSI initiator on each Dell R630 server:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --setup-initiator
   ```

#### b. Initial OpenShift Installation

1. Boot from the ISO for the first installation:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18 --reboot
   ```

2. After installation completes, switch to iSCSI boot:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --reboot
   ```

### ### 4. Version Switching

To switch between OpenShift versions:

1. Switch to a different iSCSI target:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.17 --reboot
   ```

2. To install a fresh version, boot from ISO:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.16 --reboot
   ```

### 5. Alternative OS with netboot.xyz

For booting into alternative operating systems:

1. Configure netboot.xyz boot option:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --reboot
   ```

2. This will boot the server into the netboot.xyz menu, where you can select from various OS options:
   - Various Linux distributions
   - Windows installer
   - System utilities
   - Diagnostic tools

### 6. Managing Multiple Servers

Our scripts support both R630 servers (192.168.2.230 and 192.168.2.232):

1. Specify the target server with the `--server` parameter:
   ```bash
   # Configure the first R630
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --reboot
   
   # Configure the second R630
   ./scripts/switch_openshift.py --server 192.168.2.232 --method iscsi --version 4.17 --reboot
   ```

2. You can run the same commands on both servers for identical configurations:
   ```bash
   for server in 192.168.2.230 192.168.2.232; do
     ./scripts/switch_openshift.py --server $server --method iscsi --version 4.18 --reboot
   done
   ```

3. Different OpenShift versions can run simultaneously on different servers

## Scripts

### 1. truenas_autodiscovery.py

Discovers the current TrueNAS configuration and sets up the necessary storage components:
- Datasets for ISOs (OpenShift and netboot.xyz)
- Zvols for boot disks
- iSCSI targets and extents

### 2. setup_truenas.sh

Runs on the TrueNAS Scale server to:
- Create directory structure for OpenShift ISOs
- Set appropriate permissions
- Configure NFS sharing (if needed)

### 3. generate_openshift_iso.py

Generates agent-based OpenShift installation ISOs:
- Downloads the OpenShift client and installer
- Creates customized installation configurations
- Generates the ISO
- Uploads it to TrueNAS

### 4. switch_openshift.py

Manages the boot configuration of Dell R630 servers:
- Configures iSCSI initiator
- Sets boot parameters (PXE, ISO, iSCSI, netboot)
- Controls server power (reboot when needed)
- Handles version switching
- Supports both R630 servers (192.168.2.230 and 192.168.2.232)

## Testing Plan

Follow the detailed testing plan in TEST_PLAN.md, which includes:
1. TrueNAS authentication and API connectivity testing
2. Storage configuration verification
3. ISO generation testing
4. iSCSI boot configuration testing
5. End-to-end installation and switching test

## Security Considerations

- All API credentials are stored securely and not committed to version control
- API keys have appropriate permissions and expiration settings
- Network security between the Dell servers and TrueNAS is maintained
- See docs/TRUENAS_AUTHENTICATION.md for detailed security practices

## Maintenance Procedures

### Adding a New OpenShift Version

1. Update the list of supported versions in truenas_autodiscovery.py
2. Run the discovery and apply changes:
   ```bash
   ./scripts/truenas_wrapper.sh autodiscovery --apply
   ```
3. Generate a new ISO for the version:
   ```bash
   ./scripts/generate_openshift_iso.py --version <new_version> --rendezvous-ip 192.168.2.230
   ```
4. Install using the ISO boot method:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version <new_version> --reboot
   ```

### Adding Custom netboot.xyz Options

1. Create a custom menu entry for netboot.xyz:
   ```bash
   ./scripts/setup_truenas.sh --netboot-custom --name "Custom Deployment" --kernel-url "http://example.com/vmlinuz" --initrd-url "http://example.com/initrd" --boot-options "options"
   ```

2. Update the netboot menu:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --update-menu
   ```

### Backing Up Boot Disks

To create snapshots of the boot disks:
1. Create a snapshot through the TrueNAS UI or API
2. Clone the snapshot to create a backup zvol
3. Create a new iSCSI target for the backup if needed

## Troubleshooting

### iSCSI Connection Issues

1. Verify the iSCSI service is running on TrueNAS
2. Check the iSCSI initiator configuration on the Dell servers
3. Ensure network connectivity between servers
4. Check firewall settings for iSCSI ports (typically 3260)

### Boot Failures

1. Verify the boot order in the Dell server BIOS
2. Check the iSCSI target and extent mappings
3. Validate that the zvol contains a valid boot image
4. Use the Dell iDRAC virtual console for debugging

### Network Boot Issues

1. Verify PXE is enabled in the server BIOS
2. Check network connectivity for DHCP and TFTP
3. Validate netboot.xyz configuration
4. Check firewall settings for PXE-related ports (67, 68, 69, 4011)

### Multiple Server Management

1. Both R630 servers can be managed using the same scripts
2. Use the `--server` parameter to target a specific server
3. For mass operations, use shell scripting to iterate over servers
4. Each server can boot different OpenShift versions simultaneously
