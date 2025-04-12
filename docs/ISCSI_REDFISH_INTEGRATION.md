# iSCSI Configuration via Dell Redfish API

This document explains how to configure and manage iSCSI boot settings on Dell PowerEdge R630 servers using the Dell Redfish Python API. The implementation leverages the iDRAC interface to set up iSCSI boot configurations with advanced features including authentication, multipath, and direct Redfish API access.

## Overview

The enhanced iSCSI boot integration allows for:

- Advanced iSCSI configuration including CHAP authentication
- Multipath support for redundant storage connectivity
- Direct Redfish API integration (bypassing Dell scripts when needed)
- Configuration validation and troubleshooting capabilities
- Reset/clear iSCSI configuration when needed

## Prerequisites

- Dell PowerEdge R630 servers with iDRAC8 Enterprise license
- iDRAC firmware version 2.40.40.40 or later (for full Redfish API support)
- Dell Redfish Python scripts (included in scripts/dell directory)
- TrueNAS Scale server with iSCSI targets configured

## Enhanced iSCSI Targets Configuration

The enhanced iSCSI targets configuration supports additional parameters:

```json
{
  "targets": [
    {
      "name": "openshift_4_18",
      "iqn": "iqn.2005-10.org.freenas.ctl:iscsi.r630.openshift418",
      "ip": "192.168.2.245",
      "port": 3260,
      "lun": 4,
      "description": "OpenShift 4.18 boot target"
    },
    {
      "name": "openshift_4_18_secondary",
      "iqn": "iqn.2005-10.org.freenas.ctl:iscsi.r630.openshift418",
      "ip": "192.168.2.246",
      "port": 3260,
      "lun": 4,
      "description": "OpenShift 4.18 secondary path for multipath"
    },
    {
      "name": "secure_target",
      "iqn": "iqn.2005-10.org.freenas.ctl:iscsi.r630.secure",
      "ip": "192.168.2.245",
      "port": 3260,
      "lun": 10,
      "description": "Secure iSCSI target with CHAP authentication",
      "auth_method": "CHAP",
      "chap_username": "iscsi_initiator",
      "chap_secret": "ch4p_s3cr3t_p@ssw0rd"
    }
  ]
}
```

New parameters:
- `auth_method`: Authentication method (e.g., "CHAP", "None")
- `chap_username`: CHAP username for authentication
- `chap_secret`: CHAP secret for authentication

## Advanced Usage

### Basic iSCSI Configuration

```bash
# Configure iSCSI boot for OpenShift 4.18
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --reboot
```

### Multipath Configuration

```bash
# Configure iSCSI with multipath support
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --multipath --reboot
```

This requires having both a primary target (e.g., `openshift_4_18`) and a secondary target (e.g., `openshift_4_18_secondary`) defined in your targets file.

### CHAP Authentication

To use a target with CHAP authentication:

```bash
./scripts/config_iscsi_boot.py --server 192.168.2.230 --target secure_target
```

The script will automatically detect that the target requires CHAP authentication and configure the proper settings.

### Advanced Configuration Options

You can configure additional parameters directly:

```bash
./scripts/config_iscsi_boot.py \
  --server 192.168.2.230 \
  --target openshift_4_18 \
  --initiator-name "iqn.2016-04.com.example:r630-01" \
  --gateway 192.168.2.1
```

### Direct Redfish API

Bypass the Dell scripts and use direct Redfish API calls:

```bash
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --direct-api --reboot
```

### Validation and Troubleshooting

Validate existing iSCSI configuration:

```bash
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --validate-iscsi
```

Reset iSCSI configuration to defaults:

```bash
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --reset-iscsi --reboot
```

## Implementation Details

### iSCSI Configuration Process

1. The `switch_openshift.py` script determines which OpenShift version to boot
2. It calls `config_iscsi_boot.py` with the appropriate target
3. `config_iscsi_boot.py`:
   - Loads the target information from `iscsi_targets.json`
   - Creates an iSCSI configuration based on the template in `iscsi_config_template.json`
   - Applies the configuration using either:
     - Dell Redfish scripts in `scripts/dell/`
     - Direct Redfish API calls (when `--direct-api` is specified)
   - Validates the configuration
   - Schedules a reboot if requested

### Direct Redfish API Implementation

The direct Redfish API approach uses the following endpoints:

- `/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/{id}/NetworkDeviceFunctions/{nic_id}/Settings` - For setting iSCSI parameters
- `/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset` - For rebooting the server

### Multipath Implementation

Multipath is implemented by:

1. Setting `MultipleConnectionsEnabled` to `true` in the iSCSI configuration
2. Configuring both primary and secondary targets with the same iSCSI IQN
3. Ensuring that both primary and secondary targets point to the same LUN

## Troubleshooting

### Common Issues

1. **iSCSI boot fails to configure**
   - Verify iDRAC credentials
   - Check that the Dell Redfish scripts are in the correct location
   - **Verify firmware version compatibility (minimum recommended: 2.40.40.40)**
   - Use the `--validate-iscsi` option to check current configuration
   - The system will automatically fall back to using a PXE device for iSCSI boot if no explicit iSCSI boot device is found

2. **Attribute dependency errors**
   - These are expected due to the way iDRAC implements attribute dependencies
   - The enhanced implementation now sets attributes in the correct order
   - Non-critical attributes that fail to apply will not prevent the iSCSI boot from working
   - If you see errors like "attribute is read-only and depends on other attributes", you can safely ignore them

3. **VLAN configuration errors**
   - If you see errors about `IscsiVLanMode` resource not found, this is normal on some hardware
   - The updated configuration template doesn't use VLAN settings by default
   - If you need VLAN support, verify your hardware supports it first

4. **Unable to connect to iSCSI target**
   - Verify the target exists in TrueNAS
   - Check network connectivity between the server and TrueNAS
   - Verify CHAP credentials if authentication is used
   - Check that the IQN matches between the configuration and TrueNAS

5. **Multipath not working**
   - Verify both primary and secondary targets are defined in the targets file
   - Check that both targets have the same IQN
   - Verify network connectivity to both target IP addresses

6. **CHAP authentication issues**
   - Verify CHAP credentials match between TrueNAS and the configuration
   - Check that TrueNAS has CHAP authentication enabled for the target

7. **iDRAC firmware version warnings**
   - If you see warnings about iDRAC version not supporting a feature:
     - Check your current firmware version using the built-in version checker
     - Consider upgrading to at least firmware version 2.40.40.40
     - The system will still work with older firmware, but some advanced features may be limited

### Resolving Configuration Issues

1. **Reset and retry approach**
   If you encounter persistent issues with iSCSI configuration:
   ```bash
   # First reset the iSCSI configuration
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --reset-iscsi
   
   # Then try again with direct API option
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --direct-api
   ```

2. **Verify configuration success despite warnings**
   Even when you see configuration errors, the system may have successfully set the most critical parameters:
   ```bash
   # Validate the configuration
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --validate-iscsi
   ```
   
3. **Fallback mechanisms**
   If explicit iSCSI configuration fails, the system will fall back to using PXE boot, which often works for iSCSI booting too.

## References

1. [Dell iDRAC with Lifecycle Controller Redfish API Guide](https://www.dell.com/support/manuals/en-us/idrac8-lifecycle-controller-v2.05.05.05/redfish_guide-v1)
2. [Dell OpenManage GitHub Repository](https://github.com/dell/iDRAC-Redfish-Scripting)
3. [DMTF Redfish Specification](https://www.dmtf.org/standards/redfish)
4. [TrueNAS iSCSI Configuration Guide](https://www.truenas.com/docs/scale/scaletutorials/sharing/iscsi/iscsishare/)
