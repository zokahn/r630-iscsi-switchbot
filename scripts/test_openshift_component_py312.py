#!/usr/bin/env python3
"""
Test Script for Python 3.12 OpenShift Component

This script demonstrates the usage of the Python 3.12-enhanced OpenShiftComponent
with its improved type annotations and features.
"""

import os
import sys
import json
import logging
import tempfile
from typing import Dict, Any, List, Optional, Union, cast

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Python 3.12 versions of components
from framework.base_component_py312 import BaseComponent
from framework.components.openshift_component_py312 import OpenShiftComponent, OpenShiftConfig
from framework.components.s3_component_py312 import S3Component


def setup_logging() -> logging.Logger:
    """
    Set up logging for the test script.
    
    Returns:
        A configured logger
    """
    logger = logging.getLogger("openshift_component_test_py312")
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


def setup_s3_component(logger: logging.Logger) -> Optional[S3Component]:
    """
    Set up S3Component if credentials are available.
    
    Args:
        logger: Logger instance
        
    Returns:
        S3Component instance or None if credentials not available
    """
    # Check if we have S3 credentials in environment
    endpoint = os.environ.get('S3_ENDPOINT')
    access_key = os.environ.get('S3_ACCESS_KEY')
    secret_key = os.environ.get('S3_SECRET_KEY')
    
    if not all([endpoint, access_key, secret_key]):
        logger.warning("S3 credentials not available, skipping S3 component setup")
        return None
    
    try:
        s3_config = {
            's3_endpoint': endpoint,
            's3_access_key': access_key,
            's3_secret_key': secret_key,
            's3_bucket': os.environ.get('S3_BUCKET', 'r630-switchbot-test'),
            'create_bucket': True
        }
        
        logger.info(f"Creating S3 component with endpoint: {endpoint}")
        s3_component = S3Component(s3_config, logger)
        
        # Run discovery to initialize the component
        discovery_result = s3_component.discover()
        
        if discovery_result.get('connected', False):
            logger.info("Successfully connected to S3")
            return s3_component
        else:
            logger.warning("Failed to connect to S3")
            return None
    except Exception as e:
        logger.error(f"Error setting up S3 component: {str(e)}")
        return None


def test_openshift_component_discovery(config: OpenShiftConfig, logger: logging.Logger, 
                                      s3_component: Optional[S3Component] = None) -> Dict[str, Any]:
    """
    Test the discovery phase of the OpenShiftComponent.
    
    Args:
        config: OpenShift configuration
        logger: Logger instance
        s3_component: Optional S3Component
        
    Returns:
        Discovery results
    """
    logger.info("Testing OpenShiftComponent discovery phase with Python 3.12 features")
    
    # Create component
    openshift_component = OpenShiftComponent(config, logger, s3_component)
    
    # Run discovery phase
    discovery_results = openshift_component.discover()
    
    # Print results
    logger.info(f"Discovery results: {json.dumps(discovery_results, indent=2)}")
    
    # Verify available versions
    if discovery_results.get('available_versions'):
        versions = discovery_results['available_versions']
        logger.info(f"✅ Found {len(versions)} available OpenShift versions: {', '.join(versions)}")
    else:
        logger.warning("⚠️ No OpenShift versions found")
    
    # Check for OpenShift installer
    if discovery_results.get('installer_available'):
        logger.info(f"✅ OpenShift installer found at: {discovery_results.get('installer_path')}")
    else:
        logger.warning("⚠️ OpenShift installer not found")
    
    # Check for pull secret
    if discovery_results.get('pull_secret_available'):
        logger.info(f"✅ Pull secret found at: {discovery_results.get('pull_secret_path')}")
    else:
        logger.warning("⚠️ Pull secret not found")
    
    # Check for SSH key
    if discovery_results.get('ssh_key_available'):
        logger.info(f"✅ SSH key found at: {discovery_results.get('ssh_key_path')}")
    else:
        logger.warning("⚠️ SSH key not found")
    
    # Check temp directory
    if temp_dir := discovery_results.get('temp_dir'):
        logger.info(f"✅ Temporary directory set up at: {temp_dir}")
    else:
        logger.warning("⚠️ Temporary directory not set up")
    
    return discovery_results


def test_openshift_component_processing(config: OpenShiftConfig, logger: logging.Logger, 
                                       discovery_results: Dict[str, Any],
                                       s3_component: Optional[S3Component] = None) -> Dict[str, Any]:
    """
    Test the processing phase of the OpenShiftComponent.
    
    Args:
        config: OpenShift configuration
        logger: Logger instance
        discovery_results: Results from discovery phase
        s3_component: Optional S3Component
        
    Returns:
        Processing results
    """
    logger.info("Testing OpenShiftComponent processing phase with Python 3.12 features")
    
    # Create component
    openshift_component = OpenShiftComponent(config, logger, s3_component)
    
    # Set component state from discovery
    openshift_component.discovery_results = discovery_results
    openshift_component.temp_dir = discovery_results.get('temp_dir')
    openshift_component.phases_executed['discover'] = True
    
    # Run processing phase
    processing_results = openshift_component.process()
    
    # Print results
    logger.info(f"Processing results: {json.dumps(processing_results, indent=2)}")
    
    # Check installer download
    if processing_results.get('installer_downloaded'):
        logger.info(f"✅ OpenShift installer downloaded from {processing_results.get('installer_source')}")
    else:
        logger.warning("⚠️ OpenShift installer not downloaded")
        if 'installer_error' in processing_results:
            logger.warning(f"Error: {processing_results['installer_error']}")
    
    # Check ISO generation
    if processing_results.get('iso_generated'):
        logger.info(f"✅ ISO generated at: {processing_results.get('iso_path')}")
    else:
        logger.warning("⚠️ ISO not generated")
    
    # Check S3 upload
    if upload_status := processing_results.get('upload_status'):
        if upload_status == 'success':
            logger.info(f"✅ ISO uploaded to S3: {processing_results.get('s3_iso_path')}")
        else:
            logger.warning(f"⚠️ ISO upload {upload_status}")
            if 'upload_error' in processing_results:
                logger.warning(f"Error: {processing_results['upload_error']}")
    
    return processing_results


def test_openshift_component_housekeeping(config: OpenShiftConfig, logger: logging.Logger, 
                                         discovery_results: Dict[str, Any],
                                         processing_results: Dict[str, Any],
                                         s3_component: Optional[S3Component] = None) -> Dict[str, Any]:
    """
    Test the housekeeping phase of the OpenShiftComponent.
    
    Args:
        config: OpenShift configuration
        logger: Logger instance
        discovery_results: Results from discovery phase
        processing_results: Results from processing phase
        s3_component: Optional S3Component
        
    Returns:
        Housekeeping results
    """
    logger.info("Testing OpenShiftComponent housekeeping phase with Python 3.12 features")
    
    # Create component
    openshift_component = OpenShiftComponent(config, logger, s3_component)
    
    # Set component state
    openshift_component.discovery_results = discovery_results
    openshift_component.processing_results = processing_results
    openshift_component.temp_dir = discovery_results.get('temp_dir')
    openshift_component.iso_path = processing_results.get('iso_path')
    openshift_component.phases_executed['discover'] = True
    openshift_component.phases_executed['process'] = True
    
    # Run housekeeping phase
    housekeeping_results = openshift_component.housekeep()
    
    # Print results
    logger.info(f"Housekeeping results: {json.dumps(housekeeping_results, indent=2)}")
    
    # Check ISO verification
    if housekeeping_results.get('iso_verified'):
        logger.info(f"✅ ISO verified with hash: {housekeeping_results.get('iso_hash')}")
    else:
        logger.warning("⚠️ ISO not verified")
    
    # Check temp file cleanup
    if housekeeping_results.get('temp_files_cleaned'):
        logger.info("✅ Temporary files cleaned up")
    else:
        logger.warning("⚠️ Temporary files not cleaned up")
    
    # Check metadata update
    if housekeeping_results.get('metadata_updated'):
        logger.info("✅ Metadata updated")
    else:
        logger.warning("⚠️ Metadata not updated")
    
    return housekeeping_results


def run_all_tests(dry_run: bool = True) -> None:
    """
    Run all OpenShiftComponent tests.
    
    Args:
        dry_run: If True, skip actual ISO generation and use placeholders
    """
    logger = setup_logging()
    logger.info("Starting Python 3.12 OpenShiftComponent tests")
    
    # Set up S3 component if possible
    s3_component = setup_s3_component(logger)
    
    # Create test directory
    output_dir = tempfile.mkdtemp(prefix="openshift-py312-test-")
    logger.info(f"Created test directory: {output_dir}")
    
    # Create test configuration
    config: OpenShiftConfig = {
        'openshift_version': os.environ.get('OPENSHIFT_VERSION', 'stable'),
        'domain': 'test.example.com',
        'rendezvous_ip': '192.168.1.1',
        'output_dir': output_dir,
        'skip_upload': not s3_component,  # Skip upload if no S3 component
        'cleanup_temp_files': False,  # Keep files for inspection in test
        'hostname': 'test-host',
        'server_id': f"test-{os.getpid()}"
    }
    
    if dry_run:
        logger.info("Running in DRY RUN mode - skipping actual ISO generation")
        # Override methods to use placeholders for dry run
        OpenShiftComponent._download_installer = lambda self: setattr(self.processing_results, 'installer_downloaded', True)
        OpenShiftComponent._create_install_configs = lambda self: setattr(self.processing_results, 'configs_created', True)
        OpenShiftComponent._generate_iso = lambda self: (
            setattr(self.processing_results, 'iso_generated', True),
            setattr(self.processing_results, 'iso_path', os.path.join(self.temp_dir or '', "agent.x86_64.iso")),
            setattr(self, 'iso_path', os.path.join(self.temp_dir or '', "agent.x86_64.iso")),
            # Create dummy ISO file for testing
            open(os.path.join(self.temp_dir or '', "agent.x86_64.iso"), 'wb').write(b'DUMMY ISO CONTENT')
        )
    
    try:
        # Run tests in sequence
        discovery_results = test_openshift_component_discovery(config, logger, s3_component)
        processing_results = test_openshift_component_processing(config, logger, discovery_results, s3_component)
        housekeeping_results = test_openshift_component_housekeeping(config, logger, discovery_results, processing_results, s3_component)
    
    finally:
        # Clean up test directory if needed
        if os.path.exists(output_dir) and os.environ.get('KEEP_TEST_FILES') != 'true':
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
            logger.info(f"Cleaned up test directory: {output_dir}")
    
    logger.info("Python 3.12 OpenShiftComponent tests completed")


if __name__ == "__main__":
    # Check if we should do a real run or dry run
    real_run = os.environ.get('OPENSHIFT_REAL_RUN', '').lower() in ['true', '1', 'yes']
    run_all_tests(dry_run=not real_run)
