#!/usr/bin/env python3
"""
Example Usage of S3Component for Dual-Bucket Strategy

This script demonstrates how to use the S3Component to implement the
discovery-processing-housekeeping pattern for S3 storage management.

Usage:
  ./framework/example_s3_component.py --discover
  ./framework/example_s3_component.py --setup
  ./framework/example_s3_component.py --upload ISO_PATH --server-id SERVER_ID --hostname HOSTNAME --version VERSION
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, Any, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the S3Component
from framework.components.s3_component import S3Component

def setup_logging() -> logging.Logger:
    """Set up logging configuration"""
    logger = logging.getLogger('example_s3_component')
    logger.setLevel(logging.INFO)
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

def discover_s3_environment(logger: logging.Logger) -> Dict[str, Any]:
    """
    Perform discovery phase to examine S3 environment
    
    Args:
        logger: Logger instance
        
    Returns:
        Dictionary with discovery results
    """
    logger.info("=== S3 Environment Discovery ===")
    
    # Create S3Component with minimal config
    config = {
        'component_id': 'example-s3-discovery',
    }
    
    s3 = S3Component(config, logger)
    
    # Execute only discovery phase
    result = s3.execute(phases=["discover"])
    
    logger.info("Discovery completed")
    
    return result

def setup_s3_buckets(logger: logging.Logger, force: bool = False) -> Dict[str, Any]:
    """
    Set up S3 buckets using the component
    
    Args:
        logger: Logger instance
        force: Whether to force reconfiguration if buckets exist
        
    Returns:
        Dictionary with execution results
    """
    logger.info("=== S3 Bucket Setup ===")
    
    # Create S3Component with setup config
    config = {
        'component_id': 'example-s3-setup',
        'create_buckets_if_missing': True,
        'force_recreation': force,
        'create_metadata_index': True
    }
    
    s3 = S3Component(config, logger)
    
    # Execute all phases
    result = s3.execute()
    
    logger.info("Setup completed")
    
    return result

def upload_iso(logger: logging.Logger, iso_path: str, server_id: str, 
              hostname: str, version: str, publish: bool = True) -> Dict[str, Any]:
    """
    Upload an ISO to S3 using the component
    
    Args:
        logger: Logger instance
        iso_path: Path to ISO file
        server_id: Server ID
        hostname: Server hostname
        version: OpenShift version
        publish: Whether to publish to public bucket
        
    Returns:
        Dictionary with execution results
    """
    logger.info(f"=== Uploading ISO {iso_path} ===")
    
    # Create S3Component for ISO upload
    config = {
        'component_id': f'example-s3-upload-{server_id}-{hostname}',
    }
    
    s3 = S3Component(config, logger)
    
    # First do discovery
    s3.discover()
    
    # Use the S3-specific method to upload ISO
    result = s3.upload_iso(iso_path, server_id, hostname, version, publish)
    
    if result.get('success', False):
        logger.info("ISO uploaded successfully")
        logger.info(f"Private key: {result.get('private_key')}")
        
        if result.get('public_key'):
            logger.info(f"Public key: {result.get('public_key')}")
            
            # Generate public URL
            endpoint = s3.config.get('endpoint')
            public_bucket = s3.config.get('public_bucket')
            public_url = f"http://{endpoint}/{public_bucket}/{result.get('public_key')}"
            logger.info(f"Public URL: {public_url}")
    else:
        logger.error(f"ISO upload failed: {result.get('error')}")
    
    return result

def main():
    """Main execution function"""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Example S3Component usage for dual-bucket strategy'
    )
    
    # Create mutually exclusive group for operations
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--discover', action='store_true', help='Discover S3 environment')
    group.add_argument('--setup', action='store_true', help='Set up S3 buckets')
    group.add_argument('--upload', metavar='ISO_PATH', help='Upload ISO file to S3')
    
    # Additional arguments
    parser.add_argument('--force', action='store_true', help='Force recreation of buckets')
    parser.add_argument('--server-id', help='Server ID for ISO upload')
    parser.add_argument('--hostname', help='Server hostname for ISO upload')
    parser.add_argument('--version', help='OpenShift version for ISO upload')
    parser.add_argument('--no-publish', action='store_true', help='Do not publish to public bucket')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    try:
        if args.discover:
            # Perform discovery
            results = discover_s3_environment(logger)
            print(json.dumps(results, indent=2))
            
        elif args.setup:
            # Set up buckets
            results = setup_s3_buckets(logger, args.force)
            print(json.dumps(results, indent=2))
            
        elif args.upload:
            # Check required arguments
            if not args.server_id or not args.hostname or not args.version:
                logger.error("For upload, --server-id, --hostname, and --version are required")
                return 1
                
            # Upload ISO
            results = upload_iso(
                logger, 
                args.upload, 
                args.server_id, 
                args.hostname, 
                args.version,
                not args.no_publish
            )
            print(json.dumps(results, indent=2))
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
