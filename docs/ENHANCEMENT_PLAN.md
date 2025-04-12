# Enhancement Plan for OpenShift Multiboot System

This document outlines the implementation plans for the highest priority enhancements identified during testing.

## 1. Fix Port Configuration Issues

### Current Issue
The test scripts attempt to connect to TrueNAS on the default port 443, but our testing shows the server is actually on port 444. This causes connection failures in the autodiscovery functionality.

### Implementation Plan
1. **Update TrueNAS connection handling**
   - Modify `truenas_autodiscovery.py` to use port 444 by default
   - Update `test_setup.sh` to use the correct port
   - Implement automatic port detection using the `test_truenas_connection.py` functionality

```python
# Example fix for truenas_autodiscovery.py default port
parser.add_argument("--port", type=int, default=444, help="TrueNAS Scale port (default: 444)")
```

```bash
# Example fix for test_setup.sh
./scripts/truenas_autodiscovery.py --discover-only --host 192.168.2.245 --port 444
```

2. **Add port detection in truenas_wrapper.sh**
   - Modify the wrapper script to detect the correct port first using test_truenas_connection.py
   - Store this information for subsequent calls

## 2. ISO Management

### Current Issue
The ISO check failed - OpenShift installation ISOs are not available at the expected location.

### Implementation Plan
1. **Create ISO generation script improvements**
   - Add auto-detection of pull secret from ~/.openshift/pull-secret if not provided
   - Add validation that uploaded ISOs are accessible via HTTP
   - Implement ISO version management

2. **Add ISO management commands**
   - Create a new script `manage_isos.py` to list, verify, and clean up ISOs
   - Add capability to validate ISO checksums
   - Implement automated NFS share verification and setup

```python
def verify_iso_accessibility(truenas_ip, version):
    """Verify that the ISO is accessible via HTTP from TrueNAS"""
    url = f"http://{truenas_ip}/openshift_isos/{version}/agent.x86_64.iso"
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False
```

## 3. Netboot.xyz Integration

### Current Issue
The MULTIBOOT_IMPLEMENTATION.md mentions netboot.xyz integration, but it's not implemented in switch_openshift.py.

### Implementation Plan
1. **Add netboot method to switch_openshift.py**

```python
def configure_netboot(server_ip):
    """Configure server to boot from netboot.xyz"""
    netboot_url = "http://boot.netboot.xyz/ipxe/netboot.xyz.efi"
    
    # Mount netboot.xyz via iDRAC Redfish API
    idrac_url = f"https://{server_ip}/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.SetBootSource"
    
    payload = {
        "BootSourceOverrideTarget": "UefiHttp",
        "UefiTargetBootSourceOverride": netboot_url,
        "BootSourceOverrideEnabled": "Once"
    }
    
    print(f"Configuring netboot.xyz boot for {server_ip}...")
    try:
        response = requests.post(
            idrac_url,
            json=payload,
            auth=HTTPBasicAuth(IDRAC_USER, IDRAC_PASSWORD),
            verify=False
        )
        response.raise_for_status()
        print("Netboot configured successfully")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error configuring netboot: {e}")
        return False
```

2. **Add netboot custom menu configuration**
   - Create script to generate custom netboot.xyz menu entries
   - Add OpenShift versions to the menu
   - Configure DHCP options for PXE boot

3. **Update CLI options**
   - Add 'netboot' to the method choices in switch_openshift.py
   - Add netboot-specific parameters

```python
parser.add_argument("--method", choices=["iscsi", "iso", "netboot"], required=True, help="Boot method")
parser.add_argument("--netboot-menu", help="Custom netboot.xyz menu entry to boot (for netboot method)")
```

## 4. Unified Command Interface

### Current Issue
Currently using multiple scripts with different parameters, making the system harder to use.

### Implementation Plan
1. **Create unified CLI tool (`r630-manager.py`)**

```python
#!/usr/bin/env python3
import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Dell R630 Multiboot Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Boot command
    boot_parser = subparsers.add_parser("boot", help="Configure boot options")
    boot_parser.add_argument("--server", required=True, help="Server IP address")
    boot_parser.add_argument("--method", choices=["iscsi", "iso", "netboot"], required=True, help="Boot method")
    boot_parser.add_argument("--version", default="4.18", help="OpenShift version")
    boot_parser.add_argument("--reboot", action="store_true", help="Reboot after configuration")
    
    # ISO command
    iso_parser = subparsers.add_parser("iso", help="Manage OpenShift ISOs")
    iso_parser.add_argument("--action", choices=["generate", "list", "verify"], required=True, help="Action to perform")
    iso_parser.add_argument("--version", help="OpenShift version")
    iso_parser.add_argument("--rendezvous-ip", help="Rendezvous IP address (for generate)")
    
    # Storage command
    storage_parser = subparsers.add_parser("storage", help="Manage TrueNAS storage")
    storage_parser.add_argument("--action", choices=["discover", "configure", "snapshot"], required=True, help="Action to perform")
    storage_parser.add_argument("--version", help="OpenShift version to snapshot")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if args.command == "boot":
        from scripts import switch_openshift
        # Call the appropriate function
    elif args.command == "iso":
        from scripts import generate_openshift_iso
        # Call the appropriate function
    elif args.command == "storage":
        from scripts import truenas_autodiscovery
        # Call the appropriate function
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

2. **Standardize parameter naming across all operations**
   - Review all scripts and ensure consistent parameter names
   - Create a shared configuration module for common parameters

3. **Add interactive mode**
   - Implement interactive prompts for missing parameters
   - Add wizard-like interface for common operations

```python
def interactive_mode():
    """Run in interactive mode with guided prompts"""
    print("Dell R630 Multiboot Manager - Interactive Mode")
    
    # Server selection
    server = input("Enter server IP address (e.g., 192.168.2.230): ")
    
    # Method selection
    print("\nSelect boot method:")
    print("1) iSCSI boot (for existing OpenShift installations)")
    print("2) ISO boot (for new installations)")
    print("3) Netboot.xyz (for alternative OS options)")
    method_choice = input("Select option [1]: ") or "1"
    
    method_map = {"1": "iscsi", "2": "iso", "3": "netboot"}
    method = method_map.get(method_choice, "iscsi")
    
    # Version selection
    if method in ["iscsi", "iso"]:
        version = input("\nEnter OpenShift version [4.18]: ") or "4.18"
    else:
        version = None
    
    # Reboot option
    reboot = input("\nReboot server after configuration? (y/n) [n]: ").lower() == "y"
    
    # Confirm
    print("\nConfiguration Summary:")
    print(f"Server: {server}")
    print(f"Method: {method}")
    if version:
        print(f"Version: {version}")
    print(f"Reboot: {'Yes' if reboot else 'No'}")
    
    confirm = input("\nProceed with this configuration? (y/n) [y]: ") or "y"
    if confirm.lower() != "y":
        print("Operation cancelled")
        return
    
    # Execute
    # (Implementation would call the appropriate function based on the selected options)
```

## 5. Multiple Server Orchestration

### Current Issue
Current scripts support specifying servers individually, but lack batch operations.

### Implementation Plan
1. **Add server batch operations**
   - Create a JSON schema for server configurations
   - Implement parallel execution for configuring multiple servers

```python
def configure_servers(servers_config, method, version=None, reboot=False):
    """Configure multiple servers in parallel"""
    import concurrent.futures
    
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        
        for server in servers_config:
            server_ip = server["ip"]
            server_method = server.get("method", method)
            server_version = server.get("version", version)
            server_reboot = server.get("reboot", reboot)
            
            future = executor.submit(
                configure_server,
                server_ip,
                server_method,
                server_version,
                server_reboot
            )
            futures[future] = server_ip
        
        for future in concurrent.futures.as_completed(futures):
            server_ip = futures[future]
            try:
                success = future.result()
                results[server_ip] = success
            except Exception as e:
                results[server_ip] = f"Error: {e}"
    
    return results
```

2. **Create server group configuration**
   - Implement a way to define server groups for easier management
   - Add role-based configuration (e.g., control-plane, worker)

Example JSON configuration:
```json
{
  "clusters": [
    {
      "name": "production",
      "version": "4.18",
      "servers": [
        {
          "ip": "192.168.2.230",
          "role": "control-plane",
          "method": "iscsi"
        },
        {
          "ip": "192.168.2.232",
          "role": "worker",
          "method": "iscsi"
        }
      ]
    },
    {
      "name": "development",
      "version": "4.17",
      "servers": [
        {
          "ip": "192.168.2.233",
          "role": "control-plane",
          "method": "iscsi"
        }
      ]
    }
  ]
}
```

## Implementation Priorities

Based on the user's feedback prioritizing ease of use, stability, and new features, I recommend the following implementation order:

1. Fix port configuration issues - Critical for core functionality
2. Complete netboot.xyz integration - High priority new feature
3. Create unified command interface - Ease of use improvement
4. Add multiple server orchestration - Enhanced feature for better management
5. Implement ISO generation improvements - Better stability and workflow

Each of these enhancements should be implemented as a separate pull request with proper testing and documentation to maintain code quality and stability.
