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

def create_iscsi_resources_via_ssh(args, zvol_name, target_name, extent_name, dry_run=False):
    """Create iSCSI target, extent and association using SSH commands"""
    ssh_cmd = ["ssh"]
    
    if hasattr(args, 'ssh_key') and args.ssh_key:
        ssh_cmd.extend(["-i", args.ssh_key])
    
    ssh_cmd.extend([f"root@{args.truenas_ip}"])
    
    # Create a remote shell script that will create the resources
    # We'll use direct commands rather than trying to construct a complex script via Python
    
    # First check for existing target
    target_check_cmd = ssh_cmd + [f"curl -s -k -X GET 'https://localhost/api/v2.0/iscsi/target?name={target_name}' | jq 'length'"]
    extent_check_cmd = ssh_cmd + [f"curl -s -k -X GET 'https://localhost/api/v2.0/iscsi/extent?name={extent_name}' | jq 'length'"]
    
    if dry_run:
        print("\nDRY RUN: Would execute these SSH commands:")
        print(f"Target check: {' '.join(target_check_cmd)}")
        print(f"Extent check: {' '.join(extent_check_cmd)}")
        print("Then would create target, extent, association as needed")
        return (0, 0)  # Return dummy values for dry run
    
    try:
        import subprocess
        import json
        import tempfile
        
        # Check if target exists
        print("Checking if target exists...")
        target_result = subprocess.run(target_check_cmd, check=True, capture_output=True, text=True)
        target_exists = target_result.stdout.strip() != "0"
        
        # Check if extent exists
        print("Checking if extent exists...")
        extent_result = subprocess.run(extent_check_cmd, check=True, capture_output=True, text=True)
        extent_exists = extent_result.stdout.strip() != "0"
        
        # Create target if it doesn't exist
        if not target_exists:
            print(f"Creating target {target_name}...")
            target_data = {
                "name": target_name,
                "alias": f"OpenShift {args.hostname}",
                "groups": [
                    {
                        "portal": 1,
                        "initiator": 1,
                        "auth": None
                    }
                ]
            }
            
            # Write the target data to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(target_data, f)
                target_file = f.name
            
            # SCP the file to the TrueNAS server
            scp_cmd = ["scp"]
            if hasattr(args, 'ssh_key') and args.ssh_key:
                scp_cmd.extend(["-i", args.ssh_key])
            scp_cmd.extend([target_file, f"root@{args.truenas_ip}:/tmp/target.json"])
            subprocess.run(scp_cmd, check=True)
            
            # Create the target
            create_target_cmd = ssh_cmd + ["curl -s -k -X POST -H 'Content-Type: application/json' -d @/tmp/target.json 'https://localhost/api/v2.0/iscsi/target' | jq '.id'"]
            target_id_result = subprocess.run(create_target_cmd, check=True, capture_output=True, text=True)
            target_id = target_id_result.stdout.strip()
        else:
            # Get the target ID
            get_target_id_cmd = ssh_cmd + [f"curl -s -k -X GET 'https://localhost/api/v2.0/iscsi/target?name={target_name}' | jq '.[0].id'"]
            target_id_result = subprocess.run(get_target_id_cmd, check=True, capture_output=True, text=True)
            target_id = target_id_result.stdout.strip()
            print(f"Target {target_name} already exists with ID {target_id}")
        
        # Create extent if it doesn't exist
        if not extent_exists:
            print(f"Creating extent {extent_name}...")
            extent_data = {
                "name": extent_name,
                "type": "DISK",
                "disk": f"zvol/{zvol_name}",
                "blocksize": 512,
                "pblocksize": False,
                "comment": f"OpenShift {args.hostname} boot image",
                "insecure_tpc": True,
                "xen": False,
                "rpm": "SSD",
                "ro": False
            }
            
            # Write the extent data to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(extent_data, f)
                extent_file = f.name
            
            # SCP the file to the TrueNAS server
            scp_cmd = ["scp"]
            if hasattr(args, 'ssh_key') and args.ssh_key:
                scp_cmd.extend(["-i", args.ssh_key])
            scp_cmd.extend([extent_file, f"root@{args.truenas_ip}:/tmp/extent.json"])
            subprocess.run(scp_cmd, check=True)
            
            # Create the extent
            create_extent_cmd = ssh_cmd + ["curl -s -k -X POST -H 'Content-Type: application/json' -d @/tmp/extent.json 'https://localhost/api/v2.0/iscsi/extent' | jq '.id'"]
            extent_id_result = subprocess.run(create_extent_cmd, check=True, capture_output=True, text=True)
            extent_id = extent_id_result.stdout.strip()
        else:
            # Get the extent ID
            get_extent_id_cmd = ssh_cmd + [f"curl -s -k -X GET 'https://localhost/api/v2.0/iscsi/extent?name={extent_name}' | jq '.[0].id'"]
            extent_id_result = subprocess.run(get_extent_id_cmd, check=True, capture_output=True, text=True)
            extent_id = extent_id_result.stdout.strip()
            print(f"Extent {extent_name} already exists with ID {extent_id}")
        
        # Check if association exists
        check_assoc_cmd = ssh_cmd + [f"curl -s -k -X GET 'https://localhost/api/v2.0/iscsi/targetextent?target={target_id}&extent={extent_id}' | jq 'length'"]
        assoc_result = subprocess.run(check_assoc_cmd, check=True, capture_output=True, text=True)
        assoc_exists = assoc_result.stdout.strip() != "0"
        
        if not assoc_exists:
            print("Creating target-extent association...")
            assoc_data = {
                "target": int(target_id.strip('"')),
                "extent": int(extent_id.strip('"')),
                "lunid": 0
            }
            
            # Write the association data to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(assoc_data, f)
                assoc_file = f.name
            
            # SCP the file to the TrueNAS server
            scp_cmd = ["scp"]
            if hasattr(args, 'ssh_key') and args.ssh_key:
                scp_cmd.extend(["-i", args.ssh_key])
            scp_cmd.extend([assoc_file, f"root@{args.truenas_ip}:/tmp/assoc.json"])
            subprocess.run(scp_cmd, check=True)
            
            # Create the association
            create_assoc_cmd = ssh_cmd + ["curl -s -k -X POST -H 'Content-Type: application/json' -d @/tmp/assoc.json 'https://localhost/api/v2.0/iscsi/targetextent'"]
            subprocess.run(create_assoc_cmd, check=True)
            print("Target-extent association created successfully")
        else:
            print("Target-extent association already exists")
        
        # Make sure iSCSI service is running
        print("Ensuring iSCSI service is running...")
        check_service_cmd = ssh_cmd + ["curl -s -k -X GET 'https://localhost/api/v2.0/service/id/iscsitarget' | jq '.state'"]
        service_result = subprocess.run(check_service_cmd, check=True, capture_output=True, text=True)
        service_running = service_result.stdout.strip() == '"RUNNING"'
        
        if not service_running:
            print("Starting iSCSI service...")
            start_service_cmd = ssh_cmd + ["curl -s -k -X POST -H 'Content-Type: application/json' -d '{\"service\": \"iscsitarget\"}' 'https://localhost/api/v2.0/service/start'"]
            subprocess.run(start_service_cmd, check=True)
            print("iSCSI service started")
        else:
            print("iSCSI service is already running")
        
        # Clean up temporary files on the server
        cleanup_cmd = ssh_cmd + ["rm -f /tmp/target.json /tmp/extent.json /tmp/assoc.json"]
        subprocess.run(cleanup_cmd, check=False)
        
        # Clean up local temporary files
        if 'target_file' in locals():
            import os
            os.unlink(target_file)
        if 'extent_file' in locals():
            os.unlink(extent_file)
        if 'assoc_file' in locals():
            os.unlink(assoc_file)
            
        print("Successfully created all iSCSI resources")
        return (target_id.strip('"'), extent_id.strip('"'))
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing SSH command: {e}")
        print(f"Command output: {e.stdout if hasattr(e, 'stdout') else 'no output'}")
        print(f"Command error: {e.stderr if hasattr(e, 'stderr') else 'no error output'}")
        return False
    except Exception as e:
        print(f"Error in SSH execution: {e}")
        return False

def create_zvol_via_ssh(args, zvol_name, size_str, dry_run=False):
    """Create a ZFS volume using SSH commands instead of API"""
    parent_path = zvol_name.rsplit('/', 1)[0]  # Get parent directory
    ssh_cmd = ["ssh"]
    
    if hasattr(args, 'ssh_key') and args.ssh_key:
        ssh_cmd.extend(["-i", args.ssh_key])
    
    ssh_cmd.extend([f"root@{args.truenas_ip}"])
    
    # Create parent directory first
    mkdir_cmd = ssh_cmd + [f"zfs create -p {parent_path}"]
    
    # Create zvol command
    zvol_cmd = ssh_cmd + [f"zfs create -V {size_str} -s {zvol_name}"]
    
    if dry_run:
        print("\nDRY RUN: Would create directory with SSH command:")
        print(" ".join(mkdir_cmd))
        print("\nDRY RUN: Would create zvol with SSH command:")
        print(" ".join(zvol_cmd))
        return True
    
    try:
        # First create parent directory
        print(f"Creating parent directory {parent_path} via SSH...")
        import subprocess
        try:
            result = subprocess.run(mkdir_cmd, check=False, capture_output=True, text=True)
            if result.returncode != 0 and "dataset already exists" not in result.stderr:
                print(f"Warning creating directory: {result.stderr}")
            else:
                print(f"Successfully created or found parent directory")
        except Exception as e:
            print(f"Warning during directory creation: {e}")
        
        # Check if zvol already exists
        check_cmd = ssh_cmd + [f"zfs list -t volume | grep {zvol_name}"]
        check_result = subprocess.run(check_cmd, check=False, capture_output=True, text=True)
        
        if check_result.returncode == 0:
            print(f"ZVOL {zvol_name} already exists - using existing zvol")
            return True
        
        # Create the zvol
        print(f"Creating zvol {zvol_name} via SSH...")
        result = subprocess.run(zvol_cmd, check=True, capture_output=True, text=True)
        print(f"Successfully created zvol {zvol_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating zvol via SSH: {e}")
        print(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error in SSH execution: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Create iSCSI target on TrueNAS Scale using REST API")
    parser.add_argument("--server-id", required=True, help="Server ID (e.g., 01, 02)")
    parser.add_argument("--hostname", required=True, help="Server hostname")
    parser.add_argument("--openshift-version", default="stable", help="OpenShift version (default: stable)")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--zvol-size", default="500G", help="Size of the zvol to create")
    parser.add_argument("--zfs-pool", default="test", help="ZFS pool name (default: test)")
    parser.add_argument("--api-key", required=True, help="TrueNAS API key")
    parser.add_argument("--ssh-key", help="Path to SSH key for TrueNAS (optional)")
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
    
    # Create zvol using SSH instead of API
    if not create_zvol_via_ssh(args, zvol_name, args.zvol_size, args.dry_run):
        print("\nFailed to create zvol via SSH")
        return 1
    
    # Create all iSCSI resources via SSH - the API is proving unreliable
    result = create_iscsi_resources_via_ssh(args, zvol_name, target_name, extent_name, args.dry_run)
    if not result or not isinstance(result, tuple):
        print("\nFailed to create iSCSI resources via SSH")
        return 1
    
    target_id, extent_id = result
    print("\nSuccess! iSCSI target created successfully")
    print(f"Target: {target_name} (ID: {target_id})")
    print(f"Extent: {extent_name} (ID: {extent_id})")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
