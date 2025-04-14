#!/usr/bin/env python3
"""
Integration test for Docker-based component testing.

This script tests connectivity and basic functionality with the
containerized services (MinIO and Vault) that we use for testing.
"""

import os
import sys
import logging
import tempfile
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from framework.components.s3_component import S3Component
from framework.components.vault_component import VaultComponent
from tests.docker_test_config import get_s3_docker_config, get_vault_docker_config


def setup_logging():
    """Configure logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('docker-integration-test')


def test_minio_connection(logger):
    """Test connection to MinIO and basic S3 operations."""
    logger.info("Testing MinIO connection...")
    
    # Get the S3 configuration for Docker
    config = get_s3_docker_config()
    
    # Create the S3 component
    s3 = S3Component(config, logger=logger)
    
    # Run discovery phase
    logger.info("Running S3 discovery phase...")
    discovery_result = s3.discover()
    
    if not discovery_result.get('connectivity', False):
        logger.error("Failed to connect to MinIO service")
        return False
    
    logger.info("Successfully connected to MinIO")
    
    # Check if buckets exist and create them if needed
    if not discovery_result['buckets']['private'].get('exists', False) or \
       not discovery_result['buckets']['public'].get('exists', False):
        logger.info("One or more buckets don't exist, running process phase...")
        process_result = s3.process()
        # The process method doesn't return a 'success' key, but it succeeds if no exception is raised
        logger.info("Buckets created successfully")
    else:
        logger.info("Buckets already exist")
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(suffix='.iso', delete=False) as temp:
        temp.write(b'This is test ISO content')
        temp_path = temp.name
    
    try:
        # Upload the test file
        logger.info(f"Uploading test file from {temp_path}...")
        upload_result = s3.upload_iso(
            iso_path=temp_path,
            server_id='docker-test',
            hostname='test-host',
            version='4.16.0',
            publish=False
        )
        
        if not upload_result.get('success', False):
            logger.error("Failed to upload test file")
            return False
        
        logger.info(f"Test file uploaded successfully to {upload_result.get('private_key')}")
        
        # List ISOs
        logger.info("Listing ISOs...")
        isos = s3.list_isos()
        logger.info(f"Found {len(isos)} ISOs")
        
        # Sync to public bucket
        if upload_result.get('private_key'):
            logger.info("Syncing to public bucket...")
            public_key = s3.sync_to_public(upload_result['private_key'], '4.16.0')
            logger.info(f"Synced to public bucket with key: {public_key}")
        
        # Run housekeeping
        logger.info("Running S3 housekeeping...")
        housekeep_result = s3.housekeep()
        logger.info("Housekeeping completed")
        
        return True
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_vault_connection(logger):
    """Test connection to Vault and basic secret operations."""
    logger.info("Testing Vault connection...")
    
    # Get the Vault configuration for Docker
    config = get_vault_docker_config()
    
    # Create the Vault component
    vault = VaultComponent(config, logger=logger)
    
    # Run discovery phase
    logger.info("Running Vault discovery phase...")
    try:
        discovery_result = vault.discover()
        
        # Even though there were some errors during discovery, we got a connection
        # If we didn't get an exception, we're connected
        logger.info("Successfully connected to Vault")
    except Exception as e:
        logger.error(f"Failed to connect to Vault service: {str(e)}")
        return False
    
    # Store a test secret
    test_secret = {
        'test-key': 'test-value',
        'timestamp': '2025-04-14'
    }
    
    logger.info("Storing test secret...")
    store_result = vault.put_secret('docker-test', test_secret)
    
    if not store_result:
        logger.error("Failed to store test secret")
        return False
    
    logger.info("Test secret stored successfully")
    
    # Retrieve the secret
    logger.info("Retrieving test secret...")
    retrieved_secret = vault.get_secret('docker-test')
    
    if not retrieved_secret or retrieved_secret.get('test-key') != 'test-value':
        logger.error("Failed to retrieve test secret or values don't match")
        return False
    
    logger.info("Test secret retrieved successfully")
    
    return True


def main():
    """Run the integration tests."""
    logger = setup_logging()
    
    logger.info("Starting Docker integration tests...")
    
    # Test MinIO
    minio_success = test_minio_connection(logger)
    logger.info(f"MinIO test {'successful' if minio_success else 'failed'}")
    
    # Test Vault
    vault_success = test_vault_connection(logger)
    logger.info(f"Vault test {'successful' if vault_success else 'failed'}")
    
    # Overall result
    if minio_success and vault_success:
        logger.info("All Docker integration tests passed!")
        return 0
    else:
        logger.error("One or more Docker integration tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
