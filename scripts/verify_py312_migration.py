#!/usr/bin/env python3
"""
Python 3.12 Migration Verification Script

This script verifies that all Python 3.12 components and scripts
are properly installed and functioning. It serves as a quick health
check for the Python 3.12 migration status.

Usage:
    python scripts/verify_py312_migration.py
"""

import importlib
import os
import sys
import platform
from pathlib import Path
import subprocess
from typing import Dict, List, Tuple, Literal, Any, Optional

# Define colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
ENDC = "\033[0m"
BOLD = "\033[1m"

def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{ENDC}")
    print(f"{BOLD}{BLUE}  {text}{ENDC}")
    print(f"{BOLD}{BLUE}{'=' * 80}{ENDC}\n")

def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{GREEN}✓ {text}{ENDC}")

def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{YELLOW}⚠ {text}{ENDC}")

def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{RED}✗ {text}{ENDC}")

def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{BLUE}ℹ {text}{ENDC}")

def check_python_version() -> bool:
    """Check if Python 3.12 is being used."""
    version = platform.python_version()
    major, minor, *_ = version.split('.')
    
    if int(major) == 3 and int(minor) >= 12:
        print_success(f"Using Python {version} ✓")
        return True
    else:
        print_warning(f"Using Python {version}, but Python 3.12+ is required for py312 components")
        return False

def verify_component(component_name: str) -> bool:
    """Try to import a Python 3.12 component."""
    try:
        # Handle base_component differently as it's in the framework directory, not components
        if component_name == "base_component":
            module_path = f"framework.{component_name}_py312"
        else:
            module_path = f"framework.components.{component_name}_py312"
            
        # Try to check if required packages are installed first
        try:
            if component_name == "s3_component":
                importlib.import_module("boto3")
        except ImportError:
            print_warning(f"Required package boto3 for {component_name}_py312 is not installed")
            print_info("Install boto3 with: pip install boto3")
            return False
            
        importlib.import_module(module_path)
        print_success(f"Successfully imported {component_name}_py312")
        return True
    except ImportError as e:
        print_error(f"Failed to import {component_name}_py312: {str(e)}")
        return False
    except Exception as e:
        print_error(f"Error when importing {component_name}_py312: {str(e)}")
        return False

def verify_script(script_name: str) -> bool:
    """Check if a Python 3.12 script exists and is executable."""
    script_path = Path(f"scripts/{script_name}_py312.py")
    
    if not script_path.exists():
        print_error(f"Script {script_path} does not exist")
        return False
    
    # Check if script is executable
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print_success(f"Script {script_name}_py312.py executed successfully")
            return True
        else:
            print_error(f"Script {script_name}_py312.py failed with error code {result.returncode}")
            print_info(f"Error output: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print_error(f"Script {script_name}_py312.py timed out")
        return False
    except Exception as e:
        print_error(f"Error executing {script_name}_py312.py: {str(e)}")
        return False

def main() -> int:
    """Main function to verify Python 3.12 migration."""
    print_header("Python 3.12 Migration Verification")
    
    # Check Python version
    is_py312 = check_python_version()
    if not is_py312:
        print_info("Consider running this script with Python 3.12:")
        print_info("  python3.12 scripts/verify_py312_migration.py")
        print_info("Or using the Docker environment:")
        print_info("  docker compose -f docker-compose.python312.yml run python312 python scripts/verify_py312_migration.py")
    
    # Components to verify
    components = [
        "base_component",
        "s3_component",
        "vault_component",
        "openshift_component",
        "iscsi_component",
        "r630_component"
    ]
    
    # Scripts to verify
    scripts = [
        "workflow_iso_generation_s3",
        "setup_minio_buckets",
        "test_iscsi_truenas",
        "generate_openshift_iso",
        "config_iscsi_boot"
    ]
    
    # Results tracking
    results: Dict[str, Dict[str, int]] = {
        "components": {"pass": 0, "fail": 0},
        "scripts": {"pass": 0, "fail": 0}
    }
    
    # Verify components
    print_header("Verifying Components")
    for component in components:
        if verify_component(component):
            results["components"]["pass"] += 1
        else:
            results["components"]["fail"] += 1
    
    # Verify scripts
    print_header("Verifying Scripts")
    for script in scripts:
        if verify_script(script):
            results["scripts"]["pass"] += 1
        else:
            results["scripts"]["fail"] += 1
    
    # Print summary
    print_header("Summary")
    print(f"Components: {GREEN}{results['components']['pass']} passed{ENDC}, "
          f"{RED}{results['components']['fail']} failed{ENDC}")
    print(f"Scripts: {GREEN}{results['scripts']['pass']} passed{ENDC}, "
          f"{RED}{results['scripts']['fail']} failed{ENDC}")
    
    total_pass = results['components']['pass'] + results['scripts']['pass']
    total_fail = results['components']['fail'] + results['scripts']['fail']
    total_items = len(components) + len(scripts)
    
    if total_fail == 0:
        print_success(f"All {total_items} items verified successfully!")
        return 0
    else:
        percentage = (total_pass / total_items) * 100
        print_warning(f"Migration is {percentage:.1f}% complete ({total_pass}/{total_items} items verified)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
