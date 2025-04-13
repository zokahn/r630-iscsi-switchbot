# iSCSI Target Creation for R630 Servers

This document describes how to create iSCSI targets on TrueNAS Scale for Dell R630 servers to enable iSCSI boot with OpenShift.

## Overview

We provide two methods for creating iSCSI targets on TrueNAS Scale:

1. **API-based Method (Recommended)**: The `create_iscsi_target_api.py` script uses the TrueNAS REST API for a comprehensive solution that includes system health checks, resource discovery, intelligent provisioning, and housekeeping capabilities.

2. **SSH-based Method (Legacy)**: The `iscsi_target_template.sh` script uses SSH and the TrueNAS middleware client (`midclt`) to create the necessary components.

Both methods create:
- A ZFS volume (zvol) to store the OpenShift boot image
- An iSCSI target with the appropriate IQN
- An extent linking the zvol to the iSCSI subsystem
- An association between the target and the extent

## API-based Method (Recommended)

### Requirements

- TrueNAS API key with appropriate permissions
- Python 3.6+ with the requests library

### Workflow

The API-based method follows a comprehensive workflow:

1. **System Verification**: Checks connectivity, validates credentials, and verifies system health
2. **Resource Discovery**: Examines existing storage pools, zvols, targets, extents, and associations
3. **Capacity Analysis**: Verifies sufficient space is available
4. **Intelligent Provisioning**: Creates or reuses resources as needed
5. **Service Management**: Ensures the iSCSI service is running
6. **Housekeeping (Optional)**: Identifies and optionally removes unused resources

### Usage

```bash
./scripts/create_iscsi_target_api.py --server-id ID --hostname NAME --api-key KEY [options]
```

### Required Parameters

- `--server-id ID`: Server ID (e.g., 01, 02) used in naming convention
- `--hostname NAME`: Server hostname (used in descriptions)
- `--api-key KEY`: TrueNAS API key for authentication

### Optional Parameters

- `--openshift-version VERSION`: OpenShift version (default: stable)
- `--truenas-ip IP`: TrueNAS IP address (default: 192.168.2.245)
- `--zvol-size SIZE`: Size of the zvol to create (default: 500G)
- `--zfs-pool POOL`: ZFS pool name to use (default: test)
- `--discover-only`: Only perform discovery without making changes
- `--housekeeping`: Check for unused resources
- `--cleanup`: Remove unused resources (use with `--housekeeping`)
- `--dry-run`: Show operations without executing them
- `--verbose`: Enable verbose output

### Examples

#### Discovery Mode

To discover existing resources without making any changes:

```bash
./scripts/create_iscsi_target_api.py --server-id 02 --hostname dumpty --api-key "YOUR_API_KEY" --discover-only
```

#### Create iSCSI Target with Default Settings

```bash
./scripts/create_iscsi_target_api.py --server-id 02 --hostname dumpty --api-key "YOUR_API_KEY"
```

#### Create iSCSI Target with Specific OpenShift Version

```bash
./scripts/create_iscsi_target_api.py --server-id 03 --hostname humpty --openshift-version 4.14 --api-key "YOUR_API_KEY"
```

#### Perform Housekeeping Check

```bash
./scripts/create_iscsi_target_api.py --server-id 02 --hostname dumpty --api-key "YOUR_API_KEY" --housekeeping
```

#### Perform Housekeeping and Cleanup

```bash
./scripts/create_iscsi_target_api.py --server-id 02 --hostname dumpty --api-key "YOUR_API_KEY" --housekeeping --cleanup
```

## SSH-based Method (Legacy)

### Requirements

- SSH access to the TrueNAS Scale server with root privileges
- SSH key configured for passwordless authentication (recommended)
- `jq` installed on the TrueNAS server (should be included by default)

### Usage

```bash
./scripts/iscsi_target_template.sh --server-id ID --hostname NAME [options]
```

### Required Parameters

- `--server-id ID`: Server ID (e.g., 01, 02) used in naming convention
- `--hostname NAME`: Server hostname (used in descriptions)

### Optional Parameters

- `--openshift-version VERSION`: OpenShift version (default: stable)
- `--truenas-ip IP`: TrueNAS IP address (default: 192.168.2.245)
- `--zvol-size SIZE`: Size of the zvol to create (default: 500G)
- `--zfs-pool POOL`: ZFS pool name to use (default: test)
- `--ssh-key PATH`: Path to SSH key for TrueNAS authentication
- `--dry-run`: Generate commands but don't execute them
- `--skip-zvol-check`: Skip checking if zvol exists
- `--force`: Force recreate zvol if it exists

### Examples

```bash
./scripts/iscsi_target_template.sh --server-id 02 --hostname dumpty
```

## Generated Names

Both methods generate standardized names for all components:

- **ZVOL Path**: `<zfs-pool>/openshift_installations/r630_<server-id>_<version>`
- **Target IQN**: `iqn.2005-10.org.freenas.ctl:iscsi.r630-<server-id>.openshift<version>`
- **Extent Name**: `openshift_r630_<server-id>_<version>_extent`

Where:
- `<zfs-pool>` is the ZFS pool name specified with `--zfs-pool` (default: "test")
- `<server-id>` is the ID provided with `--server-id`
- `<version>` is the OpenShift version with dots replaced by underscores

## Troubleshooting

If you encounter issues:

1. Run with `--discover-only` or `--dry-run` to see what would be done
2. Check TrueNAS logs for error messages
3. Verify connectivity to the TrueNAS server
4. Ensure the iSCSI service is enabled in TrueNAS
5. Check if the target names already exist

### Common Issues

- **422 Unprocessable Entity**: Usually indicates a validation error in the request payload
- **Portal/Initiator IDs**: The script uses portal ID 3 and initiator ID 3 by default - verify these exist on your system
- **Insufficient Space**: Make sure the specified ZFS pool has enough free space

## Best Practices

- Use the API-based method for new deployments and greater reliability
- Use portal/initiator groups that are already configured on your TrueNAS system
- Perform regular housekeeping to clean up unused resources
- Always verify free space before creating large zvols

## Related Documentation

- [R630 iSCSI Boot Guide](R630_ISCSI_BOOT_GUIDE.md)
- [iSCSI OpenShift Integration](ISCSI_OPENSHIFT_INTEGRATION.md)
- [TrueNAS Authentication](TRUENAS_AUTHENTICATION.md)
