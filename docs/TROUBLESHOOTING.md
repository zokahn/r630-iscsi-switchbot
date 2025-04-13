# OpenShift Multiboot System - Troubleshooting Guide

This document provides solutions for common issues that might be encountered when using the OpenShift Multiboot System. 

## Table of Contents
- [TrueNAS Connectivity Issues](#truenas-connectivity-issues)
- [iSCSI Boot Problems](#iscsi-boot-problems)
- [ISO Boot Problems](#iso-boot-problems)
- [Netboot Problems](#netboot-problems)
- [Authentication Issues](#authentication-issues)
- [Script Execution Errors](#script-execution-errors)

## TrueNAS Connectivity Issues

### Problem: Unable to connect to TrueNAS API

**Symptoms:**
- Error message: "Failed to connect to TrueNAS Scale: 401 Client Error: Unauthorized"
- Authentication failures in scripts

**Solutions:**
1. Verify TrueNAS is accessible at the configured IP address:
   ```bash
   ping 192.168.2.245
   ```

2. Check if the TrueNAS web interface is accessible in a browser:
   ```
   https://192.168.2.245:444
   ```

3. Verify API credentials:
   ```bash
   ./scripts/test_truenas_connection.py --host 192.168.2.245 --port 444
   ```

4. Regenerate API key in TrueNAS:
   - Log in to TrueNAS UI
   - Navigate to Credentials → API Keys
   - Delete and re-create the key for OpenShift Multiboot

5. Update your configuration:
   ```bash
   ./scripts/truenas_wrapper.sh  # Re-enter credentials
   ```

### Problem: Wrong TrueNAS port configured

**Symptoms:**
- Connection timeout or connection refused errors

**Solutions:**
1. Verify the correct port in the TrueNAS web UI
2. Update your configuration:
   ```bash
   ./scripts/truenas_wrapper.sh  # Re-enter credentials with correct port
   ```
3. Use the port flag explicitly in commands:
   ```bash
   ./scripts/truenas_autodiscovery.py --host 192.168.2.245 --port 444
   ```

## iSCSI Boot Problems

### Problem: iSCSI targets not appearing in iDRAC

**Symptoms:**
- Unable to boot from iSCSI 
- iSCSI targets not visible in boot options

**Solutions:**
1. Verify target exists and is properly configured:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --check-only
   ```

2. Check TrueNAS iSCSI service status:
   - Ensure the service is running in TrueNAS UI
   - Verify that allowed initiators include the server IQN or "ALL"

3. Check network connectivity between server and TrueNAS:
   ```bash
   ping 192.168.2.245
   ```

4. Manually reconfigure iSCSI initiator in iDRAC:
   - Log in to iDRAC web UI
   - Navigate to Storage → iSCSI Initiator
   - Configure target using values from `iscsi_targets.json`

### Problem: iSCSI boot fails with "No boot device found"

**Symptoms:**
- Server attempts to boot from iSCSI but fails
- Error message "No boot device found" or similar

**Solutions:**
1. Verify the zvol exists on TrueNAS and contains a bootable system
2. Check if iSCSI extent is properly linked to the target
3. Ensure boot order is correctly set in iDRAC
4. Verify CHAP settings (if used) match between initiator and target

### Problem: R630-specific iSCSI attribute dependency errors

**Symptoms:**
- Error messages like: `Unable to modify the attribute because the attribute is read-only and depends on other attributes`
- Warnings about attributes like `IPAddressType`, `InitiatorIPAddress`, etc.
- Configuration appears to succeed despite errors
- The server may or may not boot from iSCSI

**Solutions:**
1. **Use Dell scripts mode**:
   ```bash
   # DO NOT use --direct-api flag on R630 servers
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --reboot
   ```

2. **Verify actual boot behavior**:
   - Watch the server's POST screen (via iDRAC console) during boot
   - Look for messages indicating iSCSI connection attempts
   - Success is measured by proper boot, not absence of configuration warnings

3. **Use PXE fallback mechanism**:
   - If you see "Using Boot0000 (PXE Device) as fallback for iSCSI boot" in the logs, this is normal
   - R630 servers sometimes use PXE devices for iSCSI boot when no explicit iSCSI device is found

4. **Verify iSCSI target is reachable**:
   - After configuration appears complete, try manually pinging the target from another machine
   - Check TrueNAS logs for connection attempts during server boot

5. **Manual iDRAC configuration**:
   - If all else fails, configure iSCSI manually via the iDRAC web interface
   - Navigate to Storage → iSCSI Initiator
   - Configure the target with values from your `iscsi_targets.json` file
   - This bypasses the attribute dependency issues completely

**Understanding R630 attribute dependencies**:
- The R630 iDRAC has a strict hierarchy of iSCSI configuration settings
- Certain settings must be configured in a specific order
- Some settings depend on the state of other settings
- Dell scripts handle these dependencies better than direct Redfish API calls
- Some validation warnings are expected and can be safely ignored

## ISO Boot Problems

### Problem: ISO not available or accessible

**Symptoms:**
- Warning messages about ISO not being accessible
- Boot fails when attempting ISO boot

**Solutions:**
1. Check if ISO exists in TrueNAS:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18 --check-only
   ```

2. Regenerate the ISO:
   ```bash
   ./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230
   ```

3. Verify NFS sharing is enabled in TrueNAS

4. Check network connectivity and permissions

### Problem: ISO boot starts but installation fails

**Symptoms:**
- Boot begins but OpenShift installation fails
- Error messages during installation process

**Solutions:**
1. Check that rendezvous IP is correctly configured
2. Verify pull secret is valid
3. Ensure network settings in agent-config.yaml are correct
4. Check logs during boot:
   - Connect to the console via iDRAC
   - Press tab during boot to see boot options
   - Add `rd.break` to kernel parameters to examine initramfs

## Netboot Problems

### Problem: netboot.xyz not accessible

**Symptoms:**
- Warning about netboot.xyz not being accessible
- Boot fails when attempting netboot

**Solutions:**
1. Verify connectivity to netboot server:
   ```bash
   curl -I https://netboot.omnisack.nl/ipxe/netboot.xyz.efi
   ```

2. Set up a local netboot server if external service is unreliable

3. Check iDRAC HTTP boot configuration:
   - Ensure HTTP boot is enabled in BIOS/UEFI
   - Verify boot order includes HTTP boot

### Problem: Custom menu not appearing

**Symptoms:**
- Default netboot menu shown instead of custom OpenShift menu
- Unable to select OpenShift versions

**Solutions:**
1. Regenerate custom menu:
   ```bash
   ./scripts/setup_netboot.py --truenas-ip 192.168.2.245
   ```

2. Verify custom menu URL is correctly set in switch_openshift.py
3. Ensure the menu file is accessible via HTTP from the server

## Authentication Issues

### Problem: API key authentication fails

**Symptoms:**
- 401 Unauthorized errors
- API requests failing

**Solutions:**
1. Check API key permissions in TrueNAS
2. Regenerate API key and update configuration
3. Ensure API key is correctly formatted in auth.json

### Problem: SSH authentication fails

**Symptoms:**
- SSH connection refused
- Permission denied errors

**Solutions:**
1. Verify SSH service is enabled on TrueNAS
2. Check SSH key is correctly added to authorized_keys
3. Ensure permissions are correct on SSH files

## Script Execution Errors

### Problem: Python script fails to execute

**Symptoms:**
- "Command not found" or permission errors
- Script crashes with import errors

**Solutions:**
1. Verify Python is installed:
   ```bash
   python --version
   ```

2. Install required dependencies:
   ```bash
   pip install requests pathlib
   ```

3. Make scripts executable:
   ```bash
   chmod +x scripts/*.py
   ```

4. Check for syntax errors with linting:
   ```bash
   flake8 scripts/problematic_script.py
   ```

### Problem: finalize_deployment.sh fails

**Symptoms:**
- Deployment script stops with errors
- Not all ISOs are generated

**Solutions:**
1. Run with check-only first:
   ```bash
   ./scripts/finalize_deployment.sh  # Choose 'y' for check-only
   ```

2. Resolve specific errors reported in the log
3. Re-run individual components manually:
   ```bash
   ./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230
   ./scripts/setup_netboot.py --truenas-ip 192.168.2.245
   ```

## Deployment Test Issues

### Problem: Test deployment fails with incorrect DNS entries

**Symptoms:**
- OpenShift installation fails during DNS resolution
- Error logs show unresolved hostnames

**Solutions:**
1. Verify that the DNS entries in your test data match the generated configuration:
   ```bash
   cat config/deployments/r630-XX/r630-XX-CLUSTER-TIMESTAMP.yaml
   ```

2. Ensure the DNS server (typically your gateway) is correctly configured to resolve the test domains:
   ```bash
   dig @192.168.2.254 api.test-cluster.domain
   dig @192.168.2.254 *.apps.test-cluster.domain
   ```

3. For testing purposes, you can add temporary entries to your local hosts file:
   ```bash
   sudo sh -c 'echo "192.168.2.90 api.test-cluster.domain" >> /etc/hosts'
   ```

### Problem: MAC address configuration issues

**Symptoms:**
- DHCP does not assign the expected IP address
- Server network interface not properly configured

**Solutions:**
1. Verify the MAC address in your test data matches the physical server:
   ```bash
   # On the server, check interfaces
   ip link show
   ```

2. Check DHCP server configuration to ensure MAC address binding:
   ```bash
   # Example for checking dhcpd leases
   cat /var/lib/dhcpd/dhcpd.leases | grep -A 6 "test-cluster"
   ```

3. Manually update the configuration with the correct MAC address:
   ```bash
   # Edit the generated config file
   vim config/deployments/r630-XX/r630-XX-CLUSTER-TIMESTAMP.yaml
   ```

### Problem: Test data interpretation errors

**Symptoms:**
- Generated configuration doesn't match expected values
- Input data format misunderstood by the script

**Solutions:**
1. Double-check the format of your test data:
   ```
   api.CLUSTER.DOMAIN       IP_ADDRESS
   api-int.CLUSTER.DOMAIN   IP_ADDRESS
   *.apps.CLUSTER.DOMAIN    IP_ADDRESS
   ```

2. Use the `--check-only` or dry-run flags when available to validate without making changes:
   ```bash
   ./scripts/generate_openshift_values.py --check-only [other options]
   ```

3. Review the test documentation in `docs/TEST_PLAN.md` for the correct format and expected values

### Problem: Configuration validation failures

**Symptoms:**
- Validation script reports errors in configuration
- Required fields missing or incorrectly formatted
- Warning messages about best practices

**Solutions:**
1. Run the validation script with verbose output to see details:
   ```bash
   ./scripts/validate_openshift_config.sh --config config/deployments/r630-XX/r630-XX-CLUSTER-TIMESTAMP.yaml --verbose
   ```

2. Check for specific validation issues:
   ```bash
   # Validate only basic fields
   ./scripts/validate_openshift_config.sh --config config/deployments/r630-XX/r630-XX-CLUSTER-TIMESTAMP.yaml --skip-installer --skip-policy
   ```

3. Fix common validation issues:
   - Ensure `networkType: OVNKubernetes` is specified
   - Set `platform: none` for SNO deployments
   - Set `controlPlane.replicas: 1` for SNO
   - Add MAC address in `sno.macAddress` field
   - Add DNS records in `sno.dnsRecords` section
   - Specify installation disk in `bootstrapInPlace.installationDisk`

### Problem: Test deployment artifacts not properly tracked

**Symptoms:**
- Missing test logs or metadata
- Incomplete deployment tracking

**Solutions:**
1. Make sure to include the `--metadata status=TEST` flag to properly mark test deployments:
   ```bash
   ./scripts/upload_deployment_artifacts.sh \
     --server-id 01 \
     --deployment-name test-cluster \
     --metadata status=TEST
   ```

2. Verify the artifacts were uploaded to the correct location:
   ```bash
   ls -la /mnt/tank/deployment_artifacts/r630-01/r630-01-test-cluster-TIMESTAMP/
   ```

3. Run the test in mock mode first to validate the deployment tracking process:
   ```bash
   ./scripts/upload_deployment_artifacts.sh --mock-mode [other options]
   ```

## Additional Support

If you encounter issues not covered in this guide:

1. Check the log files:
   - Script logs: `*.log` in the current directory
   - System logs: `journalctl -u iscsi*` on the server
   - TrueNAS logs: Available in the TrueNAS UI under System → Advanced → Logs

2. Review the output of test scripts:
   ```bash
   ./scripts/test_setup.sh
   ```

3. For urgent issues, contact the system administrator at `admin@example.com`
