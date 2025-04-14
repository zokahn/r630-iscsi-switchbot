#!/usr/bin/env python3
"""
S3 Bucket Setup Script for r630-iscsi-switchbot

This script initializes the S3 bucket structure with the required folders:
- isos/
- binaries/
- artifacts/

It also tests connectivity to the S3 endpoint.
"""

import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('setup_s3_bucket')

# Get the path to the scripts directory
script_dir = os.path.dirname(os.path.abspath(__file__))
# Add the parent directory to the path to import the s3_client module
sys.path.append(os.path.dirname(script_dir))
sys.path.append(script_dir)

try:
    from s3_client import S3Client
except ImportError as e:
    logger.error(f"Error importing S3Client: {e}")
    logger.error("Make sure the s3_client.py module is available and dependencies are installed.")
    logger.error("Run: pip install -r requirements.txt")
    sys.exit(1)

def setup_bucket():
    """Initialize the S3 bucket structure"""
    try:
        # Initialize S3 client
        s3_client = S3Client()
        logger.info(f"Successfully connected to S3 endpoint: {s3_client.endpoint}")
        
        # Create the required folders
        folders = ['isos/', 'binaries/', 'artifacts/']
        
        for folder in folders:
            # Create empty file for folder creation
            key = f"{folder}.keep"
            logger.info(f"Creating folder: {folder}")
            
            # Check if folder exists (by listing objects with the prefix)
            objects = s3_client.list_objects(folder)
            if objects:
                logger.info(f"Folder {folder} already exists with {len(objects)} objects")
                continue
            
            # Create the folder by uploading a small file
            try:
                temp_path = Path(os.path.join('/tmp', '.keep'))
                with open(temp_path, 'w') as f:
                    f.write(f"Folder structure for {folder}")
                
                if s3_client.upload_file(str(temp_path), key):
                    logger.info(f"Successfully created folder: {folder}")
                else:
                    logger.error(f"Failed to create folder: {folder}")
                
                # Clean up temporary file
                if temp_path.exists():
                    os.unlink(temp_path)
                    
            except Exception as e:
                logger.error(f"Error creating folder {folder}: {e}")
        
        logger.info("S3 bucket setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up S3 bucket: {e}")
        return False

def main():
    """Main function"""
    env_file = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '.env'
    
    if not env_file.exists():
        logger.error(f"Environment file {env_file} not found")
        logger.error("Please create a .env file with your S3 credentials")
        logger.error("You can use .env.example as a template")
        return 1
    
    if setup_bucket():
        logger.info("S3 bucket setup completed successfully")
        logger.info("You can now use the S3 storage integration")
        return 0
    else:
        logger.error("S3 bucket setup failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
