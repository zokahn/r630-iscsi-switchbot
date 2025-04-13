#!/usr/bin/env python3
# set_boot_order.py - Set boot order on Dell R630 servers via iDRAC Redfish API

import argparse
import subprocess
import sys
import re
from pathlib import Path

# Set paths
SCRIPT_DIR = Path(__file__).parent
DELL_SCRIPTS_DIR = SCRIPT_DIR / "dell"
GET_BOOT_ORDER_SCRIPT = DELL_SCRIPTS_DIR / "GetSetBiosAttributesREDFISH.py"
SET_BOOT_ORDER_SCRIPT = DELL_SCRIPTS_DIR / "ChangeBiosBootOrderREDFISH.py"

# Default values
DEFAULT_IDRAC_IP = "192.168.2.230"
DEFAULT_IDRAC_USER = "root"
DEFAULT_IDRAC_PASSWORD = "calvin"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Set boot order on Dell R630 servers")
    parser.add_argument("--server", default=DEFAULT_IDRAC_IP, help="Server IP address (e.g., 192.168.2.230)")
    parser.add_argument("--user", default=DEFAULT_IDRAC_USER, help="iDRAC username")
    parser.add_argument("--password", default=DEFAULT_IDRAC_PASSWORD, help="iDRAC password")
    parser.add_argument("--first-boot", required=True, help="First boot device (iscsi, VirtualCD, HTTP, PXE, HDD)")
    parser.add_argument("--no-reboot", action="store_true", help="Don't reboot after setting boot order")
    
    return parser.parse_args()

def get_current_boot_order(server_ip, username, password):
    """Get the current boot order from the server"""
    cmd = [
        sys.executable,  # Use the current Python interpreter
        str(SET_BOOT_ORDER_SCRIPT),
        "-ip", server_ip,
        "-u", username,
        "-p", password,
        "--get"
    ]
    
    print(f"Retrieving current BIOS boot order from {server_ip}...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: Command failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return None
        
        return result.stdout
    
    except Exception as e:
        print(f"Exception executing command: {e}")
        return None

def find_boot_device_id(boot_order_output, boot_type):
    """Find the boot device ID for the specified boot type"""
    # Define patterns for different boot types
    patterns = {
        "iscsi": r'(Boot\d+)\s*:\s*.*(?:iSCSI|ISCSI)',
        "hdd": r'(Boot\d+)\s*:\s*.*(?:Hard\s*Drive|HDD)',
        "pxe": r'(Boot\d+)\s*:\s*.*(?:PXE|Network)',
        "cd": r'(Boot\d+)\s*:\s*.*(?:CD|DVD|Optical)',
        "usb": r'(Boot\d+)\s*:\s*.*(?:USB)',
        "bios": r'(Boot\d+)\s*:\s*.*(?:BIOS|Shell)',
        "floppy": r'(Boot\d+)\s*:\s*.*(?:Floppy)',
        "VirtualCD": r'(Boot\d+)\s*:\s*.*(?:Virtual\s*CD|VCD|Virtual\s*Media)',
        "HTTP": r'(Boot\d+)\s*:\s*.*(?:HTTP|UefiHttp)'
    }
    
    # Use the appropriate pattern based on boot_type
    if boot_type.lower() in patterns:
        pattern = patterns[boot_type.lower()]
        match = re.search(pattern, boot_order_output, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Special handling for iSCSI boot - if no iSCSI device is found directly, 
    # look for a PXE device that might be usable for iSCSI boot
    if boot_type.lower() == "iscsi" and "PXE Device" in boot_order_output:
        print("No explicit iSCSI boot device found, looking for a PXE device to use instead...")
        
        # Extract all Boot IDs from the output
        boot_ids = re.findall(r'Boot\d+', boot_order_output)
        if boot_ids:
            # Find first PXE boot device
            for boot_id in boot_ids:
                if f"'{boot_id}'" in boot_order_output and "PXE Device" in boot_order_output[boot_order_output.find(f"'{boot_id}'"):boot_order_output.find(f"'{boot_id}'") + 500]:
                    print(f"Using {boot_id} (PXE Device) as fallback for iSCSI boot")
                    return boot_id
            
            # If no PXE device found, use the first boot device as a last resort
            print(f"No PXE device found, using {boot_ids[0]} as fallback boot device")
            return boot_ids[0]
    
    return None

def set_boot_order(server_ip, username, password, boot_device_id, reboot=True):
    """Set the boot order on the server"""
    cmd = [
        sys.executable,  # Use the current Python interpreter
        str(SET_BOOT_ORDER_SCRIPT),
        "-ip", server_ip,
        "-u", username,
        "-p", password,
        "--change", boot_device_id
    ]
    
    print(f"Setting {boot_device_id} as the first boot device...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: Command failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print(f"Successfully set {boot_device_id} as the first boot device.")
        
        # If reboot is requested, use the reboot script
        if reboot:
            reboot_cmd = [
                sys.executable,
                str(SCRIPT_DIR / "reboot_server.py"),
                "--server", server_ip,
                "--user", username,
                "--password", password
            ]
            print("Rebooting server to apply changes...")
            try:
                subprocess.run(reboot_cmd, check=True)
                print("Reboot initiated successfully")
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to reboot the server: {e}")
                print("You may need to reboot the server manually to apply changes")
        else:
            print("NOTE: Changes will be applied on the next server reboot.")
        
        return True
    
    except Exception as e:
        print(f"Error setting boot order: {e}")
        return False

def main():
    args = parse_arguments()
    
    # Verify that the Redfish scripts exist
    for script in [GET_BOOT_ORDER_SCRIPT, SET_BOOT_ORDER_SCRIPT]:
        if not script.exists():
            print(f"Error: Could not find the Redfish script at {script}")
            print("Make sure the Dell Redfish scripts are in the scripts/dell directory.")
            sys.exit(1)
    
    # Get current boot order
    boot_order_output = get_current_boot_order(args.server, args.user, args.password)
    if not boot_order_output:
        print("Failed to retrieve current boot order.")
        print("Using default approach instead of getting current boot order...")
        
        # Try to set boot device directly based on first_boot parameter
        if args.first_boot.lower() == "iscsi":
            # For iSCSI boot, we'll try Boot0004 as a common ID
            boot_device_id = "Boot0004"
        else:
            print(f"Error: Could not determine boot device ID for {args.first_boot}.")
            print("Please check that the boot device is properly configured on the server.")
            sys.exit(1)
    else:
        print("\nCurrent boot order:")
        print(boot_order_output)
        
        # Find the boot device ID for the specified boot type
        boot_device_id = find_boot_device_id(boot_order_output, args.first_boot)
        if not boot_device_id:
            print(f"Error: Could not find a {args.first_boot} boot device in the current boot order.")
            print(f"Make sure that {args.first_boot} boot is properly configured on the server.")
            sys.exit(1)
    
    # Set the boot order
    reboot = not args.no_reboot
    if not set_boot_order(args.server, args.user, args.password, boot_device_id, reboot):
        print("Failed to set boot order.")
        sys.exit(1)

if __name__ == "__main__":
    main()
