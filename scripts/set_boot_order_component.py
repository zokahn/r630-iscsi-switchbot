#!/usr/bin/env python3
"""
set_boot_order_component.py - Set boot order on Dell R630 servers using R630Component

This script uses the R630Component to set the boot order on Dell PowerEdge R630 servers
via the Redfish API. It follows the discovery-processing-housekeeping pattern for better
error handling and standardized interfaces.
"""

import os
import sys
import logging
import argparse
import re
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Import components
from framework.components.r630_component import R630Component

# Default values
DEFAULT_IDRAC_IP = "192.168.2.230"
DEFAULT_IDRAC_USER = "root"
DEFAULT_IDRAC_PASSWORD = "calvin"

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger("set-boot-order")

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Set boot order on Dell R630 servers using component architecture")
    
    # Server configuration
    parser.add_argument("--server", default=DEFAULT_IDRAC_IP, help="Server IP address (e.g., 192.168.2.230)")
    parser.add_argument("--user", default=DEFAULT_IDRAC_USER, help="iDRAC username")
    parser.add_argument("--password", default=DEFAULT_IDRAC_PASSWORD, help="iDRAC password")
    parser.add_argument("--server-id", default="r630-01", help="Server ID for tracking")
    parser.add_argument("--hostname", default="r630-server", help="Server hostname")
    
    # Boot options
    parser.add_argument("--first-boot", required=True, help="First boot device (iscsi, cd, http, pxe, hdd)")
    parser.add_argument("--boot-mode", choices=["Uefi", "Bios"], help="Boot mode (Uefi or Bios)")
    parser.add_argument("--no-reboot", action="store_true", help="Don't reboot after setting boot order")
    
    # General options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no actual changes)")
    
    return parser.parse_args()

def find_boot_device_id(boot_devices: list, boot_type: str) -> str:
    """
    Find the boot device ID for the specified boot type
    
    Args:
        boot_devices: List of boot devices from R630Component discovery
        boot_type: Type of boot device to find (iscsi, cd, http, pxe, hdd)
        
    Returns:
        Boot device ID or None if not found
    """
    # Define keywords for different boot types
    boot_keywords = {
        "iscsi": ["iscsi", "scsi"],
        "hdd": ["hard drive", "hdd", "sata"],
        "pxe": ["pxe", "network"],
        "cd": ["cd", "dvd", "optical"],
        "usb": ["usb"],
        "bios": ["bios", "shell"],
        "virtualcd": ["virtual cd", "vcd", "virtual media"],
        "http": ["http", "uefinttp"]
    }
    
    boot_type = boot_type.lower()
    
    # Get the keywords for the requested boot type
    keywords = boot_keywords.get(boot_type, [boot_type])
    
    # Search for a matching boot device
    for device in boot_devices:
        device_name = device.get('name', '').lower()
        
        # Check if any of the keywords match
        if any(keyword in device_name for keyword in keywords):
            return device.get('id')
    
    # Special case for iSCSI - if no iSCSI device is found, look for a PXE device
    if boot_type == "iscsi":
        for device in boot_devices:
            device_name = device.get('name', '').lower()
            if any(keyword in device_name for keyword in boot_keywords.get("pxe", [])):
                return device.get('id')
    
    # If no device is found, return None
    return None

def set_boot_order(args: argparse.Namespace, logger: logging.Logger) -> bool:
    """
    Set the boot order using the R630Component
    
    Args:
        args: Command line arguments
        logger: Logger instance
        
    Returns:
        True if boot order was set successfully, False otherwise
    """
    try:
        # Configure R630Component
        r630_config = {
            'idrac_ip': args.server,
            'idrac_username': args.user,
            'idrac_password': args.password,
            'server_id': args.server_id,
            'hostname': args.hostname,
            'boot_devices': None,  # Will be set after discovery
            'bios_settings': {},   # Initialize empty, may be updated with boot mode
            'reboot_required': not args.no_reboot,
            'dry_run': args.dry_run
        }
        
        # Add BIOS settings if boot mode is specified
        if args.boot_mode:
            r630_config['bios_settings'] = {'BootMode': args.boot_mode}
        
        logger.info(f"Initializing R630Component for server {args.server}...")
        r630_component = R630Component(r630_config, logger)
        
        # Discovery phase - Get server information and current boot order
        logger.info("Running discovery phase...")
        discovery_results = r630_component.discover()
        
        # Check connectivity
        if not discovery_results.get('connectivity', False):
            error_msg = discovery_results.get('connection_error', 'Unknown error')
            logger.error(f"Failed to connect to server: {error_msg}")
            return False
        
        # Display current boot order
        current_boot_order = discovery_results.get('current_boot_order', [])
        logger.info(f"Current boot order: {current_boot_order}")
        
        # Get boot devices from discovery
        boot_devices = discovery_results.get('boot_devices', [])
        
        if not boot_devices:
            logger.error("No boot devices found during discovery")
            return False
        
        # Find the boot device ID for the specified boot type
        boot_device_id = find_boot_device_id(boot_devices, args.first_boot)
        
        if not boot_device_id:
            logger.error(f"Could not find a {args.first_boot} boot device in the current boot order")
            logger.error("Available boot devices:")
            for device in boot_devices:
                logger.error(f"  - {device.get('id')}: {device.get('name')}")
            return False
        
        logger.info(f"Found boot device for {args.first_boot}: {boot_device_id}")
        
        # Check current boot mode
        current_boot_mode = discovery_results.get('boot_mode')
        logger.info(f"Current boot mode: {current_boot_mode}")
        
        # Construct the new boot order with the specified device first, followed by others
        new_boot_order = [boot_device_id]
        
        # Add other boot devices to the boot order, preserving their relative order
        for device_id in current_boot_order:
            if device_id != boot_device_id:
                new_boot_order.append(device_id)
        
        # Update component configuration with new boot order
        r630_component.config['boot_devices'] = new_boot_order
        
        # Process phase - Set boot order
        logger.info("Running processing phase...")
        logger.info(f"Setting new boot order: {new_boot_order}")
        
        process_results = r630_component.process()
        
        # Check if boot order was changed
        if process_results.get('boot_order_changed', False):
            logger.info("Boot order changed successfully")
        else:
            if args.dry_run:
                logger.info("DRY RUN: Would have changed boot order")
            else:
                logger.error("Failed to change boot order")
                return False
        
        # Housekeeping phase - Verify changes
        if not args.dry_run:
            logger.info("Running housekeeping phase...")
            housekeep_results = r630_component.housekeep()
            
            # Check if changes were verified
            if housekeep_results.get('changes_verified', False):
                logger.info("Boot order changes verified successfully")
            else:
                logger.warning("Boot order changes could not be fully verified")
                if 'warnings' in housekeep_results:
                    for warning in housekeep_results['warnings']:
                        logger.warning(f"Warning: {warning}")
        
        # Status message based on reboot setting
        if args.no_reboot:
            logger.info("Boot order has been set. Changes will take effect on next reboot.")
        else:
            logger.info("Boot order has been set and server reboot initiated.")
            if args.dry_run:
                logger.info("DRY RUN: Would have rebooted the server")
        
        return True
        
    except Exception as e:
        logger.error(f"Error setting boot order: {str(e)}")
        if logger.level == logging.DEBUG:
            import traceback
            logger.debug(traceback.format_exc())
        return False

def main() -> int:
    """
    Main function that sets the boot order
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    try:
        success = set_boot_order(args, logger)
        
        if success:
            logger.info(f"Successfully set boot order on server {args.server}")
            return 0
        else:
            logger.error(f"Failed to set boot order on server {args.server}")
            return 1
            
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
