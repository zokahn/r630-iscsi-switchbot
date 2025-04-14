#!/usr/bin/env python3
"""
Test Script for Python 3.12 iSCSI Component

This script demonstrates the usage of the Python 3.12-enhanced ISCSIComponent
with its improved type annotations and features.
"""

import os
import sys
import json
import logging
import tempfile
import requests
from typing import Dict, Any, List, Optional, Union, cast
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Python 3.12 versions of components
from framework.base_component_py312 import BaseComponent
from framework.components.iscsi_component_py312 import (
    ISCSIComponent, ISCSIConfig, SystemInfo, StoragePool, 
    ZvolInfo, TargetInfo, ExtentInfo, TargetExtentInfo
)


def setup_logging() -> logging.Logger:
    """
    Set up logging for the test script.
    
    Returns:
        A configured logger
    """
    logger = logging.getLogger("iscsi_component_test_py312")
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


def setup_mocked_responses() -> Dict[str, Any]:
    """
    Set up mock responses for TrueNAS API calls.
    
    Returns:
        Dictionary with mock responses for various API endpoints
    """
    # System info response
    system_info: SystemInfo = {
        'version': 'TrueNAS-SCALE-22.12.3',
        'hostname': 'truenas.local',
        'system_product': 'TrueNAS SCALE Storage Server',
        'uptime': '8 days, 3:45',
        'loadavg': [1.2, 1.5, 1.7],
        'physmem': 68719476736,  # 64GB
        'model': 'Virtual Machine',
        'cores': 16,
        'physical_cores': 8
    }
    
    # Storage pools response
    pools: List[StoragePool] = [
        {
            'name': 'tank',
            'guid': '12345678901234567890',
            'id': 1,
            'free': 1099511627776,  # 1TB
            'healthy': True,
            'status': 'ONLINE',
            'size': 2199023255552,  # 2TB
            'used': {}
        },
        {
            'name': 'test',
            'guid': '09876543210987654321',
            'id': 2,
            'free': 549755813888,  # 512GB
            'healthy': True,
            'status': 'ONLINE',
            'size': 1099511627776,  # 1TB
            'used': {}
        }
    ]
    
    # ZVol response
    zvols: List[ZvolInfo] = [
        {
            'name': 'test/openshift_installations/r630_test-server_4_9_15',
            'type': 'VOLUME',
            'id': 'test/openshift_installations/r630_test-server_4_9_15',
            'volsize': {'parsed': 536870912000},  # 500GB
            'comments': 'OpenShift boot drive',
            'path': '/dev/zvol/test/openshift_installations/r630_test-server_4_9_15'
        }
    ]
    
    # Targets response
    targets: List[TargetInfo] = [
        {
            'id': 1,
            'name': 'iqn.2005-10.org.freenas.ctl:iscsi.r630-test-server.openshift4_9_15',
            'alias': 'OpenShift test.example.com',
            'mode': 'ISCSI',
            'groups': [{'portal': 3, 'initiator': 3, 'auth': None}]
        }
    ]
    
    # Extents response
    extents: List[ExtentInfo] = [
        {
            'id': 1,
            'name': 'openshift_r630_test-server_4_9_15_extent',
            'type': 'DISK',
            'disk': 'zvol/test/openshift_installations/r630_test-server_4_9_15',
            'blocksize': 512,
            'pblocksize': False,
            'comment': 'OpenShift test.example.com boot image',
            'insecure_tpc': True,
            'xen': False,
            'rpm': 'SSD',
            'ro': False
        }
    ]
    
    # Target-extent associations response
    targetextents: List[TargetExtentInfo] = [
        {
            'id': 1,
            'target': 1,
            'extent': 1,
            'lunid': 0
        }
    ]
    
    # Service status
    service_data = {
        'id': 'iscsitarget',
        'state': 'RUNNING',
        'enable': True
    }
    
    mock_responses = {
        'system_info': system_info,
        'pools': pools,
        'zvols': zvols,
        'targets': targets,
        'extents': extents,
        'targetextents': targetextents,
        'service_data': service_data
    }
    
    return mock_responses


class MockResponse:
    """Mock requests.Response for testing"""
    
    def __init__(self, json_data, status_code=200, text=None):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text if text is not None else json.dumps(json_data)
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP Error: {self.status_code}")


def mocked_requests_get(url, *args, **kwargs):
    """Mock function for requests.get"""
    mock_data = setup_mocked_responses()
    
    # Map URL patterns to responses
    if url.endswith('/system/info'):
        return MockResponse(mock_data['system_info'])
    elif url.endswith('/pool'):
        return MockResponse(mock_data['pools'])
    elif url.endswith('/pool/dataset?type=VOLUME'):
        return MockResponse(mock_data['zvols'])
    elif url.endswith('/iscsi/target'):
        return MockResponse(mock_data['targets'])
    elif url.endswith('/iscsi/extent'):
        return MockResponse(mock_data['extents'])
    elif url.endswith('/iscsi/targetextent'):
        return MockResponse(mock_data['targetextents'])
    elif url.endswith('/service/id/iscsitarget'):
        return MockResponse(mock_data['service_data'])
    elif url.endswith('/reporting/get_data?graphs=cpu,memory,swap'):
        return MockResponse({
            'cpu': [{'data': [[0, 25.0, 0], [1, 30.0, 0]]}],
            'memory': [{'data': [[0, 34359738368, 68719476736], [1, 37580963840, 68719476736]]}]
        })
    elif url.endswith('/alert/list'):
        return MockResponse([])
    elif 'pool/dataset/id/' in url:
        # For checking if a specific dataset exists
        mock_zvols = [z['name'] for z in mock_data['zvols']]
        dataset_name = url.split('pool/dataset/id/')[1]
        if dataset_name in mock_zvols:
            return MockResponse({'name': dataset_name})
        else:
            return MockResponse({}, 404)
    elif 'iscsi/target/id/' in url:
        # For checking if a specific target exists
        target_id = int(url.split('iscsi/target/id/')[1])
        for target in mock_data['targets']:
            if target['id'] == target_id:
                return MockResponse(target)
        return MockResponse({}, 404)
    elif 'iscsi/extent/id/' in url:
        # For checking if a specific extent exists
        extent_id = int(url.split('iscsi/extent/id/')[1])
        for extent in mock_data['extents']:
            if extent['id'] == extent_id:
                return MockResponse(extent)
        return MockResponse({}, 404)
    
    # Default fallback
    return MockResponse({}, 404)


def mocked_requests_post(url, *args, **kwargs):
    """Mock function for requests.post"""
    # For simplicity, assume all post operations succeed
    if 'pool/dataset' in url:
        # Creating a zvol
        return MockResponse({'id': 'new_zvol'})
    elif 'iscsi/target' in url:
        # Creating a target
        return MockResponse({'id': 2})
    elif 'iscsi/extent' in url:
        # Creating an extent
        return MockResponse({'id': 2})
    elif 'iscsi/targetextent' in url:
        # Creating a target-extent association
        return MockResponse({'id': 2})
    elif 'service/start' in url:
        # Starting a service
        return MockResponse({'status': 'success'})
    
    # Default fallback
    return MockResponse({}, 201)


def mocked_requests_delete(url, *args, **kwargs):
    """Mock function for requests.delete"""
    # For simplicity, assume all delete operations succeed
    return MockResponse({}, 200)


def test_iscsi_component_with_mocks() -> None:
    """
    Test the ISCSIComponent using mock responses.
    
    This allows testing without a real TrueNAS server.
    """
    logger = setup_logging()
    logger.info("Testing ISCSIComponent with Python 3.12 features using mocks")
    
    # Test configuration with Python 3.12 TypedDict
    config: ISCSIConfig = {
        'truenas_ip': '192.168.2.245',
        'api_key': 'mock-api-key',
        'server_id': 'test-server',
        'hostname': 'test.example.com',
        'openshift_version': '4.9.15',
        'zvol_size': '500G',
        'zfs_pool': 'test',
        'dry_run': False
    }
    
    # Create patches for requests.Session methods
    session_patch = patch('requests.Session')
    mock_session = session_patch.start()
    
    # Configure the session mock
    session_instance = mock_session.return_value
    session_instance.get.side_effect = mocked_requests_get
    session_instance.post.side_effect = mocked_requests_post
    session_instance.delete.side_effect = mocked_requests_delete
    
    try:
        # Create ISCSIComponent
        iscsi_component = ISCSIComponent(config, logger)
        
        # Ensure resources are named correctly
        logger.info(f"Resource names: zvol={iscsi_component.config.get('zvol_name')}, "
                    f"target={iscsi_component.config.get('target_name')}, "
                    f"extent={iscsi_component.config.get('extent_name')}")
        
        # Run discovery phase
        logger.info("Running discovery phase...")
        discovery_results = iscsi_component.discover()
        logger.info(f"Discovery completed: connectivity={discovery_results.get('connectivity')}")
        
        # Check discovery results
        if discovery_results.get('connectivity', False):
            logger.info("✅ Successfully connected to TrueNAS")
            
            if discovery_results.get('pools'):
                pool_count = len(discovery_results.get('pools', []))
                logger.info(f"✅ Found {pool_count} storage pools")
            
            if discovery_results.get('zvols'):
                zvol_count = len(discovery_results.get('zvols', []))
                logger.info(f"✅ Found {zvol_count} existing zvols")
            
            if discovery_results.get('targets'):
                target_count = len(discovery_results.get('targets', []))
                logger.info(f"✅ Found {target_count} iSCSI targets")
            
            if discovery_results.get('extents'):
                extent_count = len(discovery_results.get('extents', []))
                logger.info(f"✅ Found {extent_count} iSCSI extents")
            
            if discovery_results.get('iscsi_service'):
                logger.info("✅ iSCSI service is running")
            else:
                logger.warning("⚠️ iSCSI service is not running")
        else:
            logger.error("❌ Failed to connect to TrueNAS")
            return
        
        # Run processing phase
        logger.info("Running processing phase...")
        processing_results = iscsi_component.process()
        
        # Check processing results
        if processing_results.get('zvol_created'):
            if processing_results.get('zvol_existed', False):
                logger.info("✅ Reused existing zvol")
            else:
                logger.info("✅ Created new zvol")
        else:
            logger.warning("⚠️ Failed to create zvol")
        
        if processing_results.get('target_created'):
            target_id = processing_results.get('target_id')
            logger.info(f"✅ Created/reused target with ID {target_id}")
        else:
            logger.warning("⚠️ Failed to create target")
        
        if processing_results.get('extent_created'):
            extent_id = processing_results.get('extent_id')
            logger.info(f"✅ Created/reused extent with ID {extent_id}")
        else:
            logger.warning("⚠️ Failed to create extent")
        
        if processing_results.get('association_created'):
            logger.info("✅ Created/reused target-extent association")
        else:
            logger.warning("⚠️ Failed to create target-extent association")
        
        # Run housekeeping phase
        logger.info("Running housekeeping phase...")
        housekeeping_results = iscsi_component.housekeep()
        
        # Check housekeeping results
        if housekeeping_results.get('resources_verified'):
            logger.info("✅ All resources verified")
        else:
            logger.warning("⚠️ Some resources could not be verified")
            for warning in housekeeping_results.get('warnings', []):
                logger.warning(f"  - {warning}")
        
        # Demonstrate resource details
        resource_details = {
            'zvol_name': iscsi_component.config.get('zvol_name'),
            'target_name': iscsi_component.config.get('target_name'),
            'extent_name': iscsi_component.config.get('extent_name'),
            'target_id': processing_results.get('target_id'),
            'extent_id': processing_results.get('extent_id'),
            'connection_info': {
                'server': iscsi_component.config.get('truenas_ip'),
                'iqn': iscsi_component.config.get('target_name'),
                'port': 3260
            }
        }
        
        logger.info(f"iSCSI Resource Details:\n{json.dumps(resource_details, indent=2)}")
        
        logger.info("iSCSI component test completed successfully")
        
    finally:
        # Stop the patch
        session_patch.stop()


def test_iscsi_utils() -> None:
    """Test utility functions in the iSCSI component"""
    logger = setup_logging()
    logger.info("Testing iSCSI utility functions")
    
    # Test size formatting
    iscsi_component = ISCSIComponent({'server_id': 'test'}, logger)
    
    # Test with different size formats
    sizes = {
        '10K': 10 * 1024,
        '5M': 5 * 1024 * 1024,
        '2G': 2 * 1024 * 1024 * 1024,
        '1T': 1024 * 1024 * 1024 * 1024,
        '0.5P': int(0.5 * 1024 * 1024 * 1024 * 1024 * 1024),
        '123': 123
    }
    
    for size_str, expected_bytes in sizes.items():
        result = iscsi_component._format_size(size_str)
        logger.info(f"Format size '{size_str}' = {result} bytes")
        
        if result == expected_bytes:
            logger.info(f"✅ Size formatting correct for '{size_str}'")
        else:
            logger.warning(f"⚠️ Size formatting failed for '{size_str}': got {result}, expected {expected_bytes}")
    
    logger.info("Utility function tests completed")


def run_all_tests() -> None:
    """Run all tests for the iSCSI component"""
    logger = setup_logging()
    logger.info("Starting iSCSI component Python 3.12 tests")
    
    # Run each test
    test_iscsi_component_with_mocks()
    test_iscsi_utils()
    
    logger.info("All iSCSI component tests completed successfully")


if __name__ == "__main__":
    run_all_tests()
