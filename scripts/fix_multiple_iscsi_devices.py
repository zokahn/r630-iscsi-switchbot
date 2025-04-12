#!/usr/bin/python3
#
# fix_multiple_iscsi_devices.py - Eliminate redundant iSCSI boot devices on Dell R630
#

import argparse
import json
import os
import subprocess
import sys
import re
from pathlib import Path

# Set paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
REDFISH_SCRIPT = REPO_ROOT / "Redfish Python" / "SetNetworkDevicePropertiesREDFISH.py"
BOOT_ORDER_SCRIPT = REPO_ROOT / "Redfish Python" / "ChangeBiosBootOrderREDFISH.py"

# Default values
DEFAULT_IDRAC_IP = "192.168.2.230"
# Default credentials removed for security reasons - provide them via arguments or environment variables
DEFAULT_IDRAC_USER = ""  # Use --idrac-user argument or IDRAC_USER environment variable
DEFAULT_IDRAC_PASSWORD = ""  # Use --idrac-password argument or IDRAC_PASSWORD environment variable
DEFAULT_PRIMARY_NIC = "NIC.Integrated.1-1-1"  # This should be adjusted based on your system

def parse_arguments():
    parser = argparse.ArgumentParser(description="Fix multiple iSCSI boot devices on Dell R630 by disabling redundant paths")
    parser.add_argument("--idrac-ip", help=f"iDRAC IP address (default: {DEFAULT_IDRAC_IP})", default=DEFAULT_IDRAC_IP)
    parser.add_argument("--idrac-user", help="iDRAC username (required)", default=os.environ.get("IDRAC_USER", DEFAULT_IDRAC_USER))
    parser.add_argument("--idrac-password", help="iDRAC password (required)", default=os.environ.get("IDRAC_PASSWORD", DEFAULT_IDRAC_PASSWORD))
    parser.add_argument("--primary-nic", help=f"Primary NIC to keep for iSCSI boot (default: {DEFAULT_PRIMARY_NIC})", default=DEFAULT_PRIMARY_NIC)
    parser.add_argument("--no-reboot", help="Don't reboot the server after configuration", action="store_true")
    parser.add_argument("--list-only", help="Only list NICs, don't make changes", action="store_true")
    parser.add_argument("--force", help="Skip confirmation prompts", action="store_true")
    
    args = parser.parse_args()
    
    # Validate required parameters
    if not args.idrac_user:
        print("Error: iDRAC username is required. Provide with --idrac-user or IDRAC_USER environment variable.")
        sys.exit(1)
        
    if not args.idrac_password:
        print("Error: iDRAC password is required. Provide with --idrac-password or IDRAC_PASSWORD environment variable.")
        sys.exit(1)
    
    return args

def execute_command(command):
    """
    Execute a shell command and return the result
    """
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error executing command: {' '.join(command)}")
            print(f"STDERR: {result.stderr}")
            return False, result.stdout, result.stderr
        return True, result.stdout, result.stderr
    except Exception as e:
        print(f"Exception executing command: {e}")
        return False, "", str(e)

def get_nic_list(args):
    """
    Get list of all network devices
    """
    cmd = [
        sys.executable,  # Use the current Python interpreter
        str(REDFISH_SCRIPT),
        "-ip", args.idrac_ip,
        "-u", args.idrac_user,
        "-p", args.idrac_password,
        "--get-fqdds"
    ]
    
    print(f"Retrieving network devices from {args.idrac_ip}...")
    success, stdout, stderr = execute_command(cmd)
    
    if not success:
        print("Failed to retrieve network devices")
        return []
    
    nics = []
    lines = stdout.split("\n")
    for line in lines:
        if "NIC." in line and "-" in line:  # Look for lines like "NIC.Integrated.1-1-1"
            nic = line.strip()
            nics.append(nic)
    
    return nics

def check_iscsi_config(args, nic):
    """
    Check if the specified NIC has iSCSI boot enabled
    """
    cmd = [
        sys.executable,  # Use the current Python interpreter
        str(REDFISH_SCRIPT),
        "-ip", args.idrac_ip,
        "-u", args.idrac_user,
        "-p", args.idrac_password,
        "--get-properties", nic
    ]
    
    success, stdout, stderr = execute_command(cmd)
    
    if not success:
        print(f"Failed to check iSCSI configuration for {nic}")
        return False, {}
    
    # Check if iSCSI boot is configured
    iscsi_configured = "iSCSIBoot" in stdout
    
    # Extract iSCSI configuration details if available
    iscsi_config = {}
    if iscsi_configured:
        iscsi_section = False
        for line in stdout.split("\n"):
            line = line.strip()
            
            # Start capturing when we hit the iSCSIBoot section
            if "iSCSIBoot Attributes" in line:
                iscsi_section = True
                continue
            
            # Stop capturing when we hit another section
            if iscsi_section and line.startswith("-") and "Attributes" in line:
                iscsi_section = False
                break
            
            # Capture key-value pairs
            if iscsi_section and ":" in line:
                key, value = line.split(":", 1)
                iscsi_config[key.strip()] = value.strip()
    
    return iscsi_configured, iscsi_config

def disable_iscsi_on_nic(args, nic):
    """
    Disable iSCSI boot on the specified NIC
    """
    # Create an empty configuration file to clear iSCSI settings
    config = {"iSCSIBoot": {}}
    
    config_file = Path("set_network_properties.ini")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    # Build the command to set network properties
    cmd = [
        sys.executable,  # Use the current Python interpreter
        str(REDFISH_SCRIPT),
        "-ip", args.idrac_ip,
        "-u", args.idrac_user,
        "-p", args.idrac_password,
        "--set", nic,
        "--reboot", "l"  # Always use "l" for staged configuration, then reboot at the end if needed
    ]
    
    print(f"\nDisabling iSCSI boot on {nic}...")
    success, stdout, stderr = execute_command(cmd)
    
    if not success:
        print(f"Failed to disable iSCSI boot on {nic}")
        return False
    
    print(f"Successfully disabled iSCSI boot on {nic}")
    return True

def reboot_server(args):
    """
    Reboot the server
    """
    cmd = [
        sys.executable,  # Use the current Python interpreter
        str(REPO_ROOT / "Redfish Python" / "GetSetPowerStateREDFISH.py"),
        "-ip", args.idrac_ip,
        "-u", args.idrac_user,
        "-p", args.idrac_password,
        "--set", "ForceRestart"
    ]
    
    print("\nRebooting the server to apply changes...")
    success, stdout, stderr = execute_command(cmd)
    
    if not success:
        print("Failed to reboot the server")
        return False
    
    print("Server reboot initiated")
    return True

def main():
    args = parse_arguments()
    
    # Verify the Redfish script exists
    if not REDFISH_SCRIPT.exists():
        print(f"Error: Could not find the Redfish script at {REDFISH_SCRIPT}")
        print("Make sure you are running this script from the R630-iscsi-boot directory in the Dell Redfish repository.")
        sys.exit(1)
    
    # Get list of all NICs
    nics = get_nic_list(args)
    
    if not nics:
        print("No network devices found or failed to retrieve network devices")
        sys.exit(1)
    
    print(f"Found {len(nics)} network devices.")
    
    # Check which NICs have iSCSI boot enabled
    iscsi_nics = {}
    print("\nChecking which NICs have iSCSI boot enabled...")
    
    for nic in nics:
        is_iscsi, config = check_iscsi_config(args, nic)
        if is_iscsi:
            target_name = config.get("PrimaryTargetName", "Unknown")
            target_ip = config.get("PrimaryTargetIPAddress", "Unknown")
            iscsi_nics[nic] = {
                "target_name": target_name,
                "target_ip": target_ip,
                "config": config
            }
    
    # Display NICs with iSCSI boot enabled
    if not iscsi_nics:
        print("\nNo NICs have iSCSI boot enabled.")
        sys.exit(0)
    
    print(f"\nFound {len(iscsi_nics)} NICs with iSCSI boot enabled:")
    for nic, details in iscsi_nics.items():
        primary_indicator = " (PRIMARY)" if nic == args.primary_nic else ""
        print(f"  - {nic}{primary_indicator}: {details['target_name']} @ {details['target_ip']}")
    
    # If we're only listing, exit here
    if args.list_only:
        print("\nList-only mode, no changes made.")
        sys.exit(0)
    
    # Ensure the primary NIC is in the list
    if args.primary_nic not in iscsi_nics:
        print(f"\nError: Primary NIC {args.primary_nic} does not have iSCSI boot enabled.")
        print("Please choose a different primary NIC or configure iSCSI boot on this NIC first.")
        sys.exit(1)
    
    # Confirm before proceeding
    if not args.force:
        print(f"\nAbout to disable iSCSI boot on all NICs except {args.primary_nic}.")
        print(f"This will leave only one iSCSI boot device in your boot menu.")
        print(f"Server will {'not ' if args.no_reboot else ''}be rebooted after applying changes.")
        
        confirm = input("\nContinue? (y/n): ")
        if confirm.lower() != "y":
            print("Operation cancelled.")
            sys.exit(0)
    
    # Disable iSCSI boot on all NICs except the primary one
    success_count = 0
    failure_count = 0
    
    for nic in iscsi_nics:
        if nic == args.primary_nic:
            print(f"\nKeeping iSCSI boot enabled on primary NIC: {nic}")
            continue
        
        if disable_iscsi_on_nic(args, nic):
            success_count += 1
        else:
            failure_count += 1
    
    # Summary
    print("\nOperation complete!")
    print(f"  - Kept iSCSI boot on: {args.primary_nic}")
    print(f"  - Disabled iSCSI boot on: {success_count} NICs")
    if failure_count > 0:
        print(f"  - Failed to disable on: {failure_count} NICs")
    
    # Reboot if needed
    if not args.no_reboot:
        if success_count > 0:
            reboot_server(args)
            print("\nThe server is rebooting to apply changes.")
            print("After reboot, you should see only one iSCSI boot device in your boot menu.")
        else:
            print("\nNo changes were made, so no reboot is necessary.")
    else:
        print("\nNOTE: Changes will be applied on the next server reboot.")
        print("You can manually reboot the server when ready.")

if __name__ == "__main__":
    main()
