#!/usr/bin/env python3
"""
Test Script for Python 3.12 Vault Component

This script demonstrates the usage of the Python 3.12-enhanced VaultComponent
with its improved type annotations and features.
"""

import os
import sys
import json
import logging
import tempfile
from typing import Dict, Any, List, Optional, Literal, cast

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Python 3.12 versions of components
from framework.base_component_py312 import BaseComponent
from framework.components.vault_component_py312 import VaultComponent, VaultConfig


def setup_logging() -> logging.Logger:
    """
    Set up logging for the test script.
    
    Returns:
        A configured logger
    """
    logger = logging.getLogger("vault_component_test_py312")
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


def test_vault_component_discovery(config: VaultConfig, logger: logging.Logger) -> Dict[str, Any]:
    """
    Test the discovery phase of the VaultComponent.
    
    Args:
        config: Vault configuration
        logger: Logger instance
        
    Returns:
        Discovery results
    """
    logger.info("Testing VaultComponent discovery phase with Python 3.12 features")
    
    # Create component
    vault_component = VaultComponent(config, logger)
    
    # Run discovery phase
    discovery_results = vault_component.discover()
    
    # Print results (partially redacted for security)
    secure_results = discovery_results.copy()
    # Redact sensitive information
    if 'token_policies' in secure_results:
        secure_results['token_policies'] = ['[REDACTED]']
    
    logger.info(f"Discovery results: {json.dumps(secure_results, indent=2)}")
    
    # Verify connectivity
    if discovery_results.get('connected', False):
        logger.info("✅ Successfully connected to Vault server")
        logger.info(f"Vault version: {discovery_results.get('vault_version')}")
        
        # Check mount point
        if discovery_results.get('mount_point_exists', False):
            logger.info(f"✅ Mount point '{config.get('vault_mount_point')}' exists")
            logger.info(f"KV version: {discovery_results.get('kv_version')}")
        else:
            logger.warning(f"⚠️ Mount point '{config.get('vault_mount_point')}' does not exist")
            
        # Check token
        if discovery_results.get('token_valid', False):
            logger.info("✅ Token is valid")
        else:
            logger.warning("⚠️ Token is invalid or missing")
    else:
        logger.error("❌ Failed to connect to Vault server")
    
    return discovery_results


def test_vault_component_processing(config: VaultConfig, logger: logging.Logger, discovery_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test the processing phase of the VaultComponent.
    
    Args:
        config: Vault configuration
        logger: Logger instance
        discovery_results: Results from discovery phase
        
    Returns:
        Processing results
    """
    logger.info("Testing VaultComponent processing phase with Python 3.12 features")
    
    # If discovery didn't connect, skip processing
    if not discovery_results.get('connected', False):
        logger.error("❌ Skipping processing due to failed discovery")
        return {'error': 'Skipped due to failed discovery'}
    
    # Create component with recovered state
    vault_component = VaultComponent(config, logger)
    vault_component.discovery_results = discovery_results
    vault_component.connected = True
    vault_component.client_token = config.get('vault_token')
    vault_component.phases_executed['discover'] = True
    
    # Set KV version
    vault_component.kv_version = discovery_results.get('kv_version', '2')
    
    # Run processing phase
    processing_results = vault_component.process()
    
    # Print results
    logger.info(f"Processing results: {json.dumps(processing_results, indent=2)}")
    
    # Check initialization
    if processing_results.get('initialized', False):
        logger.info("✅ Vault component was initialized")
        
        # Check permissions
        if processing_results.get('permissions_verified', False):
            logger.info("✅ Permissions were verified")
        else:
            logger.warning("⚠️ Permission verification failed")
            if 'permissions_error' in processing_results:
                logger.warning(f"Error: {processing_results['permissions_error']}")
    else:
        logger.warning("⚠️ Vault component was not initialized")
        if 'error' in processing_results:
            logger.warning(f"Error: {processing_results['error']}")
    
    return processing_results


def test_vault_component_housekeeping(config: VaultConfig, logger: logging.Logger, 
                                      discovery_results: Dict[str, Any], 
                                      processing_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test the housekeeping phase of the VaultComponent.
    
    Args:
        config: Vault configuration
        logger: Logger instance
        discovery_results: Results from discovery phase
        processing_results: Results from processing phase
        
    Returns:
        Housekeeping results
    """
    logger.info("Testing VaultComponent housekeeping phase with Python 3.12 features")
    
    # If previous phases failed, skip housekeeping
    if not discovery_results.get('connected', False) or 'error' in processing_results:
        logger.error("❌ Skipping housekeeping due to failed previous phases")
        return {'error': 'Skipped due to failed previous phases'}
    
    # Create component with recovered state
    vault_component = VaultComponent(config, logger)
    vault_component.discovery_results = discovery_results
    vault_component.processing_results = processing_results
    vault_component.connected = True
    vault_component.client_token = config.get('vault_token')
    vault_component.phases_executed['discover'] = True
    vault_component.phases_executed['process'] = True
    
    # Set KV version
    vault_component.kv_version = discovery_results.get('kv_version', '2')
    
    # Run housekeeping phase
    housekeeping_results = vault_component.housekeep()
    
    # Print results (partially redacted for security)
    secure_results = housekeeping_results.copy()
    # Redact sensitive information
    if 'token_policies' in secure_results:
        secure_results['token_policies'] = ['[REDACTED]']
    
    logger.info(f"Housekeeping results: {json.dumps(secure_results, indent=2)}")
    
    # Check token status
    token_status = housekeeping_results.get('token_status', 'unknown')
    if token_status == 'valid':
        logger.info("✅ Token is valid")
        
        ttl = housekeeping_results.get('token_ttl', 0)
        renewable = housekeeping_results.get('token_renewable', False)
        logger.info(f"Token TTL: {ttl}s, Renewable: {renewable}")
        
        # Check if token was renewed
        if housekeeping_results.get('renewed', False):
            logger.info(f"✅ Token was renewed (New TTL: {housekeeping_results.get('new_ttl')}s)")
    else:
        logger.warning(f"⚠️ Token status: {token_status}")
        if 'token_error' in housekeeping_results:
            logger.warning(f"Error: {housekeeping_results['token_error']}")
    
    return housekeeping_results


def test_secret_operations(config: VaultConfig, logger: logging.Logger, 
                           discovery_results: Dict[str, Any]) -> None:
    """
    Test secret operations with the VaultComponent.
    
    Args:
        config: Vault configuration
        logger: Logger instance
        discovery_results: Results from discovery phase
    """
    # Skip if discovery didn't connect
    if not discovery_results.get('connected', False) or not discovery_results.get('token_valid', False):
        logger.error("❌ Skipping secret operations due to failed discovery")
        return
    
    logger.info("Testing VaultComponent secret operations with Python 3.12 features")
    
    # Create component with recovered state
    vault_component = VaultComponent(config, logger)
    vault_component.discovery_results = discovery_results
    vault_component.connected = True
    vault_component.client_token = config.get('vault_token')
    vault_component.kv_version = discovery_results.get('kv_version', '2')
    
    # Generate unique test path
    test_path = f"test-py312/secrets-{os.getpid()}"
    test_secrets = {
        "username": "python312-test",
        "password": f"password-{os.getpid()}",
        "pythonVersion": "3.12",
        "features": ["improved typing", "pattern matching"]
    }
    
    try:
        # Test write operation
        logger.info(f"Writing test secret to {test_path}")
        result = vault_component.put_secret(test_path, test_secrets)
        
        if result:
            logger.info("✅ Successfully wrote test secret")
            
            # Test read operation
            logger.info(f"Reading test secret from {test_path}")
            read_data = vault_component.get_secret(test_path)
            
            if read_data:
                logger.info("✅ Successfully read test secret")
                
                # Verify data integrity
                if read_data.get('username') == test_secrets['username'] and \
                   read_data.get('pythonVersion') == test_secrets['pythonVersion']:
                    logger.info("✅ Data integrity verified")
                else:
                    logger.warning("⚠️ Data integrity check failed")
                
                # Test read single key
                username = vault_component.get_secret(test_path, 'username')
                if username == test_secrets['username']:
                    logger.info("✅ Successfully read single key")
                else:
                    logger.warning("⚠️ Failed to read single key")
                
                # Test listing secrets
                parent_path = test_path.split('/')[0]
                secrets_list = vault_component.list_secrets(parent_path)
                
                if secrets_list:
                    logger.info(f"✅ Listed secrets in {parent_path}: {', '.join(secrets_list)}")
                else:
                    logger.warning(f"⚠️ No secrets found in {parent_path}")
                
                # Test delete operation
                logger.info(f"Deleting test secret from {test_path}")
                delete_result = vault_component.delete_secret(test_path)
                
                if delete_result:
                    logger.info("✅ Successfully deleted test secret")
                    
                    # Verify deletion
                    check_data = vault_component.get_secret(test_path)
                    if check_data is None:
                        logger.info("✅ Verified secret was deleted")
                    else:
                        logger.warning("⚠️ Secret still exists after deletion")
                else:
                    logger.warning("⚠️ Failed to delete test secret")
            else:
                logger.warning("⚠️ Failed to read test secret")
        else:
            logger.warning("⚠️ Failed to write test secret")
            
    except Exception as e:
        logger.error(f"Error during secret operations testing: {str(e)}")


def run_all_tests() -> None:
    """
    Run all VaultComponent tests.
    """
    logger = setup_logging()
    logger.info("Starting Python 3.12 VaultComponent tests")
    
    # Create test configuration - secure options for test usage
    # This uses values from environment or defaults
    config: VaultConfig = {
        'vault_addr': os.environ.get('VAULT_ADDR', 'http://127.0.0.1:8200'),
        'vault_token': os.environ.get('VAULT_TOKEN', None),
        'vault_mount_point': os.environ.get('VAULT_MOUNT_POINT', 'secret'),
        'vault_path_prefix': os.environ.get('VAULT_PATH_PREFIX', 'r630-switchbot-test'),
        'verify_ssl': False if os.environ.get('VAULT_SKIP_VERIFY', '').lower() == 'true' else True,
        'create_path_prefix': True
    }
    
    # Run tests in sequence
    discovery_results = test_vault_component_discovery(config, logger)
    if discovery_results.get('connected', False):
        processing_results = test_vault_component_processing(config, logger, discovery_results)
        if 'error' not in processing_results:
            test_vault_component_housekeeping(config, logger, discovery_results, processing_results)
            test_secret_operations(config, logger, discovery_results)
    
    logger.info("Python 3.12 VaultComponent tests completed")


if __name__ == "__main__":
    run_all_tests()
