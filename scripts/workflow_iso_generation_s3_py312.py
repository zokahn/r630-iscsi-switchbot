#!/usr/bin/env python3
"""
workflow_iso_generation_s3_py312.py - Orchestrates OpenShift ISO generation and S3 storage

This script manages the generation of OpenShift ISOs and their storage in S3 using the 
discovery-processing-housekeeping pattern with the component architecture.

It performs the following steps:
1. Sets up S3Component for storage operations
2. Sets up OpenShiftComponent for ISO generation
3. Executes the full workflow through discovery, processing, and housekeeping phases
4. Manages proper error handling and reporting

Python 3.12 version with enhanced typing and features.
"""

import os
import sys
import logging
import argparse
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, TypedDict, Literal, cast, get_type_hints

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Import Python 3.12 components
from framework.components.s3_component_py312 import S3Component
from framework.components.openshift_component_py312 import OpenShiftComponent


# Type definitions
class S3DiscoveryResult(TypedDict):
    """S3Component discovery phase result type"""
    connectivity: bool
    error: Optional[str]
    buckets: Dict[str, Dict[str, Any]]


class OpenShiftDiscoveryResult(TypedDict):
    """OpenShiftComponent discovery phase result type"""
    pull_secret_available: bool
    ssh_key_available: bool
    error: Optional[str]


class OpenShiftProcessResult(TypedDict):
    """OpenShiftComponent process phase result type"""
    iso_generated: bool
    iso_path: Optional[str]
    s3_iso_path: Optional[str]
    error: Optional[str]
    upload_status: Optional[Literal['success', 'failed', 'skipped']]


class OpenShiftHousekeepResult(TypedDict):
    """OpenShiftComponent housekeep phase result type"""
    iso_verified: bool
    temp_files_removed: bool
    error: Optional[str]


class S3ConfigDict(TypedDict):
    """S3Component configuration type"""
    endpoint: str
    access_key: Optional[str]
    secret_key: Optional[str]
    secure: bool
    private_bucket: str
    public_bucket: str
    create_buckets_if_missing: bool
    component_id: str
    dry_run: bool


class OpenShiftConfigDict(TypedDict):
    """OpenShiftComponent configuration type"""
    openshift_version: str
    domain: str
    rendezvous_ip: Optional[str]
    pull_secret_path: Optional[str]
    ssh_key_path: Optional[str]
    output_dir: Optional[str]
    skip_upload: bool
    upload_to_s3: bool
    cleanup_temp_files: bool
    component_id: str
    s3_config: Dict[str, str]
    server_id: Optional[str]
    hostname: Optional[str]
    dry_run: bool


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
    return logging.getLogger("workflow")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments with proper typing and descriptions.

    Returns:
        Parsed arguments as Namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate OpenShift ISO and store in S3 using the Python 3.12 component architecture"
    )
    
    # OpenShift configuration
    openshift_group = parser.add_argument_group('OpenShift Configuration')
    openshift_group.add_argument(
        "--version", 
        default="4.14", 
        help="OpenShift version (e.g., '4.14')"
    )
    openshift_group.add_argument(
        "--domain", 
        default="example.com", 
        help="Base domain for OpenShift"
    )
    openshift_group.add_argument(
        "--rendezvous-ip", 
        help="Rendezvous IP address for agent-based install"
    )
    openshift_group.add_argument(
        "--pull-secret", 
        help="Path to pull secret file (default: ~/.openshift/pull-secret)"
    )
    openshift_group.add_argument(
        "--ssh-key", 
        help="Path to SSH public key file (default: ~/.ssh/id_rsa.pub)"
    )
    
    # S3/MinIO configuration
    s3_group = parser.add_argument_group('S3/MinIO Configuration')
    s3_group.add_argument(
        "--s3-endpoint", 
        default="scratchy.omnisack.nl", 
        help="S3 endpoint URL"
    )
    s3_group.add_argument(
        "--s3-access-key", 
        help="S3 access key (can also use S3_ACCESS_KEY env var)"
    )
    s3_group.add_argument(
        "--s3-secret-key", 
        help="S3 secret key (can also use S3_SECRET_KEY env var)"
    )
    s3_group.add_argument(
        "--s3-secure", 
        action="store_true", 
        help="Use HTTPS for S3 connection"
    )
    s3_group.add_argument(
        "--iso-bucket", 
        default="r630-switchbot-isos", 
        help="Bucket for OpenShift ISOs"
    )
    s3_group.add_argument(
        "--binary-bucket", 
        default="r630-switchbot-binaries", 
        help="Bucket for OpenShift binaries"
    )
    
    # Workflow options
    workflow_group = parser.add_argument_group('Workflow Options')
    workflow_group.add_argument(
        "--skip-iso", 
        action="store_true", 
        help="Skip ISO generation"
    )
    workflow_group.add_argument(
        "--skip-upload", 
        action="store_true", 
        help="Skip uploading to S3"
    )
    workflow_group.add_argument(
        "--list-only", 
        action="store_true", 
        help="Only list ISOs in S3, don't generate"
    )
    workflow_group.add_argument(
        "--temp-dir", 
        help="Custom temporary directory for output files"
    )
    workflow_group.add_argument(
        "--server-id", 
        help="Server ID for ISO identification (e.g., '01')"
    )
    workflow_group.add_argument(
        "--hostname", 
        help="Server hostname for ISO identification"
    )
    
    # General options
    general_group = parser.add_argument_group('General Options')
    general_group.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    general_group.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Dry run (no changes)"
    )
    
    return parser.parse_args()


def create_s3_config(args: argparse.Namespace) -> S3ConfigDict:
    """
    Create S3Component configuration from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        S3Component configuration dictionary
    """
    # Use access key from args or environment variable
    access_key = args.s3_access_key or os.environ.get("S3_ACCESS_KEY")
    secret_key = args.s3_secret_key or os.environ.get("S3_SECRET_KEY")
    
    return {
        'endpoint': args.s3_endpoint,
        'access_key': access_key,
        'secret_key': secret_key,
        'secure': args.s3_secure,
        'private_bucket': args.iso_bucket,
        'public_bucket': args.iso_bucket,  # Using the same bucket for simplicity
        'create_buckets_if_missing': True,
        'component_id': 'workflow-s3-component',
        'dry_run': args.dry_run
    }


def create_openshift_config(args: argparse.Namespace) -> OpenShiftConfigDict:
    """
    Create OpenShiftComponent configuration from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        OpenShiftComponent configuration dictionary
    """
    # Python 3.12 explicit type checking for values
    s3_config_part = {
        's3_config': {
            'iso_bucket': args.iso_bucket,
            'binary_bucket': args.binary_bucket
        }
    }
    
    # Use Python 3.12 dictionary union operator (|)
    base_config = {
        'openshift_version': args.version,
        'domain': args.domain,
        'rendezvous_ip': args.rendezvous_ip,
        'pull_secret_path': args.pull_secret,
        'ssh_key_path': args.ssh_key,
        'output_dir': args.temp_dir,
        'skip_upload': args.skip_upload,
        'upload_to_s3': not args.skip_upload,
        'cleanup_temp_files': not args.temp_dir,  # Only cleanup if using temp dir
        'component_id': 'workflow-openshift-component',
        'server_id': args.server_id,
        'hostname': args.hostname,
        'dry_run': args.dry_run
    }
    
    # Combine dictionaries using Python 3.12 | operator
    return cast(OpenShiftConfigDict, base_config | s3_config_part)


def list_isos_in_s3(s3_component: S3Component, logger: logging.Logger) -> int:
    """
    List OpenShift ISOs stored in S3 using the S3Component.

    Args:
        s3_component: Initialized S3Component
        logger: Logger instance

    Returns:
        Number of ISOs found
    """
    iso_count = 0
    
    # This has been migrated to use the component's methods more directly
    try:
        # First check if we completed discovery with Python 3.12 pattern matching
        if not s3_component.phases_executed.get('discover', False):
            logger.info("Running S3 discovery phase...")
            discovery_result = s3_component.discover()
            
            # Python 3.12 pattern matching for error handling
            match discovery_result:
                case {'connectivity': True}:
                    logger.debug("S3 discovery completed successfully")
                case {'connectivity': False, 'error': error}:
                    logger.error(f"S3 discovery failed: {error}")
                    return 0
                case _:
                    logger.warning("Unexpected S3 discovery result format")
        
        # Use the component to list ISOs
        logger.info(f"Listing ISOs in bucket {s3_component.config.get('private_bucket')}")
        iso_list = s3_component.list_isos()
        
        iso_count = len(iso_list)
        
        if iso_count == 0:
            logger.info("No ISO files found")
        else:
            # Use Python 3.12 feature with assignment expressions in list comprehension
            for iso in iso_list:
                # Calculate size in MB with improved clarity
                if size := iso.get('size'):
                    size_mb = size / (1024 * 1024)
                    logger.info(f"  - {iso.get('key')} ({size_mb:.1f} MB, last modified: {iso.get('last_modified')})")
                else:
                    logger.info(f"  - {iso.get('key')} (size unknown, last modified: {iso.get('last_modified')})")
        
        return iso_count
        
    except Exception as e:
        logger.error(f"Error listing ISOs: {str(e)}")
        return 0


def run_workflow(args: argparse.Namespace, logger: logging.Logger) -> int:
    """
    Run the main workflow with error handling.

    Args:
        args: Parsed command line arguments
        logger: Logger instance

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Initialize S3 component
        logger.info("Initializing S3 component...")
        s3_config = create_s3_config(args)
        s3_component = S3Component(s3_config, logger)
        
        # Handle list-only request early
        if args.list_only:
            logger.info("List-only mode: Showing existing ISOs")
            iso_count = list_isos_in_s3(s3_component, logger)
            logger.info(f"Found {iso_count} ISO files")
            return 0
        
        # Execute S3 discovery phase
        logger.info("Running S3 discovery phase...")
        s3_discovery_results = cast(S3DiscoveryResult, s3_component.discover())
        
        # Python 3.12 pattern matching for error handling
        match s3_discovery_results:
            case {'connectivity': False, 'error': error}:
                logger.error(f"Failed to connect to S3 endpoint: {error}")
                return 1
            case {'connectivity': True}:
                logger.info(f"Successfully connected to S3 at {args.s3_endpoint}")
            case _:
                logger.warning("Unexpected S3 discovery result format")
                return 1
        
        # Initialize OpenShift component - use Python 3.12 type safety
        logger.info("Initializing OpenShift component...")
        openshift_config = create_openshift_config(args)
        openshift_component = OpenShiftComponent(openshift_config, logger, s3_component)
        
        # Skip ISO generation if requested
        if args.skip_iso:
            logger.info("Skipping ISO generation as requested")
        else:
            # Run OpenShift discovery phase
            logger.info("Running OpenShift discovery phase...")
            openshift_discovery_results = cast(OpenShiftDiscoveryResult, openshift_component.discover())
            
            # Check for required resources using Python 3.12 pattern matching
            match openshift_discovery_results:
                case {'pull_secret_available': False}:
                    logger.error("Pull secret not found - required for ISO generation")
                    return 1
                case {'ssh_key_available': False}:
                    logger.error("SSH key not found - required for ISO generation")
                    return 1
                case {'pull_secret_available': True, 'ssh_key_available': True}:
                    logger.info("All required resources found for ISO generation")
                case _:
                    logger.warning("Unexpected OpenShift discovery result format")
            
            # Generate ISO (process phase)
            logger.info("Running OpenShift processing phase (generating ISO)...")
            openshift_process_results = cast(OpenShiftProcessResult, openshift_component.process())
            
            # Check process results with Python 3.12 pattern matching
            match openshift_process_results:
                case {'iso_generated': False, 'error': error}:
                    logger.error(f"Failed to generate ISO: {error}")
                    return 1
                case {'iso_generated': True, 'iso_path': iso_path}:
                    logger.info(f"Successfully generated ISO at: {iso_path}")
                case _:
                    logger.warning("Unexpected OpenShift process result format")
            
            # Run housekeeping phase
            logger.info("Running OpenShift housekeeping phase...")
            openshift_housekeep_results = cast(OpenShiftHousekeepResult, openshift_component.housekeep())
            
            # Check housekeeping results
            if openshift_housekeep_results.get('iso_verified', False):
                logger.info("ISO verification successful")
            
        # Run S3 processing phase (needed for bucket creation/verification)
        logger.info("Running S3 processing phase...")
        s3_process_results = s3_component.process()
        
        # Run S3 housekeeping phase
        logger.info("Running S3 housekeeping phase...")
        s3_housekeep_results = s3_component.housekeep()
        
        # Final verification checks
        if not args.skip_iso and not args.skip_upload:
            logger.info("Verifying workflow completion...")
            
            # Use Python 3.12 pattern matching for verification
            match openshift_process_results:
                case {'upload_status': 'success', 's3_iso_path': path} if path:
                    logger.info("ISO successfully uploaded to S3")
                    logger.info(f"S3 path: {path}")
                case {'upload_status': status}:
                    logger.warning(f"ISO upload status: {status}")
                case _:
                    logger.warning("ISO may not have been uploaded to S3 - check logs")
        
        logger.info("Workflow completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Workflow failed with error: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


def main() -> int:
    """
    Main entry point with basic error handling.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    try:
        return run_workflow(args, logger)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
