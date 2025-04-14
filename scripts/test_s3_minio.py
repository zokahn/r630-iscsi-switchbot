#!/usr/bin/env python3
"""
test_s3_minio.py - Test S3Component with MinIO

This script tests the S3Component by connecting to a MinIO/S3 server
and performing basic operations to verify functionality.
"""

import os
import sys
import logging
import argparse
import tempfile
import uuid
import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components
from framework.components import S3Component

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
    return logging.getLogger("s3-test")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test S3Component with MinIO/S3")
    
    # S3 connection configuration
    parser.add_argument("--endpoint", required=True, help="S3/MinIO endpoint URL")
    parser.add_argument("--access-key", required=True, help="S3/MinIO access key")
    parser.add_argument("--secret-key", required=True, help="S3/MinIO secret key")
    parser.add_argument("--secure", action="store_true", help="Use HTTPS for connection")
    
    # Test configuration
    parser.add_argument("--test-bucket", default=f"test-bucket-{uuid.uuid4().hex[:8]}", 
                      help="Test bucket name (default: auto-generated)")
    parser.add_argument("--file-size", type=int, default=1024, 
                      help="Size of test file in bytes (default: 1KB)")
    parser.add_argument("--create-buckets", action="store_true", 
                      help="Create the standard project buckets")
    
    # Test actions
    parser.add_argument("--list-only", action="store_true", 
                      help="Only list buckets, don't perform tests")
    parser.add_argument("--cleanup", action="store_true", 
                      help="Clean up test resources after test")
    
    # General options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    
    return parser.parse_args()

def create_test_file(size, logger):
    """Create a test file of the specified size"""
    logger.info(f"Creating test file of {size} bytes")
    
    # Create a temporary file
    fd, path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, 'wb') as f:
            # Write a pattern of data to the file
            timestamp = datetime.datetime.now().isoformat()
            header = f"Test file created at {timestamp}\n".encode('utf-8')
            f.write(header)
            
            # Fill the rest of the file with a pattern to reach the desired size
            remaining = size - len(header)
            if remaining > 0:
                # Create a pattern of letters
                pattern = bytes(range(32, 127)) * ((remaining // 95) + 1)
                f.write(pattern[:remaining])
                
        logger.info(f"Created test file at {path}")
        return path
    except Exception as e:
        logger.error(f"Error creating test file: {e}")
        os.unlink(path)
        return None

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
            'test': args.test_bucket,
            'iso': 'r630-switchbot-isos',
            'binary': 'r630-switchbot-binaries',
            'temp': 'r630-switchbot-temp'
        },
        'create_buckets': args.create_buckets,
        'dry_run': args.dry_run
    }
    
    logger.info(f"Initializing S3Component with endpoint {args.endpoint}")
    s3_component = S3Component(s3_config, logger)
    
    # Discovery phase
    logger.info("Starting discovery phase...")
    try:
        discovery_results = s3_component.discover()
        
        # Display discovery results
        logger.info("Discovery completed:")
        logger.info(f"- Endpoint: {discovery_results.get('endpoint')}")
        logger.info(f"- Connected: {discovery_results.get('connected', False)}")
        
        # Display existing buckets
        existing_buckets = discovery_results.get('buckets', [])
        if existing_buckets:
            logger.info(f"Found {len(existing_buckets)} existing buckets:")
            for bucket in existing_buckets:
                logger.info(f"  - {bucket}")
        else:
            logger.info("No existing buckets found")
        
        # Check if connectivity failed
        if not discovery_results.get('connected', False):
            logger.error("S3/MinIO connectivity failed - cannot proceed with tests")
            if 'connection_error' in discovery_results:
                logger.error(f"Error: {discovery_results['connection_error']}")
            return 1
        
        # Stop here if only listing buckets
        if args.list_only:
            logger.info("List-only mode, skipping tests")
            return 0
        
        # Process phase - create test bucket and upload file
        logger.info("Starting processing phase...")
        
        # Create required buckets first
        if args.create_buckets:
            processing_results = s3_component.process()
            created_buckets = processing_results.get('created_buckets', [])
            if created_buckets:
                logger.info(f"Created {len(created_buckets)} buckets:")
                for bucket in created_buckets:
                    logger.info(f"  - {bucket}")
        
        # Now test with a specific test file
        try:
            # Create a test file
            test_file_path = create_test_file(args.file_size, logger)
            if not test_file_path:
                logger.error("Failed to create test file")
                return 1
            
            try:
                # Make sure test bucket exists
                logger.info(f"Ensuring test bucket {args.test_bucket} exists")
                if args.dry_run:
                    logger.info(f"DRY RUN: Would create bucket {args.test_bucket}")
                else:
                    s3_component.client.make_bucket(args.test_bucket)
                    logger.info(f"Created test bucket {args.test_bucket}")
                
                # Upload the test file
                object_name = f"test-files/test-{uuid.uuid4().hex[:8]}.dat"
                logger.info(f"Uploading test file to {args.test_bucket}/{object_name}")
                
                if args.dry_run:
                    logger.info(f"DRY RUN: Would upload {test_file_path} to {args.test_bucket}/{object_name}")
                else:
                    # Add as artifact
                    s3_component.add_artifact(
                        name="test_file",
                        artifact=test_file_path,
                        metadata={
                            "bucket": args.test_bucket,
                            "object_name": object_name,
                            "content_type": "application/octet-stream",
                            "size": os.path.getsize(test_file_path)
                        }
                    )
                    
                    # Upload artifacts
                    stored_artifacts = s3_component.store_artifacts()
                    logger.info(f"Uploaded test file successfully")
                    
                    # Verify the uploaded file exists
                    logger.info(f"Verifying uploaded file...")
                    object_stat = s3_component.client.stat_object(args.test_bucket, object_name)
                    logger.info(f"File exists in bucket with size {object_stat.size} bytes")
                    
                    # Download the file to verify
                    download_path = os.path.join(tempfile.gettempdir(), f"download-{uuid.uuid4().hex[:8]}.dat")
                    logger.info(f"Downloading file to {download_path}")
                    s3_component.client.fget_object(args.test_bucket, object_name, download_path)
                    
                    # Verify file size
                    download_size = os.path.getsize(download_path)
                    logger.info(f"Downloaded file size: {download_size} bytes")
                    if download_size == args.file_size:
                        logger.info("Download verification successful - file sizes match")
                    else:
                        logger.error(f"Download verification failed - size mismatch: {download_size} != {args.file_size}")
                    
                    # Clean up downloaded file
                    os.unlink(download_path)
                    
                # Cleanup test resources if requested
                if args.cleanup and not args.dry_run:
                    logger.info("Cleaning up test resources...")
                    
                    # Remove the test file from the bucket
                    logger.info(f"Removing test file {object_name} from bucket")
                    s3_component.client.remove_object(args.test_bucket, object_name)
                    
                    # Remove the test bucket if it was created for this test
                    if args.test_bucket not in existing_buckets:
                        logger.info(f"Removing test bucket {args.test_bucket}")
                        s3_component.client.remove_bucket(args.test_bucket)
            
            finally:
                # Clean up the local test file
                if test_file_path and os.path.exists(test_file_path):
                    os.unlink(test_file_path)
                    logger.info(f"Removed local test file {test_file_path}")
            
        except Exception as e:
            logger.error(f"Error during testing: {str(e)}")
            return 1
    
    except Exception as e:
        logger.error(f"Error during discovery: {str(e)}")
        return 1
    
    logger.info("S3/MinIO component test completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
