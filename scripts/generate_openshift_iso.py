#!/usr/bin/env python3
# generate_openshift_iso.py - Generate OpenShift agent-based ISO and upload to TrueNAS

import argparse
import os
import subprocess
import sys
import tempfile
import shutil
import requests
import yaml
from pathlib import Path

# Import our secrets provider
try:
    from secrets_provider import process_references, get_secret, put_secret
except ImportError:
    # If running from a different directory, try to import using the script's directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from secrets_provider import process_references, get_secret, put_secret
    except ImportError:
        # Define placeholder functions to avoid errors if the module is missing
        def process_references(data):
            return data

        def get_secret(path, key=None):
            print(f"Warning: secrets_provider module not found, can't retrieve secret from {path}")
            return None

        def put_secret(path, content, key=None):
            print(f"Warning: secrets_provider module not found, can't store secret to {path}")
            return False

def download_openshift_installer(version, output_dir):
    """Download the OpenShift installer binary for a specific version"""
    # Format version for URL (e.g., 4.18.0 -> 4.18.0, 4.18 -> latest 4.18.x)
    if len(version.split('.')) < 3:
        # If just major.minor (e.g., 4.18), use format suited for latest in that stream
        version_for_url = f"{version}.x"
    else:
        # Full version specified
        version_for_url = version
    
    # Determine OS and architecture
    if sys.platform.startswith('linux'):
        os_type = 'linux'
    elif sys.platform == 'darwin':
        os_type = 'mac'
    else:
        print(f"Unsupported operating system: {sys.platform}")
        return False
    
    # Use 'amd64' as the architecture since that's the most common
    arch = 'amd64'
    
    # Construct URL for the installer
    if version == "stable":
        # Use stable URL format
        url = f"https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable/openshift-install-{os_type}.tar.gz"
    else:
        # Try version-specific URL
        url = f"https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/{version_for_url}/openshift-install-{os_type}-{arch}.tar.gz"
    installer_tar = os.path.join(output_dir, "openshift-install.tar.gz")
    
    print(f"Downloading OpenShift installer version {version} from {url}")
    try:
        # Download the tarball
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(installer_tar, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extract the tarball
        subprocess.run(['tar', '-xzf', installer_tar, '-C', output_dir], check=True)
        
        # Make the installer executable
        installer_path = os.path.join(output_dir, "openshift-install")
        os.chmod(installer_path, 0o755)
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading OpenShift installer: {e}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error extracting OpenShift installer: {e}")
        return False

def create_install_config(output_dir, version, domain, pull_secret, ssh_key):
    """Create the install-config.yaml file"""
    install_config_path = os.path.join(output_dir, "install-config.yaml")
    
    content = f"""apiVersion: v1
baseDomain: {domain}
metadata:
  name: r630-cluster
compute:
- architecture: amd64
  hyperthreading: Enabled
  name: worker
  replicas: 1
controlPlane:
  architecture: amd64
  hyperthreading: Enabled
  name: master
  replicas: 3
networking:
  networkType: OVNKubernetes
  clusterNetwork:
  - cidr: 10.128.0.0/14
    hostPrefix: 23
  serviceNetwork:
  - 172.30.0.0/16
platform:
  none: {{}}
pullSecret: '{pull_secret}'
sshKey: '{ssh_key}'
"""
    
    with open(install_config_path, 'w') as f:
        f.write(content)
    
    print(f"Created install-config.yaml for OpenShift {version}")
    return True

def create_agent_config(output_dir, values=None, rendezvous_ip=None):
    """Create the agent-config.yaml file using values from config or command line"""
    agent_config_path = os.path.join(output_dir, "agent-config.yaml")
    
    # If values are provided, use them; otherwise use basic parameters
    if values:
        # Extract basic cluster info
        cluster_name = values.get('metadata', {}).get('name', 'r630-cluster')
        
        # Extract network configuration from SNO section if available
        sno_config = values.get('sno', {})
        node_ip = sno_config.get('nodeIP', rendezvous_ip)
        
        # Set network interface details - default to eno2 as per environment
        interface_name = sno_config.get('interface', 'eno2')
        mac_address = sno_config.get('macAddress', None)
        
        # Determine if using DHCP or static IP
        use_dhcp = sno_config.get('useDhcp', True)
        prefix_length = sno_config.get('prefixLength', 24)
        
        # Network infrastructure details
        dns_servers = sno_config.get('dnsServers', None)
        
        # SNO hostname
        hostname = sno_config.get('hostname', 'r630-control-1')
        
        # Storage configuration for bootstrap-in-place
        bootstrap_in_place = values.get('bootstrapInPlace', {})
        installation_disk = bootstrap_in_place.get('installationDisk', None)
        
        # Build network configuration based on values
        network_config = {
            "interfaces": [
                {
                    "name": interface_name,
                    "type": "ethernet",
                    "state": "up",
                    "ipv4": {
                        "enabled": True,
                        "dhcp": use_dhcp
                    }
                }
            ]
        }
        
        # Add MAC address if specified
        if mac_address:
            network_config["interfaces"][0]["mac-address"] = mac_address
        
        # If static IP (not DHCP), add IP configuration
        if not use_dhcp and node_ip:
            network_config["interfaces"][0]["ipv4"]["address"] = [
                {
                    "ip": node_ip,
                    "prefix-length": prefix_length
                }
            ]
        
        # Add DNS configuration if provided
        if dns_servers:
            network_config["dns-resolver"] = {
                "config": {
                    "server": dns_servers
                }
            }
        
        # Format network config as YAML with proper indentation
        network_config_yaml = yaml.dump(network_config, default_flow_style=False, indent=6)
        
        # Build the complete agent-config content
        content = f"""apiVersion: v1alpha1
kind: AgentConfig
metadata:
  name: {cluster_name}
rendezvousIP: {node_ip}
hosts:
  - hostname: {hostname}
    role: master"""

        # Add rootDeviceHints if installation disk is specified
        if installation_disk:
            content += f"""
    rootDeviceHints:
      deviceName: "{installation_disk}" """
        
        # Add network configuration
        content += f"""
    networkConfig: 
{network_config_yaml}"""

        # Add bootstrapInPlace configuration if installation disk is specified
        if installation_disk:
            content += f"""
bootstrapInPlace:
  installationDisk: "{installation_disk}" """
        
    else:
        # Basic config if no values provided (fallback for backward compatibility)
        if not rendezvous_ip:
            print("Error: No rendezvous IP provided and no values file specified")
            return False
            
        content = f"""apiVersion: v1alpha1
kind: AgentConfig
metadata:
  name: r630-cluster
rendezvousIP: {rendezvous_ip}
hosts:
  - hostname: r630-control-1
    role: master
    networkConfig:
      interfaces:
        - name: eno1
          type: ethernet
          state: up
          ipv4:
            enabled: true
            address:
              - ip: {rendezvous_ip}
                prefix-length: 24
            dhcp: false
"""
    
    with open(agent_config_path, 'w') as f:
        f.write(content)
    
    print(f"Created agent-config.yaml with rendezvous IP {rendezvous_ip or node_ip}")
    return True

def generate_iso(output_dir, version):
    """Generate the ISO using the openshift-install command"""
    installer_path = os.path.join(output_dir, "openshift-install")
    
    print(f"Generating agent-based ISO for OpenShift {version}...")
    try:
        # Run the openshift-install command
        subprocess.run([
            installer_path, 
            "agent", "create", "image", 
            "--dir", output_dir
        ], check=True)
        
        # Check if ISO was generated
        iso_path = os.path.join(output_dir, "agent.x86_64.iso")
        if os.path.exists(iso_path):
            print(f"Successfully generated ISO at {iso_path}")
            return iso_path
        else:
            print("ISO was not generated. Check logs for errors.")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error generating ISO: {e}")
        return None

def load_values_from_file(values_file):
    """Load OpenShift installation values from a YAML file"""
    try:
        with open(values_file, 'r') as f:
            values = yaml.safe_load(f)
        return values
    except Exception as e:
        print(f"Error loading values file: {e}")
        return None

def upload_to_truenas(iso_path, version, truenas_ip, username, password=None, private_key=None):
    """Upload the ISO to TrueNAS using SCP"""
    # Format version for path
    version_path = version.replace('x', '0')  # Handle cases like 4.18.x
    if len(version_path.split('.')) < 3:
        version_path = f"{version_path}.0"
    
    # Construct destination path
    remote_path = f"{username}@{truenas_ip}:/mnt/tank/openshift_isos/{version_path.split('.')[0]}.{version_path.split('.')[1]}/agent.x86_64.iso"
    
    print(f"Uploading ISO to TrueNAS at {remote_path}...")
    
    scp_command = ["scp"]
    
    # Add private key if provided
    if private_key:
        scp_command.extend(["-i", private_key])
    
    # Add the source and destination
    scp_command.extend([iso_path, remote_path])
    
    try:
        # Run the SCP command
        subprocess.run(scp_command, check=True)
        print("ISO uploaded successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error uploading ISO: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate OpenShift agent-based ISO and upload to TrueNAS")
    parser.add_argument("--version", default="4.18", help="OpenShift version (e.g., 4.18 or 4.18.0)")
    parser.add_argument("--domain", default="example.com", help="Base domain for the cluster")
    parser.add_argument("--rendezvous-ip", required=True, help="Rendezvous IP address (primary node)")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--truenas-user", default="root", help="TrueNAS SSH username")
    parser.add_argument("--private-key", help="Path to SSH private key for TrueNAS authentication")
    parser.add_argument("--pull-secret", help="Pull secret for OpenShift. If not provided, will prompt.")
    parser.add_argument("--ssh-key", help="SSH public key for OpenShift. If not provided, will use ~/.ssh/id_rsa.pub")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading to TrueNAS")
    parser.add_argument("--output-dir", help="Custom output directory (default: temporary directory)")
    parser.add_argument("--values-file", help="Path to YAML file with OpenShift installation values")
    
    args = parser.parse_args()
    
    # Use provided output directory or create a temporary one
    if args.output_dir:
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)
        should_cleanup = False
    else:
        output_dir = tempfile.mkdtemp()
        should_cleanup = True
    
    print(f"Using output directory: {output_dir}")
    
    try:
        # Check if values file is provided
        if args.values_file:
            print(f"Loading installation values from {args.values_file}")
            values = load_values_from_file(args.values_file)
            if not values:
                return 1
                
            # Extract values from the loaded file
            domain = values.get('baseDomain', args.domain)
            rendezvous_ip = values.get('sno', {}).get('nodeIP', args.rendezvous_ip)
            
            if not rendezvous_ip:
                print("Error: No rendezvous IP found in values file and none provided via command line")
                return 1
        else:
            # Use command line arguments
            domain = args.domain
            rendezvous_ip = args.rendezvous_ip
        
        # Get SSH key if not provided
        ssh_key_path = args.ssh_key
        if ssh_key_path:
            # Read the SSH key file
            if os.path.exists(ssh_key_path):
                with open(ssh_key_path, 'r') as f:
                    ssh_key = f.read().strip()
            else:
                print(f"Error: SSH key file not found at {ssh_key_path}")
                return 1
        else:
            # Try default SSH key path
            default_key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
            if os.path.exists(default_key_path):
                with open(default_key_path, 'r') as f:
                    ssh_key = f.read().strip()
            else:
                print("No SSH key provided and ~/.ssh/id_rsa.pub not found.")
                print("Please provide an SSH key with --ssh-key or generate one with ssh-keygen.")
                return 1
        
        # Get pull secret if not provided
        pull_secret_path = args.pull_secret
        if pull_secret_path:
            # Read the pull secret file
            if os.path.exists(pull_secret_path):
                with open(pull_secret_path, 'r') as f:
                    pull_secret = f.read().strip()
            else:
                print(f"Error: Pull secret file not found at {pull_secret_path}")
                return 1
        else:
            # Check for pull secret in ~/.openshift/pull-secret
            default_pull_secret_path = os.path.expanduser("~/.openshift/pull-secret")
            if os.path.exists(default_pull_secret_path):
                with open(default_pull_secret_path, 'r') as f:
                    pull_secret = f.read().strip()
                print(f"Using pull secret found at {default_pull_secret_path}")
            else:
                print("Please enter your OpenShift pull secret (paste and press Enter, then Ctrl+D):")
                pull_secret = sys.stdin.read().strip()
                
            if not pull_secret:
                print("Pull secret is required. Get it from https://console.redhat.com/openshift/install/pull-secret")
                return 1
        
        # Download the OpenShift installer
        if not download_openshift_installer(args.version, output_dir):
            return 1
        
        # Create the configuration files
        if args.values_file:
            # Create configurations based on values file
            values_copy = yaml.safe_load(yaml.dump(values))  # Create a deep copy
            
            # Process secret references first
            values_copy = process_references(values_copy)
            
            # If the secretReferences section was processed, the pullSecret and sshKey
            # should already be in the values_copy. If not, add them from the arguments.
            if 'pullSecret' not in values_copy:
                values_copy['pullSecret'] = pull_secret
            if 'sshKey' not in values_copy:
                values_copy['sshKey'] = ssh_key
            
            # For safety, store the install config on TrueNAS if possible
            if not args.skip_upload:
                try:
                    # Create a sanitized copy without secrets for logging
                    safe_copy = yaml.safe_load(yaml.dump(values_copy))
                    if 'pullSecret' in safe_copy:
                        safe_copy['pullSecret'] = '***REDACTED***'
                    if 'sshKey' in safe_copy:
                        safe_copy['sshKey'] = '***REDACTED***'
                        
                    config_path = f"openshift_configs/{args.version}/install-config.yaml"
                    if put_secret(config_path, yaml.dump(values_copy, sort_keys=False)):
                        print(f"Backed up configuration to secrets storage at {config_path}")
                except Exception as e:
                    print(f"Warning: Could not back up configuration to secrets storage: {e}")
            
            with open(os.path.join(output_dir, "install-config.yaml"), 'w') as f:
                yaml.dump(values_copy, f, sort_keys=False)
                
            print(f"Created install-config.yaml from values file for OpenShift {args.version}")
            
            # Create agent config using values
            create_agent_config(output_dir, values_copy, rendezvous_ip)
        else:
            # Create configurations from command line arguments
            if not create_install_config(output_dir, args.version, domain, pull_secret, ssh_key):
                return 1
            
            if not create_agent_config(output_dir, None, args.rendezvous_ip):
                return 1
        
        # Generate the ISO
        iso_path = generate_iso(output_dir, args.version)
        if not iso_path:
            return 1
        
        # Upload to TrueNAS if not skipped
        if not args.skip_upload:
            if not upload_to_truenas(
                iso_path, 
                args.version, 
                args.truenas_ip, 
                args.truenas_user, 
                private_key=args.private_key
            ):
                return 1
        
        print("\nISO generation completed successfully!")
        print(f"ISO file: {iso_path}")
        
        if not args.skip_upload:
            print(f"The ISO has been uploaded to TrueNAS at {args.truenas_ip}")
            print(f"It can be accessed via HTTP at: http://{args.truenas_ip}/openshift_isos/{args.version}/agent.x86_64.iso")
        
        return 0
    
    finally:
        # Clean up temporary directory if we created one
        if should_cleanup:
            print(f"Cleaning up temporary directory: {output_dir}")
            shutil.rmtree(output_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
