#!/usr/bin/env python3
"""
reboot_server_component.py - Reboot Dell R630 servers using R630Component

This script uses the R630Component to reboot Dell PowerEdge R630 servers via the Redfish API.
It follows the discovery-processing-housekeeping pattern for better error handling.
"""

import os
import sys
import logging
import argparse
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
    return logging.getLogger("reboot-server")

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Reboot Dell R630 servers using component architecture")
    
    # Server configuration
    parser.add_argument("--server", default=DEFAULT_IDRAC_IP, help="Server IP address (e.g., 192.168.2.230)")
    parser.add_argument("--user", default=DEFAULT_IDRAC_USER, help="iDRAC username")
    parser.add_argument("--password", default=DEFAULT_IDRAC_PASSWORD, help="iDRAC password")
    parser.add_argument("--server-id", default="r630-01", help="Server ID for tracking")
    parser.add_argument("--hostname", default="r630-server", help="Server hostname")
    
    # Reboot options
    parser.add_argument("--force", action="store_true", help="Force reboot even if server is already off")
    parser.add_argument("--wait", action="store_true", help="Wait for reboot to complete")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds when waiting for reboot")
    
    # General options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no actual reboot)")
    
    return parser.parse_args()

def reboot_server(args: argparse.Namespace, logger: logging.Logger) -> bool:
    """
    Reboot the server using the R630Component
    
    Args:
        args: Command line arguments
        logger: Logger instance
        
    Returns:
        True if reboot was successful, False otherwise
    """
    try:
        # Configure R630Component
        r630_config = {
            'idrac_ip': args.server,
            'idrac_username': args.user,
            'idrac_password': args.password,
            'server_id': args.server_id,
            'hostname': args.hostname,
            'reboot_required': True,
            'wait_for_job_completion': args.wait,
            'job_wait_timeout': args.timeout,
            'dry_run': args.dry_run
        }
        
        logger.info(f"Initializing R630Component for server {args.server}...")
        r630_component = R630Component(r630_config, logger)
        
        # Discovery phase - Get server information and power state
        logger.info("Running discovery phase...")
        discovery_results = r630_component.discover()
        
        # Check connectivity
        if not discovery_results.get('connectivity', False):
            error_msg = discovery_results.get('connection_error', 'Unknown error')
            logger.error(f"Failed to connect to server: {error_msg}")
            return False
        
        # Check current power state
        power_state = discovery_results.get('power_state')
        logger.info(f"Current server power state: {power_state}")
        
        # Only proceed if server is on or --force is specified for off state
        if power_state == "Off" and not args.force:
            logger.info("Server is already powered off. Use --force to power on.")
            return True
        
        # Process phase - perform reboot
        logger.info(f"Running processing phase to {'power on' if power_state == 'Off' else 'reboot'} server...")
        process_results = r630_component.process()
        
        # Check if reboot was triggered
        if process_results.get('reboot_triggered', False):
            logger.info("Server reboot triggered successfully")
        else:
            logger.error("Failed to trigger server reboot")
            return False
        
        # Housekeeping phase - verify reboot and check status
        if args.wait:
            logger.info("Running housekeeping phase to verify reboot...")
            housekeep_results = r630_component.housekeep()
            
            # Check if job completed successfully
            job_completed = housekeep_results.get('job_completed', False)
            if job_completed:
                logger.info("Server reboot job completed successfully")
            else:
                logger.warning("Server reboot job did not complete within the timeout period")
                if 'warnings' in housekeep_results:
                    for warning in housekeep_results['warnings']:
                        logger.warning(f"Warning: {warning}")
                return job_completed
        
        return True
        
    except Exception as e:
        logger.error(f"Error rebooting server: {str(e)}")
        if logger.level == logging.DEBUG:
            import traceback
            logger.debug(traceback.format_exc())
        return False

def main() -> int:
    """
    Main function that runs the reboot
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    try:
        success = reboot_server(args, logger)
        
        if success:
            logger.info(f"Successfully {'initiated reboot' if not args.wait else 'rebooted'} server {args.server}")
            return 0
        else:
            logger.error(f"Failed to reboot server {args.server}")
            return 1
            
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
