# Component Script Usage Guide

This document provides usage examples and comparison between the original scripts and their component-based equivalents. It helps users transition to the new architecture and serves as a reference for how to use the new scripts.

## Table of Contents

1. [Introduction](#introduction)
2. [S3 Storage Scripts](#s3-storage-scripts)
3. [Server Management Scripts](#server-management-scripts)
4. [OpenShift Management Scripts](#openshift-management-scripts)
5. [iSCSI Management Scripts](#iscsi-management-scripts)
6. [Usage Patterns and Best Practices](#usage-patterns-and-best-practices)

## Introduction

The r630-iscsi-switchbot project has transitioned to a component-based architecture using the discovery-processing-housekeeping pattern. This provides several benefits:

- Consistent error handling and reporting
- Better separation of concerns
- Improved testability
- Standardized logging and outputs
- Resource verification and cleanup

This guide shows how to use the new component-based scripts compared to their original counterparts.

## Server Management Scripts

### Server Reboot

#### Original Script (reboot_server.py)

```bash
# Basic usage
./scripts/reboot_server.py --server 192.168.2.230 --user root --password calvin

# Wait for reboot to complete
./scripts/reboot_server.py --server 192.168.2.230 --wait

# Force reboot even if server is off
./scripts/reboot_server.py --server 192.168.2.230 --force
```

#### New Component-Based Script (reboot_server_component.py)

```bash
# Basic usage
./scripts/reboot_server_component.py --server 192.168.2.230 --user root --password calvin

# Wait for reboot to complete
./scripts/reboot_server_component.py --server 192.168.2.230 --wait

# Force reboot even if server is off
./scripts/reboot_server_component.py --server 192.168.2.230 --force

# Additional features:
# Track server ID and hostname for better logging and artifacts
./scripts/reboot_server_component.py --server 192.168.2.230 --server-id r630-01 --hostname my-server

# Dry run mode (no actual changes)
./scripts/reboot_server_component.py --server 192.168.2.230 --dry-run

# Verbose logging
./scripts/reboot_server_component.py --server 192.168.2.230 --verbose
```

### Set Boot Order

#### Original Script (set_boot_order.py)

```bash
# Set iSCSI as first boot device
./scripts/set_boot_order.py --server 192.168.2.230 --first-boot iscsi

# Set PXE as first boot device without rebooting
./scripts/set_boot_order.py --server 192.168.2.230 --first-boot pxe --no-reboot
```

#### New Component-Based Script (set_boot_order_component.py)

```bash
# Set iSCSI as first boot device
./scripts/set_boot_order_component.py --server 192.168.2.230 --first-boot iscsi

# Set PXE as first boot device without rebooting
./scripts/set_boot_order_component.py --server 192.168.2.230 --first-boot pxe --no-reboot

# Additional features:
# Set boot mode along with boot order
./scripts/set_boot_order_component.py --server 192.168.2.230 --first-boot iscsi --boot-mode Uefi

# Track server ID and hostname for better logging and artifacts
./scripts/set_boot_order_component.py --server 192.168.2.230 --first-boot iscsi --server-id r630-01 --hostname my-server

# Dry run mode (no actual changes)
./scripts/set_boot_order_component.py --server 192.168.2.230 --first-boot iscsi --dry-run

# Verbose logging
./scripts/set_boot_order_component.py --server 192.168.2.230 --first-boot iscsi --verbose
```

## OpenShift Management Scripts

### Generate OpenShift ISO

#### Original Script

```bash
# Generate ISO with basic options
./scripts/generate_openshift_iso.py --rendezvous-ip 192.168.2.90 --pull-secret ~/.openshift/pull-secret
```

#### New Component-Based Script

```bash
# Generate ISO with basic options
./scripts/generate_openshift_iso.py --rendezvous-ip 192.168.2.90 --pull-secret ~/.openshift/pull-secret

# Additional features:
# Specify output directory
./scripts/generate_openshift_iso.py --rendezvous-ip 192.168.2.90 --output-dir ./isos

# Verbose logging
./scripts/generate_openshift_iso.py --rendezvous-ip 192.168.2.90 --verbose

# Dry run mode (validate only)
./scripts/generate_openshift_iso.py --rendezvous-ip 192.168.2.90 --dry-run
```

## iSCSI Management Scripts

### Test iSCSI TrueNAS Connection

```bash
# Test connection only
./scripts/test_iscsi_truenas.py --truenas-ip 192.168.2.245 --api-key YOUR_API_KEY --discover-only

# Create test zvol and clean up
./scripts/test_iscsi_truenas.py --truenas-ip 192.168.2.245 --api-key YOUR_API_KEY --create-test-zvol --cleanup
```

## Usage Patterns and Best Practices

### Discovery-Processing-Housekeeping Pattern

All component-based scripts follow the discovery-processing-housekeeping pattern:

1. **Discovery Phase**: Examines the environment without making changes
2. **Processing Phase**: Performs the core operations based on discovery results
3. **Housekeeping Phase**: Verifies changes and cleans up resources

### Benefits of the New Architecture

- **Better Error Handling**: Consistent error reporting and handling
- **Improved Logging**: Structured logging with consistent format
- **Verification**: Automatic verification of changes
- **Dry Run Mode**: Test changes without applying them
- **Standardized Interface**: Consistent command-line arguments

### Backward Compatibility

The new component-based scripts maintain backward compatibility with the original scripts' command-line interfaces. You can generally replace the original script with its component-based version without changing your existing commands.

### When to Use Component-Based Scripts

Always prefer the component-based scripts when:

- You need better error handling and reporting
- You want detailed logs and verification
- You're implementing automated workflows
- You need to test changes before applying them
- You need to track server and deployment information

## Conclusion

The component-based architecture provides a more robust, maintainable, and consistent way to manage your OpenShift multiboot environment. By transitioning to these new scripts, you'll benefit from improved error handling, better verification, and a more consistent user experience.
