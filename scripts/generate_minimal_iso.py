#!/usr/bin/env python3
# generate_minimal_iso.py - Generate minimal OpenShift agent-based installation ISO
#
# PURPOSE:
# This tool generates a minimal OpenShift installation ISO that establishes
# a functional base cluster. It is intentionally simple and focused only on
# Day 1 operations (initial deployment).
#
# IMPORTANT:
# Most OpenShift configuration is performed as Day 2 operations after the cluster
# is operational. This includes:
#   - Installing and configuring Operators
#   - Setting up persistent storage
#   - Configuring advanced networking (routes, ingress, etc.)
#   - Implementing monitoring and logging
#   - Securing the cluster with RBAC and security policies
#   - Deploying applications and workloads
#
# This generator creates only the baseline deployment with minimal
# configuration necessary for a functional cluster.

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
    from secrets_provider import process_references, get_secret
except ImportError:
    # If running from a different directory, try to import using the script's directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from secrets_provider import process_references, get_secret
    except ImportError:
        # Define placeholder functions to avoid errors if the module is missing
        def process_references(data):
            return data

        def get_secret(path, key=None):
            print(f"Warning: secrets_provider module not found, can't retrieve secret from {path}")
            return None

def download_openshift_installer(version, output_dir):
    """
    Download the OpenShift installer binary for a specific version
    or use an existing one if it's already present and of the correct version
    """
    installer_path = os.path.join(output_dir, "openshift-install")
    
    # Check if installer already exists
    if os.path.exists(installer_path):
        try:
            # Check the version of the existing installer
            result = subprocess.run(
                [installer_path, "version"],
                capture_output=True,
                text=True,
                check=True
            )
            current_version = result.stdout.strip()
            print(f"Found existing OpenShift installer: {current_version}")
            
            # For "stable" we'll always use what we have
            if version == "stable":
                print("Using existing OpenShift installer (requested 'stable' version)")
                return True
                
            # For specific versions, check if it matches
            if version in current_version:
                print(f"Using existing OpenShift installer - matches requested version {version}")
                return True
            else:
                print(f"Existing installer ({current_version}) doesn't match requested version ({version})")
                # Continue to download the requested version
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Existing installer check failed, will download fresh copy")
            # Continue to download
    
    # Format version for URL (e.g., 4.18.0 -> 4.18.0, 4.18 -> latest 4.18.x)
    if len(version.split('.')) < 3 and version != "stable":
        # If just major.minor (e.g., 4.18), use format suited for latest in that stream
        version_for_url = f"{version}.x"
    else:
        # Full version specified or "stable"
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
        os.chmod(installer_path, 0o755)
        
        # Clean up the tarball to save disk space
        if os.path.exists(installer_tar):
            os.unlink(installer_tar)
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading OpenShift installer: {e}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error extracting OpenShift installer: {e}")
        return False

def create_install_config(output_dir, values, pull_secret, ssh_key):
    """
    Create the install-config.yaml file with minimal settings
    
    This configuration focuses ONLY on Day 1 operations - getting a functional cluster.
    Advanced configurations should be done post-installation as Day 2 operations.
    """
    install_config_path = os.path.join(output_dir, "install-config.yaml")
    
    # Extract basic values from the source configuration
    base_domain = values.get('baseDomain')
    cluster_name = values.get('metadata', {}).get('name')
    
    # Create the install-config content directly as a YAML string to avoid
    # formatting issues with embedded JSON in the pull secret
    content = f"""apiVersion: v1
baseDomain: {base_domain}
metadata:
  name: {cluster_name}
networking:
  networkType: OVNKubernetes
  machineNetwork:
  - cidr: {values.get('networking', {}).get('machineNetwork', [{'cidr': '192.168.2.0/24'}])[0]['cidr']}
compute:
- name: worker
  replicas: 0
controlPlane:
  name: master
  replicas: 1
platform:
  none: {{}}
"""

    # Add bootstrapInPlace configuration if installation disk is specified
    # This belongs in install-config.yaml, not agent-config.yaml
    installation_disk = values.get('bootstrapInPlace', {}).get('installationDisk')
    if installation_disk:
        content += f"""bootstrapInPlace:
  installationDisk: {installation_disk}
"""

    # Add pull secret and SSH key - these need careful handling to avoid YAML formatting issues
    content += f"pullSecret: '{pull_secret}'\n"
    content += f"sshKey: '{ssh_key}'\n"
    
    # Write the configuration to file
    with open(install_config_path, 'w') as f:
        f.write(content)
    
    print(f"Created minimal install-config.yaml for {cluster_name}.{base_domain}")
    return True

def create_agent_config(output_dir, values):
    """
    Create the agent-config.yaml file with minimal settings for Day 1
    
    Only includes what's strictly necessary to get the node booted and 
    connected. Additional configuration should be done post-installation.
    
    Note: bootstrapInPlace should only be included in install-config.yaml,
    not in agent-config.yaml as of stable OpenShift version.
    """
    agent_config_path = os.path.join(output_dir, "agent-config.yaml")
    
    # Extract values from the configuration
    cluster_name = values.get('metadata', {}).get('name')
    sno_config = values.get('sno', {})
    node_ip = sno_config.get('nodeIP')
    hostname = sno_config.get('hostname')
    mac_address = sno_config.get('macAddress')
    installation_disk = values.get('bootstrapInPlace', {}).get('installationDisk')
    
    # Build minimal agent-config (without bootstrapInPlace - that belongs in install-config.yaml)
    content = f"""apiVersion: v1beta1
kind: AgentConfig
metadata:
  name: {cluster_name}
rendezvousIP: {node_ip}
hosts:
  - hostname: {hostname}
    role: master
    interfaces:
      - macAddress: {mac_address}"""

    # Add rootDeviceHints if installation disk is specified
    if installation_disk:
        content += f"""
    rootDeviceHints:
      deviceName: "{installation_disk}" """
    
    with open(agent_config_path, 'w') as f:
        f.write(content)
    
    print(f"Created minimal agent-config.yaml with rendezvous IP {node_ip}")
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

def upload_to_truenas(iso_path, version, truenas_ip, username, private_key=None):
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

def print_day2_operations():
    """Print information about Day 2 operations to be performed after installation"""
    print("\n" + "="*80)
    print("IMPORTANT: DAY 2 OPERATIONS")
    print("="*80)
    print("This ISO contains only minimal Day 1 configurations needed for installation.")
    print("After the cluster is running, you will need to perform Day 2 operations such as:")
    print()
    print("1. Installing and configuring operators")
    print("2. Setting up persistent storage")
    print("3. Configuring advanced networking")
    print("4. Implementing monitoring and logging")
    print("5. Securing the cluster with RBAC and security contexts")
    print("6. Deploying applications and workloads")
    print()
    print("Refer to the Red Hat documentation for detailed instructions:")
    print("https://docs.openshift.com/container-platform/latest/post_installation_configuration/index.html")
    print("="*80)

def main():
    parser = argparse.ArgumentParser(
        description="Generate minimal OpenShift agent-based ISO with Day 1 configurations",
        epilog="Note: This generator creates a minimal Day 1 configuration. Most configuration should be done as Day 2 operations after cluster deployment."
    )
    parser.add_argument("--config", required=True, help="Path to OpenShift configuration YAML file")
    parser.add_argument("--version", default="4.18", help="OpenShift version (e.g., 4.18 or 4.18.0)")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--truenas-user", default="root", help="TrueNAS SSH username")
    parser.add_argument("--private-key", help="Path to SSH private key for TrueNAS authentication")
    parser.add_argument("--pull-secret", help="Path to pull secret for OpenShift. If not provided, will try to find it")
    parser.add_argument("--ssh-key", help="Path to SSH public key for OpenShift. If not provided, will use ~/.ssh/id_rsa.pub")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading to TrueNAS")
    parser.add_argument("--output-dir", help="Custom output directory (default: temporary directory)")
    
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
        # Load the configuration values file
        print(f"Loading configuration from {args.config}")
        values = load_values_from_file(args.config)
        if not values:
            return 1
        
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
                # Try getting from secret provider if exists
                pull_secret_from_secret = get_secret("openshift/pull-secret")
                if pull_secret_from_secret:
                    pull_secret = pull_secret_from_secret
                    print("Using pull secret from secrets provider")
                else:
                    print("Please enter your OpenShift pull secret (paste and press Enter, then Ctrl+D):")
                    pull_secret = sys.stdin.read().strip()
                
            if not pull_secret:
                print("Pull secret is required. Get it from https://console.redhat.com/openshift/install/pull-secret")
                return 1
        
        # Download the OpenShift installer
        if not download_openshift_installer(args.version, output_dir):
            return 1
        
        # Create the minimal configuration files for Day 1
        create_install_config(output_dir, values, pull_secret, ssh_key)
        create_agent_config(output_dir, values)
        
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
            
            print(f"\nThe ISO has been uploaded to TrueNAS at {args.truenas_ip}")
            print(f"It can be accessed via HTTP at: http://{args.truenas_ip}/openshift_isos/{args.version}/agent.x86_64.iso")
        
        # Print information about Day 2 operations
        print_day2_operations()
        
        print("\nISO generation completed successfully!")
        print(f"ISO file: {iso_path}")
        
        return 0
    
    finally:
        # Clean up temporary directory if we created one
        if should_cleanup:
            print(f"Cleaning up temporary directory: {output_dir}")
            shutil.rmtree(output_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
