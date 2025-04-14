#!/usr/bin/env python3
"""
Example tests for the S3Component class using the mock_s3 fixture.

This file demonstrates how to use the enhanced testing fixtures
for testing components that interact with AWS S3.
"""

import pytest
import os
import sys
import json
import datetime
import boto3
from moto import mock_s3
from unittest.mock import MagicMock, patch, mock_open, ANY

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from framework.components.s3_component import S3Component


class TestS3ComponentExample:
    """Example test cases showing how to use the mock_s3 fixture."""

    @pytest.fixture
    def component(self, s3_test_config, mock_logger):
        """Fixture to create an S3Component instance."""
        component = S3Component(s3_test_config, logger=mock_logger)
        return component

    def test_bucket_discovery_with_mock_s3(self, component, mock_s3):
        """Test bucket discovery using the mock_s3 fixture."""
        # Configure mock_s3 for this test
        # - List buckets returns our test buckets
        mock_s3['client'].list_buckets.return_value = {
            'Buckets': [
                {'Name': 'r630-switchbot-private'},
                {'Name': 'r630-switchbot-public'},
                {'Name': 'some-other-bucket'}
            ]
        }
        
        # Run discovery
        result = component.discover()
        
        # Check discovery was successful
        assert component.phases_executed['discover'] == True
        assert result['connectivity'] == True
        
        # Check bucket discovery
        assert result['buckets']['private']['exists'] == True
        assert result['buckets']['public']['exists'] == True
        
        # Verify API call
        mock_s3['client'].list_buckets.assert_called_once()

    def test_bucket_creation_with_mock_s3(self, component, mock_s3):
        """Test bucket creation using the mock_s3 fixture."""
        # Configure mock_s3 for this test
        # - List buckets returns no buckets
        mock_s3['client'].list_buckets.return_value = {'Buckets': []}
        
        # Enable bucket creation
        component.config['create_buckets_if_missing'] = True
        
        # Run discovery and processing
        component.discover()
        result = component.process()
        
        # Check processing was successful
        assert component.phases_executed['process'] == True
        
        # Check bucket creation
        assert result['buckets']['private']['created'] == True
        assert result['buckets']['public']['created'] == True
        
        # Verify create_bucket was called twice (once for each bucket)
        assert mock_s3['client'].create_bucket.call_count == 2
        
        # Verify versioning was enabled for private bucket
        mock_s3['client'].put_bucket_versioning.assert_called_with(
            Bucket='r630-switchbot-private',
            VersioningConfiguration={'Status': 'Enabled'}
        )

    def test_object_listing_with_mock_s3(self, component, mock_s3):
        """Test object listing using the mock_s3 fixture."""
        # Configure mock objects in the bucket
        mock_obj1 = MagicMock()
        mock_obj1.key = 'isos/server-01-host1-4.16.0.iso'
        mock_obj2 = MagicMock()
        mock_obj2.key = 'isos/server-02-host2-4.17.0.iso'
        
        # Add objects to the mock private bucket
        mock_s3['private_bucket'].objects.filter.return_value = [mock_obj1, mock_obj2]
        
        # Configure head_object to return metadata
        mock_s3['client'].head_object.side_effect = [
            {
                'ContentLength': 1024,
                'LastModified': datetime.datetime.now(),
                'Metadata': {
                    'server_id': '01',
                    'hostname': 'host1',
                    'version': '4.16.0'
                }
            },
            {
                'ContentLength': 2048,
                'LastModified': datetime.datetime.now(),
                'Metadata': {
                    'server_id': '02',
                    'hostname': 'host2',
                    'version': '4.17.0'
                }
            }
        ]
        
        # Run discovery to ensure the component is ready
        component.discover()
        
        # Call list_isos with filter
        isos = component.list_isos(server_id='01')
        
        # Check result
        assert len(isos) == 1
        assert isos[0]['key'] == 'isos/server-01-host1-4.16.0.iso'
        assert isos[0]['metadata']['server_id'] == '01'
        
        # Verify filter was applied (our mock doesn't actually do filtering)
        mock_s3['private_bucket'].objects.filter.assert_called_with(Prefix='isos/')

    def test_object_upload_with_mock_s3(self, component, mock_s3):
        """Test object upload using the mock_s3 fixture."""
        # Mock file existence check and file opening
        with patch('os.path.isfile', return_value=True), \
             patch('builtins.open', mock_open(read_data=b'test data')), \
             patch('hashlib.md5') as mock_md5:
            
            # Configure mock MD5
            mock_md5_instance = MagicMock()
            mock_md5_instance.hexdigest.return_value = 'abcdef123456'
            mock_md5.return_value = mock_md5_instance
            
            # Run discovery first
            component.discover()
            
            # Call upload_iso
            result = component.upload_iso(
                iso_path='/path/to/test.iso',
                server_id='01',
                hostname='test-host',
                version='4.16.0',
                publish=False
            )
            
            # Check result
            assert result['success'] == True
            assert 'private_key' in result
            
            # Check upload was called with correct parameters
            mock_s3['client'].upload_file.assert_called_once()
            
            # Get arguments of the upload call
            args, kwargs = mock_s3['client'].upload_file.call_args
            
            # Check basic args
            assert args[0] == '/path/to/test.iso'  # Filename
            assert args[1] == 'r630-switchbot-private'  # Bucket
            
            # Check metadata in ExtraArgs
            assert 'ExtraArgs' in kwargs
            assert 'Metadata' in kwargs['ExtraArgs']
            metadata = kwargs['ExtraArgs']['Metadata']
            assert metadata['server_id'] == '01'
            assert metadata['hostname'] == 'test-host'
            assert metadata['version'] == '4.16.0'
            assert metadata['md5'] == 'abcdef123456'

    @mock_s3
    def test_with_moto(self, s3_test_config, mock_logger):
        """Test using the moto library for more realistic S3 testing."""
        # Create real S3 buckets using the mocked AWS API from moto
        s3_client = boto3.client(
            's3',
            region_name='us-east-1',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        
        # Create the test buckets
        s3_client.create_bucket(Bucket='r630-switchbot-private')
        s3_client.create_bucket(Bucket='r630-switchbot-public')
        
        # Enable versioning on private bucket (as our component would do)
        s3_client.put_bucket_versioning(
            Bucket='r630-switchbot-private',
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # Upload a test object to the private bucket
        s3_client.put_object(
            Bucket='r630-switchbot-private',
            Key='isos/test-server-4.16.0.iso',
            Body=b'test iso content',
            Metadata={
                'server_id': '01',
                'hostname': 'test-server',
                'version': '4.16.0'
            }
        )
        
        # Create component using the real boto3 (which is now mocked by moto)
        component = S3Component(s3_test_config, logger=mock_logger)
        
        # Run discovery - this should find our mocked buckets and objects
        result = component.discover()
        
        # Check discovery was successful
        assert result['connectivity'] == True
        assert result['buckets']['private']['exists'] == True
        assert result['buckets']['public']['exists'] == True
        
        # List ISOs - should find our test ISO
        isos = component.list_isos()
        
        # Check result
        assert len(isos) > 0
        assert any(iso['key'] == 'isos/test-server-4.16.0.iso' for iso in isos)
        
        # Test syncing to public bucket
        public_key = component.sync_to_public('isos/test-server-4.16.0.iso', '4.16.0')
        
        # Check sync was successful
        assert public_key is not None
        
        # Verify object is in public bucket
        response = s3_client.list_objects_v2(Bucket='r630-switchbot-public')
        assert 'Contents' in response
        assert any(obj['Key'] == public_key for obj in response['Contents'])
