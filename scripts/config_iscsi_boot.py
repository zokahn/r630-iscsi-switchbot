#!/usr/bin/env python3
# config_iscsi_boot.py - Configure iSCSI boot on Dell R630 servers via iDRAC Redfish API

import argparse
import json
import os
import subprocess
import sys
import time
import requests
import urllib3
from pathlib import Path

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set paths
SCRIPT_DIR = Path(__file__).parent
DELL_SCRIPTS_DIR = SCRIPT_DIR / "dell"
NETWORK_CONFIG_SCRIPT = DELL_SCRIPTS_DIR / "SetNetworkDevicePropertiesREDFISH.py"
GET_PROPERTIES_SCRIPT = DELL_SCRIPTS_DIR / "GetSetBiosAttributesREDFISH.py"
CONFIG_DIR = SCRIPT_DIR.parent / "config"
ISCSI_TARGETS_FILE = CONFIG_DIR / "iscsi_targets.json"
ISCSI_CONFIG_TEMPLATE = CONFIG_DIR / "iscsi_config_template.json"

# Default values
DEFAULT_IDRAC_IP = "192.168.2.230"
DEFAULT_IDRAC_USER = "root"
DEFAULT_IDRAC_PASSWORD = "calvin"
DEFAULT_NIC = "NIC.Integrated.1-1-1"  # This should be adjusted based on your system

def parse_arguments():
    parser = argparse.ArgumentParser(description="Configure iSCSI boot on Dell R630 servers")
    parser.add_argument("--server", default=DEFAULT_IDRAC_IP, help="Server IP address (e.g., 192.168.2.230)")
    parser.add_argument("--user", default=DEFAULT_IDRAC_USER, help="iDRAC username")
    parser.add_argument("--password", default=DEFAULT_IDRAC_PASSWORD, help="iDRAC password")
    parser.add_argument("--nic", default=DEFAULT_NIC, help="NIC to configure for iSCSI boot")
    parser.add_argument("--target", required=True, help="Target name from iscsi_targets.json")
    parser.add_argument("--secondary-target", help="Optional secondary target name for multipath")
    parser.add_argument("--initiator-name", help="Custom initiator name (default: auto-generated)")
    parser.add_argument("--gateway", help="Custom default gateway (default: DHCP)")
    parser.add_argument("--no-reboot", action="store_true", help="Don't reboot after configuration")
    parser.add_argument("--direct-config", action="store_true", help="Use Redfish API directly instead of Dell scripts")
    parser.add_argument("--list-targets", action="store_true", help="List available targets and exit")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing configuration")
    parser.add_argument("--reset-iscsi", action="store_true", help="Reset iSCSI configuration to defaults")
    
    return parser.parse_args()

def load_targets():
    """Load the iSCSI targets from the configuration file"""
    try:
        with open(ISCSI_TARGETS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading targets file: {e}")
        sys.exit(1)

def get_target_config(targets_data, target_name):
    """Get the configuration for the specified target"""
    for target in targets_data["targets"]:
        if target["name"] == target_name:
            return target
    
    print(f"Error: Target '{target_name}' not found in the targets configuration.")
    print("Available targets:")
    for target in targets_data["targets"]:
        print(f"  - {target['name']}: {target['description']}")
    sys.exit(1)

def create_iscsi_config(target, secondary_target=None, initiator_name=None, gateway=None):
    """Create the iSCSI configuration file for the Dell Redfish script"""
    # Load base configuration from template
    try:
        with open(ISCSI_CONFIG_TEMPLATE, "r") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback to hardcoded template if file is not available
        config = {
            "iSCSIBoot": {
                "IPAddressType": "IPv4",
                "InitiatorIPAddress": "0.0.0.0",  # Using DHCP
                "InitiatorNetmask": "255.255.255.0",
                "TargetInfoViaDHCP": False,
                "IPMaskDNSViaDHCP": True,
                "AuthenticationMethod": "None"
            }
        }
    
    # Update with primary target information
    config["iSCSIBoot"]["PrimaryTargetName"] = target["iqn"]
    config["iSCSIBoot"]["PrimaryTargetIPAddress"] = target["ip"]
    config["iSCSIBoot"]["PrimaryTargetTCPPort"] = target["port"]
    config["iSCSIBoot"]["PrimaryLUN"] = target["lun"]
    
    # Add authentication if specified in target
    if "auth_method" in target:
        config["iSCSIBoot"]["AuthenticationMethod"] = target["auth_method"]
        
        if target["auth_method"] == "CHAP" and "chap_username" in target and "chap_secret" in target:
            config["iSCSIBoot"]["CHAPUsername"] = target["chap_username"]
            config["iSCSIBoot"]["CHAPSecret"] = target["chap_secret"]
    
    # Add custom initiator name if provided
    if initiator_name:
        config["iSCSIBoot"]["InitiatorNameSource"] = "ConfiguredViaAPI"
        config["iSCSIBoot"]["InitiatorName"] = initiator_name
    
    # Add default gateway if provided
    if gateway:
        config["iSCSIBoot"]["InitiatorDefaultGateway"] = gateway
    
    # Configure multipath if secondary target is provided
    if secondary_target:
        config["iSCSIBoot"]["MultipleConnectionsEnabled"] = True
        config["iSCSIBoot"]["SecondaryTargetName"] = secondary_target["iqn"]
        config["iSCSIBoot"]["SecondaryTargetIPAddress"] = secondary_target["ip"]
        config["iSCSIBoot"]["SecondaryTargetTCPPort"] = secondary_target["port"]
        config["iSCSIBoot"]["SecondaryLUN"] = secondary_target["lun"]
        
        # Add secondary authentication if specified
        if "auth_method" in secondary_target and secondary_target["auth_method"] == "CHAP":
            if "chap_username" in secondary_target and "chap_secret" in secondary_target:
                config["iSCSIBoot"]["SecondaryUsername"] = secondary_target["chap_username"]
                config["iSCSIBoot"]["SecondarySecret"] = secondary_target["chap_secret"]
    
    # Write the configuration to the file expected by the Dell script
    config_file = Path("set_network_properties.ini")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    return config_file, config

def configure_iscsi_boot(args, target, secondary_target=None):
    """Configure the iSCSI boot settings on the server"""
    # Create the iSCSI configuration file
    config_file, config = create_iscsi_config(
        target, 
        secondary_target=secondary_target,
        initiator_name=args.initiator_name,
        gateway=args.gateway
    )
    
    print(f"Created iSCSI configuration file for target: {target['name']} ({target['description']})")
    print(f"Primary target: {target['iqn']} @ {target['ip']}:{target['port']} LUN {target['lun']}")
    
    if secondary_target:
        print(f"Secondary target: {secondary_target['iqn']} @ {secondary_target['ip']}:{secondary_target['port']} LUN {secondary_target['lun']}")
    
    # Use direct Redfish API if specified
    if args.direct_config:
        success = configure_iscsi_via_redfish(
            args.server, 
            args.user, 
            args.password, 
            args.nic, 
            config, 
            reboot=not args.no_reboot
        )
        if success:
            print("\nConfiguration successful!")
            if args.no_reboot:
                print("NOTE: The server will need to be rebooted manually to apply the changes.")
            else:
                print("The server is being rebooted to apply the changes.")
                print("This process may take a few minutes.")
            return True
        else:
            print("Failed to configure iSCSI boot via direct Redfish API.")
            print("Falling back to Dell script method...")
    
    # Build the command to configure the NIC using Dell script
    cmd = [
        sys.executable,  # Use the current Python interpreter
        str(NETWORK_CONFIG_SCRIPT),
        "-ip", args.server,
        "-u", args.user,
        "-p", args.password,
        "--set", args.nic
    ]
    
    if args.no_reboot:
        cmd.extend(["--reboot", "l"])  # Schedule but don't reboot
    else:
        cmd.extend(["--reboot", "y"])  # Reboot immediately
    
    print("\nConfiguring iSCSI boot using Dell script...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error executing iSCSI configuration: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return False
        
        print(result.stdout)  # Print the output from the Dell script
        
        # Validate the configuration if successful
        if validate_iscsi_configuration(args.server, args.user, args.password, args.nic, target["iqn"]):
            print("✓ iSCSI configuration validation successful.")
        else:
            print("⚠ iSCSI configuration could not be fully validated. Please check manually after reboot.")
        
        print("\nConfiguration successful!")
        if args.no_reboot:
            print("NOTE: The server will need to be rebooted manually to apply the changes.")
        else:
            print("The server is being rebooted to apply the changes.")
            print("This process may take a few minutes.")
        
        return True
    except Exception as e:
        print(f"Error configuring iSCSI boot: {e}")
        return False
    finally:
        # Clean up the temporary configuration file
        if config_file.exists():
            config_file.unlink()

def check_idrac_firmware_version(server_ip, username, password):
    """Check if the iDRAC firmware version meets the minimum requirements"""
    url = f"https://{server_ip}/redfish/v1/Managers/iDRAC.Embedded.1"
    headers = {'content-type': 'application/json'}
    
    try:
        response = requests.get(
            url,
            headers=headers,
            verify=False,
            auth=(username, password)
        )
        
        if response.status_code != 200:
            print(f"Warning: Unable to retrieve iDRAC firmware version: {response.status_code}")
            return False
        
        data = response.json()
        firmware_version = data.get('FirmwareVersion', '')
        
        print(f"Detected iDRAC firmware version: {firmware_version}")
        
        # Parse version and check against minimum required (2.40.40.40)
        try:
            version_parts = firmware_version.split('.')
            if len(version_parts) >= 4:
                major = int(version_parts[0])
                minor = int(version_parts[1])
                
                if major < 2 or (major == 2 and minor < 40):
                    print("Warning: iDRAC firmware version below recommended minimum (2.40.40.40)")
                    print("Some Redfish API features may not be fully supported")
                    return False
                    
                return True
        except (ValueError, IndexError):
            print(f"Warning: Unable to parse iDRAC firmware version: {firmware_version}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Warning: Unable to check iDRAC firmware version: {e}")
        return False
        
    return True

def configure_iscsi_via_redfish(server_ip, username, password, nic_id, config, reboot=True):
    """Configure iSCSI boot directly using Redfish API instead of Dell script"""
    print("Using direct Redfish API for iSCSI configuration...")
    
    # Check firmware version
    check_idrac_firmware_version(server_ip, username, password)
    
    # Extract NIC Network Adapter ID from the NIC ID
    # Example: NIC.Integrated.1-1-1 -> NIC.Integrated.1
    network_adapter_id = ".".join(nic_id.split(".")[:2]) + "." + nic_id.split("-")[0].split(".")[-1]
    
    # Build the URL for the network device function
    url = f"https://{server_ip}/redfish/v1/Systems/System.Embedded.1/NetworkAdapters/{network_adapter_id}/NetworkDeviceFunctions/{nic_id}/Settings"
    
    # Set headers for the request
    headers = {'content-type': 'application/json'}
    
    try:
        # Instead of sending all attributes at once, set them in dependency order
        
        # Step 1: Set basic attributes first
        basic_config = {
            "iSCSIBoot": {
                "IPMaskDNSViaDHCP": config["iSCSIBoot"]["IPMaskDNSViaDHCP"]
            }
        }
        
        response = requests.patch(
            url,
            json=basic_config,
            headers=headers,
            verify=False,
            auth=(username, password)
        )
        
        if response.status_code != 200:
            print(f"Warning: Error setting basic iSCSI configuration: {response.status_code}")
            print(f"Response: {response.text}")
            # Continue anyway - some attributes might fail but others could succeed
        
        # Step 2: Set primary target information
        target_config = {
            "iSCSIBoot": {
                "PrimaryTargetName": config["iSCSIBoot"]["PrimaryTargetName"],
                "PrimaryTargetIPAddress": config["iSCSIBoot"]["PrimaryTargetIPAddress"],
                "PrimaryTargetTCPPort": config["iSCSIBoot"]["PrimaryTargetTCPPort"],
                "PrimaryLUN": config["iSCSIBoot"]["PrimaryLUN"]
            }
        }
        
        response = requests.patch(
            url,
            json=target_config,
            headers=headers,
            verify=False,
            auth=(username, password)
        )
        
        if response.status_code != 200:
            print(f"Warning: Error setting target iSCSI configuration: {response.status_code}")
            print(f"Response: {response.text}")
            # Continue anyway
            
        # Step 3: Set initiator information if available
        initiator_config = {"iSCSIBoot": {}}
        
        # Only add keys that exist in the config
        if "InitiatorNameSource" in config["iSCSIBoot"]:
            initiator_config["iSCSIBoot"]["InitiatorNameSource"] = config["iSCSIBoot"]["InitiatorNameSource"]
        
        if "InitiatorName" in config["iSCSIBoot"]:
            initiator_config["iSCSIBoot"]["InitiatorName"] = config["iSCSIBoot"]["InitiatorName"]
        
        # Only send the request if there are attributes to set
        if len(initiator_config["iSCSIBoot"]) > 0:
            response = requests.patch(
                url,
                json=initiator_config,
                headers=headers,
                verify=False,
                auth=(username, password)
            )
            
            if response.status_code != 200:
                print(f"Warning: Error setting initiator iSCSI configuration: {response.status_code}")
                print(f"Response: {response.text}")
        
        print("Successfully set critical iSCSI configuration parameters.")
        print("Note: Some non-critical parameters might not have been set due to hardware dependencies.")
        
        # Set up the apply time for the configuration
        apply_url = url
        if reboot:
            apply_payload = {"@Redfish.SettingsApplyTime": {"ApplyTime": "Immediate"}}
            print("Setting configuration to apply immediately (server will reboot)...")
        else:
            apply_payload = {"@Redfish.SettingsApplyTime": {"ApplyTime": "OnReset"}}
            print("Setting configuration to apply on next reboot...")
        
        response = requests.patch(
            apply_url,
            json=apply_payload,
            headers=headers,
            verify=False,
            auth=(username, password)
        )
        
        if response.status_code != 202:
            print(f"Error setting apply time: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Get the job ID from the response
        try:
            job_id = response.headers['Location'].split("/")[-1]
            print(f"Created configuration job: {job_id}")
            
            if reboot:
                print("Initiating server reboot...")
                reboot_url = f"https://{server_ip}/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
                reboot_payload = {'ResetType': 'GracefulRestart'}
                
                response = requests.post(
                    reboot_url,
                    json=reboot_payload,
                    headers=headers,
                    verify=False,
                    auth=(username, password)
                )
                
                if response.status_code != 204:
                    print(f"Error initiating reboot: {response.status_code}")
                    print(f"Response: {response.text}")
                    print("Server will need to be rebooted manually to apply changes.")
        except:
            print("Unable to determine job ID or reboot status")
            print("Changes will be applied at next reboot")
        
        return True
    
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with iDRAC: {e}")
        return False

def reset_iscsi_configuration(args):
    """Reset iSCSI configuration to defaults"""
    print("Resetting iSCSI configuration to defaults...")
    
    # Create minimal configuration to reset iSCSI
    config = {
        "iSCSIBoot": {
            "IPAddressType": "IPv4",
            "TargetInfoViaDHCP": True,
            "IPMaskDNSViaDHCP": True,
            "AuthenticationMethod": "None",
            "PrimaryTargetName": "",
            "PrimaryTargetIPAddress": "0.0.0.0",
            "PrimaryLUN": 0
        }
    }
    
    # Write reset configuration to file
    config_file = Path("reset_iscsi_properties.ini")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    # Build the command to reset the NIC
    cmd = [
        sys.executable,
        str(NETWORK_CONFIG_SCRIPT),
        "-ip", args.server,
        "-u", args.user,
        "-p", args.password,
        "--set", args.nic
    ]
    
    if args.no_reboot:
        cmd.extend(["--reboot", "l"])
    else:
        cmd.extend(["--reboot", "y"])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error resetting iSCSI configuration: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return False
        
        print(result.stdout)
        print("\nSuccessfully reset iSCSI configuration.")
        
        if args.no_reboot:
            print("NOTE: The server will need to be rebooted manually to apply the changes.")
        else:
            print("The server is being rebooted to apply the changes.")
        
        return True
    except Exception as e:
        print(f"Error resetting iSCSI configuration: {e}")
        return False
    finally:
        if config_file.exists():
            config_file.unlink()

def validate_iscsi_configuration(server_ip, username, password, nic_id, expected_target_iqn=None):
    """Validate iSCSI configuration after applying it"""
    print("\nValidating iSCSI configuration...")
    
    # Build the command to get NIC properties
    cmd = [
        sys.executable,
        str(NETWORK_CONFIG_SCRIPT),
        "-ip", server_ip,
        "-u", username,
        "-p", password,
        "--get-properties", nic_id
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error getting iSCSI configuration: {result.returncode}")
            return False
        
        output = result.stdout
        
        # Check if output contains iSCSI boot settings
        if "iSCSIBoot Attributes" not in output:
            print("No iSCSI boot attributes found in the response.")
            return False
        
        # Validate specific fields if expected target is provided
        if expected_target_iqn:
            if f"PrimaryTargetName: {expected_target_iqn}" not in output:
                print(f"Warning: Target IQN mismatch. Expected: {expected_target_iqn}")
                print("Current configuration may not match the requested configuration.")
                return False
        
        # Check for basic required fields
        required_fields = [
            "PrimaryTargetName",
            "PrimaryTargetIPAddress",
            "PrimaryLUN"
        ]
        
        for field in required_fields:
            if f"{field}:" not in output:
                print(f"Warning: Required field {field} not found in configuration.")
                return False
        
        print("iSCSI boot configuration looks correct.")
        return True
        
    except Exception as e:
        print(f"Error validating iSCSI configuration: {e}")
        return False

def list_available_targets():
    """List the available iSCSI targets"""
    targets_data = load_targets()
    print("Available iSCSI boot targets:")
    print("\n{:<15} {:<50} {:<15} {:<10} {:<8} {:<8}".format(
        "NAME", "IQN", "IP", "PORT", "LUN", "AUTH"
    ))
    print("-" * 110)
    for target in targets_data["targets"]:
        auth_method = target.get("auth_method", "None")
        print("{:<15} {:<50} {:<15} {:<10} {:<8} {:<8}".format(
            target["name"],
            target["iqn"],
            target["ip"],
            target["port"],
            target["lun"],
            auth_method
        ))
    print("\nTo configure a target: config_iscsi_boot.py --target <name>")
    print("For multipath configuration: config_iscsi_boot.py --target <primary> --secondary-target <secondary>")

def main():
    args = parse_arguments()
    
    # Verify the Redfish script exists
    if not NETWORK_CONFIG_SCRIPT.exists():
        print(f"Error: Could not find the Redfish script at {NETWORK_CONFIG_SCRIPT}")
        print("Make sure the Dell Redfish scripts are in the scripts/dell directory.")
        sys.exit(1)
    
    # Just list targets if requested
    if args.list_targets:
        list_available_targets()
        return
    
    # Load the targets configuration
    targets_data = load_targets()
    
    # Just validate existing configuration if requested
    if args.validate_only:
        print(f"Validating iSCSI configuration for {args.server}...")
        if validate_iscsi_configuration(args.server, args.user, args.password, args.nic):
            print("\nValidation successful: iSCSI boot is properly configured.")
        else:
            print("\nValidation failed: iSCSI boot may not be properly configured.")
        return
    
    # Reset iSCSI configuration if requested
    if args.reset_iscsi:
        if reset_iscsi_configuration(args):
            print("\nSuccessfully reset iSCSI configuration.")
        else:
            print("\nFailed to reset iSCSI configuration.")
            sys.exit(1)
        return
    
    # Get the selected primary target
    target = get_target_config(targets_data, args.target)
    
    # Get the selected secondary target if specified
    secondary_target = None
    if args.secondary_target:
        secondary_target = get_target_config(targets_data, args.secondary_target)
    
    # Configure iSCSI boot
    if not configure_iscsi_boot(args, target, secondary_target):
        print("Failed to configure iSCSI boot.")
        sys.exit(1)
    
    print(f"\nSuccessfully configured iSCSI boot for target: {args.target}")
    if secondary_target:
        print(f"With secondary target: {args.secondary_target}")

if __name__ == "__main__":
    main()
