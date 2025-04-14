# Script Migration Plan

This document outlines the strategy for migrating existing scripts to use the new component-based architecture with the discovery-processing-housekeeping pattern.

## Table of Contents
1. [Migration Strategy](#migration-strategy)
2. [Priority Order](#priority-order)
3. [Migration Process](#migration-process)
4. [Backward Compatibility](#backward-compatibility)
5. [Testing Strategy](#testing-strategy)
6. [Example Migration](#example-migration)

## Migration Strategy

The migration will follow these guiding principles:

1. **Incremental Migration**: Scripts will be migrated one by one rather than all at once, ensuring stability throughout the process.
2. **Component Reuse**: Leverage existing components (S3Component, ISCSIComponent, OpenShiftComponent, etc.) rather than reimplementing functionality.
3. **Preserve Interfaces**: External interfaces (command-line arguments, return values) should remain consistent.
4. **Improve Error Handling**: Use the opportunity to enhance error handling with the patterns established in the framework.
5. **Add Tests**: Create unit tests for each migrated script using the new testing fixtures.

## Priority Order

Scripts will be migrated in the following order, based on impact and dependencies:

### High Priority
1. `workflow_iso_generation_s3.py` - Core workflow script that can leverage S3Component and OpenShiftComponent
2. `setup_minio_buckets.py` - Infrastructure setup that would benefit from S3Component error handling
3. `test_iscsi_truenas.py` - Testing script that can directly use ISCSIComponent

### Medium Priority
4. `generate_openshift_iso.py` - Can use OpenShiftComponent for better abstraction
5. `setup_truenas.sh` - Convert to Python using ISCSIComponent
6. `config_iscsi_boot.py` - Can use ISCSIComponent and R630Component
7. `test_s3_minio.py` - Can directly use S3Component
8. `secrets_provider.py` - Can use VaultComponent for better secret management

### Lower Priority
9. `reboot_server.py` - Can use R630Component
10. `set_boot_order.py` - Can use R630Component
11. Other scripts as needed

## Migration Process

For each script, follow these steps:

1. **Analysis**: 
   - Document the current functionality
   - Identify which components it should use
   - Map inputs/outputs to component methods

2. **Implementation**:
   - Create a new version of the script with `_new` suffix
   - Implement using the component architecture
   - Maintain the same CLI interface

3. **Testing**:
   - Create unit tests using the testing fixtures
   - Test backward compatibility
   - Run integration tests for E2E validation

4. **Replacement**:
   - Once validated, replace the original script
   - Update documentation to reference new patterns

## Backward Compatibility

To ensure backward compatibility:

1. **Preserve CLI Arguments**: The command-line interface should remain identical
2. **Environment Variables**: Continue supporting the same environment variables
3. **Exit Codes**: Maintain the same exit code behavior
4. **Output Format**: Keep the same output format for scripts used in pipelines

If changes are necessary, provide a compatibility layer that handles both old and new formats.

## Testing Strategy

Each migrated script should have:

1. **Unit Tests**: Using the mock fixtures for filesystem, S3, etc.
2. **Integration Tests**: For end-to-end functionality
3. **Documentation**: Update the usage examples in the docs

## Example Migration

### Original Script Pattern

```python
# Example workflow script
import argparse
import boto3
import os

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--s3-endpoint', required=True)
    parser.add_argument('--version', required=True)
    return parser.parse_args()

def setup_s3_client(endpoint, access_key, secret_key):
    return boto3.client(
        's3',
        endpoint_url=f'https://{endpoint}',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

def main():
    args = parse_args()
    
    # Setup S3
    s3_client = setup_s3_client(
        args.s3_endpoint,
        os.environ.get('S3_ACCESS_KEY'),
        os.environ.get('S3_SECRET_KEY')
    )
    
    # Do work
    # ...

if __name__ == '__main__':
    main()
```

### Migrated Script Pattern

```python
#!/usr/bin/env python3
"""
Script description.
This script demonstrates using the component architecture.
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
        description="Script description"
    )
    parser.add_argument('--s3-endpoint', required=True, help="S3 endpoint URL")
    parser.add_argument('--version', required=True, help="OpenShift version")
    return parser.parse_args()

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
        'component_id': 's3-workflow-component'
    }

def main() -> int:
    """Main function that runs the workflow."""
    args = parse_args()
    
    try:
        # Initialize components
        s3_config = build_s3_config(args)
        s3_component = S3Component(s3_config)
        
        # Execute discovery-processing-housekeeping pattern
        s3_result = s3_component.discover()
        if not s3_result['connectivity']:
            logger.error(f"Cannot connect to S3: {s3_result.get('connection_error')}")
            return 1
            
        logger.info(f"Connected to S3 endpoint: {args.s3_endpoint}")
        
        # Process phase
        process_result = s3_component.process()
        
        # Housekeeping phase
        housekeep_result = s3_component.housekeep()
        
        # Return success
        return 0
        
    except Exception as e:
        logger.exception(f"Error in workflow: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

This example demonstrates how to migrate a script to use the component architecture while preserving the CLI interface.
