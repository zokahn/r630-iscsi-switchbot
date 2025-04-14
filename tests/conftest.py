#!/usr/bin/env python3
"""
Pytest configuration for r630-iscsi-switchbot tests.

This file contains shared fixtures and configurations for unit tests.
"""

import os
import sys
import pytest
import logging
import datetime
from unittest.mock import MagicMock, patch, mock_open

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))


@pytest.fixture
def mock_logger():
    """Fixture providing a mock logger that won't output during tests."""
    logger = MagicMock(spec=logging.Logger)
    return logger


@pytest.fixture
def test_config():
    """Fixture providing a basic test configuration for components."""
    return {
        'component_id': 'test-component-001',
        'test_param': 'test_value'
    }


@pytest.fixture
def s3_test_config():
    """Fixture providing a test configuration for S3Component."""
    return {
        'endpoint': 'test-endpoint.com',
        'access_key': 'test-access-key',
        'secret_key': 'test-secret-key',
        'private_bucket': 'r630-switchbot-private',
        'public_bucket': 'r630-switchbot-public',
        'component_id': 's3-test-component'
    }


@pytest.fixture
def iscsi_test_config():
    """Fixture providing a test configuration for ISCSIComponent."""
    return {
        'truenas_ip': '192.168.2.245',
        'api_key': 'test-api-key',
        'server_id': 'test01',
        'hostname': 'test-server',
        'openshift_version': '4.14.0',
        'zvol_size': '1G',
        'zfs_pool': 'test',
        'component_id': 'iscsi-test-component'
    }


@pytest.fixture
def openshift_test_config():
    """Fixture providing a test configuration for OpenShiftComponent."""
    return {
        'openshift_version': '4.14.0',
        'base_domain': 'lab.local',
        'cluster_name': 'sno',
        'node_ip': '192.168.2.230',
        'pull_secret_path': '/path/to/pull-secret.json',
        'rendezvous_ip': '192.168.2.230',
        'component_id': 'openshift-test-component'
    }


@pytest.fixture
def r630_test_config():
    """Fixture providing a test configuration for R630Component."""
    return {
        'idrac_ip': '192.168.2.230',
        'idrac_username': 'root',
        'idrac_password': 'calvin',
        'server_id': '01',
        'boot_mode': 'iscsi',
        'component_id': 'r630-test-component'
    }


@pytest.fixture
def vault_test_config():
    """Fixture providing a test configuration for VaultComponent."""
    return {
        'vault_addr': 'http://localhost:8200',
        'vault_token': 'test-token',
        'secret_path': 'r630-switchbot',
        'component_id': 'vault-test-component'
    }


@pytest.fixture
def mock_filesystem():
    """
    Fixture providing comprehensive mocks for file system operations.
    
    This is especially useful for OpenShiftComponent tests that need to
    simulate file existence and operations without accessing the actual file system.
    """
    with patch('os.path.exists') as mock_exists, \
         patch('os.path.isfile') as mock_isfile, \
         patch('builtins.open', mock_open(read_data=b'iso content')), \
         patch('os.makedirs') as mock_makedirs, \
         patch('os.path.getsize') as mock_getsize, \
         patch('shutil.copy2') as mock_copy2, \
         patch('shutil.move') as mock_move, \
         patch('shutil.rmtree') as mock_rmtree, \
         patch('os.chmod') as mock_chmod:
        
        # Set default behaviors
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_getsize.return_value = 1024
        
        # Return a configuration object that tests can customize
        yield {
            'exists': mock_exists,
            'isfile': mock_isfile,
            'open': mock_open,
            'makedirs': mock_makedirs,
            'getsize': mock_getsize,
            'copy2': mock_copy2,
            'move': mock_move,
            'rmtree': mock_rmtree,
            'chmod': mock_chmod
        }


@pytest.fixture
def mock_s3():
    """
    Fixture providing comprehensive mocks for AWS S3 operations.
    
    This is especially useful for S3Component tests that need to simulate
    S3 bucket and object operations without connecting to a real S3 endpoint.
    """
    with patch('boto3.client') as mock_client, \
         patch('boto3.resource') as mock_resource:
        
        # Create detailed mock responses
        s3_client = MagicMock()
        s3_resource = MagicMock()
        
        # Mock common S3 client methods
        s3_client.list_buckets.return_value = {'Buckets': [
            {'Name': 'r630-switchbot-private'},
            {'Name': 'r630-switchbot-public'}
        ]}
        
        # Mock bucket head check (success by default)
        s3_client.head_bucket.return_value = {}
        
        # Mock version and policy checks
        s3_client.get_bucket_versioning.return_value = {'Status': 'Enabled'}
        s3_client.get_bucket_policy.return_value = {
            'Policy': '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject"}]}'
        }
        
        # Mock object metadata
        s3_client.head_object.return_value = {
            'ContentLength': 1024,
            'LastModified': datetime.datetime.now(),
            'Metadata': {'version': '4.16.0', 'server_id': '01'}
        }
        
        # Mock bucket objects and operations
        mock_private_bucket = MagicMock()
        mock_public_bucket = MagicMock()
        
        # Configure mock objects in buckets
        mock_obj1 = MagicMock()
        mock_obj1.key = 'isos/test1.iso'
        mock_obj2 = MagicMock()
        mock_obj2.key = 'isos/test2.iso'
        
        mock_private_bucket.objects.all.return_value = [mock_obj1, mock_obj2]
        mock_private_bucket.objects.filter.return_value = [mock_obj1, mock_obj2]
        
        # Configure mock resource to return different mock buckets
        s3_resource.Bucket.side_effect = lambda name: mock_private_bucket if name == 'r630-switchbot-private' else mock_public_bucket
        
        # Set return values
        mock_client.return_value = s3_client
        mock_resource.return_value = s3_resource
        
        yield {
            'client': s3_client,
            'resource': s3_resource,
            'private_bucket': mock_private_bucket,
            'public_bucket': mock_public_bucket,
            'objects': [mock_obj1, mock_obj2]
        }


def create_mock_iso(temp_dir, filename="agent.x86_64.iso"):
    """
    Helper function to simulate ISO file creation during tests.
    
    Args:
        temp_dir: The directory path where the mock ISO would be created
        filename: Name of the ISO file (default: agent.x86_64.iso)
        
    Returns:
        str: Path to the mock ISO file
    """
    iso_path = f"{temp_dir}/{filename}"
    return iso_path
