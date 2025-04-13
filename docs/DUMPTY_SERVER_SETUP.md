Dumpty Server Setup (R630-02)

This document tracks the setup of the "dumpty" server (R630-02, IP: 192.168.2.232) with iSCSI boot configuration.

## Completed Steps

1. **Documentation Updates**
   - Added server inventory to `docs/DEPLOYMENT_TRACKING.md`
   - Updated `docs/R630_ISCSI_BOOT_GUIDE.md` with both server configurations
   - Added server-specific examples to `docs/ISCSI_OPENSHIFT_INTEGRATION.md`
   - Created comprehensive process flow diagrams in `docs/PROCESS_FLOWS.md`

2. **iSCSI Boot Configuration**
   - Configured dumpty's integrated NIC.1-1-1 for iSCSI boot using `config_iscsi_boot.py`
   - Successfully validated the iSCSI boot configuration
   - Boot configuration is using target: `iqn.2005-10.org.freenas.ctl:iscsi.r630-02.openshiftstable`
   - Expected device path: `/dev/sda`

3. **Device Mapping**
   - Updated device mapping in `config/iscsi_device_mapping.json`
   - Added dumpty's target to `config/iscsi_targets.json`
   - Generated OpenShift values at `config/deployments/r630-02/r630-02-dumpty-20250413132115.yaml`

## Pending Steps

1. **TrueNAS iSCSI Target Creation**
   - API authentication to TrueNAS needs to be configured
   - Create the target using the API-based script:

   ```bash
   # Using the standalone API script
   ./scripts/create_iscsi_target_api.py \
     --server-id 02 \
     --hostname dumpty \
     --api-key "YOUR_API_KEY" \
     --zvol-size 500G
   ```

   Or alternatively:

   ```bash
   # Using the integrated script
   ./scripts/integrate_iscsi_openshift.py \
     --server-id 02 \
     --hostname dumpty \
     --truenas-api-key "YOUR_API_KEY" \
     --node-ip 192.168.2.232 \
     --mac-address XX:XX:XX:XX:XX:XX \
     --skip-iscsi-config
   ```

2. **Server Reboot and Verification**
   - After TrueNAS target is created, reboot the dumpty server
   - Verify that it successfully boots from the iSCSI target
   - Monitor server boot process through iDRAC console

3. **Optional: OpenShift Installation**
   - To deploy OpenShift, generate an installation ISO:
   ```bash
   python3 scripts/integrate_iscsi_openshift.py \
     --server-id 02 \
     --hostname dumpty \
     --node-ip 192.168.2.232 \
     --mac-address dummy:mac:address:00:00:00 \
     --idrac-ip 192.168.2.232 \
     --skip-target-creation \
     --skip-iscsi-config \
     --truenas-api-key "YOUR_API_KEY"
   ```

## TrueNAS Authentication Setup

To set up API authentication for TrueNAS:

1. Generate API key:
   - Log in to TrueNAS web interface
   - Navigate to user menu (top right) → "API Keys"
   - Create a new API key with appropriate permissions
   - Copy the generated key

2. Test API access:
   ```bash
   # Test API connectivity and functionality
   ./scripts/create_iscsi_target_api.py \
     --api-key "YOUR_API_KEY" \
     --discover-only
   ```

## Troubleshooting Tips

- If the server fails to boot from iSCSI after reboot:
  - Check if the TrueNAS target is accessible by using the API to verify
  - Verify the iSCSI configuration (`python3 scripts/config_iscsi_boot.py --server 192.168.2.232 --validate-only --target dumpty`)
  - Check for pending configuration jobs in iDRAC that may need to be completed

- Expected warnings during configuration:
  - "Pending configuration values are already committed, unable to perform another set operation"
  - "Target IQN mismatch" (This is normal on R630 and the configuration will still work)
