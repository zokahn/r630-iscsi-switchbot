#!/usr/bin/env python3
"""
setup_minio_buckets.py - Configure MinIO buckets for persistent storage

This script sets up MinIO buckets for OpenShift ISOs, binaries, and temporary storage
using the component infrastructure.
"""

import os
import sys
import logging
import argparse
import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components
from framework.components import S3Component, OpenShiftComponent

def setup_logging(verbose=False):
    """Set up logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("minio-setup")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Set up MinIO buckets for persistent storage")
    
    # MinIO connection configuration
    parser.add_argument("--endpoint", default="scratchy.omnisack.nl", help="MinIO endpoint URL")
    parser.add_argument("--access-key", help="MinIO access key")
    parser.add_argument("--secret-key", help="MinIO secret key")
    parser.add_argument("--secure", action="store_true", help="Use HTTPS for MinIO connection")
    
    # Bucket configuration
    parser.add_argument("--iso-bucket", default="r630-switchbot-isos", help="Bucket for OpenShift ISOs")
    parser.add_argument("--binary-bucket", default="r630-switchbot-binaries", help="Bucket for OpenShift binaries")
    parser.add_argument("--temp-bucket", default="r630-switchbot-temp", help="Bucket for temporary storage")
    
    # Initialization options
    parser.add_argument("--init-all", action="store_true", help="Initialize all buckets")
    parser.add_argument("--upload-example", action="store_true", help="Upload example files to test buckets")
    parser.add_argument("--clean", action="store_true", help="Clean up buckets (remove all objects)")
    
    # General options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    # S3 configuration
    s3_config = {
        'endpoint': args.endpoint,
        'access_key': args.access_key,
        'secret_key': args.secret_key,
        'secure': args.secure,
        'buckets': {
            'iso': args.iso_bucket,
            'binary': args.binary_bucket,
            'temp': args.temp_bucket
        },
        'create_buckets': args.init_all,
        'dry_run': args.dry_run
    }
    
    # Initialize S3Component
    logger.info("Initializing S3Component...")
    s3_component = S3Component(s3_config, logger)
    
    # Discovery phase
    logger.info("Starting discovery phase...")
    discovery_results = s3_component.discover()
    
    logger.info(f"Discovery completed:")
    logger.info(f"- Endpoint: {discovery_results.get('endpoint')}")
    logger.info(f"- Connected: {discovery_results.get('connected', False)}")
    
    # Show discovered buckets
    existing_buckets = discovery_results.get('buckets', [])
    if existing_buckets:
        logger.info(f"Discovered {len(existing_buckets)} buckets:")
        for bucket in existing_buckets:
            logger.info(f"  - {bucket}")
    else:
        logger.warning("No existing buckets found")
    
    # Process phase (create buckets)
    if args.init_all:
        logger.info("Starting processing phase to create buckets...")
        processing_results = s3_component.process()
        
        created_buckets = processing_results.get('created_buckets', [])
        if created_buckets:
            logger.info(f"Created {len(created_buckets)} buckets:")
            for bucket in created_buckets:
                logger.info(f"  - {bucket}")
    
    # Upload example files if requested
    if args.upload_example:
        logger.info("Uploading example files to buckets...")
        
        # Create a temporary example file
        example_path = os.path.join(os.getcwd(), "example.txt")
        with open(example_path, "w") as f:
            f.write(f"Example file created at {datetime.datetime.now().isoformat()}\n")
            f.write("This is used to test the MinIO bucket setup.\n")
        
        try:
            # Upload to all buckets
            for bucket_type, bucket_name in s3_config['buckets'].items():
                object_name = f"example/example-{bucket_type}.txt"
                
                # Add the example file as an artifact
                logger.info(f"Uploading example file to {bucket_name}/{object_name}")
                s3_component.add_artifact(
                    name="example_file",
                    artifact=example_path,
                    metadata={
                        "bucket": bucket_name,
                        "object_name": object_name,
                        "content_type": "text/plain"
                    }
                )
            
            # Upload artifacts
            s3_component.store_artifacts()
            
        finally:
            # Clean up temporary file
            if os.path.exists(example_path):
                os.unlink(example_path)
                logger.info(f"Removed temporary file {example_path}")
    
    # Housekeeping phase
    if args.clean:
        logger.info("Starting housekeeping phase to clean up buckets...")
        s3_component.housekeep()
    
    logger.info("MinIO setup completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
