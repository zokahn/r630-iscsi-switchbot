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
