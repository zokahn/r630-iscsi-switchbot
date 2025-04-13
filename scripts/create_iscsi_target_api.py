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
        "groups": [{"portal": 3, "initiator": 3, "auth": None}]  # Portal ID 3 and Initiator ID 3 based on system config
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

def ensure_parent_directory_exists(session, api_url, parent_path, dry_run=False):
    """Make sure the parent directory structure exists"""
    # Split the parent path into components
    parts = parent_path.split('/')
    
    # Start with the pool name
    current_path = parts[0]
    
    # Check and create each directory level
    for i in range(1, len(parts)):
        current_path = f"{current_path}/{parts[i]}"
        
        # Check if this level exists
        check_url = f"{api_url}/pool/dataset/id/{current_path}"
        check_response = session.get(check_url)
        
        if check_response.status_code == 200:
            print(f"Dataset {current_path} already exists")
            continue
        
        # If it doesn't exist, create it
        print(f"Creating dataset {current_path}...")
        
        payload = {
            "name": current_path,
            "type": "FILESYSTEM",
            "compression": "lz4"
        }
        
        if dry_run:
            print(f"DRY RUN: Would create dataset {current_path}")
            continue
        
        try:
            url = f"{api_url}/pool/dataset"
            response = session.post(url, json=payload)
            response.raise_for_status()
            print(f"Successfully created dataset {current_path}")
        except requests.exceptions.HTTPError as e:
            print(f"Error creating dataset {current_path}: {e}")
            # If we get a 422 error, it might be because the dataset already exists
            if e.response.status_code == 422:
                print("Dataset might already exist, continuing anyway")
            else:
                raise
    
    return True

def create_zvol_api(session, api_url, zvol_name, size_str, dry_run=False):
    """Create a ZFS volume using direct API calls"""
    # Format the size from human-readable to bytes
    size_bytes = format_size(size_str)
    
    # Ensure parent directory exists
    parent_path = zvol_name.rsplit('/', 1)[0]
    try:
        ensure_parent_directory_exists(session, api_url, parent_path, dry_run)
    except Exception as e:
        print(f"Error ensuring parent directory exists: {e}")
        # Continue anyway - the zvol creation might still succeed
    
    # Check if zvol already exists
    check_url = f"{api_url}/pool/dataset/id/{zvol_name}"
    check_response = session.get(check_url)
    
    if check_response.status_code == 200:
        print(f"ZVOL {zvol_name} already exists - using existing zvol")
        return True
    
    print(f"Creating zvol {zvol_name}...")
    url = f"{api_url}/pool/dataset"
    payload = {
        "name": zvol_name,
        "type": "VOLUME",
        "volsize": size_bytes,
        "sparse": True
    }
    
    if dry_run:
        print(f"DRY RUN: Would create zvol {zvol_name}")
        return True
    
    try:
        response = session.post(url, json=payload)
        response.raise_for_status()
        print(f"Successfully created zvol {zvol_name}")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"Error creating zvol: {e}")
        # Check if the error is a 422 - zvol might already exist
        if hasattr(e, 'response') and e.response.status_code == 422:
            print("ZVOL might already exist, continuing anyway")
            return True
        return False
    except Exception as e:
        print(f"Unexpected error creating zvol: {e}")
        return False

def create_iscsi_resources_api(session, api_url, zvol_name, target_name, extent_name, hostname, dry_run=False):
    """Create iSCSI target, extent and association using direct API calls"""
    # Get or create target
    target_id = create_iscsi_target(session, api_url, target_name, hostname, dry_run)
    if not target_id:
        print("Failed to create iSCSI target")
        return False
        
    # Get or create extent
    extent_id = create_iscsi_extent(session, api_url, extent_name, zvol_name, hostname, dry_run)
    if not extent_id:
        print("Failed to create iSCSI extent")
        return False
        
    # Associate target with extent
    if not associate_target_extent(session, api_url, target_id, extent_id, dry_run):
        print("Failed to associate target with extent")
        return False
    
    # Make sure iSCSI service is running
    print("Ensuring iSCSI service is running...")
    service_url = f"{api_url}/service/id/iscsitarget"
    service_response = session.get(service_url)
    
    if service_response.status_code == 200:
        service_data = service_response.json()
        service_running = service_data.get('state') == 'RUNNING'
        
        if not service_running:
            print("Starting iSCSI service...")
            start_url = f"{api_url}/service/start"
            start_payload = {"service": "iscsitarget"}
            
            if dry_run:
                print("DRY RUN: Would start iSCSI service")
            else:
                try:
                    start_response = session.post(start_url, json=start_payload)
                    start_response.raise_for_status()
                    print("Successfully started iSCSI service")
                except Exception as e:
                    print(f"Error starting iSCSI service: {e}")
                    # Continue anyway - the service might already be running
        else:
            print("iSCSI service is already running")
    else:
        print(f"Warning: Could not check iSCSI service status: {service_response.status_code}")
    
    return (target_id, extent_id)

def main():
    parser = argparse.ArgumentParser(description="Create iSCSI target on TrueNAS Scale using REST API")
    parser.add_argument("--server-id", required=True, help="Server ID (e.g., 01, 02)")
    parser.add_argument("--hostname", required=True, help="Server hostname")
    parser.add_argument("--openshift-version", default="stable", help="OpenShift version (default: stable)")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--zvol-size", default="500G", help="Size of the zvol to create")
    parser.add_argument("--zfs-pool", default="test", help="ZFS pool name (default: test)")
    parser.add_argument("--api-key", required=True, help="TrueNAS API key")
    parser.add_argument("--ssh-key", help="Path to SSH key for TrueNAS (optional, not used)")
    parser.add_argument("--dry-run", action="store_true", help="Show API calls without executing them")
    
    args = parser.parse_args()
    
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
    
    # Create zvol using direct API calls
    if not create_zvol_api(session, api_url, zvol_name, args.zvol_size, args.dry_run):
        print("\nFailed to create zvol via API")
        return 1
    
    # Create all iSCSI resources using direct API calls
    result = create_iscsi_resources_api(session, api_url, zvol_name, target_name, extent_name, args.hostname, args.dry_run)
    if not result or not isinstance(result, tuple):
        print("\nFailed to create iSCSI resources via API")
        return 1
    
    target_id, extent_id = result
    print("\nSuccess! iSCSI target created successfully")
    print(f"Target: {target_name} (ID: {target_id})")
    print(f"Extent: {extent_name} (ID: {extent_id})")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
