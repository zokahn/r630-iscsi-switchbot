#!/usr/bin/env python3
"""
Test Script for Python 3.12 S3 Component

This script demonstrates the usage of the Python 3.12-enhanced S3Component
with its improved type annotations and features.
"""

import os
import sys
import json
import logging
import tempfile
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Python 3.12 versions of components
from framework.base_component_py312 import BaseComponent
from framework.components.s3_component_py312 import S3Component, S3Config


def setup_logging() -> logging.Logger:
    """
    Set up logging for the test script.
    
    Returns:
        A configured logger
    """
    logger = logging.getLogger("s3_component_test_py312")
    logger.setLevel(logging.DEBUG)
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


def test_s3_component_discovery(config: S3Config, logger: logging.Logger) -> Dict[str, Any]:
    """
    Test the discovery phase of the S3Component.
    
    Args:
        config: S3 configuration
        logger: Logger instance
        
    Returns:
        Discovery results
    """
    logger.info("Testing S3Component discovery phase with Python 3.12 features")
    
    # Create component
    s3_component = S3Component(config, logger)
    
    # Run discovery phase
    discovery_results = s3_component.discover()
    
    # Print results
    logger.info(f"Discovery results: {json.dumps(discovery_results, indent=2)}")
    
    # Verify connectivity
    if discovery_results.get('connectivity', False):
        logger.info("✅ Successfully connected to S3 endpoint")
        logger.info(f"Found {discovery_results.get('bucket_count', 0)} buckets")
        
        # Check buckets
        for bucket_type in ['private', 'public']:
            if discovery_results.get('buckets', {}).get(bucket_type, {}).get('exists', False):
                logger.info(f"✅ {bucket_type.capitalize()} bucket exists")
                logger.info(f"Contains {discovery_results.get('buckets', {}).get(bucket_type, {}).get('objects_count', 0)} objects")
            else:
                logger.warning(f"⚠️ {bucket_type.capitalize()} bucket does not exist")
    else:
        logger.error("❌ Failed to connect to S3 endpoint")
    
    return discovery_results


def test_s3_component_processing(config: S3Config, logger: logging.Logger, discovery_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test the processing phase of the S3Component.
    
    Args:
        config: S3 configuration
        logger: Logger instance
        discovery_results: Results from discovery phase
        
    Returns:
        Processing results
    """
    logger.info("Testing S3Component processing phase with Python 3.12 features")
    
    # If discovery didn't connect, skip processing
    if not discovery_results.get('connectivity', False):
        logger.error("❌ Skipping processing due to failed discovery")
        return {'error': 'Skipped due to failed discovery'}
    
    # Create component with recovered state
    s3_component = S3Component(config, logger)
    s3_component.discovery_results = discovery_results
    s3_component.phases_executed['discover'] = True
    
    # Run processing phase
    processing_results = s3_component.process()
    
    # Print results
    logger.info(f"Processing results: {json.dumps(processing_results, indent=2)}")
    
    # Check actions
    if processing_results.get('actions'):
        logger.info(f"Performed {len(processing_results.get('actions', []))} actions")
        for action in processing_results.get('actions', []):
            logger.info(f"  - {action}")
    else:
        logger.warning("⚠️ No actions performed during processing")
    
    return processing_results


def test_s3_component_housekeeping(config: S3Config, logger: logging.Logger, 
                                   discovery_results: Dict[str, Any], 
                                   processing_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test the housekeeping phase of the S3Component.
    
    Args:
        config: S3 configuration
        logger: Logger instance
        discovery_results: Results from discovery phase
        processing_results: Results from processing phase
        
    Returns:
        Housekeeping results
    """
    logger.info("Testing S3Component housekeeping phase with Python 3.12 features")
    
    # If previous phases failed, skip housekeeping
    if not discovery_results.get('connectivity', False) or 'error' in processing_results:
        logger.error("❌ Skipping housekeeping due to failed previous phases")
        return {'error': 'Skipped due to failed previous phases'}
    
    # Create component with recovered state
    s3_component = S3Component(config, logger)
    s3_component.discovery_results = discovery_results
    s3_component.processing_results = processing_results
    s3_component.phases_executed['discover'] = True
    s3_component.phases_executed['process'] = True
    
    # Run housekeeping phase
    housekeeping_results = s3_component.housekeep()
    
    # Print results
    logger.info(f"Housekeeping results: {json.dumps(housekeeping_results, indent=2)}")
    
    # Check verifications
    for verification, status in housekeeping_results.get('verification', {}).items():
        if status:
            logger.info(f"✅ Verified {verification}")
        else:
            logger.warning(f"⚠️ Failed to verify {verification}")
    
    # Check warnings
    if housekeeping_results.get('warnings'):
        logger.warning(f"Found {len(housekeeping_results.get('warnings', []))} warnings during housekeeping")
        for warning in housekeeping_results.get('warnings', []):
            logger.warning(f"  - {warning}")
    
    return housekeeping_results


def test_s3_component_artifact_handling(config: S3Config, logger: logging.Logger) -> None:
    """
    Test artifact handling with the S3Component.
    
    Args:
        config: S3 configuration
        logger: Logger instance
    """
    logger.info("Testing S3Component artifact handling with Python 3.12 features")
    
    # Create component
    s3_component = S3Component(config, logger)
    
    # First discover and process to ensure buckets exist
    s3_component.discover()
    s3_component.process()
    
    # Create a test file
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        temp_file = f.name
        f.write(b"This is a test artifact file for Python 3.12 S3Component")
    
    try:
        # Add string artifact
        string_id = s3_component.add_artifact(
            "test-string",
            "This is a test string artifact from Python 3.12",
            {"description": "Test string artifact", "format": "text/plain"}
        )
        logger.info(f"Added string artifact with ID: {string_id}")
        
        # Add file artifact
        file_id = s3_component.add_artifact(
            "test-file",
            temp_file,
            {"description": "Test file artifact", "format": "text/plain"}
        )
        logger.info(f"Added file artifact with ID: {file_id}")
        
        # Add JSON artifact
        json_id = s3_component.add_artifact(
            "test-json",
            {"test": True, "python_version": "3.12", "features": ["improved typing", "dict merging"]},
            {"description": "Test JSON artifact", "format": "application/json"}
        )
        logger.info(f"Added JSON artifact with ID: {json_id}")
        
        # Store artifacts
        s3_component._store_artifacts()
        logger.info(f"Stored {len(s3_component.artifacts)} artifacts")
        
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_iso_operations(config: S3Config, logger: logging.Logger) -> None:
    """
    Test ISO operations with the S3Component.
    
    Note: This is a simulation only as we don't have actual ISO files.
    
    Args:
        config: S3 configuration
        logger: Logger instance
    """
    logger.info("Testing S3Component ISO operations simulation with Python 3.12 features")
    
    # Create component and ensure basics work
    s3_component = S3Component(config, logger)
    s3_component.discover()
    
    # List ISOs (if any)
    try:
        isos = s3_component.list_isos()
        logger.info(f"Found {len(isos)} ISOs in S3 storage")
        
        # Show first few
        for iso in isos[:3]:
            logger.info(f"ISO: {iso.get('key')} - Size: {iso.get('size')}")
            
    except Exception as e:
        logger.error(f"Error listing ISOs: {str(e)}")


def run_all_tests() -> None:
    """
    Run all S3Component tests.
    """
    logger = setup_logging()
    logger.info("Starting Python 3.12 S3Component tests")
    
    # Create test configuration
    # Note: This uses default values and environment variables
    config: S3Config = {
        'create_buckets_if_missing': False,  # Set to True to create buckets if needed
        'create_metadata_index': True
    }
    
    # Run tests in sequence
    discovery_results = test_s3_component_discovery(config, logger)
    if discovery_results.get('connectivity', False):
        processing_results = test_s3_component_processing(config, logger, discovery_results)
        if 'error' not in processing_results:
            test_s3_component_housekeeping(config, logger, discovery_results, processing_results)
            test_s3_component_artifact_handling(config, logger)
            test_iso_operations(config, logger)
    
    logger.info("Python 3.12 S3Component tests completed")


if __name__ == "__main__":
    run_all_tests()
