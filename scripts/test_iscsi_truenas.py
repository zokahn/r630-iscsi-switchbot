#!/usr/bin/env python3
"""
test_iscsi_truenas.py - Test ISCSIComponent with TrueNAS

This script tests the ISCSIComponent by connecting to a real TrueNAS instance
and performing discovery operations. Optionally, it can create and clean up
a test zvol to verify the full functionality.
"""

import os
import sys
import logging
import argparse
import getpass
from pprint import pformat

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components
from framework.components import ISCSIComponent

def setup_logging(verbose=False):
    """Set up logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("iscsi-test")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test ISCSIComponent with TrueNAS")
    
    # TrueNAS connection configuration
    parser.add_argument("--truenas-ip", required=True, help="TrueNAS IP address")
    parser.add_argument("--api-key", help="TrueNAS API key (if not provided, will prompt)")
    
    # Test configuration
    parser.add_argument("--server-id", default="test01", help="Server ID for test zvol")
    parser.add_argument("--hostname", default="test-server", help="Hostname for test zvol")
    parser.add_argument("--openshift-version", default="4.14.0", help="OpenShift version for test zvol")
    parser.add_argument("--zvol-size", default="1G", help="Size of test zvol")
    parser.add_argument("--zfs-pool", default="test", help="ZFS pool name")
    
    # Test actions
    parser.add_argument("--create-test-zvol", action="store_true", help="Create a test zvol")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test resources")
    parser.add_argument("--discover-only", action="store_true", help="Only perform discovery")
    
    # General options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    # Get API key if not provided
    api_key = args.api_key
    if not api_key:
        api_key = getpass.getpass("Enter TrueNAS API key: ")
    
    # Configure ISCSIComponent
    iscsi_config = {
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
    
    logger.info(f"Initializing ISCSIComponent for TrueNAS at {args.truenas_ip}")
    iscsi_component = ISCSIComponent(iscsi_config, logger)
    
    # Discovery phase
    logger.info("Starting discovery phase...")
    try:
        discovery_results = iscsi_component.discover()
        
        # Display discovery results
        logger.info("Discovery completed:")
        logger.info(f"- TrueNAS connectivity: {discovery_results.get('connectivity', False)}")
        logger.info(f"- iSCSI service running: {discovery_results.get('iscsi_service', False)}")
        
        # Display pools
        pools = discovery_results.get('pools', [])
        if pools:
            logger.info(f"Found {len(pools)} storage pools:")
            for pool in pools:
                pool_name = pool.get('name')
                free_bytes = pool.get('free', 0)
                free_gb = free_bytes / (1024**3)
                logger.info(f"  - {pool_name} ({free_gb:.1f} GB free)")
        else:
            logger.warning("No storage pools found")
        
        # Display existing zvols
        zvols = discovery_results.get('zvols', [])
        if zvols:
            logger.info(f"Found {len(zvols)} existing zvols:")
            for zvol in zvols:
                zvol_name = zvol.get('name')
                zvol_size = zvol.get('volsize', {}).get('parsed', 0)
                zvol_size_gb = zvol_size / (1024**3)
                logger.info(f"  - {zvol_name} ({zvol_size_gb:.1f} GB)")
        else:
            logger.info("No existing zvols found")
        
        # Display existing targets
        targets = discovery_results.get('targets', [])
        if targets:
            logger.info(f"Found {len(targets)} existing iSCSI targets:")
            for target in targets:
                target_id = target.get('id')
                target_name = target.get('name')
                logger.info(f"  - {target_name} (ID: {target_id})")
        else:
            logger.info("No existing iSCSI targets found")
        
        # Check if connectivity failed
        if not discovery_results.get('connectivity', False):
            logger.error("TrueNAS connectivity failed - cannot proceed with tests")
            if 'connection_error' in discovery_results:
                logger.error(f"Error: {discovery_results['connection_error']}")
            return 1
        
        # Check storage capacity
        storage_capacity = discovery_results.get('storage_capacity', {})
        if storage_capacity:
            if 'error' in storage_capacity:
                logger.error(f"Storage capacity check failed: {storage_capacity['error']}")
            elif not storage_capacity.get('found', True):
                logger.error(f"ZFS pool '{args.zfs_pool}' not found")
            elif 'sufficient' in storage_capacity:
                if storage_capacity['sufficient']:
                    logger.info(f"Storage capacity is sufficient for test zvol")
                else:
                    logger.warning(f"Storage capacity may be insufficient for test zvol")
                    free_gb = storage_capacity.get('free_bytes', 0) / (1024**3)
                    required_gb = storage_capacity.get('required_bytes', 0) / (1024**3)
                    logger.warning(f"  Required: {required_gb:.1f} GB, Available: {free_gb:.1f} GB")
        
        # Stop here if only discovery requested
        if args.discover_only:
            logger.info("Discovery-only mode, skipping processing phase")
            return 0
        
        # Processing phase - create test zvol
        if args.create_test_zvol:
            logger.info("Starting processing phase to create test zvol...")
            try:
                processing_results = iscsi_component.process()
                
                logger.info("Processing results:")
                logger.info(f"- Zvol created: {processing_results.get('zvol_created', False)}")
                logger.info(f"- Target created: {processing_results.get('target_created', False)}")
                logger.info(f"- Extent created: {processing_results.get('extent_created', False)}")
                logger.info(f"- Association created: {processing_results.get('association_created', False)}")
                
                if processing_results.get('target_id'):
                    logger.info(f"- Target ID: {processing_results.get('target_id')}")
                if processing_results.get('extent_id'):
                    logger.info(f"- Extent ID: {processing_results.get('extent_id')}")
                
                # Display error messages if any component failed
                for component in ['zvol', 'target', 'extent', 'association']:
                    error_key = f"{component}_error"
                    if error_key in processing_results:
                        logger.error(f"{component.capitalize()} creation error: {processing_results[error_key]}")
                
                # Housekeeping phase - verify and clean up
                if args.cleanup:
                    logger.info("Starting housekeeping phase...")
                    housekeeping_results = iscsi_component.housekeep()
                    
                    logger.info("Housekeeping results:")
                    logger.info(f"- Resources verified: {housekeeping_results.get('resources_verified', False)}")
                    logger.info(f"- Unused resources found: {housekeeping_results.get('unused_resources_found', 0)}")
                    logger.info(f"- Unused resources cleaned: {housekeeping_results.get('unused_resources_cleaned', 0)}")
                    
                    # Display warnings if any
                    warnings = housekeeping_results.get('warnings', [])
                    if warnings:
                        logger.warning(f"Housekeeping warnings:")
                        for warning in warnings:
                            logger.warning(f"  - {warning}")
            
            except Exception as e:
                logger.error(f"Error during testing: {str(e)}")
                return 1
    
    except Exception as e:
        logger.error(f"Error during discovery: {str(e)}")
        return 1
    
    logger.info("TrueNAS iSCSI component test completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
