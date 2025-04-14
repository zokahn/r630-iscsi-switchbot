#!/usr/bin/env python3
"""
S3 Lifecycle Management Script for r630-iscsi-switchbot

This script implements the lifecycle management for S3 objects,
automatically cleaning up old files based on configured retention periods.

Default retention periods:
- ISO files: 365 days (1 year)
- Binary files: 365 days (1 year)
- Artifact files: 365 days (1 year)

Usage:
  ./scripts/s3_lifecycle_cleanup.py [--days DAYS] [--prefix PREFIX] [--dry-run]

Example:
  # Clean up all files older than 90 days
  ./scripts/s3_lifecycle_cleanup.py --days 90

  # Clean up only ISO files older than 30 days
  ./scripts/s3_lifecycle_cleanup.py --days 30 --prefix isos/

  # Dry run to show what would be deleted
  ./scripts/s3_lifecycle_cleanup.py --dry-run
"""

import os
import sys
import logging
import argparse
import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('s3_lifecycle_cleanup')

# Get the path to the scripts directory
script_dir = os.path.dirname(os.path.abspath(__file__))
# Add the parent directory to the path to import the s3_client module
sys.path.append(os.path.dirname(script_dir))
sys.path.append(script_dir)

try:
    from s3_client import S3Client, S3_FOLDERS
except ImportError as e:
    logger.error(f"Error importing S3Client: {e}")
    logger.error("Make sure the s3_client.py module is available and dependencies are installed.")
    logger.error("Run: pip install -r requirements.txt")
    sys.exit(1)

def cleanup_s3_objects(days=365, prefix='', dry_run=False):
    """
    Clean up S3 objects older than the specified number of days
    
    Args:
        days (int): Delete objects older than this many days
        prefix (str): Only delete objects with this prefix
        dry_run (bool): If True, only show what would be deleted without actually deleting
        
    Returns:
        tuple: (deleted_count, skipped_count)
    """
    try:
        # Initialize S3 client
        s3_client = S3Client()
        logger.info(f"Successfully connected to S3 endpoint: {s3_client.endpoint}")
        
        # List objects with the given prefix
        objects = s3_client.list_objects(prefix)
        if not objects:
            logger.info(f"No objects found with prefix '{prefix}'")
            return (0, 0)
        
        logger.info(f"Found {len(objects)} objects with prefix '{prefix}'")
        
        # Calculate cutoff date
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        logger.info(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')} (objects older than this will be deleted)")
        
        # Track counts
        deleted_count = 0
        skipped_count = 0
        
        # Process each object
        for obj in objects:
            try:
                s3_key = obj.get('Key')
                last_modified = obj.get('LastModified')
                
                # Skip if key ends with / (directory marker)
                if s3_key.endswith('/'):
                    logger.debug(f"Skipping directory marker: {s3_key}")
                    skipped_count += 1
                    continue
                
                # Skip .keep files (directory markers)
                if s3_key.endswith('.keep'):
                    logger.debug(f"Skipping directory marker file: {s3_key}")
                    skipped_count += 1
                    continue
                
                # Check metadata for creation date
                metadata = s3_client.get_object_metadata(s3_key)
                creation_date = None
                if metadata and 'creationdate' in metadata:
                    try:
                        creation_date = datetime.datetime.strptime(metadata['creationdate'], '%Y-%m-%d')
                        logger.debug(f"Object {s3_key} has creation date: {creation_date}")
                    except ValueError:
                        logger.warning(f"Invalid creation date format in metadata for {s3_key}: {metadata['creationdate']}")
                
                # If no creation date in metadata, use last modified
                if not creation_date and last_modified:
                    creation_date = last_modified.replace(tzinfo=None)
                    logger.debug(f"Using last modified date for {s3_key}: {creation_date}")
                
                # Skip if no date information
                if not creation_date:
                    logger.warning(f"No date information for {s3_key}, skipping")
                    skipped_count += 1
                    continue
                
                # Check if object is older than cutoff date
                if creation_date < cutoff_date:
                    logger.info(f"Object {s3_key} is older than {days} days (created: {creation_date.strftime('%Y-%m-%d')})")
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would delete: {s3_key}")
                        deleted_count += 1
                    else:
                        if s3_client.delete_object(s3_key):
                            logger.info(f"Deleted: {s3_key}")
                            deleted_count += 1
                        else:
                            logger.error(f"Failed to delete: {s3_key}")
                            skipped_count += 1
                else:
                    logger.debug(f"Object {s3_key} is newer than {days} days (created: {creation_date.strftime('%Y-%m-%d')})")
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing object: {e}")
                skipped_count += 1
                continue
        
        return (deleted_count, skipped_count)
        
    except Exception as e:
        logger.error(f"Error cleaning up S3 objects: {e}")
        return (0, 0)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="S3 Lifecycle Management Script for r630-iscsi-switchbot",
        epilog="This script cleans up old S3 objects based on retention periods."
    )
    parser.add_argument("--days", type=int, default=365, help="Delete objects older than this many days (default: 365)")
    parser.add_argument("--prefix", default="", help="Only delete objects with this prefix (default: all objects)")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually delete, just show what would be deleted")
    
    args = parser.parse_args()
    
    # Check if .env file exists
    env_file = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '.env'
    if not env_file.exists():
        logger.error(f"Environment file {env_file} not found")
        logger.error("Please create a .env file with your S3 credentials")
        logger.error("You can use .env.example as a template")
        return 1
    
    # Run cleanup
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no files will be deleted")
    
    deleted, skipped = cleanup_s3_objects(args.days, args.prefix, args.dry_run)
    
    logger.info(f"S3 lifecycle cleanup completed:")
    logger.info(f"  - Objects processed: {deleted + skipped}")
    logger.info(f"  - Objects deleted: {deleted}")
    logger.info(f"  - Objects skipped: {skipped}")
    
    if args.dry_run:
        logger.info("This was a DRY RUN - no files were actually deleted")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
