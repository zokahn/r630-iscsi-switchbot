#!/usr/bin/env python3
"""
create_iscsi_target_api.py - Create iSCSI target on TrueNAS Scale using the REST API
Uses API key authentication for secure access.
"""

import argparse
import json
import os
import sys
import time
import requests
import urllib3

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Create iSCSI target on TrueNAS Scale using REST API")
    parser.add_argument("--server-id", required=True, help="Server ID (e.g., 01, 02)")
    parser.add_argument("--hostname", required=True, help="Server hostname")
    parser.add_argument("--openshift-version", default="stable", help="OpenShift version (default: stable)")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--zvol-size", default="500G", help="Size of the zvol to create")
    parser.add_argument("--zfs-pool", default="test", help="ZFS pool name (default: test)")
    parser.add_argument("--api-key", required=True, help="TrueNAS API key")
    parser.add_argument("--dry-run", action="store_true", help="Show API calls without executing them")
    
    return parser.parse_args()

def get_api_session(args):
    """Set up API session with authentication"""
    session = requests.Session()
    
    # Set up API URL (TrueNAS SCALE uses port 444 for the API)
    api_url = f"https://{args.truenas_ip}:444/api/v2.0"
    
    # Add API key authentication
    session.headers.update({"Authorization": f"Bearer {args.api_key}"})
    
    # Disable SSL verification for self-signed certs
    session.verify = False
    
    return session, api_url

def format_size(size_str):
    """Convert a size string like 500G to bytes for the API"""
    if size_str.endswith('G'):
        return int(size_str[:-1]) * 1024 * 1024 * 1024
    elif size_str.endswith('M'):
        return int(size_str[:-1]) * 1024 * 1024
    elif size_str.endswith('T'):
        return int(size_str[:-1]) * 1024 * 1024 * 1024 * 1024
    elif size_str.endswith('K'):
        return int(size_str[:-1]) * 1024
    else:
        return int(size_str)

def create_directory_structure(session, api_url, path, dry_run=False):
    """Create a directory structure recursively"""
    # Split path into components
    parts = path.split('/')
    
    # Create each level of the directory structure
    current_path = parts[0]  # Start with the pool name
    
    for i in range(1, len(parts)):
        # Build the path up to this point
        current_path = f"{current_path}/{parts[i]}"
        
        # Skip if this is the whole path (we'll create the final item separately)
        if current_path == path:
            continue
            
        if not create_single_directory(session, api_url, current_path, dry_run):
            return False
            
    return True

def create_single_directory(session, api_url, dir_path, dry_run=False):
    """Create a single directory (dataset) if it doesn't exist"""
    url = f"{api_url}/pool/dataset"
    payload = {
        "name": dir_path,
        "type": "FILESYSTEM",
        "compression": "lz4",  # Match existing datasets
        "atime": "off",        # Match existing datasets
        "exec": "on"           # Match existing datasets
    }
    
    if dry_run:
        print(f"\nDRY RUN: Would create directory with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return True
    
    try:
        # First check if directory already exists
        check_url = f"{api_url}/pool/dataset/id/{dir_path}"
        check_response = session.get(check_url)
        
        if check_response.status_code == 200:
            print(f"Directory {dir_path} already exists - using existing directory")
            return True
            
        # Create the directory if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        print(f"Successfully created directory {dir_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error creating directory {dir_path}: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
            try:
                print(f"Response JSON: {json.dumps(e.response.json(), indent=2)}")
            except:
                print("Could not parse response as JSON")
        return False

def create_zvol(session, api_url, zvol_name, size_str, dry_run=False):
    """Create a ZFS volume using TrueNAS API"""
    # Format the size from human-readable to bytes
    size_bytes = format_size(size_str)
    
    # First ensure parent directory exists
    parent_path = zvol_name.rsplit('/', 1)[0]
    if not create_directory_structure(session, api_url, parent_path, dry_run):
        print(f"Failed to create parent directory structure {parent_path}")
        return False
    
    url = f"{api_url}/pool/dataset"
    payload = {
        "name": zvol_name,
        "type": "VOLUME",
        "volsize": size_bytes,
        "sparse": True
    }
    
    if dry_run:
        print(f"\nDRY RUN: Would create zvol with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return True
    
    try:
        # First check if zvol already exists
        check_url = f"{api_url}/pool/dataset/id/{zvol_name}"
        check_response = session.get(check_url)
        
        if check_response.status_code == 200:
            print(f"ZVOL {zvol_name} already exists - using existing zvol")
            return True
            
        # Create the zvol if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        print(f"Successfully created zvol {zvol_name}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error creating zvol: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return False

def create_iscsi_target(session, api_url, target_name, hostname, dry_run=False):
    """Create an iSCSI target using TrueNAS API"""
    url = f"{api_url}/iscsi/target"
    payload = {
        "name": target_name,
        "alias": f"OpenShift {hostname}",
        "mode": "ISCSI",
        "groups": [{"portal": 1, "initiator": 1, "auth": None}]
    }
    
    if dry_run:
        print(f"\nDRY RUN: Would create target with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return 1  # Return a dummy ID for dry run
        
    try:
        # First check if target already exists
        query_url = f"{api_url}/iscsi/target?name={target_name}"
        query_response = session.get(query_url)
        
        if query_response.status_code == 200 and query_response.json():
            targets = query_response.json()
            if targets:
                target_id = targets[0]['id']
                print(f"Target {target_name} already exists with ID {target_id} - reusing")
                return target_id
        
        # Create the target if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        target_id = response.json()['id']
        print(f"Successfully created target {target_name} with ID {target_id}")
        return target_id
    except requests.exceptions.RequestException as e:
        print(f"Error creating iSCSI target: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return None

def create_iscsi_extent(session, api_url, extent_name, zvol_name, hostname, dry_run=False):
    """Create an iSCSI extent using TrueNAS API"""
    url = f"{api_url}/iscsi/extent"
    payload = {
        "name": extent_name,
        "type": "DISK",
        "disk": f"zvol/{zvol_name}",
        "blocksize": 512,
        "pblocksize": False,
        "comment": f"OpenShift {hostname} boot image",
        "insecure_tpc": True,
        "xen": False,
        "rpm": "SSD",
        "ro": False
    }
    
    if dry_run:
        print(f"\nDRY RUN: Would create extent with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return 1  # Return a dummy ID for dry run
    
    try:
        # First check if extent already exists
        query_url = f"{api_url}/iscsi/extent?name={extent_name}"
        query_response = session.get(query_url)
        
        if query_response.status_code == 200 and query_response.json():
            extents = query_response.json()
            if extents:
                extent_id = extents[0]['id']
                print(f"Extent {extent_name} already exists with ID {extent_id} - reusing")
                return extent_id
        
        # Create the extent if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        extent_id = response.json()['id']
        print(f"Successfully created extent {extent_name} with ID {extent_id}")
        return extent_id
    except requests.exceptions.RequestException as e:
        print(f"Error creating iSCSI extent: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return None

def associate_target_extent(session, api_url, target_id, extent_id, dry_run=False):
    """Associate an iSCSI target with an extent using TrueNAS API"""
    url = f"{api_url}/iscsi/targetextent"
    payload = {
        "target": target_id,
        "extent": extent_id,
        "lunid": 0
    }
    
    if dry_run:
        print(f"\nDRY RUN: Would associate target-extent with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return True
    
    try:
        # First check if association already exists
        query_url = f"{api_url}/iscsi/targetextent?target={target_id}&extent={extent_id}"
        query_response = session.get(query_url)
        
        if query_response.status_code == 200 and query_response.json():
            associations = query_response.json()
            if associations:
                print(f"Target-extent association already exists - skipping")
                return True
        
        # Create the association if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        print(f"Successfully associated target {target_id} with extent {extent_id}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error creating target-extent association: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return False

def main():
    args = parse_arguments()
    
    # Format the zvol name and target name
    server_id = args.server_id
    version_format = args.openshift_version.replace(".", "_")
    zvol_name = f"{args.zfs_pool}/openshift_installations/r630_{server_id}_{version_format}"
    target_name = f"iqn.2005-10.org.freenas.ctl:iscsi.r630-{server_id}.openshift{version_format}"
    extent_name = f"openshift_r630_{server_id}_{version_format}_extent"
    
    print(f"=== Creating iSCSI Target for {args.hostname} (Server ID: {server_id}) ===")
    print(f"OpenShift Version: {args.openshift_version}")
    print(f"Zvol: {zvol_name} (Size: {args.zvol_size})")
    print(f"Target: {target_name}")
    print(f"Extent: {extent_name}")
    print(f"Using TrueNAS API on {args.truenas_ip}")
    print("=" * 60)
    
    # Set up API session
    session, api_url = get_api_session(args)
    
    # Create zvol
    if not create_zvol(session, api_url, zvol_name, args.zvol_size, args.dry_run):
        print("\nFailed to create zvol")
        return 1
    
    # Create iSCSI target
    target_id = create_iscsi_target(session, api_url, target_name, args.hostname, args.dry_run)
    if not target_id:
        print("\nFailed to create iSCSI target")
        return 1
    
    # Create iSCSI extent
    extent_id = create_iscsi_extent(session, api_url, extent_name, zvol_name, args.hostname, args.dry_run)
    if not extent_id:
        print("\nFailed to create iSCSI extent")
        return 1
    
    # Associate target with extent
    if not associate_target_extent(session, api_url, target_id, extent_id, args.dry_run):
        print("\nFailed to associate target with extent")
        return 1
    
    print("\nSuccess! iSCSI target created successfully")
    print(f"Target: {target_name} (ID: {target_id})")
    print(f"Extent: {extent_name} (ID: {extent_id})")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
