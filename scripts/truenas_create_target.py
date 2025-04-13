#!/usr/bin/env python3
# truenas_create_target.py - Create an iSCSI target on TrueNAS Scale
# Designed to be used either directly or by integrate_iscsi_openshift.py

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import requests
import urllib3

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
CONFIG_DIR = Path.home() / ".config" / "truenas"
AUTH_FILE = CONFIG_DIR / "auth.json"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Create an iSCSI target on TrueNAS Scale")
    parser.add_argument("--server-id", required=True, help="Server ID (e.g., 01, 02)")
    parser.add_argument("--hostname", required=True, help="Server hostname")
    parser.add_argument("--openshift-version", default="stable", help="OpenShift version")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--zvol-size", default="500G", help="Size of the zvol to create")
    parser.add_argument("--api-key", help="TrueNAS API key (overrides auth file)")
    parser.add_argument("--username", help="TrueNAS username (overrides auth file)")
    parser.add_argument("--password", help="TrueNAS password (overrides auth file)")
    parser.add_argument("--ssh-key", help="Path to SSH key for TrueNAS")
    parser.add_argument("--dry-run", action="store_true", help="Generate commands but don't execute them")
    parser.add_argument("--ssh-method", action="store_true", help="Use SSH instead of API")
    
    return parser.parse_args()

def load_auth_file():
    """Load TrueNAS authentication from config file"""
    if not AUTH_FILE.exists():
        print(f"Authentication file not found at {AUTH_FILE}")
        return None
    
    try:
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading authentication file: {e}")
        return None

def get_api_session(args, auth_config):
    """Set up API session with authentication"""
    session = requests.Session()
    
    # Determine TrueNAS IP
    if args.truenas_ip:
        host = args.truenas_ip
    elif auth_config and "host" in auth_config:
        host = auth_config["host"]
    else:
        host = "192.168.2.245"  # Default
    
    # Set up API URL
    api_url = f"https://{host}:444/api/v2.0"
    
    # Add authentication
    if args.api_key:
        session.headers.update({"Authorization": f"Bearer {args.api_key}"})
    elif auth_config and "api_key" in auth_config:
        session.headers.update({"Authorization": f"Bearer {auth_config['api_key']}"})
    elif args.username and args.password:
        session.auth = (args.username, args.password)
    elif auth_config and "username" in auth_config and "password" in auth_config:
        session.auth = (auth_config["username"], auth_config["password"])
    else:
        print("No authentication credentials provided.")
        return None, None
    
    # Disable SSL verification for self-signed certs
    session.verify = False
    
    return session, api_url

def create_zvol_api(session, api_url, zvol_name, size):
    """Create a ZFS zvol using TrueNAS API"""
    url = f"{api_url}/pool/dataset"
    payload = {
        "name": zvol_name,
        "type": "VOLUME",
        "volsize": size,
        "sparse": True
    }
    
    try:
        response = session.post(url, json=payload)
        response.raise_for_status()
        print(f"Successfully created zvol {zvol_name}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error creating zvol: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return False

def create_iscsi_target_api(session, api_url, target_name, zvol_name, extent_name):
    """Create an iSCSI target and extent using TrueNAS API"""
    # Create the target
    target_url = f"{api_url}/iscsi/target"
    target_payload = {
        "name": target_name,
        "alias": f"OpenShift {target_name}",
        "mode": "ISCSI",
        "groups": [{"portal": 1, "initiator": 1, "auth": None}]
    }
    
    try:
        target_response = session.post(target_url, json=target_payload)
        target_response.raise_for_status()
        target_id = target_response.json().get("id")
        print(f"Successfully created target {target_name} with ID {target_id}")
        
        # Create the extent
        extent_url = f"{api_url}/iscsi/extent"
        extent_payload = {
            "name": extent_name,
            "type": "DISK",
            "disk": f"zvol/{zvol_name}",
            "blocksize": 512,
            "pblocksize": False,
            "comment": f"OpenShift {target_name} boot image",
            "insecure_tpc": True,
            "xen": False,
            "rpm": "SSD",
            "ro": False
        }
        
        extent_response = session.post(extent_url, json=extent_payload)
        extent_response.raise_for_status()
        extent_id = extent_response.json().get("id")
        print(f"Successfully created extent {extent_name} with ID {extent_id}")
        
        # Associate the extent with the target
        targetextent_url = f"{api_url}/iscsi/targetextent"
        targetextent_payload = {
            "target": target_id,
            "extent": extent_id,
            "lunid": 0
        }
        
        targetextent_response = session.post(targetextent_url, json=targetextent_payload)
        targetextent_response.raise_for_status()
        print(f"Successfully associated extent with target")
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error creating iSCSI target: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return False

def generate_ssh_commands(args, zvol_name, target_name, extent_name):
    """Generate SSH commands for creating the zvol and iSCSI target"""
    # Use temporary files for JSON to avoid escaping and quoting issues in the shell
    commands = [
        "# Create the zvol",
        f"zfs create -V {args.zvol_size} -s {zvol_name}",
        "",
        "# Create the target and extent with cleaner JSON",
        "# Use python to generate properly formatted JSON files",
        "cat > /tmp/create_json.py << 'EOF'",
        "import json",
        "import sys",
        "",
        "target_name = sys.argv[1]",
        "hostname = sys.argv[2]",
        "extent_name = sys.argv[3]",
        "zvol_name = sys.argv[4]",
        "",
        "# Target JSON",
        "target_data = {",
        "    \"name\": target_name,",
        "    \"alias\": f\"OpenShift {hostname}\",",
        "    \"mode\": \"ISCSI\",",
        "    \"groups\": [{\"portal\": 1, \"initiator\": 1, \"auth\": None}]",
        "}",
        "",
        "# Convert None to null for JSON",
        "target_json = json.dumps(target_data).replace('null', 'null')",
        "with open('/tmp/target.json', 'w') as f:",
        "    f.write(target_json)",
        "",
        "# Extent JSON",
        "extent_data = {",
        "    \"name\": extent_name,",
        "    \"type\": \"DISK\",",
        "    \"disk\": f\"zvol/{zvol_name}\",",
        "    \"blocksize\": 512,",
        "    \"pblocksize\": False,",
        "    \"comment\": f\"OpenShift {hostname} boot image\",",
        "    \"insecure_tpc\": True,",
        "    \"xen\": False,",
        "    \"rpm\": \"SSD\",",
        "    \"ro\": False",
        "}",
        "",
        "# Convert booleans to proper JSON format",
        "extent_json = json.dumps(extent_data).replace('true', 'true').replace('false', 'false')",
        "with open('/tmp/extent.json', 'w') as f:",
        "    f.write(extent_json)",
        "EOF",
        "",
        f"python3 /tmp/create_json.py '{target_name}' '{args.hostname}' '{extent_name}' '{zvol_name}'",
        "",
        "# Execute the commands",
        "TARGET_ID=$(cat /tmp/target.json | midclt call iscsi.target.create - | jq '.id')",
        "EXTENT_ID=$(cat /tmp/extent.json | midclt call iscsi.extent.create - | jq '.id')",
        "",
        "cat > /tmp/targetextent.json << 'EOF'",
        "{",
        '  "target": '"$TARGET_ID"',',
        '  "extent": '"$EXTENT_ID"',',
        '  "lunid": 0',
        "}",
        "EOF",
        "",
        "midclt call iscsi.targetextent.create - < /tmp/targetextent.json",
        "",
        "# Clean up temporary files",
        "rm -f /tmp/target.json /tmp/extent.json /tmp/targetextent.json"
    ]
    
    return "\n".join(commands)

def execute_ssh_commands(args, auth_config, commands):
    """Execute commands on TrueNAS via SSH"""
    # Determine SSH key
    ssh_key = args.ssh_key
    if not ssh_key and os.path.exists(os.path.expanduser(f"~/.ssh/{args.truenas_ip}.id_rsa")):
        ssh_key = os.path.expanduser(f"~/.ssh/{args.truenas_ip}.id_rsa")
    
    # Create a temporary script file
    script_path = Path("truenas_commands.sh")
    with open(script_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("set -e\n\n")
        f.write(commands)
    
    # Make it executable
    os.chmod(script_path, 0o755)
    
    # Build the SSH command
    if ssh_key:
        ssh_cmd = f"ssh -i {ssh_key} root@{args.truenas_ip} 'bash -s' < {script_path}"
    else:
        ssh_cmd = f"ssh root@{args.truenas_ip} 'bash -s' < {script_path}"
    
    print(f"Executing: {ssh_cmd}")
    
    try:
        result = subprocess.run(ssh_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("Success! Output:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing SSH commands: {e}")
        print(f"STDERR: {e.stderr}")
        return False
    finally:
        # Clean up temp file
        if script_path.exists():
            script_path.unlink()

def main():
    args = parse_arguments()
    
    # Format the zvol name and target name
    server_id = args.server_id
    version_format = args.openshift_version.replace(".", "_")
    zvol_name = f"tank/openshift_installations/r630_{server_id}_{version_format}"
    target_name = f"iqn.2005-10.org.freenas.ctl:iscsi.r630-{server_id}.openshift{version_format}"
    extent_name = f"openshift_r630_{server_id}_{version_format}_extent"
    
    print(f"=== Creating iSCSI Target for {args.hostname} (Server ID: {server_id}) ===")
    print(f"OpenShift Version: {args.openshift_version}")
    print(f"Zvol: {zvol_name} (Size: {args.zvol_size})")
    print(f"Target: {target_name}")
    print(f"Extent: {extent_name}")
    print("=" * 60)
    
    # Load authentication information
    auth_config = load_auth_file()
    
    # Generate SSH commands
    ssh_commands = generate_ssh_commands(args, zvol_name, target_name, extent_name)
    
    if args.dry_run:
        print("\nDry run mode - commands that would be executed:")
        print("-" * 60)
        print(ssh_commands)
        print("-" * 60)
        print("No changes were made to TrueNAS.")
        return 0
    
    if args.ssh_method:
        # Execute via SSH
        print("\nExecuting commands via SSH:")
        if execute_ssh_commands(args, auth_config, ssh_commands):
            print("\nSuccess! iSCSI target created successfully.")
            return 0
        else:
            print("\nFailed to create iSCSI target via SSH.")
            return 1
    else:
        # Execute via API
        session, api_url = get_api_session(args, auth_config)
        if not session or not api_url:
            print("\nCould not set up API session. Try using --ssh-method instead.")
            return 1
        
        print("\nExecuting commands via API:")
        # Create zvol
        if not create_zvol_api(session, api_url, zvol_name, args.zvol_size):
            print("\nFailed to create zvol via API.")
            return 1
        
        # Create iSCSI target
        if not create_iscsi_target_api(session, api_url, target_name, zvol_name, extent_name):
            print("\nFailed to create iSCSI target via API.")
            return 1
        
        print("\nSuccess! iSCSI target created successfully.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
