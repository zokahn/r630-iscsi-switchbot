# NetBoot.xyz Integration Implementation

This document provides detailed implementation steps for integrating netboot.xyz into the OpenShift multiboot system.

## Overview

netboot.xyz is a network boot utility that allows booting various operating systems and utilities over the network. By integrating it into our Dell R630 multiboot system, we can provide a more flexible boot experience beyond just OpenShift versions.

## Architecture

The integration will consist of three main components:

1. **Boot configuration** - Configuring R630 servers to boot from netboot.xyz
2. **Custom menu** - Creating custom menu entries for our OpenShift versions
3. **PXE infrastructure** - Setting up the required DHCP and TFTP services

```
┌───────────────────┐     ┌──────────────────────────────────────┐
│ Dell R630 Servers │     │         TrueNAS Scale Server         │
│  192.168.2.230    │◄────┤             192.168.2.245            │
│  192.168.2.232    │     │                                      │
└───────────────────┘     │ ┌────────────┐  ┌─────────────────┐  │
         │                │ │ iSCSI      │  │ OpenShift ISOs  │  │
         │                │ │ Boot       │  │                 │  │
         └───────────────►│ │ Targets    │  │                 │  │
                          │ └────────────┘  └─────────────────┘  │
                          │                                      │
                          │ ┌──────────────────────────────────┐ │
                          │ │ netboot.xyz (iPXE scripts)       │ │
                          │ └──────────────────────────────────┘ │
                          └──────────────────────────────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────────────────┐
                          │         Network Services             │
                          │                                      │
                          │ ┌────────────┐  ┌─────────────────┐  │
                          │ │ DHCP       │  │ TFTP            │  │
                          │ │ Server     │  │ Server          │  │
                          │ └────────────┘  └─────────────────┘  │
                          └──────────────────────────────────────┘
```

## Implementation Steps

### 1. Netboot Method in switch_openshift.py

First, we need to add netboot support to our main switching script:

```python
def configure_netboot(server_ip):
    """Configure server to boot from netboot.xyz"""
    # For Dell R630, we can use UEFI HTTP boot
    netboot_url = "http://boot.netboot.xyz/ipxe/netboot.xyz.efi"
    
    # Configure via iDRAC Redfish API
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
        
        # Set boot order to use HTTP first
        return set_boot_order(server_ip, "HTTP")
    except requests.exceptions.RequestException as e:
        print(f"Error configuring netboot: {e}")
        return False
```

### 2. Custom Netboot Menu for OpenShift

We'll need to create a custom menu for netboot.xyz to include our OpenShift options:

```
#!ipxe
###
### OpenShift Multiboot Menu
###

:openshift_menu
menu OpenShift Multiboot Menu
item --gap -- --------------------
item --gap -- OpenShift Versions:
item openshift_4_18 OpenShift 4.18 Installation
item openshift_4_17 OpenShift 4.17 Installation
item openshift_4_16 OpenShift 4.16 Installation
item --gap -- --------------------
item back Back to Main Menu...
choose version || goto openshift_exit

goto ${version}

:openshift_4_18
kernel http://192.168.2.245/openshift_isos/4.18/agent.x86_64.iso
boot || goto openshift_menu

:openshift_4_17
kernel http://192.168.2.245/openshift_isos/4.17/agent.x86_64.iso
boot || goto openshift_menu

:openshift_4_16
kernel http://192.168.2.245/openshift_isos/4.16/agent.x86_64.iso
boot || goto openshift_menu

:back
chain http://boot.netboot.xyz/ipxe/menu.ipxe

:openshift_exit
exit
```

### 3. Setup Script for Netboot Infrastructure

Create a script to set up the netboot.xyz infrastructure:

```python
#!/usr/bin/env python3
# setup_netboot.py - Configure netboot.xyz support for OpenShift multiboot

import argparse
import os
import subprocess
import requests
import sys
import tempfile

def setup_netboot_menu(truenas_ip, output_dir):
    """Create and upload the netboot.xyz custom menu"""
    # Create the custom menu content
    menu_content = """#!ipxe
###
### OpenShift Multiboot Menu
###

:openshift_menu
menu OpenShift Multiboot Menu
item --gap -- --------------------
item --gap -- OpenShift Versions:
item openshift_4_18 OpenShift 4.18 Installation
item openshift_4_17 OpenShift 4.17 Installation
item openshift_4_16 OpenShift 4.16 Installation
item --gap -- --------------------
item back Back to Main Menu...
choose version || goto openshift_exit

goto ${version}

:openshift_4_18
kernel http://{truenas_ip}/openshift_isos/4.18/agent.x86_64.iso
boot || goto openshift_menu

:openshift_4_17
kernel http://{truenas_ip}/openshift_isos/4.17/agent.x86_64.iso
boot || goto openshift_menu

:openshift_4_16
kernel http://{truenas_ip}/openshift_isos/4.16/agent.x86_64.iso
boot || goto openshift_menu

:back
chain http://boot.netboot.xyz/ipxe/menu.ipxe

:openshift_exit
exit
""".format(truenas_ip=truenas_ip)

    # Write the menu to a file
    menu_file = os.path.join(output_dir, "openshift.ipxe")
    with open(menu_file, "w") as f:
        f.write(menu_content)
    
    # Upload to TrueNAS
    upload_to_truenas(menu_file, truenas_ip, "root", "/mnt/test/netboot/openshift.ipxe")
    
    return menu_file

def verify_netboot_xyz():
    """Verify that netboot.xyz is accessible"""
    try:
        response = requests.head("http://boot.netboot.xyz/ipxe/netboot.xyz.efi", timeout=5)
        if response.status_code == 200:
            print("✅ netboot.xyz is accessible")
            return True
        else:
            print(f"❌ netboot.xyz returned status code {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing netboot.xyz: {e}")
        return False

def upload_to_truenas(local_file, truenas_ip, username, remote_path):
    """Upload a file to TrueNAS using SCP"""
    try:
        subprocess.run(["scp", local_file, f"{username}@{truenas_ip}:{remote_path}"], check=True)
        print(f"✅ Uploaded {local_file} to {truenas_ip}:{remote_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error uploading file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Set up netboot.xyz support for OpenShift multiboot")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--output-dir", help="Output directory for temporary files")
    
    args = parser.parse_args()
    
    # Use provided output directory or create a temporary one
    if args.output_dir:
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)
        should_cleanup = False
    else:
        output_dir = tempfile.mkdtemp()
        should_cleanup = True
    
    try:
        # Verify netboot.xyz is accessible
        if not verify_netboot_xyz():
            print("⚠️ netboot.xyz is not accessible. Custom menu may not work.")
        
        # Set up custom menu
        menu_file = setup_netboot_menu(args.truenas_ip, output_dir)
        
        print("\nNetboot setup completed.")
        print("To use netboot.xyz, run:")
        print(f"./scripts/switch_openshift.py --server SERVER_IP --method netboot --reboot")
        
        return 0
    finally:
        # Clean up temporary directory if we created one
        if should_cleanup:
            import shutil
            print(f"Cleaning up temporary directory: {output_dir}")
            shutil.rmtree(output_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
```

### 4. DHCP Configuration for PXE Boot

For the Dell R630 servers to boot from the network, proper DHCP configuration is required:

1. **Option 66 (Next-Server)**: Set to the IP address of the TFTP server
2. **Option 67 (Bootfile-Name)**: Set to `netboot.xyz.efi` for UEFI boot

Example DHCP configuration (for ISC DHCP server):

```
subnet 192.168.2.0 netmask 255.255.255.0 {
  option routers 192.168.2.1;
  option domain-name-servers 192.168.2.1;
  option subnet-mask 255.255.255.0;
  
  # PXE boot configuration
  filename "netboot.xyz.efi";
  next-server 192.168.2.245;
  
  # R630 server static IPs
  host r630-server-1 {
    hardware ethernet 00:11:22:33:44:55; # Replace with actual MAC
    fixed-address 192.168.2.230;
  }
  
  host r630-server-2 {
    hardware ethernet 00:11:22:33:44:66; # Replace with actual MAC
    fixed-address 192.168.2.232;
  }
}
```

## Integration with Existing System

### 1. Update switch_openshift.py

Modify the `switch_openshift.py` script to include the netboot method:

```python
# Add netboot to the method choices
parser.add_argument("--method", choices=["iscsi", "iso", "netboot"], required=True, help="Boot method")

# In the main function
elif args.method == "netboot":
    # Configure netboot.xyz
    success = configure_netboot(args.server)
```

### 2. Add Custom Menu Support

Extend the script to support custom menu selection:

```python
# Add parameter for custom menu
parser.add_argument("--netboot-menu", help="Custom netboot.xyz menu entry (for netboot method)")

# In the configure_netboot function
def configure_netboot(server_ip, custom_menu=None):
    """Configure server to boot from netboot.xyz"""
    # Base netboot.xyz URL
    netboot_url = "http://boot.netboot.xyz/ipxe/netboot.xyz.efi"
    
    # If a custom menu is specified, use it
    if custom_menu:
        if custom_menu == "openshift":
            netboot_url = f"http://192.168.2.245/netboot/openshift.ipxe"
    
    # Rest of the function...
```

## Testing the Integration

1. **Verify connectivity to netboot.xyz**:
   ```bash
   curl -I http://boot.netboot.xyz/ipxe/netboot.xyz.efi
   ```

2. **Set up custom menu**:
   ```bash
   ./scripts/setup_netboot.py
   ```

3. **Test netboot configuration**:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --check-only
   ```

4. **Configure for netboot**:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --reboot
   ```

5. **Test custom menu**:
   ```bash
   ./scripts/switch_openshift.py --server 192.168.2.230 --method netboot --netboot-menu openshift --reboot
   ```

## Troubleshooting

1. **Server fails to boot from network**:
   - Verify DHCP server configuration
   - Check that UEFI network boot is enabled in BIOS
   - Verify the server can reach netboot.xyz

2. **Custom menu not loading**:
   - Verify the menu file exists on TrueNAS
   - Check permissions on the menu file
   - Verify HTTP access to the menu file

3. **OpenShift options not working**:
   - Verify ISOs exist at the specified locations
   - Check permissions on ISO files
   - Validate HTTP access to the ISOs
