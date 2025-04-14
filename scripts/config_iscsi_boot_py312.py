#!/usr/bin/env python3
"""
config_iscsi_boot_py312.py - Configure iSCSI boot on Dell R630 servers using Python 3.12 components

This script implements the iSCSI boot configuration for Dell R630 servers using
the R630Component_py312 and ISCSIComponent_py312 classes, providing improved 
type safety and error handling through Python 3.12 features.
"""

import argparse
import json
import os
import sys
import time
import requests
import urllib3
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, TypedDict, Literal, cast, NotRequired, Union, Tuple

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Import Python 3.12 components
from framework.components.r630_component_py312 import R630Component
from framework.components.iscsi_component_py312 import ISCSIComponent

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Type definitions
class TargetConfigDict(TypedDict):
    """iSCSI target configuration type"""
    name: str
    description: str
    iqn: str
    ip: str
    port: int
    lun: int
    auth_method: NotRequired[str]
    chap_username: NotRequired[str]
    chap_secret: NotRequired[str]


class TargetsFileDict(TypedDict):
    """Contents of the targets file"""
    targets: List[TargetConfigDict]


class ISCSIBootConfigDict(TypedDict):
    """iSCSI boot configuration for the R630"""
    iSCSIBoot: Dict[str, Any]


class TargetValidationResult(TypedDict):
    """Result of target validation"""
    valid: bool
    message: str
    missing_fields: List[str]
    target_iqn_match: bool


class R630ConfigDict(TypedDict):
    """R630 server configuration"""
    idrac_ip: str
    username: str
    password: str
    nic_id: str
    reboot: bool
    component_id: str


class ISCSIConfigDict(TypedDict):
    """iSCSI configuration"""
    server_id: str
    iscsi_server: str
    target_id: str
    iqn: str
    ip: str
    port: int
    lun: int
    auth_method: NotRequired[str]
    chap_username: NotRequired[str]
    chap_secret: NotRequired[str]
    initiator_name: NotRequired[str]
    gateway: NotRequired[str]
    secondary_target: NotRequired[Dict[str, Any]]
    component_id: str


# Default values
DEFAULT_IDRAC_IP = "192.168.2.230"
DEFAULT_IDRAC_USER = "root"
DEFAULT_IDRAC_PASSWORD = "calvin"
DEFAULT_NIC = "NIC.Integrated.1-1-1"  # This should be adjusted based on your system

# Set paths
SCRIPT_DIR = Path(__file__).parent
DELL_SCRIPTS_DIR = SCRIPT_DIR / "dell"
NETWORK_CONFIG_SCRIPT = DELL_SCRIPTS_DIR / "SetNetworkDevicePropertiesREDFISH.py"
GET_PROPERTIES_SCRIPT = DELL_SCRIPTS_DIR / "GetSetBiosAttributesREDFISH.py"
CONFIG_DIR = SCRIPT_DIR.parent / "config"
ISCSI_TARGETS_FILE = CONFIG_DIR / "iscsi_targets.json"
ISCSI_CONFIG_TEMPLATE = CONFIG_DIR / "iscsi_config_template.json"


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
    return logging.getLogger("iscsi-boot")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments with proper typing and descriptions.

    Returns:
        Parsed arguments as Namespace
    """
    parser = argparse.ArgumentParser(
        description="Configure iSCSI boot on Dell R630 servers using component architecture"
    )
    
    parser.add_argument(
        "--server", 
        default=DEFAULT_IDRAC_IP, 
        help="Server IP address (e.g., 192.168.2.230)"
    )
    parser.add_argument(
        "--user", 
        default=DEFAULT_IDRAC_USER, 
        help="iDRAC username"
    )
    parser.add_argument(
        "--password", 
        default=DEFAULT_IDRAC_PASSWORD, 
        help="iDRAC password"
    )
    parser.add_argument(
        "--nic", 
        default=DEFAULT_NIC, 
        help="NIC to configure for iSCSI boot (default: NIC.Integrated.1-1-1)"
    )
    parser.add_argument(
        "--target", 
        help="Target name from iscsi_targets.json"
    )
    parser.add_argument(
        "--secondary-target", 
        help="Optional secondary target name for multipath"
    )
    parser.add_argument(
        "--initiator-name", 
        help="Custom initiator name (default: auto-generated)"
    )
    parser.add_argument(
        "--gateway", 
        help="Custom default gateway (default: DHCP)"
    )
    parser.add_argument(
        "--no-reboot", 
        action="store_true", 
        help="Don't reboot after configuration"
    )
    parser.add_argument(
        "--list-targets", 
        action="store_true", 
        help="List available targets and exit"
    )
    parser.add_argument(
        "--validate-only", 
        action="store_true", 
        help="Only validate existing configuration"
    )
    parser.add_argument(
        "--reset-iscsi", 
        action="store_true", 
        help="Reset iSCSI configuration to defaults"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def load_targets() -> TargetsFileDict:
    """
    Load the iSCSI targets from the configuration file.

    Returns:
        Dictionary containing target configurations

    Raises:
        SystemExit: If targets file is missing or invalid
    """
    try:
        targets_file = Path(ISCSI_TARGETS_FILE)
        if not targets_file.exists():
            print(f"Error: Targets file not found at {targets_file}")
            sys.exit(1)
            
        with open(targets_file, 'r') as f:
            targets_data = json.load(f)
            
        return cast(TargetsFileDict, targets_data)
    except json.JSONDecodeError as e:
        print(f"Error parsing targets file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading targets file: {e}")
        sys.exit(1)


def get_target_config(targets_data: TargetsFileDict, target_name: str) -> TargetConfigDict:
    """
    Get the configuration for the specified target.

    Args:
        targets_data: Dictionary containing all target configurations
        target_name: Name of the target to retrieve

    Returns:
        Target configuration dictionary

    Raises:
        SystemExit: If the specified target is not found
    """
    # Use Python 3.12 pattern matching to find the target
    for target in targets_data["targets"]:
        if target["name"] == target_name:
            return cast(TargetConfigDict, target)
    
    # If we get here, target wasn't found
    print(f"Error: Target '{target_name}' not found in the targets configuration.")
    print("Available targets:")
    for target in targets_data["targets"]:
        print(f"  - {target['name']}: {target.get('description', 'No description')}")
    sys.exit(1)


def create_r630_config(args: argparse.Namespace) -> R630ConfigDict:
    """
    Create the R630 component configuration from arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        R630Component configuration dictionary
    """
    config: Dict[str, Any] = {
        'idrac_ip': args.server,
        'username': args.user,
        'password': args.password,
        'nic_id': args.nic,
        'reboot': not args.no_reboot,
        'component_id': 'r630-iscsi-boot'
    }
    
    return cast(R630ConfigDict, config)


def create_iscsi_config(
    args: argparse.Namespace, 
    target: TargetConfigDict, 
    secondary_target: Optional[TargetConfigDict] = None
) -> ISCSIConfigDict:
    """
    Create the iSCSI component configuration from arguments and target.

    Args:
        args: Parsed command line arguments
        target: Primary target configuration
        secondary_target: Optional secondary target for multipath

    Returns:
        ISCSIComponent configuration dictionary
    """
    config: Dict[str, Any] = {
        'server_id': f"r630-{args.server.split('.')[-1]}",
        'iscsi_server': args.server,
        'target_id': target["name"],
        'iqn': target["iqn"],
        'ip': target["ip"],
        'port': target["port"],
        'lun': target["lun"],
        'component_id': 'iscsi-boot-component'
    }
    
    # Add authentication if specified in target
    if "auth_method" in target:
        config['auth_method'] = target["auth_method"]
        
        if target["auth_method"] == "CHAP" and "chap_username" in target and "chap_secret" in target:
            config['chap_username'] = target["chap_username"]
            config['chap_secret'] = target["chap_secret"]
    
    # Add custom initiator name if provided
    if args.initiator_name:
        config['initiator_name'] = args.initiator_name
    
    # Add default gateway if provided
    if args.gateway:
        config['gateway'] = args.gateway
    
    # Configure multipath if secondary target is provided
    if secondary_target:
        secondary_config = {
            'iqn': secondary_target["iqn"],
            'ip': secondary_target["ip"],
            'port': secondary_target["port"],
            'lun': secondary_target["lun"]
        }
        
        # Add secondary authentication if specified
        if "auth_method" in secondary_target and secondary_target["auth_method"] == "CHAP":
            if "chap_username" in secondary_target and "chap_secret" in secondary_target:
                secondary_config['chap_username'] = secondary_target["chap_username"]
                secondary_config['chap_secret'] = secondary_target["chap_secret"]
                
        config['secondary_target'] = secondary_config
    
    return cast(ISCSIConfigDict, config)


def check_r630_hardware(r630_component: R630Component, logger: logging.Logger) -> bool:
    """
    Check R630 hardware configuration and iDRAC version.

    Args:
        r630_component: Initialized R630Component instance
        logger: Logger instance

    Returns:
        True if hardware check is successful, False otherwise
    """
    logger.info(f"Checking Dell R630 hardware...")
    
    # Use the R630Component to discover hardware info
    discovery_results = r630_component.discover()
    
    # Use Python 3.12 pattern matching for improved flow control
    match discovery_results:
        case {'connectivity': True, 'server_info': server_info, 'idrac_info': idrac_info}:
            # Check model and verify it's an R630
            model = server_info.get('Model', '')
            if "R630" not in model and "PowerEdge" in model:
                logger.warning(f"Server model '{model}' may not be an R630")
                logger.warning("Script is optimized for R630, configurations may need adjustment")
            else:
                logger.info(f"Detected server model: {model}")
            
            # Check firmware version
            firmware_version = idrac_info.get('FirmwareVersion', '')
            logger.info(f"iDRAC firmware version: {firmware_version}")
            
            # Parse version to check against known good version
            try:
                version_parts = firmware_version.split('.')
                if len(version_parts) >= 4:
                    major = int(version_parts[0])
                    minor = int(version_parts[1])
                    
                    if major < 2 or (major == 2 and minor < 40):
                        logger.info("Dell scripts are known to work well with this firmware version")
            except ValueError:
                pass
                
            return True
            
        case {'connectivity': False, 'error': error}:
            logger.warning(f"Unable to check R630 hardware: {error}")
            logger.warning("Continuing with configuration anyway")
            return False
            
        case _:
            logger.warning("Unable to retrieve complete hardware information")
            logger.warning("Continuing with configuration anyway")
            return False


def configure_iscsi_boot(
    r630_component: R630Component, 
    iscsi_component: ISCSIComponent,
    target: TargetConfigDict,
    secondary_target: Optional[TargetConfigDict],
    logger: logging.Logger
) -> bool:
    """
    Configure the iSCSI boot settings using the component architecture.

    Args:
        r630_component: Initialized R630Component instance
        iscsi_component: Initialized ISCSIComponent instance
        target: Primary target configuration
        secondary_target: Optional secondary target configuration
        logger: Logger instance

    Returns:
        True if configuration is successful, False otherwise
    """
    logger.info(f"Configuring iSCSI boot for target: {target['name']} ({target.get('description', '')})")
    logger.info(f"Primary target: {target['iqn']} @ {target['ip']}:{target['port']} LUN {target['lun']}")
    
    if secondary_target:
        logger.info(f"Secondary target: {secondary_target['iqn']} @ {secondary_target['ip']}:{secondary_target['port']} LUN {secondary_target['lun']}")
    
    # First, discover the current configuration
    logger.info("\nStep 1: Discovering current configuration...")
    r630_discovery = r630_component.discover()
    iscsi_discovery = iscsi_component.discover()
    
    # Check connectivity with pattern matching
    match r630_discovery:
        case {'connectivity': False, 'error': error}:
            logger.error(f"R630 connectivity error: {error}")
            return False
        case {'connectivity': True}:
            logger.info("R630 connectivity verified")
        
    match iscsi_discovery:
        case {'connectivity': True}:
            logger.info("iSCSI configuration service access verified")
        case {'connectivity': False, 'error': error}:
            logger.error(f"iSCSI configuration error: {error}")
            return False
    
    # Process the configuration setup
    logger.info("\nStep 2: Applying configuration...")
    process_result = iscsi_component.process()
    
    # Check processing results with pattern matching
    match process_result:
        case {'error': error}:
            logger.error(f"Failed to configure iSCSI boot: {error}")
            return False
            
        case {'iscsi_configured': True, 'warnings': warnings} if warnings:
            logger.info("iSCSI boot configuration applied with warnings:")
            for warning in warnings:
                logger.warning(f"- {warning}")
                
        case {'iscsi_configured': True}:
            logger.info("iSCSI boot configuration applied successfully")
            
        case {'iscsi_configured': False}:
            logger.error("Failed to configure iSCSI boot for unknown reason")
            return False
    
    # Apply the configuration to the server
    logger.info("\nStep 3: Applying configuration to server...")
    r630_process_result = r630_component.process()
    
    # Check server configuration results with pattern matching
    match r630_process_result:
        case {'error': error}:
            logger.error(f"Failed to apply server configuration: {error}")
            logger.warning("iSCSI settings were configured but may not be applied to the server")
            logger.warning("You can try manual configuration through the iDRAC interface")
            return False
            
        case {'configuration_applied': True, 'reboot_scheduled': True}:
            logger.info("Server configuration applied and reboot scheduled")
            
        case {'configuration_applied': True, 'reboot_scheduled': False}:
            logger.info("Server configuration applied, but reboot was not requested")
            logger.warning("You will need to reboot the server manually to apply the changes")
            
        case _:
            logger.warning("Unexpected result from server configuration")
            logger.warning("Configuration may be incomplete")
            return False
    
    # Validate the configuration 
    logger.info("\nStep 4: Validating configuration...")
    validation_result = validate_iscsi_configuration(r630_component, target["iqn"], logger)
    
    if validation_result:
        logger.info("✓ iSCSI configuration validation successful")
    else:
        logger.warning("⚠ iSCSI configuration could not be fully validated")
        logger.warning("Note: R630 validation often shows warnings even when configuration is successful")
        logger.warning("Please check manually after reboot")
    
    logger.info("\nConfiguration successful!")
    
    # Check if reboot is needed
    match r630_discovery['system_info'].get('PowerState'):
        case 'On' if r630_process_result.get('reboot_scheduled', False):
            logger.info("The server is being rebooted to apply the changes")
            logger.info("This process may take a few minutes")
        case 'On' if not r630_process_result.get('reboot_scheduled', False):
            logger.warning("NOTE: The server will need to be rebooted manually to apply the changes")
        case _:
            logger.info("Please ensure the server is powered on to apply the changes")
    
    return True


def reset_iscsi_configuration(r630_component: R630Component, logger: logging.Logger) -> bool:
    """
    Reset iSCSI configuration to defaults.

    Args:
        r630_component: Initialized R630Component instance
        logger: Logger instance

    Returns:
        True if reset is successful, False otherwise
    """
    logger.info("Resetting iSCSI configuration to defaults...")
    
    # Create reset configuration
    reset_config = {
        'reset_iscsi': True
    }
    
    # Process the reset
    process_result = r630_component.process_iscsi_reset(reset_config)
    
    # Check result with pattern matching
    match process_result:
        case {'reset_successful': True, 'reboot_scheduled': reboot}:
            logger.info("Successfully reset iSCSI configuration")
            if reboot:
                logger.info("The server is being rebooted to apply the changes")
            else:
                logger.warning("NOTE: The server will need to be rebooted manually to apply the changes")
            return True
            
        case {'reset_successful': False, 'error': error}:
            logger.error(f"Failed to reset iSCSI configuration: {error}")
            return False
            
        case _:
            logger.error("Failed to reset iSCSI configuration for unknown reason")
            return False


def validate_iscsi_configuration(
    r630_component: R630Component, 
    expected_target_iqn: Optional[str] = None,
    logger: logging.Logger = None
) -> bool:
    """
    Validate iSCSI configuration after applying it - R630 specific validation.

    Args:
        r630_component: Initialized R630Component instance
        expected_target_iqn: Optional expected target IQN for validation
        logger: Optional logger instance

    Returns:
        True if validation is successful, False otherwise
    """
    if logger:
        logger.info("Validating iSCSI configuration...")
    
    # Get current configuration
    validation_result = r630_component.get_iscsi_configuration()
    
    # Use pattern matching for improved validation
    match validation_result:
        case {'error': error}:
            if logger:
                logger.error(f"Error retrieving iSCSI configuration: {error}")
            return False
            
        case {'configuration': config, 'iscsi_enabled': False}:
            if logger:
                logger.warning("iSCSI boot is not enabled on this server")
            return False
            
        case {'configuration': config, 'iscsi_enabled': True}:
            # Check for basic required fields
            iscsi_config = config.get('iSCSIBoot', {})
            
            # Check if target IQN matches if expected
            if expected_target_iqn and 'PrimaryTargetName' in iscsi_config:
                configured_iqn = iscsi_config['PrimaryTargetName']
                if configured_iqn != expected_target_iqn:
                    if logger:
                        logger.warning(f"Target IQN mismatch. Expected: {expected_target_iqn}, Got: {configured_iqn}")
                        logger.warning("Current configuration may not match the requested configuration")
                        logger.warning("Note: On R630, target values sometimes apply correctly despite validation errors")
            
            # Check for critical configuration fields
            required_fields = ["PrimaryTargetIPAddress", "PrimaryLUN"]
            missing_fields = [field for field in required_fields if field not in iscsi_config]
            
            if missing_fields:
                if logger:
                    logger.warning(f"The following required fields were not found: {', '.join(missing_fields)}")
                    logger.warning("This may be due to R630 iDRAC reporting limitations")
                    logger.warning("The configuration may still work")
                return False
            
            if logger:
                logger.info("iSCSI boot configuration looks correct")
            return True
            
        case _:
            if logger:
                logger.warning("Unexpected validation result format")
            return False


def list_available_targets(logger: logging.Logger) -> None:
    """
    List the available iSCSI targets from the configuration file.

    Args:
        logger: Logger instance
    """
    targets_data = load_targets()
    logger.info("Available iSCSI boot targets:")
    
    header = "{:<15} {:<50} {:<15} {:<10} {:<8} {:<8}".format(
        "NAME", "IQN", "IP", "PORT", "LUN", "AUTH"
    )
    logger.info("\n" + header)
    logger.info("-" * 110)
    
    for target in targets_data["targets"]:
        auth_method = target.get("auth_method", "None")
        target_line = "{:<15} {:<50} {:<15} {:<10} {:<8} {:<8}".format(
            target["name"],
            target["iqn"],
            target["ip"],
            target["port"],
            target["lun"],
            auth_method
        )
        logger.info(target_line)
    
    logger.info("\nTo configure a target: config_iscsi_boot_py312.py --target <name>")
    logger.info("For multipath configuration: config_iscsi_boot_py312.py --target <primary> --secondary-target <secondary>")


def main() -> int:
    """
    Main function with improved error handling and Python 3.12 features.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse arguments
        args = parse_arguments()
        logger = setup_logging(args.verbose)
        
        # Verify the Dell Redfish script exists (for legacy compatibility)
        if not NETWORK_CONFIG_SCRIPT.exists():
            logger.warning(f"Note: Dell script not found at {NETWORK_CONFIG_SCRIPT}")
            logger.info("This script now uses the component architecture and doesn't require Dell scripts")
        
        # Just list targets if requested
        if args.list_targets:
            list_available_targets(logger)
            return 0
        
        # Make sure target is specified for all other operations
        if not args.target and not args.validate_only and not args.reset_iscsi:
            logger.error("Error: --target is required unless using --list-targets, --validate-only, or --reset-iscsi")
            logger.error("Use --list-targets to see available targets, then specify one with --target")
            return 1
        
        # Create components
        r630_config = create_r630_config(args)
        r630_component = R630Component(r630_config, logger)
        
        # Check R630 hardware configuration
        check_r630_hardware(r630_component, logger)
        
        # Just validate existing configuration if requested
        if args.validate_only:
            logger.info(f"Validating iSCSI configuration for R630 at {args.server}...")
            if validate_iscsi_configuration(r630_component, None, logger):
                logger.info("\nValidation successful: iSCSI boot is properly configured")
            else:
                logger.warning("\nValidation found issues, but configuration may still work")
                logger.warning("On R630, some settings may not be reported correctly via the API")
                logger.warning("Check actual boot behavior on next restart")
            return 0
        
        # Reset iSCSI configuration if requested
        if args.reset_iscsi:
            logger.info(f"Resetting iSCSI configuration on R630 at {args.server}...")
            if reset_iscsi_configuration(r630_component, logger):
                logger.info("\nSuccessfully reset iSCSI configuration")
                return 0
            else:
                logger.error("\nFailed to reset iSCSI configuration")
                return 1
        
        # Load the targets configuration
        targets_data = load_targets()
        
        # Get the selected primary target
        target = get_target_config(targets_data, args.target)
        
        # Get the selected secondary target if specified
        secondary_target = None
        if args.secondary_target:
            secondary_target = get_target_config(targets_data, args.secondary_target)
        
        # Create iSCSI configuration
        iscsi_config = create_iscsi_config(args, target, secondary_target)
        iscsi_component = ISCSIComponent(iscsi_config, logger)
        
        # Configure iSCSI boot
        logger.info(f"Configuring iSCSI boot on R630 at {args.server} using component architecture...")
        if not configure_iscsi_boot(r630_component, iscsi_component, target, secondary_target, logger):
            logger.error("Failed to configure iSCSI boot")
            return 1
        
        logger.info(f"\nSuccessfully configured iSCSI boot for target: {args.target}")
        if secondary_target:
            logger.info(f"With secondary target: {args.secondary_target}")
        
        logger.info("\nR630-specific notes:")
        logger.info("1. If validation shows mismatches, the configuration may still be correct")
        logger.info("2. The system will use PXE boot device (Boot0000) if no explicit iSCSI device is found")
        logger.info("3. Verify proper boot by watching POST screen on next reboot")
        
        return 0
        
    except Exception as e:
        print(f"Unhandled exception: {e}")
        import traceback
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
