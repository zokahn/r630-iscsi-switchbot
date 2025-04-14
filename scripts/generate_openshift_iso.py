#!/usr/bin/env python3
"""
generate_openshift_iso.py - Generate OpenShift agent-based ISO and upload to TrueNAS

This script uses the OpenShiftComponent to generate an OpenShift ISO file and optionally
upload it to TrueNAS. It follows the discovery-processing-housekeeping pattern for better
error handling and component-based architecture.
"""

import os
import sys
import logging
import argparse
import tempfile
import shutil
import yaml
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Import components
from framework.components.openshift_component import OpenShiftComponent

# Import secrets provider
try:
    from scripts.secrets_provider import process_references, get_secret, put_secret
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


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Set up logging configuration with proper formatting.

    Args:
        verbose: Whether to use DEBUG level logging

    Returns:
        Configured logger instance
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger("openshift-iso")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments with proper typing and descriptions.

    Returns:
        Parsed arguments as Namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate OpenShift agent-based ISO and upload to TrueNAS using the component architecture"
    )
    
    # OpenShift configuration
    openshift_group = parser.add_argument_group('OpenShift Configuration')
    openshift_group.add_argument(
        "--version", 
        default="4.18",
        help="OpenShift version (e.g., 4.18 or 4.18.0)"
    )
    openshift_group.add_argument(
        "--domain", 
        default="example.com",
        help="Base domain for the cluster"
    )
    openshift_group.add_argument(
        "--rendezvous-ip", 
        required=True,
        help="Rendezvous IP address (primary node)"
    )
    openshift_group.add_argument(
        "--pull-secret",
        help="Path to pull secret file (if not provided, will try ~/.openshift/pull-secret)"
    )
    openshift_group.add_argument(
        "--ssh-key",
        help="Path to SSH public key (if not provided, will try ~/.ssh/id_rsa.pub)"
    )
    openshift_group.add_argument(
        "--values-file",
        help="Path to YAML file with OpenShift installation values"
    )
    
    # TrueNAS configuration
    truenas_group = parser.add_argument_group('TrueNAS Configuration')
    truenas_group.add_argument(
        "--truenas-ip", 
        default="192.168.2.245",
        help="TrueNAS IP address"
    )
    truenas_group.add_argument(
        "--truenas-user", 
        default="root",
        help="TrueNAS SSH username"
    )
    truenas_group.add_argument(
        "--private-key",
        help="Path to SSH private key for TrueNAS authentication"
    )
    truenas_group.add_argument(
        "--skip-upload", 
        action="store_true",
        help="Skip uploading to TrueNAS"
    )
    
    # General options
    general_group = parser.add_argument_group('General Options')
    general_group.add_argument(
        "--output-dir",
        help="Custom output directory (default: temporary directory)"
    )
    general_group.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="Enable verbose logging"
    )
    general_group.add_argument(
        "--dry-run", 
        action="store_true",
        help="Validate configuration without generating ISO"
    )
    
    return parser.parse_args()


def load_values_from_file(values_file: str) -> Optional[Dict[str, Any]]:
    """
    Load OpenShift installation values from a YAML file.

    Args:
        values_file: Path to the YAML values file

    Returns:
        Dictionary of values or None if loading failed
    """
    try:
        with open(values_file, 'r') as f:
            values = yaml.safe_load(f)
            
        # Process secret references
        values = process_references(values)
        return values
    except Exception as e:
        logging.error(f"Error loading values file: {e}")
        return None


def get_ssh_key(ssh_key_path: Optional[str] = None) -> Optional[str]:
    """
    Get SSH public key content from file.

    Args:
        ssh_key_path: Path to SSH public key file (optional)

    Returns:
        SSH key content or None if not found
    """
    # If path is provided, try to read it
    if ssh_key_path:
        if os.path.exists(ssh_key_path):
            with open(ssh_key_path, 'r') as f:
                return f.read().strip()
        else:
            logging.error(f"SSH key file not found at {ssh_key_path}")
            return None
    
    # Try default location
    default_key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
    if os.path.exists(default_key_path):
        with open(default_key_path, 'r') as f:
            logging.info(f"Using SSH key from {default_key_path}")
            return f.read().strip()
    
    logging.error("No SSH key provided and ~/.ssh/id_rsa.pub not found")
    return None


def get_pull_secret(pull_secret_path: Optional[str] = None) -> Optional[str]:
    """
    Get OpenShift pull secret content.

    Args:
        pull_secret_path: Path to pull secret file (optional)

    Returns:
        Pull secret content or None if not found
    """
    # If path is provided, try to read it
    if pull_secret_path:
        if os.path.exists(pull_secret_path):
            with open(pull_secret_path, 'r') as f:
                return f.read().strip()
        else:
            logging.error(f"Pull secret file not found at {pull_secret_path}")
            return None
    
    # Try default location
    default_pull_secret_path = os.path.expanduser("~/.openshift/pull-secret")
    if os.path.exists(default_pull_secret_path):
        with open(default_pull_secret_path, 'r') as f:
            logging.info(f"Using pull secret from {default_pull_secret_path}")
            return f.read().strip()
    
    # Try to get from secrets provider
    pull_secret = get_secret('openshift/pull-secret')
    if pull_secret:
        logging.info("Using pull secret from secrets provider")
        return pull_secret
    
    logging.error("No pull secret provided and none found in default locations")
    return None


def upload_to_truenas(iso_path: str, version: str, truenas_ip: str, username: str, private_key: Optional[str] = None) -> bool:
    """
    Upload the ISO to TrueNAS using SCP.

    Args:
        iso_path: Path to the ISO file
        version: OpenShift version
        truenas_ip: TrueNAS server IP address
        username: TrueNAS SSH username
        private_key: Path to SSH private key (optional)

    Returns:
        True if upload successful, False otherwise
    """
    # Format version for path
    version_path = version.replace('x', '0')  # Handle cases like 4.18.x
    if len(version_path.split('.')) < 3:
        version_path = f"{version_path}.0"
    
    # Construct destination path
    remote_path = f"{username}@{truenas_ip}:/mnt/tank/openshift_isos/{version_path.split('.')[0]}.{version_path.split('.')[1]}/agent.x86_64.iso"
    
    logging.info(f"Uploading ISO to TrueNAS at {remote_path}...")
    
    scp_command = ["scp"]
    
    # Add private key if provided
    if private_key:
        scp_command.extend(["-i", private_key])
    
    # Add the source and destination
    scp_command.extend([iso_path, remote_path])
    
    try:
        # Run the SCP command
        subprocess.run(scp_command, check=True)
        logging.info("ISO uploaded successfully")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error uploading ISO: {e}")
        return False


def create_openshift_config(args: argparse.Namespace, values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create OpenShift component configuration from command line arguments and/or values file.

    Args:
        args: Parsed command line arguments
        values: Values loaded from YAML file (optional)

    Returns:
        Configuration dictionary for OpenShiftComponent
    """
    # Get basic configuration values either from values file or command line
    if values:
        domain = values.get('baseDomain', args.domain)
        rendezvous_ip = values.get('sno', {}).get('nodeIP', args.rendezvous_ip)
        pull_secret = values.get('pullSecret')
        ssh_key = values.get('sshKey')
    else:
        domain = args.domain
        rendezvous_ip = args.rendezvous_ip
        pull_secret = None
        ssh_key = None
    
    # If pull_secret and ssh_key weren't in the values file, get them from command line or defaults
    if not pull_secret:
        pull_secret = get_pull_secret(args.pull_secret)
    
    if not ssh_key:
        ssh_key = get_ssh_key(args.ssh_key)
    
    # Set up configuration
    config = {
        'openshift_version': args.version,
        'domain': domain,
        'rendezvous_ip': rendezvous_ip,
        'node_ip': rendezvous_ip,  # Use rendezvous IP as node IP by default
        'pull_secret_content': pull_secret,
        'ssh_key_content': ssh_key,
        'output_dir': args.output_dir or None,
        'component_id': 'openshift-iso-component',
        'dry_run': args.dry_run
    }
    
    # If values file was provided, store the complete configuration
    if values:
        config['values_file_content'] = values
        
        # Extract additional configuration from values file
        if 'sno' in values:
            sno_config = values.get('sno', {})
            # Use hostname if specified
            if 'hostname' in sno_config:
                config['hostname'] = sno_config['hostname']
            
            # Use server_id if specified
            if 'server_id' in sno_config:
                config['server_id'] = sno_config['server_id']
            
            # Use installation disk if specified
            if 'installationDisk' in sno_config:
                config['installation_disk'] = sno_config['installationDisk']
            elif 'bootstrapInPlace' in values and 'installationDisk' in values['bootstrapInPlace']:
                config['installation_disk'] = values['bootstrapInPlace']['installationDisk']
    
    return config


def run_workflow(args: argparse.Namespace, logger: logging.Logger) -> int:
    """
    Run the main workflow with proper error handling.

    Args:
        args: Command line arguments
        logger: Logger instance

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Load values from file if specified
        values = None
        if args.values_file:
            logger.info(f"Loading installation values from {args.values_file}")
            values = load_values_from_file(args.values_file)
            if not values:
                logger.error("Failed to load values file")
                return 1
        
        # Create OpenShift component configuration
        openshift_config = create_openshift_config(args, values)
        
        # Validate required configuration
        if not openshift_config.get('pull_secret_content'):
            logger.error("Pull secret is required. Get it from https://console.redhat.com/openshift/install/pull-secret")
            return 1
        
        if not openshift_config.get('ssh_key_content'):
            logger.error("SSH key is required. Generate one with ssh-keygen if needed.")
            return 1
        
        # Create component
        logger.info("Initializing OpenShift component...")
        openshift_component = OpenShiftComponent(openshift_config, logger)
        
        # Discovery phase
        logger.info("Running discovery phase...")
        discovery_results = openshift_component.discover()
        
        # Check if we have everything we need
        if not discovery_results.get('pull_secret_available', False):
            logger.error("Pull secret verification failed")
            return 1
        
        if not discovery_results.get('ssh_key_available', False):
            logger.error("SSH key verification failed")
            return 1
        
        logger.info(f"OpenShift discovery completed successfully")
        logger.info(f"Using OpenShift version: {args.version}")
        
        # Process phase (generate ISO)
        logger.info("Running processing phase (generating ISO)...")
        process_results = openshift_component.process()
        
        # Check if ISO was generated
        if not process_results.get('iso_generated', False):
            logger.error("Failed to generate ISO")
            return 1
        
        iso_path = process_results.get('iso_path')
        logger.info(f"Successfully generated ISO at: {iso_path}")
        
        # Upload to TrueNAS if not skipped
        if not args.skip_upload and iso_path:
            if not upload_to_truenas(
                iso_path,
                args.version,
                args.truenas_ip,
                args.truenas_user,
                args.private_key
            ):
                logger.error("Failed to upload ISO to TrueNAS")
                return 1
            
            # Print access URL
            version_parts = args.version.split('.')
            major_minor = f"{version_parts[0]}.{version_parts[1]}"
            logger.info(f"ISO can be accessed via HTTP at: http://{args.truenas_ip}/openshift_isos/{major_minor}/agent.x86_64.iso")
        
        # Housekeeping phase
        logger.info("Running housekeeping phase...")
        housekeeping_results = openshift_component.housekeep()
        
        # If we're keeping the output directory, let the user know
        if args.output_dir:
            logger.info(f"ISO and configuration files are in: {args.output_dir}")
        
        logger.info("OpenShift ISO generation completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error generating OpenShift ISO: {str(e)}")
        if logger.level == logging.DEBUG:
            import traceback
            logger.debug(traceback.format_exc())
        return 1


def main() -> int:
    """
    Main entry point with error handling.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    # Create output directory if specified
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        logger.info(f"Using output directory: {args.output_dir}")
    
    try:
        return run_workflow(args, logger)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
