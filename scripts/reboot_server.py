#!/usr/bin/env python3
# reboot_server.py - Reboot Dell R630 servers using Redfish API

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Set paths
SCRIPT_DIR = Path(__file__).parent
DELL_SCRIPTS_DIR = SCRIPT_DIR / "dell"
REBOOT_SCRIPT = DELL_SCRIPTS_DIR / "CreateServerRebootJobREDFISH.py"

# Default values
DEFAULT_IDRAC_IP = "192.168.2.230"
DEFAULT_IDRAC_USER = "root"
DEFAULT_IDRAC_PASSWORD = "calvin"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Reboot Dell R630 servers")
    parser.add_argument("--server", default=DEFAULT_IDRAC_IP, help="Server IP address (e.g., 192.168.2.230)")
    parser.add_argument("--user", default=DEFAULT_IDRAC_USER, help="iDRAC username")
    parser.add_argument("--password", default=DEFAULT_IDRAC_PASSWORD, help="iDRAC password")
    parser.add_argument("--force", action="store_true", help="Force reboot even if server is already off")
    parser.add_argument("--wait", action="store_true", help="Wait for reboot to complete")
    
    return parser.parse_args()

def reboot_server(args):
    """Reboot the server using the Dell Redfish script"""
    # Note: Since we don't have the Dell CreateServerRebootJobREDFISH.py script,
    # we'll use the direct Redfish API to reboot the server
    
    # First check if the Dell script exists
    if REBOOT_SCRIPT.exists():
        # Use the Dell script
        cmd = [
            sys.executable,  # Use the current Python interpreter
            str(REBOOT_SCRIPT),
            "-ip", args.server,
            "-u", args.user,
            "-p", args.password,
            "--reboot-job-type", "2",  # 2 = GracefulRestart
            "--start-time", "TIME_NOW"
        ]
        
        print(f"Rebooting server {args.server} using Dell Redfish script...")
        try:
            subprocess.run(cmd, check=True)
            print("Reboot job created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating reboot job: {e}")
            return False
    else:
        # Fall back to direct Redfish API
        import requests
        from requests.auth import HTTPBasicAuth
        import time
        import urllib3
        
        # Disable SSL warnings for self-signed certs
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        base_url = f"https://{args.server}/redfish/v1"
        power_url = f"{base_url}/Systems/System.Embedded.1"
        reset_url = f"{power_url}/Actions/ComputerSystem.Reset"
        
        print(f"Dell Redfish script not found at {REBOOT_SCRIPT}")
        print("Falling back to direct Redfish API...")
        
        try:
            # Check current power state
            response = requests.get(
                power_url,
                auth=HTTPBasicAuth(args.user, args.password),
                verify=False
            )
            
            if response.status_code >= 400:
                print(f"Error querying server power state: {response.status_code}")
                print(response.text)
                return False
                
            power_state = response.json().get('PowerState')
            print(f"Current server power state: {power_state}")
            
            # Choose appropriate reboot action
            if power_state == 'Off' and not args.force:
                print("Server is already powered off. Use --force to power on.")
                return True
                
            reset_type = 'GracefulRestart'
            if power_state == 'Off':
                reset_type = 'On'
                print("Powering on server...")
            else:
                print("Initiating graceful server restart...")
                
            reset_payload = {
                "ResetType": reset_type
            }
            
            response = requests.post(
                reset_url,
                json=reset_payload,
                auth=HTTPBasicAuth(args.user, args.password),
                verify=False
            )
            
            if response.status_code >= 400:
                print(f"Error initiating server reboot: {response.status_code}")
                print(response.text)
                return False
                
            print(f"Server {args.server} reboot initiated")
            
            # Wait for reboot to complete if requested
            if args.wait:
                max_wait_time = 300  # 5 minutes
                interval = 15  # 15 seconds
                elapsed = 0
                
                print(f"Waiting for server to reboot (timeout: {max_wait_time} seconds)...")
                
                # Wait for server to come back up
                while elapsed < max_wait_time:
                    print(f"Checking if server is back online... ({elapsed}/{max_wait_time} seconds)")
                    time.sleep(interval)
                    elapsed += interval
                    
                    try:
                        response = requests.get(
                            power_url,
                            auth=HTTPBasicAuth(args.user, args.password),
                            verify=False,
                            timeout=5
                        )
                        
                        if response.status_code < 400:
                            current_state = response.json().get('PowerState')
                            if current_state == 'On':
                                print("Server has successfully rebooted and is now powered on")
                                return True
                    except requests.exceptions.RequestException:
                        # Server still rebooting
                        pass
                
                print(f"Timeout waiting for server to reboot (waited {max_wait_time} seconds)")
                print("The server might still be rebooting. Check its status manually.")
                return False
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Error rebooting server: {e}")
            return False

def main():
    args = parse_arguments()
    
    if reboot_server(args):
        print(f"Successfully initiated reboot for server {args.server}")
        sys.exit(0)
    else:
        print(f"Failed to reboot server {args.server}")
        sys.exit(1)

if __name__ == "__main__":
    main()
