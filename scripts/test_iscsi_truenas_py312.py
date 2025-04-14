#!/usr/bin/env python3
"""
test_iscsi_truenas_py312.py - Test ISCSIComponent with TrueNAS

This script tests the ISCSIComponent by connecting to a real TrueNAS instance
and performing discovery operations. Optionally, it can create and clean up
a test zvol to verify the full functionality.

Python 3.12 version with enhanced typing and features.
"""

import os
import sys
import logging
import argparse
import getpass
from pprint import pformat
from pathlib import Path
from typing import Dict, Any, Optional, List, TypedDict, Literal, cast, NotRequired, Set

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import Python 3.12 components
from framework.components.iscsi_component_py312 import ISCSIComponent


# Type definitions
class ISCSIConfigDict(TypedDict):
    """ISCSIComponent configuration type"""
    truenas_ip: str
    api_key: str
    server_id: str
    hostname: str
    openshift_version: str
    zvol_size: str
    zfs_pool: str
    dry_run: bool
    discover_only: bool


class StorageCapacityInfo(TypedDict):
    """Storage capacity information type"""
    found: bool
    sufficient: NotRequired[bool]
    free_bytes: NotRequired[int]
    required_bytes: NotRequired[int]
    error: NotRequired[str]


class ZvolInfo(TypedDict):
    """ZFS volume information"""
    name: str
    volsize: Dict[str, Any]  # Contains 'parsed' which is the size in bytes


class PoolInfo(TypedDict):
    """ZFS pool information"""
    name: str
    free: int  # Free space in bytes


class TargetInfo(TypedDict):
    """iSCSI target information"""
    id: int
    name: str


class ISCSIDiscoveryResult(TypedDict):
    """ISCSIComponent discovery phase result type"""
    connectivity: bool
    iscsi_service: bool
    connection_error: NotRequired[str]
    storage_capacity: NotRequired[StorageCapacityInfo]
    pools: NotRequired[List[PoolInfo]]
    zvols: NotRequired[List[ZvolInfo]]
    targets: NotRequired[List[TargetInfo]]


class ISCSIProcessResult(TypedDict):
    """ISCSIComponent process phase result type"""
    zvol_created: bool
    target_created: bool
    extent_created: bool
    association_created: bool
    target_id: NotRequired[int]
    extent_id: NotRequired[int]
    zvol_error: NotRequired[str]
    target_error: NotRequired[str]
    extent_error: NotRequired[str]
    association_error: NotRequired[str]


class ISCSIHousekeepResult(TypedDict):
    """ISCSIComponent housekeep phase result type"""
    resources_verified: bool
    unused_resources_found: int
    unused_resources_cleaned: int
    warnings: List[str]


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        verbose: Whether to use DEBUG level logging

    Returns:
        Configured logger instance
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("iscsi-test")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments as Namespace
    """
    parser = argparse.ArgumentParser(
        description="Test ISCSIComponent_py312 with TrueNAS"
    )
    
    # TrueNAS connection configuration
    parser.add_argument(
        "--truenas-ip", 
        required=True, 
        help="TrueNAS IP address"
    )
    parser.add_argument(
        "--api-key", 
        help="TrueNAS API key (if not provided, will prompt)"
    )
    
    # Test configuration
    parser.add_argument(
        "--server-id", 
        default="test01", 
        help="Server ID for test zvol"
    )
    parser.add_argument(
        "--hostname", 
        default="test-server", 
        help="Hostname for test zvol"
    )
    parser.add_argument(
        "--openshift-version", 
        default="4.14.0", 
        help="OpenShift version for test zvol"
    )
    parser.add_argument(
        "--zvol-size", 
        default="1G", 
        help="Size of test zvol"
    )
    parser.add_argument(
        "--zfs-pool", 
        default="test", 
        help="ZFS pool name"
    )
    
    # Test actions
    parser.add_argument(
        "--create-test-zvol", 
        action="store_true", 
        help="Create a test zvol"
    )
    parser.add_argument(
        "--cleanup", 
        action="store_true", 
        help="Clean up test resources"
    )
    parser.add_argument(
        "--discover-only", 
        action="store_true", 
        help="Only perform discovery"
    )
    
    # General options
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Dry run (no changes)"
    )
    
    return parser.parse_args()


def create_iscsi_config(args: argparse.Namespace, api_key: str) -> ISCSIConfigDict:
    """
    Create ISCSI component configuration from command line arguments.
    
    Args:
        args: Parsed command line arguments
        api_key: TrueNAS API key
        
    Returns:
        ISCSIConfigDict: ISCSIComponent configuration
    """
    # Create the configuration dictionary
    base_config: Dict[str, Any] = {
        'truenas_ip': args.truenas_ip,
        'api_key': api_key,
        'server_id': args.server_id,
        'hostname': args.hostname,
        'openshift_version': args.openshift_version,
        'zvol_size': args.zvol_size,
        'zfs_pool': args.zfs_pool,
        'dry_run': args.dry_run,
        'discover_only': args.discover_only
    }
    
    # Return with proper typing
    return cast(ISCSIConfigDict, base_config)


def display_discovery_results(discovery_results: ISCSIDiscoveryResult, args: argparse.Namespace, logger: logging.Logger) -> None:
    """
    Display discovery results in a structured way.
    
    Args:
        discovery_results: Results from ISCSIComponent discovery
        args: Command line arguments
        logger: Logger instance
    """
    # Display basic connectivity results
    logger.info("Discovery completed:")
    logger.info(f"- TrueNAS connectivity: {discovery_results.get('connectivity', False)}")
    logger.info(f"- iSCSI service running: {discovery_results.get('iscsi_service', False)}")
    
    # Check if connectivity failed
    if not discovery_results.get('connectivity', False):
        if error := discovery_results.get('connection_error'):
            logger.error(f"TrueNAS connectivity failed: {error}")
        else:
            logger.error("TrueNAS connectivity failed - no specific error message available")
        return
    
    # Display pools using pattern matching
    if pools := discovery_results.get('pools', []):
        logger.info(f"Found {len(pools)} storage pools:")
        for pool in pools:
            # Use Python 3.12 pattern matching to handle different pool structures
            match pool:
                case {'name': name, 'free': free_bytes}:
                    free_gb = free_bytes / (1024**3)
                    logger.info(f"  - {name} ({free_gb:.1f} GB free)")
                case {'name': name}:
                    logger.info(f"  - {name} (free space unknown)")
                case _:
                    logger.info(f"  - {pool}")
    else:
        logger.warning("No storage pools found")
    
    # Display existing zvols with pattern matching
    if zvols := discovery_results.get('zvols', []):
        logger.info(f"Found {len(zvols)} existing zvols:")
        for zvol in zvols:
            # Use pattern matching to handle different zvol structures
            match zvol:
                case {'name': name, 'volsize': {'parsed': size}}:
                    size_gb = size / (1024**3)
                    logger.info(f"  - {name} ({size_gb:.1f} GB)")
                case {'name': name}:
                    logger.info(f"  - {name} (size unknown)")
                case _:
                    logger.info(f"  - {zvol}")
    else:
        logger.info("No existing zvols found")
    
    # Display existing targets
    if targets := discovery_results.get('targets', []):
        logger.info(f"Found {len(targets)} existing iSCSI targets:")
        for target in targets:
            # Use pattern matching for target info
            match target:
                case {'id': target_id, 'name': name}:
                    logger.info(f"  - {name} (ID: {target_id})")
                case {'name': name}:
                    logger.info(f"  - {name} (ID unknown)")
                case _:
                    logger.info(f"  - {target}")
    else:
        logger.info("No existing iSCSI targets found")
    
    # Check storage capacity using pattern matching
    if storage_capacity := discovery_results.get('storage_capacity'):
        match storage_capacity:
            case {'error': error}:
                logger.error(f"Storage capacity check failed: {error}")
            case {'found': False}:
                logger.error(f"ZFS pool '{args.zfs_pool}' not found")
            case {'sufficient': True}:
                logger.info(f"Storage capacity is sufficient for test zvol")
            case {'sufficient': False, 'free_bytes': free, 'required_bytes': required}:
                logger.warning(f"Storage capacity may be insufficient for test zvol")
                free_gb = free / (1024**3)
                required_gb = required / (1024**3)
                logger.warning(f"  Required: {required_gb:.1f} GB, Available: {free_gb:.1f} GB")
            case _:
                logger.warning(f"Storage capacity check returned unexpected format: {storage_capacity}")


def display_processing_results(processing_results: ISCSIProcessResult, logger: logging.Logger) -> None:
    """
    Display processing results in a structured way.
    
    Args:
        processing_results: Results from ISCSIComponent processing
        logger: Logger instance
    """
    # Main processing results
    logger.info("Processing results:")
    logger.info(f"- Zvol created: {processing_results.get('zvol_created', False)}")
    logger.info(f"- Target created: {processing_results.get('target_created', False)}")
    logger.info(f"- Extent created: {processing_results.get('extent_created', False)}")
    logger.info(f"- Association created: {processing_results.get('association_created', False)}")
    
    # Display IDs if available
    if target_id := processing_results.get('target_id'):
        logger.info(f"- Target ID: {target_id}")
    if extent_id := processing_results.get('extent_id'):
        logger.info(f"- Extent ID: {extent_id}")
    
    # Display error messages using pattern matching
    for component in ['zvol', 'target', 'extent', 'association']:
        error_key = f"{component}_error"
        if error := processing_results.get(error_key):
            logger.error(f"{component.capitalize()} creation error: {error}")


def display_housekeeping_results(housekeeping_results: ISCSIHousekeepResult, logger: logging.Logger) -> None:
    """
    Display housekeeping results in a structured way.
    
    Args:
        housekeeping_results: Results from ISCSIComponent housekeeping
        logger: Logger instance
    """
    logger.info("Housekeeping results:")
    logger.info(f"- Resources verified: {housekeeping_results.get('resources_verified', False)}")
    logger.info(f"- Unused resources found: {housekeeping_results.get('unused_resources_found', 0)}")
    logger.info(f"- Unused resources cleaned: {housekeeping_results.get('unused_resources_cleaned', 0)}")
    
    # Display warnings if any using pattern matching
    match housekeeping_results:
        case {'warnings': warnings} if warnings:
            logger.warning(f"Housekeeping warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        case _:
            pass  # No warnings


def main() -> int:
    """
    Main function with improved error handling and Python 3.12 features.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    try:
        # Get API key if not provided
        api_key: str
        if args.api_key:
            api_key = args.api_key
        else:
            api_key = getpass.getpass("Enter TrueNAS API key: ")
        
        # Configure ISCSIComponent
        iscsi_config = create_iscsi_config(args, api_key)
        
        logger.info(f"Initializing ISCSIComponent for TrueNAS at {args.truenas_ip}")
        iscsi_component = ISCSIComponent(iscsi_config, logger)
        
        # Discovery phase
        logger.info("Starting discovery phase...")
        discovery_results = cast(ISCSIDiscoveryResult, iscsi_component.discover())
        
        # Display discovery results
        display_discovery_results(discovery_results, args, logger)
        
        # Check connectivity result with pattern matching
        match discovery_results:
            case {'connectivity': False}:
                logger.error("TrueNAS connectivity failed - cannot proceed with tests")
                return 1
        
        # Stop here if only discovery requested
        if args.discover_only:
            logger.info("Discovery-only mode, skipping processing phase")
            return 0
        
        # Processing phase - create test zvol
        if args.create_test_zvol:
            logger.info("Starting processing phase to create test zvol...")
            try:
                processing_results = cast(ISCSIProcessResult, iscsi_component.process())
                
                # Display processing results
                display_processing_results(processing_results, logger)
                
                # Housekeeping phase - verify and clean up
                if args.cleanup:
                    logger.info("Starting housekeeping phase...")
                    housekeeping_results = cast(ISCSIHousekeepResult, iscsi_component.housekeep())
                    
                    # Display housekeeping results
                    display_housekeeping_results(housekeeping_results, logger)
            
            except Exception as e:
                logger.error(f"Error during testing: {str(e)}")
                return 1
    
    except Exception as e:
        logger.error(f"Error during discovery: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1
    
    logger.info("TrueNAS iSCSI component test completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
