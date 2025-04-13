#!/usr/bin/env python3
# test_iscsi_redfish.py - Test script for enhanced iSCSI Redfish configuration

import argparse
import os
import sys
import json
import subprocess
from pathlib import Path

# Set paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
ISCSI_CONFIG_SCRIPT = SCRIPT_DIR / "config_iscsi_boot.py"
SWITCH_SCRIPT = SCRIPT_DIR / "switch_openshift.py"

# Default values
DEFAULT_IDRAC_IP = "192.168.2.230"
DEFAULT_IDRAC_USER = "root"
DEFAULT_IDRAC_PASSWORD = "calvin"
DEFAULT_NIC = "NIC.Integrated.1-1-1"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Test enhanced iSCSI Redfish configuration options")
    parser.add_argument("--server", default=DEFAULT_IDRAC_IP, help="Server IP address (e.g., 192.168.2.230)")
    parser.add_argument("--user", default=DEFAULT_IDRAC_USER, help="iDRAC username")
    parser.add_argument("--password", default=DEFAULT_IDRAC_PASSWORD, help="iDRAC password")
    parser.add_argument("--nic", default=DEFAULT_NIC, help="NIC to configure for iSCSI boot")
    parser.add_argument("--test", choices=["basic", "multipath", "chap", "direct-api", "validate", "reset"], 
                      required=True, help="Test to run")
    parser.add_argument("--reboot", action="store_true", help="Reboot after configuration")
    parser.add_argument("--ocp-version", default="4.18", help="OpenShift version for testing")
    parser.add_argument("--dry-run", action="store_true", help="Show commands but don't run them")
    
    return parser.parse_args()

def run_command(cmd, dry_run=False):
    """Run a command and print its output"""
    cmd_str = " ".join(cmd)
    print(f"\nRunning: {cmd_str}")
    
    if dry_run:
        print("(Dry run - command not executed)")
        return True
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"STDERR: {e.stderr}")
        return False

def test_basic_config(args):
    """Test basic iSCSI configuration"""
    print("\n=== Testing Basic iSCSI Configuration ===")
    
    cmd = [
        sys.executable,
        str(SWITCH_SCRIPT),
        "--server", args.server,
        "--method", "iscsi",
        "--version", args.ocp_version
    ]
    
    if args.reboot:
        cmd.append("--reboot")
    
    return run_command(cmd, args.dry_run)

def test_multipath_config(args):
    """Test multipath iSCSI configuration"""
    print("\n=== Testing Multipath iSCSI Configuration ===")
    
    cmd = [
        sys.executable,
        str(SWITCH_SCRIPT),
        "--server", args.server,
        "--method", "iscsi",
        "--version", args.ocp_version,
        "--multipath"
    ]
    
    if args.reboot:
        cmd.append("--reboot")
    
    return run_command(cmd, args.dry_run)

def test_chap_config(args):
    """Test CHAP authentication configuration"""
    print("\n=== Testing CHAP Authentication ===")
    
    cmd = [
        sys.executable,
        str(ISCSI_CONFIG_SCRIPT),
        "--server", args.server,
        "--user", args.user,
        "--password", args.password,
        "--target", "secure_target"
    ]
    
    if not args.reboot:
        cmd.append("--no-reboot")
    
    return run_command(cmd, args.dry_run)

def test_direct_api(args):
    """Test direct Redfish API configuration"""
    print("\n=== Testing Direct Redfish API ===")
    
    cmd = [
        sys.executable,
        str(SWITCH_SCRIPT),
        "--server", args.server,
        "--method", "iscsi",
        "--version", args.ocp_version,
        "--direct-api"
    ]
    
    if args.reboot:
        cmd.append("--reboot")
    
    return run_command(cmd, args.dry_run)

def test_validate_config(args):
    """Test validation of existing configuration"""
    print("\n=== Testing iSCSI Configuration Validation ===")
    
    cmd = [
        sys.executable,
        str(SWITCH_SCRIPT),
        "--server", args.server,
        "--method", "iscsi",
        "--version", args.ocp_version,
        "--validate-iscsi"
    ]
    
    return run_command(cmd, args.dry_run)

def test_reset_config(args):
    """Test resetting iSCSI configuration"""
    print("\n=== Testing iSCSI Configuration Reset ===")
    
    cmd = [
        sys.executable,
        str(SWITCH_SCRIPT),
        "--server", args.server,
        "--method", "iscsi",
        "--version", args.ocp_version,
        "--reset-iscsi"
    ]
    
    if args.reboot:
        cmd.append("--reboot")
    
    return run_command(cmd, args.dry_run)

def verify_script_exists(script_path):
    """Verify that script exists"""
    if not script_path.exists():
        print(f"Error: Script not found at {script_path}")
        return False
    return True

def verify_enhanced_targets_exists():
    """Verify enhanced targets file exists and copy it to the standard location if needed"""
    enhanced_targets = CONFIG_DIR / "iscsi_targets_enhanced.json"
    standard_targets = CONFIG_DIR / "iscsi_targets.json"
    standard_targets_backup = CONFIG_DIR / "iscsi_targets.json.bak"
    
    if not enhanced_targets.exists():
        print(f"Error: Enhanced targets file not found at {enhanced_targets}")
        return False
    
    # Make a backup of the standard targets file if it exists
    if standard_targets.exists():
        try:
            import shutil
            shutil.copy2(standard_targets, standard_targets_backup)
            print(f"Made backup of {standard_targets} to {standard_targets_backup}")
        except Exception as e:
            print(f"Warning: Unable to backup targets file: {e}")
    
    # Copy the enhanced targets file to the standard location
    try:
        import shutil
        shutil.copy2(enhanced_targets, standard_targets)
        print(f"Copied enhanced targets from {enhanced_targets} to {standard_targets}")
        return True
    except Exception as e:
        print(f"Error: Unable to copy enhanced targets file: {e}")
        return False

def main():
    args = parse_arguments()
    
    # Verify scripts exist
    if not verify_script_exists(ISCSI_CONFIG_SCRIPT) or not verify_script_exists(SWITCH_SCRIPT):
        sys.exit(1)
    
    # Verify enhanced targets exist and copy to standard location
    if not verify_enhanced_targets_exists():
        print("Error: Enhanced targets file not available or couldn't be copied")
        sys.exit(1)
    
    # Run the selected test
    success = False
    
    if args.test == "basic":
        success = test_basic_config(args)
    elif args.test == "multipath":
        success = test_multipath_config(args)
    elif args.test == "chap":
        success = test_chap_config(args)
    elif args.test == "direct-api":
        success = test_direct_api(args)
    elif args.test == "validate":
        success = test_validate_config(args)
    elif args.test == "reset":
        success = test_reset_config(args)
    
    if success:
        print("\n✅ Test completed successfully.")
    else:
        print("\n❌ Test failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
