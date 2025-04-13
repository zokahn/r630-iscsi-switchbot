# Dell R630 iSCSI Boot Configuration Guide

This document explains the specific approach taken for configuring iSCSI boot on Dell PowerEdge R630 servers in our lab environment. It provides details on the Dell script-focused implementation, hardware considerations, and troubleshooting tips.

## Configured Servers

This guide applies to the following Dell R630 servers:

- **humpty** (192.168.2.230): Primary server with iSCSI boot configured
- **dumpty** (192.168.2.232): Secondary server with separate iSCSI volume

Each server requires its own dedicated iSCSI target to avoid boot conflicts.

## Overview

The OpenShift deployment system has been optimized specifically for Dell R630 servers using Dell-provided scripts for iSCSI boot configuration. This approach was chosen based on extensive testing that showed Dell scripts handle hardware-specific dependencies better than direct Redfish API implementations.

## Dell Scripts Approach

Our implementation:

1. **Uses Dell Redfish Scripts Exclusively** - We've removed the direct Redfish API option that was previously available
2. **Optimizes for R630 Hardware** - Configuration parameters are tailored specifically for R630 servers
3. **Handles Known Firmware Limitations** - Accommodates specific iDRAC firmware limitations on R630
4. **Adds R630-Specific Error Handling** - Improved validation and fallback mechanisms

## Configuration Process

When configuring an R630 for iSCSI boot:

1. The `switch_openshift.py` script calls `config_iscsi_boot.py` with the appropriate target
2. `config_iscsi_boot.py`:
   - Creates a simplified configuration template with only parameters known to work reliably on R630
   - Uses Dell's `SetNetworkDevicePropertiesREDFISH.py` to apply the configuration
   - Validates the configuration using Dell scripts
   - Handles PXE device fallback when no explicit iSCSI device is found

## Expected Warnings and Behaviors

### Normal Warnings

The following warnings are expected and can be safely ignored on R630 servers:

1. **Attribute dependency errors**:
   ```
   Unable to modify the attribute because the attribute is read-only and depends on other attributes
   ```
   
   These occur because of hardware-specific dependencies in the R630 iDRAC firmware. The Dell scripts handle these dependencies correctly despite the errors.

2. **Validation mismatches**:
   ```
   Warning: Target IQN mismatch. Expected: iqn.2005-10.org.freenas.ctl:iscsi.r630.openshift418
   ```
   
   These occur because the R630 iDRAC sometimes doesn't report the correct values through the API. The configuration is often applied correctly despite these validation errors.

3. **PXE Device Fallback**:
   ```
   No explicit iSCSI boot device found looking for a PXE device to use instead...
   Using Boot0000 (PXE Device) as fallback for iSCSI boot
   ```
   
   This is normal on R630 servers - the system will use a PXE boot device for iSCSI boot when no explicit iSCSI device is found.

### Firmware Considerations

Our scripts are designed to work with all R630 firmware versions, but we've found the following:

1. **iDRAC Firmware below 2.40.40.40**: May not fully support some Redfish API features, but Dell scripts work reliably
2. **Latest Available Firmware**: May have additional features, but isn't necessary for our implementation

### R630 iDRAC Firmware Constraints 

Through intrusive testing of the R630 iDRAC interfaces, we've discovered several important limitations:

1. **Sequential Configuration Only**: 
   - Only one attribute group can be configured at a time
   - You must reboot between configuration operations
   - Attempting to set multiple parameters at once causes errors

2. **Configuration Job Handling**:
   - Each successful configuration creates a pending job
   - Further configurations will fail until the pending job completes (via reboot)
   - Error: `Pending configuration values are already committed unable to perform another set operation`

3. **Parameter Dependencies**:
   - `TargetInfoViaDHCP` has strict dependencies with other attributes
   - Setting this parameter first usually fails with: `Unable to modify the attribute because the attribute is read-only and depends on other attributes`
   - Instead, set `IPMaskDNSViaDHCP` first, reboot, then set the target parameters

4. **Validation vs. Actual Configuration**:
   - Validation may show "iSCSI boot configuration looks correct" even when attributes appear blank
   - Our validation accounts for this discrepancy by detecting both explicit iSCSI configurations and PXE fallback

5. **Parameter Set Order**:
   For best results, set parameters in this specific order:
   - Set network parameters (`IPMaskDNSViaDHCP`) and reboot
   - Set target parameters (`PrimaryTargetName`, `PrimaryTargetIPAddress`, etc.) and reboot
   - Set any authentication parameters, if needed, and reboot

## Troubleshooting

1. **iSCSI Boot Fails Despite Successful Configuration**:
   - Check that the server has rebooted completely
   - Verify boot order in iDRAC web interface (iSCSI or PXE should be first)
   - Verify network connectivity to the iSCSI target
   - See the troubleshooting guide for more detailed steps

2. **Configuration Fails with Error**:
   - Verify iDRAC credentials
   - Ensure the target exists in the iSCSI targets configuration
   - Check that Dell scripts are available in the scripts/dell directory

3. **Validation Warnings**:
   - Most validation warnings can be ignored on R630
   - The true test is whether the server successfully boots from iSCSI after reboot
   - Look for "Configuration successful" message despite validation warnings

## References

1. [Dell Redfish API Guide](https://www.dell.com/support/manuals/en-us/idrac-lifecycle-controller-v2.60.60.60/redfish_whitepaper)
2. [Dell PowerEdge R630 Technical Guide](https://www.dell.com/support/manuals/en-us/poweredge-r630/r630_om_pub/introduction-to-dell-poweredge-r630-system)
3. [iSCSI Boot Implementation Guide](docs/ISCSI_REDFISH_INTEGRATION.md)
4. [Complete Troubleshooting Guide](docs/TROUBLESHOOTING.md)
