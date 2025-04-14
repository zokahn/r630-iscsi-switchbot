#!/usr/bin/env python3
"""
Test Script for Python 3.12 R630 Component

This script demonstrates the usage of the Python 3.12-enhanced R630Component
with its improved type annotations and features.
"""

import os
import sys
import json
import logging
import requests
import datetime
from typing import Dict, Any, List, Optional, Union, cast
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Python 3.12 versions of components
from framework.base_component_py312 import BaseComponent
from framework.components.r630_component_py312 import (
    R630Component, R630Config, ServerInfo, BIOSSettings, 
    BootDevice, NetworkInterface, JobDetails
)


def setup_logging() -> logging.Logger:
    """
    Set up logging for the test script.
    
    Returns:
        A configured logger
    """
    logger = logging.getLogger("r630_component_test_py312")
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
    Set up mock responses for iDRAC API calls.
    
    Returns:
        Dictionary with mock responses for various API endpoints
    """
    # System info response
    system_info = {
        'Manufacturer': 'Dell Inc.',
        'Model': 'PowerEdge R630',
        'SerialNumber': 'ABC123XYZ',
        'PartNumber': '0A1B2C3',
        'PowerState': 'On',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'ProcessorSummary': {
            'Count': 2,
            'Model': 'Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz'
        },
        'MemorySummary': {
            'TotalSystemMemoryGiB': 64,
            'Status': {'State': 'Enabled', 'Health': 'OK'}
        },
        'Boot': {
            'BootOrder': ['HardDisk', 'PXE', 'CD/DVD']
        }
    }
    
    # iDRAC info response
    idrac_info = {
        'Id': 'iDRAC.Embedded.1',
        'Model': 'iDRAC 8 Enterprise',
        'FirmwareVersion': '2.70.70.70'
    }
    
    # BIOS settings response
    bios_data = {
        'Attributes': {
            'BootMode': 'Bios',
            'EmbNic1Enabled': 'Enabled',
            'EmbNic2Enabled': 'Enabled',
            'IscsiInitiatorName': 'iqn.1988-11.com.dell:r630-abc123xyz',
            'SriovGlobalEnable': 'Enabled',
            'ProcVirtualization': 'Enabled',
            'IscsiDev1Con1Auth': 'None',
            'IscsiDev1Con1ChapId': '',
            'IscsiDev1Con1ChapSecret': '',
            'IscsiDev1Con1TargetName': 'iqn.2005-10.org.freenas.ctl:iscsi.r630-test-server.openshift4_9_15',
            'IscsiDev1Con1TargetIpAddress': '192.168.2.245',
            'IscsiDev1Con1TargetPort': 3260
        }
    }
    
    # Boot options response
    boot_options_data = {
        'Members': [
            {
                '@odata.id': '/redfish/v1/Systems/System.Embedded.1/BootOptions/HardDisk',
                'Id': 'HardDisk',
                'DisplayName': 'Hard Disk',
                'Enabled': True,
                'BootOptionReference': 'HardDisk'
            },
            {
                '@odata.id': '/redfish/v1/Systems/System.Embedded.1/BootOptions/PXE',
                'Id': 'PXE',
                'DisplayName': 'PXE Network',
                'Enabled': True,
                'BootOptionReference': 'PXE'
            },
            {
                '@odata.id': '/redfish/v1/Systems/System.Embedded.1/BootOptions/CD/DVD',
                'Id': 'CD/DVD',
                'DisplayName': 'CD/DVD Drive',
                'Enabled': True,
                'BootOptionReference': 'CD/DVD'
            }
        ]
    }
    
    # Network interfaces response
    network_interfaces_data = {
        'Members': [
            {
                '@odata.id': '/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/NIC.1'
            },
            {
                '@odata.id': '/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces/NIC.2'
            }
        ]
    }
    
    # Network interface 1 response
    nic1_data = {
        'Id': 'NIC.1',
        'Name': 'NIC 1',
        'MACAddress': '01:23:45:67:89:AB',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'LinkStatus': 'Up',
        'SpeedMbps': 1000,
        'IPv4Addresses': [
            {
                'Address': '192.168.1.100',
                'SubnetMask': '255.255.255.0',
                'Gateway': '192.168.1.1'
            }
        ],
        'IPv6Addresses': []
    }
    
    # Network interface 2 response
    nic2_data = {
        'Id': 'NIC.2',
        'Name': 'NIC 2',
        'MACAddress': 'CD:EF:01:23:45:67',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'LinkStatus': 'Down',
        'SpeedMbps': 0,
        'IPv4Addresses': [],
        'IPv6Addresses': []
    }
    
    # Job status response
    job_data = {
        'Id': 'JID_123456789',
        'JobState': 'Completed',
        'PercentComplete': 100,
        'Message': 'Job completed successfully',
        'StartTime': '2025-04-14T10:30:00Z',
        'EndTime': '2025-04-14T10:35:00Z'
    }
    
    # Setup response for patch operations
    patch_response = {
        '@Message.ExtendedInfo': [
            {
                'MessageId': 'JID123',
                'Message': 'Job successfully created',
                'MessageArgs': ['JID_123456789']
            }
        ]
    }
    
    mock_responses = {
        'system_info': system_info,
        'idrac_info': idrac_info,
        'bios_data': bios_data,
        'boot_options_data': boot_options_data,
        'network_interfaces_data': network_interfaces_data,
        'nic1_data': nic1_data,
        'nic2_data': nic2_data,
        'job_data': job_data,
        'patch_response': patch_response
    }
    
    return mock_responses


class MockResponse:
    """Mock requests.Response for testing"""
    
    def __init__(self, json_data, status_code=200, headers=None, text=None):
        self.json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text if text is not None else json.dumps(json_data)
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP Error: {self.status_code}")


def mocked_requests_get(url, *args, **kwargs):
    """Mock function for requests.get"""
    mock_data = setup_mocked_responses()
    
    # Base URL pattern matching
    if 'redfish/v1/Systems/System.Embedded.1' in url:
        if url.endswith('System.Embedded.1'):
            return MockResponse(mock_data['system_info'])
        elif 'Bios' in url:
            return MockResponse(mock_data['bios_data'])
        elif 'BootOptions' in url:
            return MockResponse(mock_data['boot_options_data'])
        elif 'EthernetInterfaces' in url:
            if url.endswith('EthernetInterfaces'):
                return MockResponse(mock_data['network_interfaces_data'])
            elif 'NIC.1' in url:
                return MockResponse(mock_data['nic1_data'])
            elif 'NIC.2' in url:
                return MockResponse(mock_data['nic2_data'])
    elif 'redfish/v1/Managers/iDRAC.Embedded.1' in url:
        if url.endswith('iDRAC.Embedded.1'):
            return MockResponse(mock_data['idrac_info'])
        elif 'Jobs' in url:
            return MockResponse(mock_data['job_data'])
    
    # Default fallback
    return MockResponse({}, 404)


def mocked_requests_patch(url, *args, **kwargs):
    """Mock function for requests.patch"""
    mock_data = setup_mocked_responses()
    
    headers = {'Location': '/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/JID_123456789'}
    return MockResponse(mock_data['patch_response'], 202, headers)


def mocked_requests_post(url, *args, **kwargs):
    """Mock function for requests.post"""
    if 'Actions/ComputerSystem.Reset' in url:
        return MockResponse({}, 204)
    
    return MockResponse({}, 404)


def test_r630_component_with_mocks():
    """
    Test the R630Component using mock responses.
    
    This allows testing without a real Dell R630 server.
    """
    logger = setup_logging()
    logger.info("Testing R630Component with Python 3.12 features using mocks")
    
    # Test configuration with Python 3.12 TypedDict
    config: R630Config = {
        'idrac_ip': '192.168.1.10',
        'idrac_username': 'admin',
        'idrac_password': 'password',
        'server_id': 'r630-test',
        'hostname': 'r630.example.com',
        'boot_devices': ['PXE', 'HardDisk', 'CD/DVD'],
        'bios_settings': {
            'BootMode': 'UEFI',
            'EmbNic1Enabled': 'Enabled',
            'EmbNic2Enabled': 'Enabled',
            'ProcVirtualization': 'Enabled',
            'SriovGlobalEnable': 'Enabled',
            'IscsiDev1Con1TargetName': 'iqn.2005-10.org.freenas.ctl:iscsi.r630-test.openshift'
        }
    }
    
    # Create patches for requests module
    get_patch = patch('requests.Session.get', side_effect=mocked_requests_get)
    patch_patch = patch('requests.Session.patch', side_effect=mocked_requests_patch)
    post_patch = patch('requests.Session.post', side_effect=mocked_requests_post)
    
    # Start patches
    get_patch.start()
    patch_patch.start()
    post_patch.start()
    
    try:
        # Create R630Component
        r630_component = R630Component(config, logger)
        
        # Run discovery phase
        logger.info("Running discovery phase...")
        discovery_results = r630_component.discover()
        logger.info(f"Discovery completed: connectivity={discovery_results.get('connectivity')}")
        
        # Check discovery results
        if discovery_results.get('connectivity', False):
            logger.info("✅ Successfully connected to iDRAC")
            
            if server_info := discovery_results.get('server_info'):
                logger.info(f"✅ Server model: {server_info.get('model')}")
                logger.info(f"✅ Serial number: {server_info.get('serial_number')}")
                logger.info(f"✅ Power state: {server_info.get('power_state')}")
            
            if boot_mode := discovery_results.get('boot_mode'):
                logger.info(f"✅ Current boot mode: {boot_mode}")
            
            if boot_order := discovery_results.get('current_boot_order'):
                logger.info(f"✅ Current boot order: {boot_order}")
            
            if bios_settings := discovery_results.get('bios_settings'):
                logger.info(f"✅ Retrieved {len(bios_settings)} BIOS settings")
        else:
            logger.error("❌ Failed to connect to iDRAC")
            return
        
        # Run processing phase
        logger.info("Running processing phase...")
        processing_results = r630_component.process()
        
        # Check processing results
        if processing_results.get('boot_order_changed'):
            logger.info("✅ Changed boot order")
        else:
            logger.warning("⚠️ Failed to change boot order")
        
        if processing_results.get('bios_settings_changed'):
            logger.info("✅ Changed BIOS settings")
        else:
            logger.warning("⚠️ Failed to change BIOS settings")
        
        if processing_results.get('reboot_triggered'):
            logger.info("✅ Triggered server reboot")
        
        if job_id := processing_results.get('job_id'):
            logger.info(f"✅ Job ID for configuration changes: {job_id}")
        
        # Run housekeeping phase
        logger.info("Running housekeeping phase...")
        housekeeping_results = r630_component.housekeep()
        
        # Check housekeeping results
        if housekeeping_results.get('job_completed'):
            logger.info("✅ Configuration job completed successfully")
        else:
            logger.warning("⚠️ Configuration job not completed")
        
        if housekeeping_results.get('changes_verified'):
            logger.info("✅ Configuration changes verified")
        else:
            logger.warning("⚠️ Configuration changes not verified")
            for warning in housekeeping_results.get('warnings', []):
                logger.warning(f"  - {warning}")
        
        # Demonstrate configuration details
        config_details = {
            'server_id': r630_component.config.get('server_id'),
            'idrac_ip': r630_component.config.get('idrac_ip'),
            'boot_order': housekeeping_results.get('final_state', {}).get('boot_order', []),
            'bios_settings': housekeeping_results.get('final_state', {}).get('bios_settings', {})
        }
        
        logger.info(f"R630 Configuration Details:\n{json.dumps(config_details, indent=2)}")
        
        logger.info("R630 component test completed successfully")
        
    finally:
        # Stop patches
        get_patch.stop()
        patch_patch.stop()
        post_patch.stop()


def test_r630_utils():
    """Test utility methods in the R630 component"""
    logger = setup_logging()
    logger.info("Testing R630 utility methods")
    
    # Create a minimal component instance for testing utilities
    r630_component = R630Component({'server_id': 'test'}, logger)
    
    # Test Python 3.12 dictionary merging
    default_config = R630Component.DEFAULT_CONFIG
    custom_config = {
        'idrac_ip': '10.0.0.10',
        'server_id': 'custom_server',
        'boot_devices': ['HardDisk', 'PXE']
    }
    
    # Test the merge operation
    merged_config = default_config | custom_config
    
    logger.info(f"Default config has {len(default_config)} keys")
    logger.info(f"Custom config has {len(custom_config)} keys")
    logger.info(f"Merged config has {len(merged_config)} keys")
    
    # Verify merge retained all default keys
    all_default_keys_preserved = all(key in merged_config for key in default_config.keys())
    logger.info(f"All default keys preserved: {all_default_keys_preserved}")
    
    # Verify custom values override defaults
    custom_values_applied = all(merged_config[key] == custom_config[key] for key in custom_config.keys())
    logger.info(f"Custom values properly applied: {custom_values_applied}")
    
    logger.info("Utility method tests completed")


def run_all_tests():
    """Run all tests for the R630 component"""
    logger = setup_logging()
    logger.info("Starting R630 component Python 3.12 tests")
    
    # Run each test
    test_r630_component_with_mocks()
    test_r630_utils()
    
    logger.info("All R630 component tests completed successfully")


if __name__ == "__main__":
    run_all_tests()
