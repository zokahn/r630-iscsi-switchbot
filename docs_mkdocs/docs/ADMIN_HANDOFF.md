<div align="center">
  <img src="assets/images/r630-iscsi-switchbot-new-logo.png" alt="R630 iSCSI SwitchBot Logo" width="150">
</div>

# OpenShift Multiboot System - Administrator Handoff

This document serves as a comprehensive handoff guide for system administrators who will be managing the OpenShift Multiboot System. It covers the system architecture, maintenance procedures, and operational responsibilities.

## System Overview

The OpenShift Multiboot System provides flexible boot options for Dell PowerEdge R630 servers, allowing administrators to:
- Deploy multiple OpenShift versions on the same hardware
- Switch between versions without reinstallation
- Boot via iSCSI, ISO, or Netboot methods
- Manage the entire workflow through a set of Python scripts

## Architecture

```
┌───────────────────┐     ┌──────────────────────────────────────┐
│ Dell R630 Servers │     │         TrueNAS Scale Server         │
│  192.168.2.230    │◄────┤             192.168.2.245            │
│  192.168.2.232    │     │                                      │
└───────────────────┘     │ ┌────────────┐  ┌─────────────────┐  │
         │                │ │ iSCSI      │  │ OpenShift ISOs  │  │
         │                │ │ Boot       │  │ (Agent-based)   │  │
         └───────────────►│ │ Targets    │  │                 │  │
                          │ └────────────┘  └─────────────────┘  │
                          └──────────────────────────────────────┘
```

### Key Components

1. **TrueNAS Scale (192.168.2.245)**
   - Storage for OpenShift ISOs and boot volumes
   - iSCSI target provider
   - HTTP server for netboot menu

2. **Dell PowerEdge R630 Servers**
   - Target servers to boot OpenShift
   - Configurable via iDRAC Redfish API

3. **OpenShift Versions**
   - Multiple OpenShift versions (4.16, 4.17, 4.18)
   - Boot volumes stored as zvols on TrueNAS
   - ISOs stored in datasets on TrueNAS

## Credentials and Access Management

### TrueNAS Access

TrueNAS authentication can be configured in several ways (see [TRUENAS_AUTHENTICATION.md](TRUENAS_AUTHENTICATION.md) for details):

1. **API Key** (recommended for automation)
   - Created in TrueNAS UI under Credentials → API Keys
   - Stored locally in `~/.config/truenas/auth.json`
   - Managed via the `truenas_wrapper.sh` script

2. **Username/Password**
   - Alternative method, not recommended for production
   - Can be used as a fallback if API keys are unavailable

### iDRAC Access

Dell iDRAC credentials are used for server management:

1. **Default Configuration**
   - Default credentials are used as fallbacks (root/calvin)
   - Production deployments should set these via environment variables:
     ```bash
     # EXAMPLE - Replace with your actual credentials
     export IDRAC_USER="EXAMPLE_USERNAME_HERE"
     export IDRAC_PASSWORD="EXAMPLE_PASSWORD_HERE"
     ```

2. **Security Recommendations**
   - Change default iDRAC passwords on all servers
   - Use API keys or SSH keys where possible
   - Restrict network access to management interfaces

## Regular Maintenance Tasks

### Weekly Tasks

1. **Verify iSCSI target availability**
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --check-only
   ```

2. **Verify ISOs are accessible**
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18 --check-only
   ```

3. **Check netboot service**
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --check-only
   ```

### Monthly Tasks

1. **Update OpenShift ISOs for latest point releases**
   ```bash
   ./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230
   ```

2. **TrueNAS maintenance**
   - Check disk health in TrueNAS UI
   - Review storage pool usage and expand if necessary
   - Apply TrueNAS updates during maintenance windows

3. **Create ZFS snapshots of OpenShift volumes**
   - Create snapshots in TrueNAS UI under Datasets
   - Label with date and purpose
   - Consider automating via TrueNAS API

### Quarterly Tasks

1. **Rotate API keys**
   - Generate new API keys in TrueNAS
   - Update `~/.config/truenas/auth.json` with new keys
   - Test connectivity after rotation

2. **Review and update documentation**
   - Verify all procedures are current
   - Update IP addresses, URLs, or other configuration if changed
   - Document any new issues in the troubleshooting guide

## Common Operations

### Switching OpenShift Versions

To switch a server from one OpenShift version to another:

```bash
# Switch to OpenShift 4.18
./scripts/switch_openshift.py --server 192.168.2.230 --method iscsi --version 4.18 --reboot
```

### Installing a Fresh OpenShift Instance

To install a fresh copy of OpenShift:

```bash
# First generate/update the ISO
./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230

# Configure for ISO boot
./scripts/switch_openshift.py --server 192.168.2.230 --method iso --version 4.18 --reboot
```

### Using Netboot for Advanced Options

To use the netboot menu:

```bash
# Configure netboot menu
./scripts/setup_netboot.py --truenas-ip 192.168.2.245

# Boot from netboot
./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --reboot
```

## Troubleshooting

See the detailed [TROUBLESHOOTING.md](TROUBLESHOOTING.md) document for guidance on resolving common issues.

For urgent support or problems not covered in the documentation:

1. Check log files in the project directory (`*.log`)
2. Review iDRAC logs through the web interface
3. Contact system administrators at `admin@example.com`

## Disaster Recovery

### TrueNAS Failure

If the TrueNAS server fails:

1. Restore TrueNAS from backup
2. Verify ZFS pool import was successful
3. Ensure iSCSI service is running
4. Test connectivity with:
   ```bash
   ./scripts/test_truenas_connection.py
   ```

### Server Boot Failure

If a server fails to boot:

1. Connect to iDRAC console to observe boot messages
2. Use iDRAC virtual console to diagnose issues
3. Try alternative boot methods:
   ```bash
   # Try alternative boot method
   ./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --reboot
   ```

### Data Recovery

To recover OpenShift data:

1. Create a new zvol in TrueNAS
2. Restore from the most recent snapshot
3. Create a new iSCSI target for the recovered volume
4. Update `iscsi_targets.json` with the new target
5. Boot from the recovered volume

## Security Considerations

1. **Network Isolation**
   - Keep management networks (iDRAC, TrueNAS admin) separate from data networks
   - Use firewall rules to restrict access

2. **Authentication**
   - Rotate API keys quarterly
   - Use complex passwords for all accounts
   - Consider LDAP integration for centralized authentication

3. **Monitoring**
   - Set up monitoring for TrueNAS health
   - Configure alerts for boot failures
   - Monitor disk space on TrueNAS

## Contact Information

- **Primary System Administrator**: admin@example.com
- **TrueNAS Support**: truenas-admin@example.com
- **OpenShift Support**: openshift-admin@example.com

## Appendices

### Environment Variables

| Variable Name | Purpose | Example Value |
|---------------|---------|---------------|
| IDRAC_USER | Username for iDRAC access | root |
| IDRAC_PASSWORD | Password for iDRAC access | ******** |
| TRUENAS_API_KEY | API key for TrueNAS access | 1-a2b3c4d5... |

### Useful Commands

| Command | Purpose |
|---------|---------|
| `./scripts/truenas_wrapper.sh` | Set up or update TrueNAS credentials |
| `./scripts/test_setup.sh` | Verify entire system configuration |
| `./scripts/finalize_deployment.sh` | Run complete deployment process |
