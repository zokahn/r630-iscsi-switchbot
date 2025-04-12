#!/usr/bin/env python3
# switch_openshift.py - Script to configure R630 boot options for OpenShift

import argparse
import requests
import subprocess
import sys
import os
import json
from pathlib import Path
from requests.auth import HTTPBasicAuth
import urllib3

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Default paths and settings
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
ISCSI_TARGETS_FILE = CONFIG_DIR / "iscsi_targets.json"

# iDRAC credentials - read from environment variables or use defaults
# NOTE: For production, set these environment variables instead of using defaults
IDRAC_USER = os.environ.get("IDRAC_USER", "root")
IDRAC_PASSWORD = os.environ.get("IDRAC_PASSWORD", "calvin")

def load_iscsi_targets():
    """Load iSCSI targets from configuration file"""
    try:
        with open(ISCSI_TARGETS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading iSCSI targets: {e}")
        sys.exit(1)

def get_target_by_name(targets_data, target_name):
    """Find a specific target by name in the targets data"""
    for target in targets_data.get('targets', []):
        if target.get('name') == target_name:
            return target
    return None

def configure_iscsi_boot(server_ip, version):
    """Configure server to boot from iSCSI target"""
    version_fmt = version.replace('.', '_')
    target_name = f"openshift_{version_fmt}"
    
    # Load targets to verify target exists
    targets_data = load_iscsi_targets()
    target = get_target_by_name(targets_data, target_name)
    
    if not target:
        print(f"Error: Target '{target_name}' not found in {ISCSI_TARGETS_FILE}")
        print("Available targets:")
        for t in targets_data.get('targets', []):
            print(f"  - {t.get('name')}: {t.get('description', 'No description')}")
        sys.exit(1)
    
    # Configure iSCSI boot
    cmd = [
        "python", str(SCRIPT_DIR / "config_iscsi_boot.py"), 
        "--target", target_name
    ]
    
    print(f"Configuring iSCSI boot for OpenShift {version}...")
    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully configured iSCSI boot for target: {target_name}")
        
        # Ensure iSCSI is set as first boot device
        set_boot_order(server_ip, "iscsi")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error configuring iSCSI boot: {e}")
        return False

def configure_iso_boot(server_ip, version):
    """Configure server to boot from ISO using iDRAC virtual media"""
    version_fmt = version.replace('.', '_')
    iso_url = f"http://192.168.2.245/openshift_isos/{version}/agent.x86_64.iso"
    
    # Mount ISO via iDRAC Redfish API
    idrac_url = f"https://{server_ip}/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/VirtualMedia.InsertMedia"
    
    payload = {
        "Image": iso_url,
        "Inserted": True,
        "WriteProtected": True
    }
    
    print(f"Mounting ISO {iso_url} to {server_ip}...")
    try:
        response = requests.post(
            idrac_url,
            json=payload,
            auth=HTTPBasicAuth(IDRAC_USER, IDRAC_PASSWORD),
            verify=False
        )
        response.raise_for_status()
        print("ISO mounted successfully")
        
        # Set boot order to use virtual media first
        return set_boot_order(server_ip, "VirtualCD")
        
    except requests.exceptions.RequestException as e:
        print(f"Error configuring iDRAC: {e}")
        return False

def set_boot_order(server_ip, first_boot):
    """Set the boot order using existing script"""
    cmd = [
        "python", 
        str(SCRIPT_DIR / "set_boot_order.py"), 
        "--first-boot", 
        first_boot
    ]
    
    print(f"Setting boot order with {first_boot} as first boot device...")
    try:
        subprocess.run(cmd, check=True)
        print("Boot order updated successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting boot order: {e}")
        return False

def reboot_server(server_ip):
    """Reboot the server"""
    cmd = ["python", str(SCRIPT_DIR / "reboot_server.py"), "--server", server_ip]
    
    print(f"Rebooting server {server_ip}...")
    try:
        subprocess.run(cmd, check=True)
        print("Reboot initiated")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error rebooting server: {e}")
        return False

def check_iso_availability(version):
    """Check if the ISO for the specified version is available"""
    version_fmt = version.replace('.', '_')
    iso_url = f"http://192.168.2.245/openshift_isos/{version}/agent.x86_64.iso"
    
    try:
        response = requests.head(iso_url, timeout=5)
        if response.status_code != 200:
            print(f"Warning: ISO file at {iso_url} may not be accessible (HTTP {response.status_code})")
            return False
        return True
    except requests.exceptions.RequestException:
        print(f"Warning: Unable to verify ISO availability at {iso_url}")
        return False

def configure_netboot(server_ip, custom_menu=None):
    """Configure server to boot from netboot.xyz"""
    # Base netboot URL
    netboot_url = "https://netboot.omnisack.nl/ipxe/netboot.xyz.efi"
    
    # If a custom menu is specified, use it
    if custom_menu:
        if custom_menu == "openshift":
            netboot_url = f"http://192.168.2.245/netboot/openshift.ipxe"
    
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
        
        # Set boot order to use HTTP first
        return set_boot_order(server_ip, "HTTP")
    except requests.exceptions.RequestException as e:
        print(f"Error configuring netboot: {e}")
        return False

def check_netboot_connectivity():
    """Check if netboot service is accessible"""
    netboot_url = "https://netboot.omnisack.nl/ipxe/netboot.xyz.efi"
    
    try:
        response = requests.head(netboot_url, timeout=5)
        if response.status_code != 200:
            print(f"Warning: Netboot.xyz at {netboot_url} may not be accessible (HTTP {response.status_code})")
            return False
        return True
    except requests.exceptions.RequestException:
        print(f"Warning: Unable to verify netboot.xyz availability at {netboot_url}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Configure OpenShift boot options for Dell R630")
    parser.add_argument("--server", required=True, help="Server IP address (e.g., 192.168.2.230)")
    parser.add_argument("--method", choices=["iscsi", "iso", "netboot"], required=True, help="Boot method")
    parser.add_argument("--version", default="4.18", help="OpenShift version (e.g., 4.18)")
    parser.add_argument("--reboot", action="store_true", help="Reboot after configuration")
    parser.add_argument("--check-only", action="store_true", help="Check configuration only, don't make changes")
    parser.add_argument("--netboot-menu", help="Custom netboot.xyz menu entry (for netboot method)")
    
    args = parser.parse_args()
    
    success = False
    
    if args.check_only:
        # Just check if targets/ISOs are available
        if args.method == "iscsi":
            targets_data = load_iscsi_targets()
            target_name = f"openshift_{args.version.replace('.', '_')}"
            target = get_target_by_name(targets_data, target_name)
            
            if target:
                print(f"Target '{target_name}' is available in configuration")
                print(f"  IQN: {target.get('iqn')}")
                print(f"  IP: {target.get('ip')}:{target.get('port')}")
                print(f"  LUN: {target.get('lun')}")
                print(f"  Description: {target.get('description')}")
            else:
                print(f"Target '{target_name}' not found in {ISCSI_TARGETS_FILE}")
                
        elif args.method == "iso":
            if check_iso_availability(args.version):
                print(f"ISO for OpenShift {args.version} is accessible")
            else:
                print(f"ISO for OpenShift {args.version} might not be accessible")
        
        elif args.method == "netboot":
            if check_netboot_connectivity():
                print(f"netboot.xyz is accessible")
                if args.netboot_menu:
                    print(f"Using custom menu: {args.netboot_menu}")
            else:
                print(f"netboot.xyz might not be accessible")
                
        sys.exit(0)
    
    # Perform the actual configuration
    if args.method == "iscsi":
        success = configure_iscsi_boot(args.server, args.version)
    elif args.method == "iso":
        if check_iso_availability(args.version):
            success = configure_iso_boot(args.server, args.version)
        else:
            print("Warning: Proceeding with ISO boot configuration despite availability check failure")
            success = configure_iso_boot(args.server, args.version)
    elif args.method == "netboot":
        if check_netboot_connectivity():
            success = configure_netboot(args.server, args.netboot_menu)
        else:
            print("Warning: Proceeding with netboot configuration despite connectivity check failure")
            success = configure_netboot(args.server, args.netboot_menu)
    
    if success and args.reboot:
        reboot_server(args.server)
    
    if success:
        print(f"\nServer {args.server} successfully configured to boot OpenShift {args.version} using {args.method}")
        if not args.reboot:
            print("Note: Server was not rebooted. Use --reboot to automatically reboot after configuration")
    else:
        print(f"\nFailed to configure server {args.server}")
        sys.exit(1)

if __name__ == "__main__":
    main()
