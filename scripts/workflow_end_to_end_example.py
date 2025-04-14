#!/usr/bin/env python3
"""
workflow_end_to_end_example.py - End-to-end workflow for OpenShift deployment on R630

This script demonstrates a complete end-to-end workflow using the component architecture:
1. Generates an OpenShift ISO
2. Uploads it to S3 storage
3. Creates an iSCSI target with the ISO
4. Configures a Dell R630 server to boot from the iSCSI target

It serves as a reference implementation for the discovery-processing-housekeeping pattern
with proper error handling and component interactions.
"""

import os
import sys
import logging
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Import components
from framework.components.s3_component import S3Component
from framework.components.openshift_component import OpenShiftComponent
from framework.components.iscsi_component import ISCSIComponent
from framework.components.r630_component import R630Component


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
    return logging.getLogger("e2e-workflow")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments with proper typing and descriptions.

    Returns:
        Parsed arguments as Namespace
    """
    parser = argparse.ArgumentParser(
        description="End-to-end workflow for OpenShift deployment on R630 via iSCSI"
    )
    
    # Required arguments
    required_group = parser.add_argument_group('Required Arguments')
    required_group.add_argument(
        "--server-id", 
        required=True, 
        help="Server ID (e.g., '01')"
    )
    required_group.add_argument(
        "--hostname", 
        required=True, 
        help="Server hostname"
    )
    required_group.add_argument(
        "--node-ip", 
        required=True, 
        help="Node IP address"
    )
    required_group.add_argument(
        "--openshift-version", 
        required=True, 
        help="OpenShift version (e.g., '4.14.0')"
    )
    
    # Storage arguments
    storage_group = parser.add_argument_group('Storage Configuration')
    storage_group.add_argument(
        "--s3-endpoint", 
        required=True, 
        help="S3 endpoint URL"
    )
    storage_group.add_argument(
        "--s3-access-key", 
        help="S3 access key (can also use S3_ACCESS_KEY env var)"
    )
    storage_group.add_argument(
        "--s3-secret-key", 
        help="S3 secret key (can also use S3_SECRET_KEY env var)"
    )
    storage_group.add_argument(
        "--truenas-ip", 
        required=True, 
        help="TrueNAS IP address"
    )
    storage_group.add_argument(
        "--truenas-api-key", 
        help="TrueNAS API key (can also use TRUENAS_API_KEY env var)"
    )
    
    # iDRAC arguments
    idrac_group = parser.add_argument_group('iDRAC Configuration')
    idrac_group.add_argument(
        "--idrac-ip", 
        required=True, 
        help="iDRAC IP address"
    )
    idrac_group.add_argument(
        "--idrac-username", 
        help="iDRAC username (can also use IDRAC_USERNAME env var, defaults to 'root')"
    )
    idrac_group.add_argument(
        "--idrac-password", 
        help="iDRAC password (can also use IDRAC_PASSWORD env var)"
    )
    
    # OpenShift configuration
    openshift_group = parser.add_argument_group('OpenShift Configuration')
    openshift_group.add_argument(
        "--domain", 
        default="lab.example.com", 
        help="Base domain for OpenShift deployment"
    )
    openshift_group.add_argument(
        "--pull-secret-path", 
        help="Path to OpenShift pull secret"
    )
    openshift_group.add_argument(
        "--ssh-key-path", 
        help="Path to SSH public key"
    )
    
    # iSCSI configuration
    iscsi_group = parser.add_argument_group('iSCSI Configuration')
    iscsi_group.add_argument(
        "--zvol-size", 
        default="20G", 
        help="Size of the iSCSI zvol"
    )
    iscsi_group.add_argument(
        "--zfs-pool", 
        default="tank", 
        help="ZFS pool to use for iSCSI targets"
    )
    
    # Optional workflow arguments
    workflow_group = parser.add_argument_group('Workflow Options')
    workflow_group.add_argument(
        "--skip-iso", 
        action="store_true", 
        help="Skip ISO generation step"
    )
    workflow_group.add_argument(
        "--skip-iscsi", 
        action="store_true", 
        help="Skip iSCSI target creation"
    )
    workflow_group.add_argument(
        "--skip-r630", 
        action="store_true", 
        help="Skip R630 configuration"
    )
    workflow_group.add_argument(
        "--temp-dir", 
        help="Custom temporary directory for output files"
    )
    workflow_group.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Validate without making changes"
    )
    workflow_group.add_argument(
        "--cleanup", 
        action="store_true", 
        help="Clean up orphaned resources"
    )
    
    # General options
    general_group = parser.add_argument_group('General Options')
    general_group.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def build_s3_config(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Build S3Component configuration from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Configuration dictionary for S3Component
    """
    return {
        'endpoint': args.s3_endpoint,
        'access_key': args.s3_access_key,
        'secret_key': args.s3_secret_key,
        'private_bucket': f'r630-switchbot-private',
        'public_bucket': f'r630-switchbot-public',
        'create_buckets_if_missing': True,
        'component_id': f's3-component-{args.server_id}',
        'dry_run': args.dry_run
    }


def build_openshift_config(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Build OpenShiftComponent configuration from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Configuration dictionary for OpenShiftComponent
    """
    return {
        'openshift_version': args.openshift_version,
        'domain': args.domain,
        'rendezvous_ip': args.node_ip,
        'node_ip': args.node_ip,
        'server_id': args.server_id,
        'hostname': args.hostname,
        'pull_secret_path': args.pull_secret_path,
        'ssh_key_path': args.ssh_key_path,
        'output_dir': args.temp_dir,
        'component_id': f'openshift-component-{args.server_id}',
        'dry_run': args.dry_run
    }


def build_iscsi_config(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Build ISCSIComponent configuration from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Configuration dictionary for ISCSIComponent
    """
    return {
        'truenas_ip': args.truenas_ip,
        'api_key': args.truenas_api_key,
        'server_id': args.server_id,
        'hostname': args.hostname,
        'openshift_version': args.openshift_version,
        'zvol_size': args.zvol_size,
        'zfs_pool': args.zfs_pool,
        'dry_run': args.dry_run,
        'cleanup_unused': args.cleanup,
        'component_id': f'iscsi-component-{args.server_id}'
    }


def build_r630_config(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Build R630Component configuration from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Configuration dictionary for R630Component
    """
    return {
        'idrac_ip': args.idrac_ip,
        'idrac_username': args.idrac_username,
        'idrac_password': args.idrac_password,
        'server_id': args.server_id,
        'boot_mode': 'iscsi',
        'dry_run': args.dry_run,
        'component_id': f'r630-component-{args.server_id}'
    }


def setup_s3_component(args: argparse.Namespace, logger: logging.Logger) -> Tuple[S3Component, Dict[str, Any]]:
    """
    Set up and initialize the S3Component.

    Args:
        args: Parsed command line arguments
        logger: Logger instance

    Returns:
        Tuple of (S3Component, discovery results dict)
    """
    s3_config = build_s3_config(args)
    s3_component = S3Component(s3_config, logger)
    
    # Run discovery phase
    logger.info("Running S3 discovery phase...")
    try:
        s3_result = s3_component.discover()
        
        if not s3_result.get('connectivity', False):
            raise Exception(f"Cannot connect to S3: {s3_result.get('error', 'Unknown error')}")
        
        logger.info(f"Successfully connected to S3 at {args.s3_endpoint}")
        logger.info(f"Private bucket: {s3_result['buckets']['private'].get('exists', False)}")
        logger.info(f"Public bucket: {s3_result['buckets']['public'].get('exists', False)}")
        
        return s3_component, s3_result
    except Exception as e:
        logger.error(f"S3 discovery failed: {str(e)}")
        raise


def setup_openshift_component(args: argparse.Namespace, s3_component: S3Component, logger: logging.Logger) -> Tuple[OpenShiftComponent, Dict[str, Any]]:
    """
    Set up and initialize the OpenShiftComponent.

    Args:
        args: Parsed command line arguments
        s3_component: Initialized S3Component instance
        logger: Logger instance

    Returns:
        Tuple of (OpenShiftComponent, discovery results dict)
    """
    openshift_config = build_openshift_config(args)
    openshift_component = OpenShiftComponent(openshift_config, logger, s3_component)
    
    # Run discovery phase
    logger.info("Running OpenShift discovery phase...")
    try:
        openshift_result = openshift_component.discover()
        
        if not openshift_result.get('pull_secret_available', False):
            raise Exception(f"Pull secret not found at {openshift_config.get('pull_secret_path', 'default location')}")
        
        if not openshift_result.get('ssh_key_available', False):
            raise Exception(f"SSH key not found at {openshift_config.get('ssh_key_path', 'default location')}")
        
        logger.info(f"OpenShift discovery completed successfully")
        
        if openshift_result.get('installer_available', False):
            logger.info(f"OpenShift installer found")
        else:
            logger.info(f"OpenShift installer will be downloaded")
            
        if openshift_result.get('available_versions'):
            logger.info(f"Available versions: {', '.join(openshift_result['available_versions'])}")
        
        return openshift_component, openshift_result
    except Exception as e:
        logger.error(f"OpenShift discovery failed: {str(e)}")
        raise


def setup_iscsi_component(args: argparse.Namespace, logger: logging.Logger) -> Tuple[ISCSIComponent, Dict[str, Any]]:
    """
    Set up and initialize the ISCSIComponent.

    Args:
        args: Parsed command line arguments
        logger: Logger instance

    Returns:
        Tuple of (ISCSIComponent, discovery results dict)
    """
    iscsi_config = build_iscsi_config(args)
    iscsi_component = ISCSIComponent(iscsi_config, logger)
    
    # Run discovery phase
    logger.info("Running iSCSI discovery phase...")
    try:
        iscsi_result = iscsi_component.discover()
        
        if not iscsi_result.get('connectivity', False):
            raise Exception(f"Cannot connect to TrueNAS: {iscsi_result.get('connection_error', 'Unknown error')}")
        
        logger.info(f"Successfully connected to TrueNAS at {args.truenas_ip}")
        
        if iscsi_result.get('system_info', {}).get('hostname'):
            logger.info(f"TrueNAS hostname: {iscsi_result['system_info']['hostname']}")
            
        logger.info(f"iSCSI service running: {iscsi_result.get('iscsi_service', False)}")
        
        return iscsi_component, iscsi_result
    except Exception as e:
        logger.error(f"iSCSI discovery failed: {str(e)}")
        raise


def setup_r630_component(args: argparse.Namespace, logger: logging.Logger) -> Tuple[R630Component, Dict[str, Any]]:
    """
    Set up and initialize the R630Component.

    Args:
        args: Parsed command line arguments
        logger: Logger instance

    Returns:
        Tuple of (R630Component, discovery results dict)
    """
    r630_config = build_r630_config(args)
    r630_component = R630Component(r630_config, logger)
    
    # Run discovery phase
    logger.info("Running R630 discovery phase...")
    try:
        r630_result = r630_component.discover()
        
        if not r630_result.get('connectivity', False):
            raise Exception(f"Cannot connect to iDRAC: {r630_result.get('connection_error', 'Unknown error')}")
        
        logger.info(f"Successfully connected to iDRAC at {args.idrac_ip}")
        
        if r630_result.get('system_info', {}).get('model'):
            logger.info(f"System model: {r630_result['system_info']['model']}")
            
        logger.info(f"Current boot mode: {r630_result.get('boot_mode', 'unknown')}")
        
        return r630_component, r630_result
    except Exception as e:
        logger.error(f"R630 discovery failed: {str(e)}")
        raise


def process_openshift_component(openshift_component: OpenShiftComponent, logger: logging.Logger) -> Dict[str, Any]:
    """
    Run the processing phase for the OpenShiftComponent.

    Args:
        openshift_component: Initialized OpenShiftComponent
        logger: Logger instance

    Returns:
        Processing results dict
    """
    logger.info("Running OpenShift processing phase...")
    try:
        process_result = openshift_component.process()
        
        if not process_result.get('iso_generated', False):
            raise Exception("Failed to generate OpenShift ISO")
        
        iso_path = process_result.get('iso_path')
        logger.info(f"Successfully generated ISO at {iso_path}")
        
        return process_result
    except Exception as e:
        logger.error(f"OpenShift processing failed: {str(e)}")
        raise


def process_s3_component(s3_component: S3Component, logger: logging.Logger) -> Dict[str, Any]:
    """
    Run the processing phase for the S3Component.

    Args:
        s3_component: Initialized S3Component
        logger: Logger instance

    Returns:
        Processing results dict
    """
    logger.info("Running S3 processing phase...")
    try:
        process_result = s3_component.process()
        
        # Check bucket creation/configuration status
        for bucket_type in ['private', 'public']:
            if process_result.get('buckets', {}).get(bucket_type, {}).get('created', False):
                logger.info(f"Created {bucket_type} bucket")
            elif process_result.get('buckets', {}).get(bucket_type, {}).get('configured', False):
                logger.info(f"Configured existing {bucket_type} bucket")
        
        return process_result
    except Exception as e:
        logger.error(f"S3 processing failed: {str(e)}")
        raise


def process_iscsi_component(iscsi_component: ISCSIComponent, logger: logging.Logger) -> Dict[str, Any]:
    """
    Run the processing phase for the ISCSIComponent.

    Args:
        iscsi_component: Initialized ISCSIComponent
        logger: Logger instance

    Returns:
        Processing results dict
    """
    logger.info("Running iSCSI processing phase...")
    try:
        process_result = iscsi_component.process()
        
        if not process_result.get('target_created', False):
            raise Exception("Failed to create iSCSI target")
        
        target_name = process_result.get('target_name')
        logger.info(f"Successfully created iSCSI target: {target_name}")
        
        return process_result
    except Exception as e:
        logger.error(f"iSCSI processing failed: {str(e)}")
        raise


def process_r630_component(r630_component: R630Component, iscsi_result: Dict[str, Any], truenas_ip: str, logger: logging.Logger) -> Dict[str, Any]:
    """
    Run the processing phase for the R630Component with iSCSI target details.

    Args:
        r630_component: Initialized R630Component
        iscsi_result: Results from iSCSI component processing
        truenas_ip: IP address of the TrueNAS server
        logger: Logger instance

    Returns:
        Processing results dict
    """
    logger.info("Running R630 processing phase...")
    try:
        # Pass iSCSI target details to R630 component
        r630_component.config['iscsi_target'] = iscsi_result.get('target_name')
        r630_component.config['iscsi_ip'] = truenas_ip
        
        process_result = r630_component.process()
        
        if not process_result.get('boot_configured', False):
            raise Exception("Failed to configure iSCSI boot")
        
        logger.info("Successfully configured server for iSCSI boot")
        
        return process_result
    except Exception as e:
        logger.error(f"R630 processing failed: {str(e)}")
        raise


def run_housekeeping_phases(components: Dict[str, Any], logger: logging.Logger) -> Dict[str, Dict[str, Any]]:
    """
    Run housekeeping phases for all components.

    Args:
        components: Dictionary of component instances
        logger: Logger instance

    Returns:
        Dictionary of housekeeping results by component
    """
    housekeeping_results = {}
    logger.info("Running housekeeping phases...")
    
    # Run housekeeping for all components in reverse order
    for component_name, component in reversed(list(components.items())):
        try:
            logger.info(f"Running {component_name} housekeeping phase...")
            result = component.housekeep()
            housekeeping_results[component_name] = result
            logger.info(f"Completed {component_name} housekeeping phase")
        except Exception as e:
            logger.error(f"Error in {component_name} housekeeping: {str(e)}")
            housekeeping_results[component_name] = {"error": str(e)}
    
    return housekeeping_results


def run_workflow(args: argparse.Namespace, logger: logging.Logger) -> int:
    """
    Run the end-to-end workflow with proper error handling.

    Args:
        args: Parsed command line arguments
        logger: Logger instance

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    components = {}  # Store initialized components
    
    try:
        # Step 1: Set up S3 component
        logger.info("Setting up S3 component...")
        s3_component, s3_discovery = setup_s3_component(args, logger)
        components['s3'] = s3_component
        
        # Step 2: Set up OpenShift component
        if not args.skip_iso:
            logger.info("Setting up OpenShift component...")
            openshift_component, openshift_discovery = setup_openshift_component(args, s3_component, logger)
            components['openshift'] = openshift_component
        
        # Step 3: Set up iSCSI component
        if not args.skip_iscsi:
            logger.info("Setting up iSCSI component...")
            iscsi_component, iscsi_discovery = setup_iscsi_component(args, logger)
            components['iscsi'] = iscsi_component
        
        # Step 4: Set up R630 component
        if not args.skip_r630:
            logger.info("Setting up R630 component...")
            r630_component, r630_discovery = setup_r630_component(args, logger)
            components['r630'] = r630_component
        
        # Process phase for S3
        s3_process_result = process_s3_component(s3_component, logger)
        
        # Process phase for OpenShift component
        if not args.skip_iso:
            openshift_process_result = process_openshift_component(openshift_component, logger)
        
        # Process phase for iSCSI component
        if not args.skip_iscsi:
            iscsi_process_result = process_iscsi_component(iscsi_component, logger)
        
        # Process phase for R630 component
        if not args.skip_r630 and not args.skip_iscsi:
            r630_process_result = process_r630_component(
                r630_component, 
                iscsi_process_result, 
                args.truenas_ip, 
                logger
            )
        
        # Housekeeping phases for all components
        housekeeping_results = run_housekeeping_phases(components, logger)
        
        # Final summary
        logger.info("Workflow completed successfully!")
        logger.info(f"Server {args.hostname} (ID: {args.server_id}) configured for OpenShift {args.openshift_version}")
        
        if not args.skip_iso:
            logger.info(f"ISO generated at: {openshift_process_result.get('iso_path')}")
            
        if not args.skip_iscsi:
            logger.info(f"iSCSI target: {iscsi_process_result.get('target_name')}")
            
        if not args.skip_r630:
            logger.info("Server configured for iSCSI boot")
        
        return 0
        
    except Exception as e:
        logger.error(f"Workflow failed with error: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        
        # Run housekeeping for initialized components on failure
        if components:
            logger.info("Running housekeeping for initialized components after failure...")
            try:
                housekeeping_results = run_housekeeping_phases(components, logger)
            except Exception as he:
                logger.error(f"Error during failure cleanup: {str(he)}")
        
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
        logger.info("Starting end-to-end workflow for OpenShift deployment via iSCSI")
        return run_workflow(args, logger)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
