#!/usr/bin/env python3
"""
setup_minio_buckets_py312.py - Configure MinIO buckets for persistent storage

This script uses the S3Component to manage and configure MinIO buckets for the 
R630 iSCSI SwitchBot system. It follows the discovery-processing-housekeeping
pattern to ensure proper bucket setup and configuration.

It performs:
1. Bucket discovery and validation
2. Bucket creation with proper versioning and permissions
3. Folder structure setup with standardized paths
4. Optional test uploads to verify functionality

Python 3.12 version with enhanced typing and features.
"""

import os
import sys
import logging
import argparse
import datetime
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, TypedDict, Literal, cast, NotRequired

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Import Python 3.12 components
from framework.components.s3_component_py312 import S3Component


# Type definitions
class S3ConfigDict(TypedDict):
    """S3Component configuration type"""
    endpoint: str
    access_key: Optional[str]
    secret_key: Optional[str]
    secure: bool
    private_bucket: str
    public_bucket: str
    folder_structure_private: List[str]
    folder_structure_public: List[str]
    create_buckets_if_missing: bool
    force_recreation: bool
    component_id: str
    dry_run: bool


class S3DiscoveryResult(TypedDict):
    """S3Component discovery phase result type"""
    connectivity: bool
    endpoint: str
    error: NotRequired[str]
    buckets: Dict[str, Dict[str, Any]]


class BucketInfo(TypedDict):
    """Bucket information type"""
    exists: bool
    objects_count: NotRequired[int]
    folders: NotRequired[List[str]]


class ProcessingResult(TypedDict):
    """S3Component processing phase result type"""
    buckets: Dict[str, Dict[str, Any]]


class BucketProcessResult(TypedDict):
    """Bucket processing result type"""
    created: bool
    configured: NotRequired[bool]
    folders_created: NotRequired[List[str]]


class HousekeepingResult(TypedDict):
    """S3Component housekeeping phase result type"""
    verification: Dict[str, bool]
    warnings: List[str]


class ArtifactMetadata(TypedDict):
    """S3 artifact metadata type"""
    bucket: str
    object_name: str
    content_type: str
    bucket_type: str
    timestamp: str


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
        description="Set up MinIO buckets for persistent storage using the Python 3.12 component architecture"
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


def create_s3_config(args: argparse.Namespace) -> S3ConfigDict:
    """
    Create S3Component configuration from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        S3Component configuration dictionary
    """
    # Use access key from args or environment variable
    access_key = args.access_key or os.environ.get("S3_ACCESS_KEY")
    secret_key = args.secret_key or os.environ.get("S3_SECRET_KEY")
    
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
    
    # Dictionary for base config
    base_config = {
        'endpoint': args.endpoint,
        'access_key': access_key,
        'secret_key': secret_key,
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
    
    # Return with proper typing
    return cast(S3ConfigDict, base_config)


def create_example_file() -> str:
    """
    Create a temporary example file for testing uploads.

    Returns:
        Path to the created example file
    """
    timestamp = datetime.datetime.now().isoformat()
    
    # Use Path from pathlib for better path handling
    example_path = Path.cwd() / "example.txt"
    
    # Use with statement for better resource management
    with open(example_path, "w") as f:
        f.write(f"Example file created at {timestamp}\n")
        f.write("This is used to test the MinIO bucket setup.\n")
        f.write("This file was created by the setup_minio_buckets_py312.py script.\n")
    
    return str(example_path)


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
            
            # Use assignment expressions to improve flow
            if timestamp := datetime.datetime.now().strftime('%Y%m%d%H%M%S'):
                for i, bucket in enumerate(buckets):
                    # Use Python 3.12 assignment in conditional
                    if i < len(bucket_types) and (bucket_type := bucket_types[i]):
                        object_name = f"example/example-{bucket_type}-{timestamp}.txt"
                    else:
                        bucket_type = 'unknown'
                        object_name = f"example/example-unknown-{timestamp}.txt"
                    
                    logger.info(f"Adding example file to bucket {bucket} at {object_name}")
                    
                    # Create metadata with typed dict
                    metadata: ArtifactMetadata = {
                        "bucket": bucket,
                        "object_name": object_name,
                        "content_type": "text/plain",
                        "bucket_type": bucket_type,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    
                    # Add the artifact to the component
                    s3_component.add_artifact(
                        name=f"example_file_{bucket_type}",
                        content=example_path,
                        metadata=metadata
                    )
            
            # Run housekeeping phase to store artifacts
            logger.info("Storing example files...")
            s3_component.housekeep()
            
            logger.info("Example files successfully uploaded")
            return True
            
        finally:
            # Clean up temporary file
            # Use pathlib.Path with existence check
            path = Path(example_path)
            if path.exists():
                path.unlink()
                logger.info(f"Removed temporary file {path}")
                
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
        discovery_results = cast(S3DiscoveryResult, s3_component.discover())
        
        # Use Python 3.12 pattern matching for error handling
        match discovery_results:
            case {'connectivity': False, 'error': error}:
                logger.error(f"Failed to connect to MinIO/S3 endpoint: {error}")
                return 1
            case {'connectivity': True, 'endpoint': endpoint}:
                logger.info(f"Discovery completed:")
                logger.info(f"- Endpoint: {endpoint}")
                logger.info(f"- Connected: Successfully connected to MinIO")
            case _:
                logger.warning("Unexpected discovery result format")
        
        # Show discovered buckets using more Python 3.12 pattern matching
        if existing_buckets := discovery_results.get('buckets', {}):
            private_bucket = existing_buckets.get('private', {})
            public_bucket = existing_buckets.get('public', {})
            
            # Use pattern matching for private bucket info
            match private_bucket:
                case {'exists': True, 'objects_count': count, 'folders': folders}:
                    logger.info(f"- Private bucket exists: {s3_config['private_bucket']}")
                    logger.info(f"  - Object count: {count}")
                    logger.info(f"  - Folders: {', '.join(folders)}")
                case {'exists': False}:
                    logger.warning(f"- Private bucket doesn't exist: {s3_config['private_bucket']}")
                case _:
                    logger.warning(f"- Unexpected private bucket info format")
            
            # Use pattern matching for public bucket info
            match public_bucket:
                case {'exists': True, 'objects_count': count, 'folders': folders}:
                    logger.info(f"- Public bucket exists: {s3_config['public_bucket']}")
                    logger.info(f"  - Object count: {count}")
                    logger.info(f"  - Folders: {', '.join(folders)}")
                case {'exists': False}:
                    logger.warning(f"- Public bucket doesn't exist: {s3_config['public_bucket']}")
                case _:
                    logger.warning(f"- Unexpected public bucket info format")
        else:
            logger.warning("No existing buckets found")
        
        # Process phase (create buckets if needed)
        if args.init_all:
            logger.info("Starting processing phase to create buckets...")
            processing_results = cast(ProcessingResult, s3_component.process())
            
            # Use dict.get() with default for safer access
            buckets_results = processing_results.get('buckets', {})
            
            # Get bucket results with appropriate types
            private_bucket_results = cast(BucketProcessResult, 
                                          buckets_results.get('private', {}))
            public_bucket_results = cast(BucketProcessResult, 
                                          buckets_results.get('public', {}))
            
            # Use pattern matching for private bucket results
            match private_bucket_results:
                case {'created': True, 'folders_created': folders}:
                    logger.info(f"Created private bucket: {s3_config['private_bucket']}")
                    logger.info(f"Created folders: {', '.join(folders)}")
                case {'created': False, 'configured': True}:
                    logger.info(f"Configured existing private bucket: {s3_config['private_bucket']}")
                case _:
                    logger.info(f"No changes to private bucket: {s3_config['private_bucket']}")
            
            # Use pattern matching for public bucket results
            match public_bucket_results:
                case {'created': True, 'folders_created': folders}:
                    logger.info(f"Created public bucket: {s3_config['public_bucket']}")
                    logger.info(f"Created folders: {', '.join(folders)}")
                case {'created': False, 'configured': True}:
                    logger.info(f"Configured existing public bucket: {s3_config['public_bucket']}")
                case _:
                    logger.info(f"No changes to public bucket: {s3_config['public_bucket']}")
        else:
            logger.info("Skipping bucket creation (--init-all not specified)")
        
        # Upload example files if requested
        if args.upload_example:
            logger.info("Uploading example files to buckets...")
            upload_example_files(s3_component, args, logger)
        
        # Housekeeping phase
        if args.clean:
            logger.info("Starting housekeeping phase to clean up buckets...")
            housekeeping_results = cast(HousekeepingResult, s3_component.housekeep())
            
            # Get verification results
            verification = housekeeping_results.get('verification', {})
            
            # Report verification results
            logger.info(f"Bucket verification results:")
            logger.info(f"- Private bucket: {'Verified' if verification.get('private_bucket', False) else 'Failed'}")
            logger.info(f"- Public bucket: {'Verified' if verification.get('public_bucket', False) else 'Failed'}")
            
            # Report any warnings using enhanced pattern matching
            match housekeeping_results:
                case {'warnings': warnings} if warnings:
                    logger.warning(f"Warnings during housekeeping:")
                    for warning in warnings:
                        logger.warning(f"- {warning}")
                case _:
                    logger.info("No warnings during housekeeping")
        
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
