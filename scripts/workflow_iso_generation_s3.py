#!/usr/bin/env python3
"""
workflow_iso_generation_s3.py - Orchestrates OpenShift ISO generation and S3 storage

This script demonstrates a complete workflow involving:
1. S3 component to provide persistent storage
2. OpenShift component to generate ISO images
3. Storing and retrieving artifacts from S3
"""

import os
import sys
import logging
import argparse
import json
import tempfile
from pathlib import Path
from datetime import datetime

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
    return logging.getLogger("workflow")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate OpenShift ISO and store in S3"
    )
    
    # OpenShift configuration
    parser.add_argument("--version", default="4.14", help="OpenShift version")
    parser.add_argument("--domain", default="example.com", help="Base domain for OpenShift")
    parser.add_argument("--rendezvous-ip", help="Rendezvous IP address for agent-based install")
    parser.add_argument("--pull-secret", help="Path to pull secret file")
    parser.add_argument("--ssh-key", help="Path to SSH public key file")
    
    # S3/MinIO configuration
    parser.add_argument("--s3-endpoint", default="scratchy.omnisack.nl", help="S3 endpoint URL")
    parser.add_argument("--s3-access-key", help="S3 access key")
    parser.add_argument("--s3-secret-key", help="S3 secret key")
    parser.add_argument("--s3-secure", action="store_true", help="Use HTTPS for S3 connection")
    parser.add_argument("--iso-bucket", default="r630-switchbot-isos", help="Bucket for OpenShift ISOs")
    parser.add_argument("--binary-bucket", default="r630-switchbot-binaries", help="Bucket for OpenShift binaries")
    
    # Workflow options
    parser.add_argument("--skip-iso", action="store_true", help="Skip ISO generation")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading to S3")
    parser.add_argument("--list-only", action="store_true", help="Only list ISOs in S3, don't generate")
    parser.add_argument("--temp-dir", help="Custom temporary directory")
    
    # General options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    
    return parser.parse_args()

def initialize_s3_component(args, logger):
    """Initialize and configure S3Component"""
    s3_config = {
        'endpoint': args.s3_endpoint,
        'access_key': args.s3_access_key, 
        'secret_key': args.s3_secret_key,
        'secure': args.s3_secure,
        'buckets': {
            'iso': args.iso_bucket,
            'binary': args.binary_bucket
        },
        'create_buckets': True,  # Create buckets if they don't exist
        'dry_run': args.dry_run
    }
    
    logger.info(f"Initializing S3Component with endpoint {args.s3_endpoint}")
    s3 = S3Component(s3_config, logger)
    
    # Run discovery phase
    discovery_results = s3.discover()
    if not discovery_results.get('connected', False):
        logger.error("Failed to connect to S3 endpoint")
        return None
        
    # Ensure buckets exist in process phase
    process_results = s3.process()
    
    return s3

def initialize_openshift_component(args, s3_component, logger):
    """Initialize and configure OpenShiftComponent"""
    # Create temporary directory if not specified
    if args.temp_dir:
        output_dir = args.temp_dir
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = tempfile.mkdtemp()
        
    logger.info(f"Using output directory: {output_dir}")
    
    # Configure OpenShift component
    openshift_config = {
        'openshift_version': args.version,
        'domain': args.domain,
        'rendezvous_ip': args.rendezvous_ip,
        'pull_secret_path': args.pull_secret,
        'ssh_key_path': args.ssh_key,
        'output_dir': output_dir,
        'skip_upload': args.skip_upload,
        'upload_to_s3': not args.skip_upload,
        'cleanup_temp_files': not args.temp_dir,  # Only cleanup if using temp dir
        's3_config': {
            'iso_bucket': args.iso_bucket,
            'binary_bucket': args.binary_bucket
        },
        'dry_run': args.dry_run
    }
    
    logger.info(f"Initializing OpenShiftComponent for version {args.version}")
    openshift = OpenShiftComponent(openshift_config, logger)
    
    # Set S3 component for storage
    # In a real implementation, we would create a method to set this
    # but for this example we'll just add it as an attribute
    openshift.s3_component = s3_component
    
    return openshift

def list_isos_in_s3(s3_component, iso_bucket, logger):
    """List OpenShift ISOs stored in S3"""
    logger.info(f"Listing ISOs in bucket {iso_bucket}")
    
    # This is a simplified example - you would implement this using
    # S3Component methods to list objects in a bucket
    try:
        # We'll just reference the MinIO client directly for this example
        objects = s3_component.client.list_objects(iso_bucket, prefix="openshift/", recursive=True)
        
        iso_count = 0
        for obj in objects:
            if obj.object_name.endswith('.iso'):
                size_mb = obj.size / (1024 * 1024)
                logger.info(f"  - {obj.object_name} ({size_mb:.1f} MB, last modified: {obj.last_modified})")
                iso_count += 1
        
        if iso_count == 0:
            logger.info("No ISO files found")
            
        return iso_count
    except Exception as e:
        logger.error(f"Error listing ISOs: {e}")
        return 0

def upload_iso_to_s3(openshift_component, s3_component, iso_bucket, logger):
    """Upload ISO to S3 bucket"""
    # In a real implementation, OpenShiftComponent would use S3Component
    # to store artifacts. For this example script, we'll orchestrate it manually.
    
    iso_path = openshift_component.iso_path
    if not iso_path or not os.path.exists(iso_path):
        logger.error("ISO file not found")
        return False
        
    iso_size = os.path.getsize(iso_path)
    logger.info(f"Uploading ISO {iso_path} ({iso_size/(1024*1024):.1f} MB) to bucket {iso_bucket}")
    
    version = openshift_component.config.get('openshift_version')
    object_name = f"openshift/{version}/agent.x86_64.iso"
    
    if openshift_component.config.get('dry_run', False):
        logger.info(f"DRY RUN: Would upload ISO to {iso_bucket}/{object_name}")
        return True
        
    try:
        # Create metadata JSON file
        metadata_path = os.path.join(os.path.dirname(iso_path), "metadata.json")
        metadata = {
            "version": version,
            "domain": openshift_component.config.get('domain'),
            "rendezvous_ip": openshift_component.config.get('rendezvous_ip'),
            "size_bytes": iso_size,
            "generated_at": datetime.now().isoformat(),
            "md5_hash": openshift_component.housekeeping_results.get('iso_hash')
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        # Upload ISO file
        s3_component.client.fput_object(
            iso_bucket, object_name, iso_path,
            content_type="application/octet-stream"
        )
        
        # Upload metadata file
        metadata_object_name = f"openshift/{version}/metadata.json"
        s3_component.client.fput_object(
            iso_bucket, metadata_object_name, metadata_path,
            content_type="application/json"
        )
        
        logger.info(f"Successfully uploaded ISO and metadata to {iso_bucket}")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading ISO to S3: {e}")
        return False

def main():
    """Main function"""
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    # Initialize S3 component
    s3 = initialize_s3_component(args, logger)
    if not s3:
        return 1
    
    # List ISOs only if requested
    if args.list_only:
        iso_count = list_isos_in_s3(s3, args.iso_bucket, logger)
        logger.info(f"Found {iso_count} ISO files")
        return 0
    
    # Initialize OpenShift component
    openshift = initialize_openshift_component(args, s3, logger)
    
    # Discovery phase
    logger.info("Starting OpenShift component discovery...")
    openshift.discover()
    
    # Skip ISO generation if requested
    if args.skip_iso:
        logger.info("Skipping ISO generation as requested")
    else:
        # Generate ISO
        logger.info("Starting OpenShift ISO generation...")
        openshift.process()
        
        # Verify ISO and perform housekeeping
        logger.info("Performing housekeeping...")
        openshift.housekeep()
    
    # Upload ISO to S3 if it exists and upload not skipped
    if not args.skip_upload and openshift.iso_path and os.path.exists(openshift.iso_path):
        upload_iso_to_s3(openshift, s3, args.iso_bucket, logger)
    
    logger.info("Workflow completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
