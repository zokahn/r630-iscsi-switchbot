#!/usr/bin/env python3
# integrate_iscsi_openshift.py - Integrate iSCSI target creation with OpenShift configuration

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
import requests
import yaml
import urllib3
from pathlib import Path

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
TRUENAS_CONFIG_SCRIPT = SCRIPT_DIR / "setup_truenas.sh"
ISCSI_BOOT_SCRIPT = SCRIPT_DIR / "config_iscsi_boot.py"
OPENSHIFT_ISO_SCRIPT = SCRIPT_DIR / "generate_openshift_iso.py"
ISCSI_TARGETS_FILE = CONFIG_DIR / "iscsi_targets.json"
MAPPING_FILE = CONFIG_DIR / "iscsi_device_mapping.json"

# Default values
DEFAULT_TRUENAS_IP = "192.168.2.245"
DEFAULT_IDRAC_IP = "192.168.2.230"
DEFAULT_IDRAC_USER = "root"
DEFAULT_IDRAC_PASSWORD = "calvin"
DEFAULT_TRUENAS_USER = "root"
DEFAULT_OPENSHIFT_VERSION = "stable"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Integrate iSCSI target creation with OpenShift configuration")
    parser.add_argument("--server-id", required=True, help="Server ID (e.g., 01)")
    parser.add_argument("--hostname", required=True, help="Server hostname")
    parser.add_argument("--node-ip", required=True, help="Server IP address")
    parser.add_argument("--mac-address", required=True, help="Server MAC address for primary NIC")
    parser.add_argument("--idrac-ip", default=DEFAULT_IDRAC_IP, help="iDRAC IP address")
    parser.add_argument("--idrac-user", default=DEFAULT_IDRAC_USER, help="iDRAC username")
    parser.add_argument("--idrac-password", default=DEFAULT_IDRAC_PASSWORD, help="iDRAC password")
    parser.add_argument("--truenas-ip", default=DEFAULT_TRUENAS_IP, help="TrueNAS IP address")
    parser.add_argument("--truenas-user", default=DEFAULT_TRUENAS_USER, help="TrueNAS username")
    parser.add_argument("--openshift-version", default=DEFAULT_OPENSHIFT_VERSION, help="OpenShift version (e.g., stable, 4.18)")
    parser.add_argument("--base-domain", default="example.com", help="Base domain for the cluster")
    parser.add_argument("--skip-target-creation", action="store_true", help="Skip TrueNAS iSCSI target creation")
    parser.add_argument("--skip-iscsi-config", action="store_true", help="Skip iSCSI boot configuration")
    parser.add_argument("--skip-iso-generation", action="store_true", help="Skip OpenShift ISO generation")
    parser.add_argument("--output-dir", help="Output directory for generated files")
    parser.add_argument("--device-path", help="Override iSCSI device path (e.g., /dev/sda)")
    
    return parser.parse_args()

def load_or_create_device_mapping():
    """Load existing iSCSI device mapping or create a new one"""
    if MAPPING_FILE.exists():
        try:
            with open(MAPPING_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {MAPPING_FILE}. Creating new mapping.")
    
    # Create initial mapping structure
    mapping = {
        "version": "1.0",
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "description": "Mapping between iSCSI targets and device paths",
        "targets": {}
    }
    
    return mapping

def save_device_mapping(mapping):
    """Save the iSCSI device mapping to file"""
    # Create parent directory if it doesn't exist
    MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Update the timestamp
    mapping["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Save to file
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)

def create_iscsi_target(args):
    """Create an iSCSI target on TrueNAS for the specified server"""
    print(f"Creating iSCSI target for server {args.hostname} ({args.server_id})...")
    
    # Generate unique identifiers for this server
    server_id = args.server_id
    version_format = args.openshift_version.replace(".", "_")
    target_name = f"iqn.2005-10.org.freenas.ctl:iscsi.r630-{server_id}.openshift{version_format}"
    zvol_name = f"tank/openshift_installations/r630_{server_id}_{version_format}"
    extent_name = f"openshift_r630_{server_id}_{version_format}_extent"
    
    # Create zvol using midclt (TrueNAS management interface)
    # This would typically be done via SSH on the TrueNAS server
    print(f"To create zvol on TrueNAS: ssh {args.truenas_user}@{args.truenas_ip} 'zfs create -V 500G -s {zvol_name}'")
    
    # Create JSON for iSCSI target configuration
    iscsi_config = {
        "target_name": target_name,
        "zvol_name": zvol_name,
        "extent_name": extent_name
    }
    
    # Print command to create iSCSI target using TrueNAS API
    print(f"To create iSCSI target on TrueNAS, run these commands:")
    print(f"""
# Create the target
TARGET_ID=$(midclt call iscsi.target.create '{{"name":"{target_name}","alias":"OpenShift {args.hostname}","mode":"ISCSI","groups":[{{"portal":1,"initiator":1,"auth":null}}]}}' | jq '.id')

# Create the extent
EXTENT_ID=$(midclt call iscsi.extent.create '{{"name":"{extent_name}","type":"DISK","disk":"zvol/{zvol_name}","blocksize":512,"pblocksize":false,"comment":"OpenShift {args.hostname} boot image","insecure_tpc":true,"xen":false,"rpm":"SSD","ro":false}}' | jq '.id')

# Associate the extent with the target
midclt call iscsi.targetextent.create '{{"target":$TARGET_ID,"extent":$EXTENT_ID,"lunid":0}}'
""")
    
    # Update the iscsi_targets.json file with the new target
    update_iscsi_targets(args, target_name, zvol_name)
    
    # Update the device mapping with the expected device path
    device_path = args.device_path if args.device_path else "/dev/sda"
    mapping = load_or_create_device_mapping()
    mapping["targets"][target_name] = {
        "server_id": server_id,
        "hostname": args.hostname,
        "device_path": device_path,
        "zvol_path": f"/dev/zvol/{zvol_name}",
        "created": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_device_mapping(mapping)
    
    return {
        "target_name": target_name,
        "device_path": device_path,
        "iqn": target_name,
        "ip": args.truenas_ip,
        "port": 3260,
        "lun": 0
    }

def update_iscsi_targets(args, target_name, zvol_name):
    """Update the iscsi_targets.json file with the new target"""
    # Load existing targets or create new file
    if ISCSI_TARGETS_FILE.exists():
        try:
            with open(ISCSI_TARGETS_FILE, "r") as f:
                targets_data = json.load(f)
        except json.JSONDecodeError:
            targets_data = {"targets": []}
    else:
        targets_data = {"targets": []}
    
    # Check if target already exists
    for target in targets_data["targets"]:
        if target.get("name") == args.hostname or target.get("iqn") == target_name:
            print(f"Target {args.hostname} already exists in targets file.")
            return
    
    # Add the new target
    new_target = {
        "name": args.hostname,
        "description": f"OpenShift {args.openshift_version} for R630-{args.server_id}",
        "iqn": target_name,
        "ip": args.truenas_ip,
        "port": 3260,
        "lun": 0
    }
    
    targets_data["targets"].append(new_target)
    
    # Save the updated targets file
    with open(ISCSI_TARGETS_FILE, "w") as f:
        json.dump(targets_data, f, indent=2)
    
    print(f"Updated {ISCSI_TARGETS_FILE} with target {args.hostname}")

def configure_iscsi_boot(args, target_info):
    """Configure the server for iSCSI boot using config_iscsi_boot.py"""
    print(f"Configuring iSCSI boot for server {args.hostname} ({args.server_id})...")
    
    # Build the command to run config_iscsi_boot.py
    cmd = [
        sys.executable,
        str(ISCSI_BOOT_SCRIPT),
        "--server", args.idrac_ip,
        "--user", args.idrac_user,
        "--password", args.idrac_password,
        "--target", args.hostname,
        "--no-reboot"  # Don't reboot immediately
    ]
    
    # Print the command for reference
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error configuring iSCSI boot: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return False
        
        print(result.stdout)
        print("Successfully configured iSCSI boot.")
        return True
    except Exception as e:
        print(f"Error running config_iscsi_boot.py: {e}")
        return False

def generate_openshift_values(args, target_info):
    """Generate OpenShift values YAML file for use with generate_openshift_iso.py"""
    print(f"Generating OpenShift values for server {args.hostname} ({args.server_id})...")
    
    # Define the output directory and filename
    output_dir = Path(args.output_dir) if args.output_dir else CONFIG_DIR / "deployments" / f"r630-{args.server_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate a timestamp for the filename
    timestamp = time.strftime("%Y%m%d%H%M%S")
    output_file = output_dir / f"r630-{args.server_id}-{args.hostname}-{timestamp}.yaml"
    
    # Create the OpenShift values
    values = {
        "apiVersion": "v1",
        "baseDomain": args.base_domain,
        "metadata": {
            "name": args.hostname
        },
        "compute": [
            {
                "architecture": "amd64",
                "hyperthreading": "Enabled",
                "name": "worker",
                "replicas": 0
            }
        ],
        "controlPlane": {
            "architecture": "amd64",
            "hyperthreading": "Enabled",
            "name": "master",
            "replicas": 1
        },
        "networking": {
            "networkType": "OVNKubernetes",
            "clusterNetwork": [
                {
                    "cidr": "10.128.0.0/14",
                    "hostPrefix": 23
                }
            ],
            "serviceNetwork": [
                "172.30.0.0/16"
            ],
            "machineNetwork": [
                {
                    "cidr": f"{'.'.join(args.node_ip.split('.')[:3])}.0/24"
                }
            ]
        },
        "platform": {
            "none": {}
        },
        "bootstrapInPlace": {
            "installationDisk": target_info["device_path"]
        },
        "sno": {
            "hostname": args.hostname,
            "nodeIP": args.node_ip,
            "macAddress": args.mac_address,
            "interface": "eno2",  # Default to eno2 as per environment
            "prefixLength": 24,
            "gateway": f"{'.'.join(args.node_ip.split('.')[:3])}.254",
            "dnsServers": [
                f"{'.'.join(args.node_ip.split('.')[:3])}.254"
            ],
            "useDhcp": False
        }
    }
    
    # Write the values to the file
    with open(output_file, "w") as f:
        yaml.dump(values, f, default_flow_style=False)
    
    print(f"Generated OpenShift values at {output_file}")
    return output_file

def generate_openshift_iso(args, values_file):
    """Generate OpenShift ISO using generate_openshift_iso.py"""
    print(f"Generating OpenShift ISO for server {args.hostname} ({args.server_id})...")
    
    # Define the output directory
    output_dir = Path(args.output_dir) if args.output_dir else Path(f"./test_run_{args.hostname}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build the command to run generate_openshift_iso.py
    cmd = [
        sys.executable,
        str(OPENSHIFT_ISO_SCRIPT),
        "--values-file", str(values_file),
        "--rendezvous-ip", args.node_ip,
        "--output-dir", str(output_dir),
        "--skip-upload",  # Skip uploading to TrueNAS for now
        "--version", args.openshift_version
    ]
    
    # Print the command for reference
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error generating OpenShift ISO: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return False
        
        print(result.stdout)
        print(f"Successfully generated OpenShift ISO at {output_dir}/agent.x86_64.iso")
        
        # Create a symbolic link with a meaningful name
        iso_path = output_dir / "agent.x86_64.iso"
        link_path = output_dir / f"{args.hostname}-{args.openshift_version}.iso"
        if iso_path.exists() and not link_path.exists():
            os.symlink(iso_path, link_path)
            print(f"Created symbolic link {link_path}")
        
        return True
    except Exception as e:
        print(f"Error running generate_openshift_iso.py: {e}")
        return False

def main():
    args = parse_arguments()
    
    print("==== Integrating iSCSI Boot with OpenShift Installation ====")
    print(f"Server: {args.hostname} (ID: {args.server_id})")
    print(f"IP: {args.node_ip}, MAC: {args.mac_address}")
    print(f"OpenShift Version: {args.openshift_version}")
    print(f"Base Domain: {args.base_domain}")
    print("=" * 60)
    
    # Step 1: Create the iSCSI target on TrueNAS
    if not args.skip_target_creation:
        target_info = create_iscsi_target(args)
        print("=" * 60)
    else:
        # If skipping target creation, load from existing mapping
        mapping = load_or_create_device_mapping()
        # Look for target by hostname or server ID
        target_info = None
        for iqn, info in mapping.get("targets", {}).items():
            if info.get("hostname") == args.hostname or info.get("server_id") == args.server_id:
                target_info = {
                    "target_name": iqn,
                    "device_path": info.get("device_path", "/dev/sda"),
                    "iqn": iqn,
                    "ip": args.truenas_ip,
                    "port": 3260,
                    "lun": 0
                }
                break
        
        if not target_info:
            device_path = args.device_path if args.device_path else "/dev/sda"
            version_format = args.openshift_version.replace(".", "_")
            # Use a generic target name if one doesn't exist
            target_name = f"iqn.2005-10.org.freenas.ctl:iscsi.r630-{args.server_id}.openshift{version_format}"
            target_info = {
                "target_name": target_name,
                "device_path": device_path,
                "iqn": target_name,
                "ip": args.truenas_ip,
                "port": 3260,
                "lun": 0
            }
    
    # Step 2: Configure iSCSI boot on the server
    if not args.skip_iscsi_config:
        if not configure_iscsi_boot(args, target_info):
            print("Failed to configure iSCSI boot. Continuing with other steps...")
        print("=" * 60)
    
    # Step 3: Generate OpenShift values
    values_file = generate_openshift_values(args, target_info)
    print("=" * 60)
    
    # Step 4: Generate OpenShift ISO
    if not args.skip_iso_generation:
        if not generate_openshift_iso(args, values_file):
            print("Failed to generate OpenShift ISO.")
            return 1
        print("=" * 60)
    
    print("\nIntegration process complete!")
    print(f"iSCSI Target: {target_info['iqn']} @ {args.truenas_ip}:3260")
    print(f"Expected Device Path: {target_info['device_path']}")
    print(f"OpenShift Values: {values_file}")
    if not args.skip_iso_generation:
        output_dir = Path(args.output_dir) if args.output_dir else Path(f"./test_run_{args.hostname}")
        print(f"OpenShift ISO: {output_dir}/agent.x86_64.iso")
    
    print("\nNext Steps:")
    print("1. Boot the server from the generated ISO")
    print("2. Monitor the installation progress")
    print("3. Verify that the iSCSI device is detected and used correctly")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
