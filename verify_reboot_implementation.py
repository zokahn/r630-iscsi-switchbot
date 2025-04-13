#!/usr/bin/env python3
"""
R630 iSCSI Direct Reboot and Configuration Tool
Use this tool to directly reboot servers and configure iSCSI for sandbox environments.
"""

import argparse
import subprocess
import os
import sys
import time
import requests
import urllib3
import json
from pathlib import Path

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def parse_args():
    parser = argparse.ArgumentParser(description="R630 iSCSI Direct Reboot Tool")
    parser.add_argument("--server", default="192.168.2.230", help="iDRAC IP address")
    parser.add_argument("--user", default="root", help="iDRAC username")
    parser.add_argument("--password", default="calvin", help="iDRAC password") 
    parser.add_argument("--nic", default="NIC.Integrated.1-1-1", help="NIC to configure")
    parser.add_argument("--target", help="iSCSI target name (from config file)")
    parser.add_argument("--no-reboot", action="store_true", help="Skip rebooting after configuration")
    parser.add_argument("--verify-only", action="store_true", help="Only verify script parameters, don't execute actions")
    parser.add_argument("--direct-reboot", action="store_true", help="Perform an immediate direct reboot without configuration")
    parser.add_argument("--force", action="store_true", help="Force operations without confirmation")
    return parser.parse_args()

def check_server_power_state(server, user, password):
    """Check the current power state of the server via iDRAC"""
    print(f"Checking power state of {server}...")
    url = f"https://{server}/redfish/v1/Systems/System.Embedded.1"
    try:
        response = requests.get(
            url,
            auth=(user, password),
            verify=False,
            timeout=10
        )
        if response.status_code < 400:
            data = response.json()
            power_state = data.get('PowerState', 'unknown')
            print(f"Server power state: {power_state}")
            return power_state
        else:
            print(f"Error querying server: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error connecting to iDRAC: {e}")
        return None

def verify_dell_script_parameters():
    """Verify that we're using the correct Dell script parameters"""
    script_path = Path("./scripts/config_iscsi_boot.py")
    
    if not script_path.exists():
        print(f"Error: Script not found at {script_path}")
        return False
    
    with open(script_path, "r") as f:
        content = f.read()
    
    # Check for the correct reboot parameter
    correct_param_count = content.count('cmd.extend(["--reboot", "n"])')
    incorrect_param_count = content.count('cmd.extend(["--reboot", "y"])')
    
    print(f"Instances of correct reboot parameter (n): {correct_param_count}")
    print(f"Instances of incorrect reboot parameter (y): {incorrect_param_count}")
    
    if correct_param_count >= 3 and incorrect_param_count <= 1:
        print("✅ Script appears to be using the correct Dell reboot parameters")
        return True
    else:
        print("❌ Script may not have all reboot parameters fixed")
        return False

def create_reboot_config():
    """Create a minimal configuration for rebooting"""
    config = {
        "iSCSIBoot": {
            "IPMaskDNSViaDHCP": True,
            "IPAddressType": "IPv4"
        }
    }
    
    config_file = Path("set_network_properties.ini")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    return config_file

def perform_direct_reboot(args):
    """Directly reboot the server using the most direct method possible"""
    print(f"🔄 Executing FORCEFUL direct reboot for server {args.server}...")
    
    url = f"https://{args.server}/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
    headers = {'Content-Type': 'application/json'}
    
    # Most forceful reboot type
    data = {"ResetType": "ForceRestart"}
    
    try:
        print(f"Sending ForceRestart command directly to iDRAC REST API...")
        response = requests.post(
            url,
            headers=headers,
            json=data,
            auth=(args.user, args.password),
            verify=False,
            timeout=30
        )
        
        if response.status_code < 300:
            print(f"✅ Direct reboot command successful - Status code: {response.status_code}")
            print("Server should now be forcefully rebooting...")
            return True
        else:
            print(f"❌ Direct reboot failed - Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Try fallback to graceful reboot
            print("\nAttempting fallback to graceful reboot...")
            data = {"ResetType": "GracefulRestart"}
            response = requests.post(
                url,
                headers=headers,
                json=data,
                auth=(args.user, args.password),
                verify=False,
                timeout=30
            )
            
            if response.status_code < 300:
                print(f"✅ Graceful reboot command successful - Status code: {response.status_code}")
                return True
            else:
                print(f"❌ All reboot attempts failed")
                return False
    except Exception as e:
        print(f"❌ Error executing direct reboot: {e}")
        return False

def main():
    args = parse_args()
    
    print("🚀 R630 iSCSI Direct Reboot Tool 🚀")
    print("===================================")
    
    # Check current server state
    current_power_state = check_server_power_state(args.server, args.user, args.password)
    if current_power_state is None:
        print("Unable to determine server state. Continuing anyway...")
    
    # Only verify script parameters if requested
    if args.verify_only:
        print("Verifying script parameters only...")
        verify_dell_script_parameters()
        print("Verification complete.")
        return
    
    # Handle direct reboot request
    if args.direct_reboot:
        print("🔄 Performing direct reboot without configuration...")
        if not args.force and current_power_state != "On":
            proceed = input(f"Server may not be powered on (state: {current_power_state}). Proceed anyway? (y/N): ")
            if proceed.lower() != 'y':
                print("Reboot aborted.")
                return
        
        reboot_result = perform_direct_reboot(args)
        if reboot_result:
            print("✅ Reboot command completed. Server should be rebooting now.")
        else:
            print("❌ Reboot attempt failed.")
        return
    
    # If we have a target, execute configuration with the fixed script
    if args.target:
        print(f"📡 Executing iSCSI configuration for target {args.target}...")
        cmd = [
            sys.executable,
            "./scripts/config_iscsi_boot.py",
            "--server", args.server, 
            "--user", args.user,
            "--password", args.password,
            "--nic", args.nic,
            "--target", args.target
        ]
        
        if args.no_reboot:
            cmd.append("--no-reboot")
        
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode == 0:
            print("✅ iSCSI configuration completed successfully")
        else:
            print(f"❌ iSCSI configuration failed with exit code {result.returncode}")
        return
    
    # If we get here, no specific action was requested
    print("No specific action requested. Use one of the following options:")
    print("  --direct-reboot         Immediately reboot the server")
    print("  --target TARGET_NAME    Configure iSCSI for a specific target")
    print("  --verify-only           Just check the script parameters")

if __name__ == "__main__":
    main()
