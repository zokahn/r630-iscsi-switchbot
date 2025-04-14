#!/usr/bin/env python3
"""
generate_openshift_iso_py312.py - Generate OpenShift agent-based ISO and upload to TrueNAS

This script uses the OpenShiftComponent to generate an OpenShift ISO file and optionally
upload it to TrueNAS. It follows the discovery-processing-housekeeping pattern for better
error handling and component-based architecture.

Python 3.12 version with enhanced typing and features.
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
from typing import Dict, Any, Optional, Tuple, TypedDict, Literal, cast, NotRequired, Union

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Import Python 3.12 components
from framework.components.openshift_component_py312 import OpenShiftComponent

# Import secrets provider
try:
    from scripts.secrets_provider import process_references, get_secret, put_secret
except ImportError:
    # Define placeholder functions to avoid errors if the module is missing
    def process_references(data: Any) -> Any:
        return data

    def get_secret(path: str, key: Optional[str] = None) -> Optional[str]:
        print(f"Warning: secrets_provider module not found, can't retrieve secret from {path}")
        return None

    def put_secret(path: str, content: str, key: Optional[str] = None) -> bool:
        print(f"Warning: secrets_provider module not found, can't store secret to {path}")
        return False


# Type definitions
class OpenShiftConfigDict(TypedDict):
    """OpenShift component configuration type"""
    openshift_version: str
    domain: str
    rendezvous_ip: str
    node_ip: str
    pull_secret_content: Optional[str]
    ssh_key_content: Optional[str]
    output_dir: Optional[str]
    component_id: str
    dry_run: bool
    values_file_content: NotRequired[Dict[str, Any]]
    hostname: NotRequired[str]
    server_id: NotRequired[str]
    installation_disk: NotRequired[str]


class OpenShiftDiscoveryResult(TypedDict):
    """OpenShift component discovery phase result type"""
    pull_secret_available: bool
    ssh_key_available: bool
    error: NotRequired[str]


class OpenShiftProcessResult(TypedDict):
    """OpenShift component process phase result type"""
    iso_generated: bool
    iso_path: Optional[str]
    error: NotRequired[str]


class OpenShiftHousekeepResult(TypedDict):
    """OpenShift component housekeep phase result type"""
    temp_files_removed: bool
    error: NotRequired[str]


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
        description="Generate OpenShift agent-based ISO and upload to TrueNAS using the Python 3.12 component architecture"
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


def load_values_from_file(values_file: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Load OpenShift installation values from a YAML file.

    Args:
        values_file: Path to the YAML values file

    Returns:
        Dictionary of values or None if loading failed
    """
    try:
        # Use pathlib for better path handling
        file_path = Path(values_file)
        if not file_path.exists():
            logging.error(f"Values file not found: {file_path}")
            return None
            
        with open(file_path, 'r') as f:
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
        ssh_key_file = Path(ssh_key_path)
        if ssh_key_file.exists():
            return ssh_key_file.read_text().strip()
        else:
            logging.error(f"SSH key file not found at {ssh_key_file}")
            return None
    
    # Try default location
    default_key_path = Path.home() / ".ssh" / "id_rsa.pub"
    if default_key_path.exists():
        logging.info(f"Using SSH key from {default_key_path}")
        return default_key_path.read_text().strip()
    
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
        pull_secret_file = Path(pull_secret_path)
        if pull_secret_file.exists():
            return pull_secret_file.read_text().strip()
        else:
            logging.error(f"Pull secret file not found at {pull_secret_file}")
            return None
    
    # Try default location
    default_pull_secret_path = Path.home() / ".openshift" / "pull-secret"
    if default_pull_secret_path.exists():
        logging.info(f"Using pull secret from {default_pull_secret_path}")
        return default_pull_secret_path.read_text().strip()
    
    # Try to get from secrets provider
    if pull_secret := get_secret('openshift/pull-secret'):
        logging.info("Using pull secret from secrets provider")
        return pull_secret
    
    logging.error("No pull secret provided and none found in default locations")
    return None


def upload_to_truenas(
    iso_path: Union[str, Path], 
    version: str, 
    truenas_ip: str, 
    username: str, 
    private_key: Optional[str] = None
) -> bool:
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
    # Format version for path - use improved string handling
    version_parts = version.replace('x', '0').split('.')
    
    # Ensure we have at least major.minor.patch format
    while len(version_parts) < 3:
        version_parts.append('0')
    
    # Use Python 3.12 pattern matching for better version string parsing
    match version_parts:
        case [major, minor, *_]:
            version_dir = f"{major}.{minor}"
        case _:
            version_dir = version
    
    # Construct destination path
    remote_path = f"{username}@{truenas_ip}:/mnt/tank/openshift_isos/{version_dir}/agent.x86_64.iso"
    
    logging.info(f"Uploading ISO to TrueNAS at {remote_path}...")
    
    # Build SCP command
    scp_command = ["scp"]
    
    # Add private key if provided
    if private_key:
        scp_command.extend(["-i", private_key])
    
    # Add the source and destination
    scp_command.extend([str(iso_path), remote_path])
    
    try:
        # Run the SCP command
        result = subprocess.run(scp_command, check=True, capture_output=True, text=True)
        logging.info("ISO uploaded successfully")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error uploading ISO: {e}")
        if e.stderr:
            logging.error(f"Command output: {e.stderr}")
        return False


def create_openshift_config(
    args: argparse.Namespace, 
    values: Optional[Dict[str, Any]] = None
) -> OpenShiftConfigDict:
    """
    Create OpenShift component configuration from command line arguments and/or values file.

    Args:
        args: Parsed command line arguments
        values: Values loaded from YAML file (optional)

    Returns:
        Configuration dictionary for OpenShiftComponent
    """
    # Get basic configuration values either from values file or command line
    # Using pattern matching to handle different cases
    match values:
        case {'baseDomain': domain, 'sno': {'nodeIP': node_ip, **sno_data}}:
            domain = domain
            rendezvous_ip = node_ip
            # Extract additional SNO data if available
            hostname = sno_data.get('hostname', None)
            server_id = sno_data.get('server_id', None)
            installation_disk = sno_data.get('installationDisk', None)
        case {'baseDomain': domain}:
            domain = domain
            rendezvous_ip = args.rendezvous_ip
            hostname = None
            server_id = None
            installation_disk = None
        case _:
            domain = args.domain
            rendezvous_ip = args.rendezvous_ip
            hostname = None
            server_id = None
            installation_disk = None
    
    # Handle installation disk from bootstrapInPlace if not already set
    if not installation_disk and values and 'bootstrapInPlace' in values:
        installation_disk = values['bootstrapInPlace'].get('installationDisk', None)
    
    # Get pull secret and SSH key - first try values then command line/defaults
    pull_secret = None
    ssh_key = None
    
    if values:
        pull_secret = values.get('pullSecret')
        ssh_key = values.get('sshKey')
    
    # If not in values, get from args or defaults
    if not pull_secret:
        pull_secret = get_pull_secret(args.pull_secret)
    
    if not ssh_key:
        ssh_key = get_ssh_key(args.ssh_key)
    
    # Base configuration
    base_config: Dict[str, Any] = {
        'openshift_version': args.version,
        'domain': domain,
        'rendezvous_ip': rendezvous_ip,
        'node_ip': rendezvous_ip,  # Use rendezvous IP as node IP by default
        'pull_secret_content': pull_secret,
        'ssh_key_content': ssh_key,
        'output_dir': args.output_dir,
        'component_id': 'openshift-iso-component',
        'dry_run': args.dry_run
    }
    
    # Add optional fields if they exist
    if hostname:
        base_config['hostname'] = hostname
    if server_id:
        base_config['server_id'] = server_id
    if installation_disk:
        base_config['installation_disk'] = installation_disk
    if values:
        base_config['values_file_content'] = values
    
    # Return with proper type assertion
    return cast(OpenShiftConfigDict, base_config)


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
        
        # Use pattern matching to validate required configuration
        match openshift_config:
            case {'pull_secret_content': None}:
                logger.error("Pull secret is required. Get it from https://console.redhat.com/openshift/install/pull-secret")
                return 1
            case {'ssh_key_content': None}:
                logger.error("SSH key is required. Generate one with ssh-keygen if needed.")
                return 1
        
        # Create component
        logger.info("Initializing OpenShift component...")
        openshift_component = OpenShiftComponent(openshift_config, logger)
        
        # Discovery phase
        logger.info("Running discovery phase...")
        discovery_results = cast(OpenShiftDiscoveryResult, openshift_component.discover())
        
        # Use pattern matching to check discovery results
        match discovery_results:
            case {'pull_secret_available': False}:
                logger.error("Pull secret verification failed")
                return 1
            case {'ssh_key_available': False}:
                logger.error("SSH key verification failed")
                return 1
            case {'pull_secret_available': True, 'ssh_key_available': True}:
                logger.info(f"OpenShift discovery completed successfully")
                logger.info(f"Using OpenShift version: {args.version}")
            case _:
                logger.warning("Unexpected discovery result format")
        
        # Process phase (generate ISO)
        logger.info("Running processing phase (generating ISO)...")
        process_results = cast(OpenShiftProcessResult, openshift_component.process())
        
        # Use pattern matching to check process results
        match process_results:
            case {'iso_generated': False, 'error': error}:
                logger.error(f"Failed to generate ISO: {error}")
                return 1
            case {'iso_generated': False}:
                logger.error("Failed to generate ISO for unknown reason")
                return 1
            case {'iso_generated': True, 'iso_path': iso_path} if iso_path:
                logger.info(f"Successfully generated ISO at: {iso_path}")
                
                # Upload to TrueNAS if not skipped
                if not args.skip_upload:
                    if not upload_to_truenas(
                        iso_path,
                        args.version,
                        args.truenas_ip,
                        args.truenas_user,
                        args.private_key
                    ):
                        logger.error("Failed to upload ISO to TrueNAS")
                        return 1
                    
                    # Print access URL - use Python 3.12 version string parsing
                    if version_parts := args.version.split('.'):
                        # Ensure we have at least major.minor
                        if len(version_parts) < 2:
                            version_parts.append('0')
                        major_minor = f"{version_parts[0]}.{version_parts[1]}"
                        logger.info(f"ISO can be accessed via HTTP at: http://{args.truenas_ip}/openshift_isos/{major_minor}/agent.x86_64.iso")
            case _:
                logger.warning("Unexpected process result format")
        
        # Housekeeping phase
        logger.info("Running housekeeping phase...")
        housekeeping_results = cast(OpenShiftHousekeepResult, openshift_component.housekeep())
        
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
        # Use pathlib for better path handling
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using output directory: {output_dir}")
    
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
