#!/usr/bin/env python3
"""
setup_minio_buckets.py - Configure MinIO buckets for persistent storage

This script uses the S3Component to manage and configure MinIO buckets for the 
R630 iSCSI SwitchBot system. It follows the discovery-processing-housekeeping
pattern to ensure proper bucket setup and configuration.

It performs:
1. Bucket discovery and validation
2. Bucket creation with proper versioning and permissions
3. Folder structure setup with standardized paths
4. Optional test uploads to verify functionality
"""

import os
import sys
import logging
import argparse
import datetime
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Import components
from framework.components.s3_component import S3Component


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
    return logging.getLogger("minio-setup")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments with proper typing and descriptions.

    Returns:
        Parsed arguments as Namespace
    """
    parser = argparse.ArgumentParser(
        description="Set up MinIO buckets for persistent storage using the component architecture"
    )
    
    # MinIO connection configuration
    minio_group = parser.add_argument_group('MinIO Connection Configuration')
    minio_group.add_argument(
        "--endpoint", 
        default="scratchy.omnisack.nl", 
        help="MinIO endpoint URL"
    )
    minio_group.add_argument(
        "--access-key", 
        help="MinIO access key (can also use S3_ACCESS_KEY env var)"
    )
    minio_group.add_argument(
        "--secret-key", 
        help="MinIO secret key (can also use S3_SECRET_KEY env var)"
    )
    minio_group.add_argument(
        "--secure", 
        action="store_true", 
        help="Use HTTPS for MinIO connection"
    )
    
    # Bucket configuration
    bucket_group = parser.add_argument_group('Bucket Configuration')
    bucket_group.add_argument(
        "--iso-bucket", 
        default="r630-switchbot-isos", 
        help="Bucket for OpenShift ISOs"
    )
    bucket_group.add_argument(
        "--binary-bucket", 
        default="r630-switchbot-binaries", 
        help="Bucket for OpenShift binaries"
    )
    bucket_group.add_argument(
        "--temp-bucket", 
        default="r630-switchbot-temp", 
        help="Bucket for temporary storage"
    )
    
    # Initialization options
    init_group = parser.add_argument_group('Initialization Options')
    init_group.add_argument(
        "--init-all", 
        action="store_true", 
        help="Initialize all buckets"
    )
    init_group.add_argument(
        "--upload-example", 
        action="store_true", 
        help="Upload example files to test buckets"
    )
    init_group.add_argument(
        "--clean", 
        action="store_true", 
        help="Clean up buckets (remove all objects)"
    )
    
    # General options
    general_group = parser.add_argument_group('General Options')
    general_group.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    general_group.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Dry run (no changes)"
    )
    
    return parser.parse_args()


def create_s3_config(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Create S3Component configuration from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        S3Component configuration dictionary
    """
    # Set up folder structure for each bucket
    folder_structure_private = [
        'isos/',
        'binaries/',
        'artifacts/',
        'temp/'
    ]
    
    folder_structure_public = [
        'isos/4.16/',
        'isos/4.17/',
        'isos/4.18/',
        'isos/stable/'
    ]
    
    # Map temp bucket as the private bucket for simplicity
    # but allow for full public/private bucket setup
    return {
        'endpoint': args.endpoint,
        'access_key': args.access_key,
        'secret_key': args.secret_key,
        'secure': args.secure,
        'private_bucket': args.iso_bucket,
        'public_bucket': args.binary_bucket,
        'folder_structure_private': folder_structure_private,
        'folder_structure_public': folder_structure_public,
        'create_buckets_if_missing': args.init_all,
        'force_recreation': False,
        'component_id': 'minio-bucket-setup-component',
        'dry_run': args.dry_run
    }


def create_example_file() -> str:
    """
    Create a temporary example file for testing uploads.

    Returns:
        Path to the created example file
    """
    example_path = os.path.join(os.getcwd(), "example.txt")
    with open(example_path, "w") as f:
        f.write(f"Example file created at {datetime.datetime.now().isoformat()}\n")
        f.write("This is used to test the MinIO bucket setup.\n")
        f.write("This file was created by the setup_minio_buckets.py script.\n")
    
    return example_path


def upload_example_files(s3_component: S3Component, args: argparse.Namespace, logger: logging.Logger) -> bool:
    """
    Upload example files to all configured buckets for testing.

    Args:
        s3_component: Initialized S3Component
        args: Parsed command line arguments
        logger: Logger instance

    Returns:
        True if successful, False on failure
    """
    try:
        # Create a temporary example file
        logger.info("Creating example file for upload test...")
        example_path = create_example_file()
        
        try:
            # Add example files to each bucket
            buckets = [args.iso_bucket, args.binary_bucket, args.temp_bucket]
            bucket_types = ['iso', 'binary', 'temp']
            
            for i, bucket in enumerate(buckets):
                bucket_type = bucket_types[i] if i < len(bucket_types) else 'unknown'
                object_name = f"example/example-{bucket_type}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
                
                logger.info(f"Adding example file to bucket {bucket} at {object_name}")
                
                # Add the artifact to the component
                s3_component.add_artifact(
                    name=f"example_file_{bucket_type}",
                    content=example_path,
                    metadata={
                        "bucket": bucket,
                        "object_name": object_name,
                        "content_type": "text/plain",
                        "bucket_type": bucket_type,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                )
            
            # Run housekeeping phase to store artifacts
            logger.info("Storing example files...")
            s3_component.housekeep()
            
            logger.info("Example files successfully uploaded")
            return True
            
        finally:
            # Clean up temporary file
            if os.path.exists(example_path):
                os.unlink(example_path)
                logger.info(f"Removed temporary file {example_path}")
                
    except Exception as e:
        logger.error(f"Failed to upload example files: {str(e)}")
        return False


def run_setup(args: argparse.Namespace, logger: logging.Logger) -> int:
    """
    Run the main bucket setup workflow with error handling.

    Args:
        args: Parsed command line arguments
        logger: Logger instance

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Create S3Component configuration
        s3_config = create_s3_config(args)
        
        # Initialize S3Component
        logger.info("Initializing S3Component...")
        s3_component = S3Component(s3_config, logger)
        
        # Discovery phase
        logger.info("Starting discovery phase...")
        discovery_results = s3_component.discover()
        
        # Check connectivity
        if not discovery_results.get('connectivity', False):
            error_msg = discovery_results.get('error', 'Unknown connection error')
            logger.error(f"Failed to connect to MinIO/S3 endpoint: {error_msg}")
            return 1
        
        # Report discovery results
        logger.info(f"Discovery completed:")
        logger.info(f"- Endpoint: {discovery_results.get('endpoint')}")
        logger.info(f"- Connected: Successfully connected to MinIO")
        
        # Show discovered buckets
        existing_buckets = discovery_results.get('buckets', {})
        if existing_buckets:
            private_bucket = existing_buckets.get('private', {})
            public_bucket = existing_buckets.get('public', {})
            
            if private_bucket.get('exists', False):
                logger.info(f"- Private bucket exists: {s3_config.get('private_bucket')}")
                logger.info(f"  - Object count: {private_bucket.get('objects_count', 0)}")
                logger.info(f"  - Folders: {', '.join(private_bucket.get('folders', []))}")
            else:
                logger.warning(f"- Private bucket doesn't exist: {s3_config.get('private_bucket')}")
                
            if public_bucket.get('exists', False):
                logger.info(f"- Public bucket exists: {s3_config.get('public_bucket')}")
                logger.info(f"  - Object count: {public_bucket.get('objects_count', 0)}")
                logger.info(f"  - Folders: {', '.join(public_bucket.get('folders', []))}")
            else:
                logger.warning(f"- Public bucket doesn't exist: {s3_config.get('public_bucket')}")
        else:
            logger.warning("No existing buckets found")
        
        # Process phase (create buckets if needed)
        if args.init_all:
            logger.info("Starting processing phase to create buckets...")
            processing_results = s3_component.process()
            
            # Report created buckets
            private_bucket_results = processing_results.get('buckets', {}).get('private', {})
            public_bucket_results = processing_results.get('buckets', {}).get('public', {})
            
            if private_bucket_results.get('created', False):
                logger.info(f"Created private bucket: {s3_config.get('private_bucket')}")
                logger.info(f"Created folders: {', '.join(private_bucket_results.get('folders_created', []))}")
            elif private_bucket_results.get('configured', False):
                logger.info(f"Configured existing private bucket: {s3_config.get('private_bucket')}")
            
            if public_bucket_results.get('created', False):
                logger.info(f"Created public bucket: {s3_config.get('public_bucket')}")
                logger.info(f"Created folders: {', '.join(public_bucket_results.get('folders_created', []))}")
            elif public_bucket_results.get('configured', False):
                logger.info(f"Configured existing public bucket: {s3_config.get('public_bucket')}")
        else:
            logger.info("Skipping bucket creation (--init-all not specified)")
        
        # Upload example files if requested
        if args.upload_example:
            logger.info("Uploading example files to buckets...")
            upload_example_files(s3_component, args, logger)
        
        # Housekeeping phase
        if args.clean:
            logger.info("Starting housekeeping phase to clean up buckets...")
            housekeeping_results = s3_component.housekeep()
            
            # Report verification results
            verification = housekeeping_results.get('verification', {})
            logger.info(f"Bucket verification results:")
            logger.info(f"- Private bucket: {'Verified' if verification.get('private_bucket', False) else 'Failed'}")
            logger.info(f"- Public bucket: {'Verified' if verification.get('public_bucket', False) else 'Failed'}")
            
            # Report any warnings
            warnings = housekeeping_results.get('warnings', [])
            if warnings:
                logger.warning(f"Warnings during housekeeping:")
                for warning in warnings:
                    logger.warning(f"- {warning}")
        
        logger.info("MinIO bucket setup completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Bucket setup failed with error: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


def main() -> int:
    """
    Main entry point with basic error handling.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    try:
        return run_setup(args, logger)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
