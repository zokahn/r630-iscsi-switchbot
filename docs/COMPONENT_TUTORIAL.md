# Component Architecture Tutorial

This tutorial demonstrates how to use the component architecture to implement a common workflow in the R630 iSCSI SwitchBot system.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Workflow: OpenShift ISO Generation and iSCSI Boot Configuration](#workflow-openshift-iso-generation-and-iscsi-boot-configuration)
4. [Step 1: Setting up the Environment](#step-1-setting-up-the-environment)
5. [Step 2: Creating the S3 Component](#step-2-creating-the-s3-component)
6. [Step 3: Creating the OpenShift Component](#step-3-creating-the-openshift-component)
7. [Step 4: Creating the iSCSI Component](#step-4-creating-the-iscsi-component)
8. [Step 5: Creating the R630 Component](#step-5-creating-the-r630-component)
9. [Step 6: Implementing the Workflow](#step-6-implementing-the-workflow)
10. [Best Practices](#best-practices)
11. [Testing the Workflow](#testing-the-workflow)
12. [Troubleshooting](#troubleshooting)

## Overview

This tutorial will guide you through creating a workflow script that:

1. Generates an OpenShift installation ISO
2. Uploads the ISO to S3 storage
3. Creates an iSCSI target with the ISO
4. Configures a Dell R630 server to boot from the iSCSI target

This workflow demonstrates how multiple components can work together in a single script while following the discovery-processing-housekeeping pattern.

## Prerequisites

- Python 3.8 or later
- Access to TrueNAS server for iSCSI
- Access to S3-compatible storage (MinIO or AWS)
- A Dell R630 server with iDRAC access
- OpenShift pull secret

## Workflow: OpenShift ISO Generation and iSCSI Boot Configuration

Let's implement a script that automates the process of generating an OpenShift ISO, storing it in S3, creating an iSCSI target, and configuring the R630 server for iSCSI boot.

## Step 1: Setting up the Environment

First, we need to set up our environment and parse the command-line arguments:

```python
#!/usr/bin/env python3
"""
End-to-end workflow for OpenShift deployment on R630 via iSCSI.

This script demonstrates using the component architecture to:
1. Generate an OpenShift ISO
2. Upload it to S3
3. Create an iSCSI target
4. Configure R630 for iSCSI boot
"""
import argparse
import os
import sys
import logging
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from framework.components.s3_component import S3Component
from framework.components.openshift_component import OpenShiftComponent
from framework.components.iscsi_component import ISCSIComponent
from framework.components.r630_component import R630Component
from scripts.secrets_provider import get_secret

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Configure OpenShift deployment on R630 via iSCSI"
    )
    # Required arguments
    parser.add_argument('--server-id', required=True, help="Server ID (e.g., '01')")
    parser.add_argument('--hostname', required=True, help="Server hostname")
    parser.add_argument('--node-ip', required=True, help="Node IP address")
    parser.add_argument('--openshift-version', required=True, help="OpenShift version (e.g., '4.14.0')")
    
    # Storage arguments
    parser.add_argument('--s3-endpoint', required=True, help="S3 endpoint URL")
    parser.add_argument('--truenas-ip', required=True, help="TrueNAS IP address")
    
    # iDRAC arguments
    parser.add_argument('--idrac-ip', required=True, help="iDRAC IP address")
    
    # Optional arguments
    parser.add_argument('--pull-secret-path', help="Path to OpenShift pull secret")
    parser.add_argument('--ssh-key-path', help="Path to SSH public key")
    parser.add_argument('--dry-run', action='store_true', help="Validate without making changes")
    parser.add_argument('--cleanup', action='store_true', help="Clean up orphaned resources")
    
    return parser.parse_args()
```

## Step 2: Creating the S3 Component

Next, let's set up the S3Component that will handle storage for our ISO:

```python
def build_s3_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Build S3Component configuration from args and environment."""
    # Get secrets from environment or secret provider
    access_key = get_secret('s3/credentials', 'access_key', 
                           fallback=os.environ.get('S3_ACCESS_KEY'))
    secret_key = get_secret('s3/credentials', 'secret_key',
                           fallback=os.environ.get('S3_SECRET_KEY'))
    
    return {
        'endpoint': args.s3_endpoint,
        'access_key': access_key,
        'secret_key': secret_key,
        'private_bucket': 'r630-switchbot-private',
        'public_bucket': 'r630-switchbot-public',
        'create_buckets_if_missing': True,
        'component_id': f's3-component-{args.server_id}'
    }

def setup_s3_component(args: argparse.Namespace) -> S3Component:
    """Set up and initialize the S3Component."""
    s3_config = build_s3_config(args)
    s3_component = S3Component(s3_config)
    
    # Run discovery phase
    logger.info("Running S3 discovery phase...")
    s3_result = s3_component.discover()
    
    if not s3_result['connectivity']:
        raise Exception(f"Cannot connect to S3: {s3_result.get('connection_error')}")
    
    logger.info(f"Successfully connected to S3 at {args.s3_endpoint}")
    logger.info(f"Private bucket: {s3_result['buckets']['private']['exists']}")
    logger.info(f"Public bucket: {s3_result['buckets']['public']['exists']}")
    
    return s3_component
```

## Step 3: Creating the OpenShift Component

Now, let's set up the OpenShiftComponent that will generate our ISO:

```python
def build_openshift_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Build OpenShiftComponent configuration from args."""
    # Use default paths if not specified
    pull_secret_path = args.pull_secret_path or os.path.expanduser("~/.openshift/pull-secret")
    ssh_key_path = args.ssh_key_path or os.path.expanduser("~/.ssh/id_rsa.pub")
    
    return {
        'openshift_version': args.openshift_version,
        'domain': 'lab.example.com',  # Could be made configurable
        'cluster_name': f'r630-{args.server_id}',
        'rendezvous_ip': args.node_ip,
        'node_ip': args.node_ip,
        'server_id': args.server_id,
        'hostname': args.hostname,
        'pull_secret_path': pull_secret_path,
        'ssh_key_path': ssh_key_path,
        'dry_run': args.dry_run,
        'component_id': f'openshift-component-{args.server_id}'
    }

def setup_openshift_component(args: argparse.Namespace, s3_component: S3Component) -> OpenShiftComponent:
    """Set up and initialize the OpenShiftComponent."""
    openshift_config = build_openshift_config(args)
    openshift_component = OpenShiftComponent(openshift_config, s3_component=s3_component)
    
    # Run discovery phase
    logger.info("Running OpenShift discovery phase...")
    openshift_result = openshift_component.discover()
    
    if not openshift_result['pull_secret_available']:
        raise Exception(f"Pull secret not found at {openshift_config['pull_secret_path']}")
    
    if not openshift_result['ssh_key_available']:
        raise Exception(f"SSH key not found at {openshift_config['ssh_key_path']}")
    
    logger.info(f"OpenShift discovery completed successfully")
    logger.info(f"Installer available: {openshift_result['installer_available']}")
    logger.info(f"Available versions: {openshift_result['available_versions']}")
    
    return openshift_component
```

## Step 4: Creating the iSCSI Component

Next, let's set up the ISCSIComponent to manage our iSCSI target:

```python
def build_iscsi_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Build ISCSIComponent configuration from args."""
    # Get API key from secrets
    api_key = get_secret('truenas/credentials', 'api_key',
                        fallback=os.environ.get('TRUENAS_API_KEY'))
    
    return {
        'truenas_ip': args.truenas_ip,
        'api_key': api_key,
        'server_id': args.server_id,
        'hostname': args.hostname,
        'openshift_version': args.openshift_version,
        'zvol_size': '20G',  # Could be made configurable
        'zfs_pool': 'tank',  # Could be made configurable
        'dry_run': args.dry_run,
        'cleanup_unused': args.cleanup,
        'component_id': f'iscsi-component-{args.server_id}'
    }

def setup_iscsi_component(args: argparse.Namespace) -> ISCSIComponent:
    """Set up and initialize the ISCSIComponent."""
    iscsi_config = build_iscsi_config(args)
    iscsi_component = ISCSIComponent(iscsi_config)
    
    # Run discovery phase
    logger.info("Running iSCSI discovery phase...")
    iscsi_result = iscsi_component.discover()
    
    if not iscsi_result['connectivity']:
        raise Exception(f"Cannot connect to TrueNAS: {iscsi_result.get('connection_error')}")
    
    logger.info(f"Successfully connected to TrueNAS at {args.truenas_ip}")
    logger.info(f"System info: {iscsi_result['system_info']['hostname']}")
    logger.info(f"iSCSI service running: {iscsi_result['iscsi_service']}")
    
    return iscsi_component
```

## Step 5: Creating the R630 Component

Now, let's set up the R630Component to configure the server:

```python
def build_r630_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Build R630Component configuration from args."""
    # Get iDRAC credentials from secrets
    idrac_username = get_secret('idrac/credentials', 'username',
                              fallback=os.environ.get('IDRAC_USERNAME', 'root'))
    idrac_password = get_secret('idrac/credentials', 'password',
                              fallback=os.environ.get('IDRAC_PASSWORD'))
    
    return {
        'idrac_ip': args.idrac_ip,
        'idrac_username': idrac_username,
        'idrac_password': idrac_password,
        'server_id': args.server_id,
        'boot_mode': 'iscsi',
        'dry_run': args.dry_run,
        'component_id': f'r630-component-{args.server_id}'
    }

def setup_r630_component(args: argparse.Namespace) -> R630Component:
    """Set up and initialize the R630Component."""
    r630_config = build_r630_config(args)
    r630_component = R630Component(r630_config)
    
    # Run discovery phase
    logger.info("Running R630 discovery phase...")
    r630_result = r630_component.discover()
    
    if not r630_result['connectivity']:
        raise Exception(f"Cannot connect to iDRAC: {r630_result.get('connection_error')}")
    
    logger.info(f"Successfully connected to iDRAC at {args.idrac_ip}")
    logger.info(f"System info: {r630_result['system_info']['model']}")
    logger.info(f"Current boot mode: {r630_result['boot_mode']}")
    
    return r630_component
```

## Step 6: Implementing the Workflow

Finally, let's implement the main workflow function that uses all components:

```python
def run_workflow(args: argparse.Namespace) -> int:
    """Run the end-to-end workflow."""
    try:
        # Set up components
        logger.info("Setting up components...")
        s3_component = setup_s3_component(args)
        openshift_component = setup_openshift_component(args, s3_component)
        iscsi_component = setup_iscsi_component(args)
        r630_component = setup_r630_component(args)
        
        # Process phase for S3
        logger.info("Running S3 processing phase...")
        s3_process_result = s3_component.process()
        
        # Process phase for OpenShift
        logger.info("Running OpenShift processing phase...")
        openshift_process_result = openshift_component.process()
        
        if not openshift_process_result['iso_generated']:
            raise Exception("Failed to generate OpenShift ISO")
        
        iso_path = openshift_process_result['iso_path']
        logger.info(f"Generated ISO at {iso_path}")
        
        # Process phase for iSCSI
        logger.info("Running iSCSI processing phase...")
        iscsi_process_result = iscsi_component.process()
        
        if not iscsi_process_result['target_created']:
            raise Exception("Failed to create iSCSI target")
        
        target_name = iscsi_process_result['target_name']
        logger.info(f"Created iSCSI target: {target_name}")
        
        # Process phase for R630
        logger.info("Running R630 processing phase...")
        # Pass iSCSI target details to R630 component
        r630_component.config['iscsi_target'] = target_name
        r630_component.config['iscsi_ip'] = args.truenas_ip
        r630_process_result = r630_component.process()
        
        if not r630_process_result['boot_configured']:
            raise Exception("Failed to configure iSCSI boot")
        
        logger.info("Server configured for iSCSI boot")
        
        # Housekeeping phases
        logger.info("Running housekeeping phases...")
        s3_component.housekeep()
        openshift_component.housekeep()
        iscsi_component.housekeep()
        r630_component.housekeep()
        
        logger.info("Workflow completed successfully!")
        return 0
        
    except Exception as e:
        logger.exception(f"Error in workflow: {str(e)}")
        return 1

def main() -> int:
    """Main function."""
    args = parse_args()
    return run_workflow(args)

if __name__ == '__main__':
    sys.exit(main())
```

## Best Practices

When working with the component architecture, follow these best practices:

1. **Always Run All Phases**: For each component, run all three phases: discover, process, and housekeep.
2. **Handle Errors**: Catch exceptions at the workflow level and provide meaningful error messages.
3. **Share Components**: Pass components between each other when needed (like passing S3Component to OpenShiftComponent).
4. **Log Everything**: Use the logging system consistently to track progress and diagnose issues.
5. **Check Phase Results**: Always check the results of each phase before proceeding.
6. **Use Secrets Provider**: Get sensitive information from the secrets provider rather than hardcoding.
7. **Preserve CLI Interface**: Maintain the same command-line interface for backward compatibility.

## Testing the Workflow

To test this workflow, you can create a unit test using the testing fixtures:

```python
import pytest
from unittest.mock import MagicMock, patch

# Import your workflow script
from scripts import workflow_example

@pytest.fixture
def args():
    """Mock command line arguments."""
    args = MagicMock()
    args.server_id = "01"
    args.hostname = "test-server"
    args.node_ip = "192.168.1.100"
    args.openshift_version = "4.14.0"
    args.s3_endpoint = "s3.example.com"
    args.truenas_ip = "192.168.1.245"
    args.idrac_ip = "192.168.1.200"
    args.dry_run = False
    args.cleanup = False
    return args

@pytest.fixture
def mock_components(mock_s3, mock_filesystem):
    """Mock all components."""
    # Mock S3Component
    mock_s3_component = MagicMock()
    mock_s3_component.discover.return_value = {"connectivity": True, "buckets": {"private": {"exists": True}, "public": {"exists": True}}}
    mock_s3_component.process.return_value = {"buckets": {"private": {"created": False}, "public": {"created": False}}}
    mock_s3_component.housekeep.return_value = {"verification": {"private_bucket": True, "public_bucket": True}}
    
    # Mock OpenShiftComponent
    mock_openshift_component = MagicMock()
    mock_openshift_component.discover.return_value = {"pull_secret_available": True, "ssh_key_available": True, "installer_available": True, "available_versions": ["4.14.0"]}
    mock_openshift_component.process.return_value = {"iso_generated": True, "iso_path": "/tmp/test-dir/agent.x86_64.iso"}
    mock_openshift_component.housekeep.return_value = {"iso_verified": True, "temp_files_cleaned": True}
    
    # Mock ISCSIComponent
    mock_iscsi_component = MagicMock()
    mock_iscsi_component.discover.return_value = {"connectivity": True, "system_info": {"hostname": "truenas"}, "iscsi_service": True}
    mock_iscsi_component.process.return_value = {"target_created": True, "target_name": "iqn.2005-10.org.freenas.ctl:r630-01"}
    mock_iscsi_component.housekeep.return_value = {"resources_verified": True}
    
    # Mock R630Component
    mock_r630_component = MagicMock()
    mock_r630_component.discover.return_value = {"connectivity": True, "system_info": {"model": "R630"}, "boot_mode": "bios"}
    mock_r630_component.process.return_value = {"boot_configured": True}
    mock_r630_component.housekeep.return_value = {"configuration_verified": True}
    
    # Return all mocks
    return {
        "s3": mock_s3_component,
        "openshift": mock_openshift_component,
        "iscsi": mock_iscsi_component,
        "r630": mock_r630_component
    }

def test_workflow(args, mock_components):
    """Test the workflow execution."""
    # Patch the setup functions to return mocks
    with patch("scripts.workflow_example.setup_s3_component", return_value=mock_components["s3"]), \
         patch("scripts.workflow_example.setup_openshift_component", return_value=mock_components["openshift"]), \
         patch("scripts.workflow_example.setup_iscsi_component", return_value=mock_components["iscsi"]), \
         patch("scripts.workflow_example.setup_r630_component", return_value=mock_components["r630"]):
        
        # Run the workflow
        result = workflow_example.run_workflow(args)
        
        # Check result
        assert result == 0
        
        # Verify each component's phases were called
        for component in mock_components.values():
            component.discover.assert_called_once()
            component.process.assert_called_once()
            component.housekeep.assert_called_once()
```

## Troubleshooting

Common issues and their solutions:

1. **Connection Errors**: If components fail to connect, check endpoint URLs, credentials, and network connectivity.
2. **File Not Found Errors**: For OpenShift component, ensure the pull secret and SSH key are in the expected location.
3. **Permission Errors**: For TrueNAS, verify the API key has sufficient privileges.
4. **Boot Failures**: For R630, check iDRAC connectivity and ensure the correct iSCSI target details are provided.
5. **S3 Errors**: Verify bucket existence and permissions.

For detailed troubleshooting, check the individual component logs.
