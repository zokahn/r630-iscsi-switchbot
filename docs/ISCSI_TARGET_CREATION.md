# iSCSI Target Creation for R630 Servers

This document describes how to create iSCSI targets on TrueNAS Scale for Dell R630 servers to enable iSCSI boot with OpenShift.

## Overview

The `iscsi_target_template.sh` script provides a robust way to create iSCSI targets on TrueNAS Scale. It uses the TrueNAS middleware client (`midclt`) via SSH to create the necessary components:

1. A ZFS volume (zvol) to store the OpenShift boot image
2. An iSCSI target with the appropriate IQN
3. An extent linking the zvol to the iSCSI subsystem
4. An association between the target and the extent

## Requirements

- SSH access to the TrueNAS Scale server with root privileges
- SSH key configured for passwordless authentication (recommended)
- `jq` installed on the TrueNAS server (should be included by default)

## Usage

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
- `--ssh-key PATH`: Path to SSH key for TrueNAS authentication
- `--dry-run`: Generate commands but don't execute them
- `--skip-zvol-check`: Skip checking if zvol exists
- `--force`: Force recreate zvol if it exists

## Examples

### Dry Run Mode

To see what would be executed without making any changes:

```bash
./scripts/iscsi_target_template.sh --server-id 02 --hostname dumpty --dry-run
```

### Create iSCSI Target with Default Settings

```bash
./scripts/iscsi_target_template.sh --server-id 02 --hostname dumpty
```

### Create iSCSI Target with Specific OpenShift Version

```bash
./scripts/iscsi_target_template.sh --server-id 03 --hostname humpty --openshift-version 4.14
```

### Force Recreation of Existing Volume

```bash
./scripts/iscsi_target_template.sh --server-id 02 --hostname dumpty --force
```

## Generated Names

The script generates standardized names for all components:

- **ZVOL Path**: `tank/openshift_installations/r630_<server-id>_<version>`
- **Target IQN**: `iqn.2005-10.org.freenas.ctl:iscsi.r630-<server-id>.openshift<version>`
- **Extent Name**: `openshift_r630_<server-id>_<version>_extent`

Where `<version>` is the OpenShift version with dots replaced by underscores.

## Error Handling

The script includes robust error handling:

- Validates required arguments
- Checks if the iSCSI service is running on TrueNAS
- Verifies if zvols already exist and handles them according to options
- Tracks and reports command execution status

## Notes

- The script uses the first portal (ID: 1) and initiator group (ID: 1) by default
- By default, existing zvols are reused rather than recreated
- The script requires root SSH access to the TrueNAS server
- For security, use SSH keys rather than password authentication

## Troubleshooting

If you encounter issues:

1. Run with `--dry-run` to see the commands that would be executed
2. Check TrueNAS logs for error messages
3. Verify SSH connectivity to the TrueNAS server
4. Ensure the iSCSI service is enabled in TrueNAS
5. Check if the target names already exist and use `--force` if needed

## Related Documentation

- [R630 iSCSI Boot Guide](R630_ISCSI_BOOT_GUIDE.md)
- [iSCSI OpenShift Integration](ISCSI_OPENSHIFT_INTEGRATION.md)
- [TrueNAS Authentication](TRUENAS_AUTHENTICATION.md)
