#!/usr/bin/env python3
"""
Unit tests for the workflow_iso_generation_s3.py script
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
import argparse

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the script under test
import scripts.workflow_iso_generation_s3 as workflow_script


class TestWorkflowIsoGenerationS3:
    """Test class for workflow_iso_generation_s3.py script"""

    @pytest.fixture
    def mock_args(self):
        """Mock command-line arguments"""
        args = argparse.Namespace()
        args.version = "4.14"
        args.domain = "example.com"
        args.rendezvous_ip = "192.168.1.100"
        args.pull_secret = None
        args.ssh_key = None
        args.s3_endpoint = "test-endpoint.example.com"
        args.s3_access_key = "test-access-key"
        args.s3_secret_key = "test-secret-key"
        args.s3_secure = False
        args.iso_bucket = "test-iso-bucket"
        args.binary_bucket = "test-binary-bucket"
        args.skip_iso = False
        args.skip_upload = False
        args.list_only = False
        args.temp_dir = None
        args.server_id = "01"
        args.hostname = "test-server"
        args.verbose = False
        args.dry_run = True
        return args

    @pytest.fixture
    def mock_logger(self):
        """Mock logger instance"""
        return MagicMock()

    @pytest.fixture
    def mock_s3_component(self):
        """Mock S3Component instance"""
        mock = MagicMock()
        mock.discover.return_value = {
            'connectivity': True,
            'buckets': {
                'private': {
                    'exists': True,
                    'objects_count': 5
                },
                'public': {
                    'exists': True,
                    'objects_count': 3
                }
            }
        }
        mock.process.return_value = {
            'buckets': {
                'private': {
                    'created': False,
                    'configured': True
                },
                'public': {
                    'created': False,
                    'configured': True
                }
            }
        }
        mock.housekeep.return_value = {
            'verification': {
                'private_bucket': True,
                'public_bucket': True
            }
        }
        return mock

    @pytest.fixture
    def mock_openshift_component(self):
        """Mock OpenShiftComponent instance"""
        mock = MagicMock()
        mock.discover.return_value = {
            'pull_secret_available': True,
            'ssh_key_available': True,
            'installer_available': True,
            'available_versions': ['4.14.0']
        }
        mock.process.return_value = {
            'iso_generated': True,
            'iso_path': '/tmp/test-dir/agent.x86_64.iso',
            'upload_status': 'success',
            's3_iso_path': 'test-iso-bucket/openshift/4.14/agent.x86_64.iso'
        }
        mock.housekeep.return_value = {
            'iso_verified': True,
            'temp_files_cleaned': True
        }
        return mock

    def test_parse_arguments(self):
        """Test argument parsing functionality"""
        # Mock sys.argv
        test_args = [
            "workflow_iso_generation_s3.py",
            "--version", "4.14.5",
            "--domain", "test.local",
            "--s3-endpoint", "minio.example.com",
            "--dry-run"
        ]
        
        with patch('sys.argv', test_args):
            args = workflow_script.parse_arguments()
            
            assert args.version == "4.14.5"
            assert args.domain == "test.local"
            assert args.s3_endpoint == "minio.example.com"
            assert args.dry_run is True
            assert args.skip_iso is False  # Default value

    def test_create_s3_config(self, mock_args):
        """Test S3 configuration creation"""
        config = workflow_script.create_s3_config(mock_args)
        
        assert config['endpoint'] == mock_args.s3_endpoint
        assert config['access_key'] == mock_args.s3_access_key
        assert config['secret_key'] == mock_args.s3_secret_key
        assert config['private_bucket'] == mock_args.iso_bucket
        assert config['dry_run'] is True
        assert config['create_buckets_if_missing'] is True

    def test_create_openshift_config(self, mock_args):
        """Test OpenShift configuration creation"""
        config = workflow_script.create_openshift_config(mock_args)
        
        assert config['openshift_version'] == mock_args.version
        assert config['domain'] == mock_args.domain
        assert config['rendezvous_ip'] == mock_args.rendezvous_ip
        assert config['server_id'] == mock_args.server_id
        assert config['hostname'] == mock_args.hostname
        assert config['dry_run'] is True
        assert config['s3_config']['iso_bucket'] == mock_args.iso_bucket
        assert config['s3_config']['binary_bucket'] == mock_args.binary_bucket

    @patch('scripts.workflow_iso_generation_s3.S3Component')
    def test_list_isos_in_s3(self, mock_s3_component_class, mock_logger):
        """Test listing ISOs in S3 functionality"""
        # Configure the mock
        mock_s3_instance = MagicMock()
        mock_s3_component_class.return_value = mock_s3_instance
        
        # Set up the mock's list_isos method to return test data
        mock_s3_instance.list_isos.return_value = [
            {
                'key': 'isos/server-01-test-4.14-20250414.iso',
                'size': 1024 * 1024 * 500,  # 500 MB
                'last_modified': '2025-04-14T12:00:00Z',
                'metadata': {
                    'version': '4.14',
                    'server_id': '01'
                }
            }
        ]
        mock_s3_instance.config = {'private_bucket': 'test-bucket'}
        mock_s3_instance.phases_executed = {'discover': True}
        
        # Call the function
        result = workflow_script.list_isos_in_s3(mock_s3_instance, mock_logger)
        
        # Verify the results
        assert result == 1
        mock_s3_instance.list_isos.assert_called_once()

    @patch('scripts.workflow_iso_generation_s3.S3Component')
    @patch('scripts.workflow_iso_generation_s3.OpenShiftComponent')
    def test_run_workflow_list_only(self, mock_openshift_class, mock_s3_class, 
                                   mock_args, mock_logger):
        """Test run_workflow with list-only mode"""
        # Set up the test
        mock_args.list_only = True
        
        # Configure mocks
        mock_s3_instance = MagicMock()
        mock_s3_class.return_value = mock_s3_instance
        
        # Mock the list_isos_in_s3 function
        with patch('scripts.workflow_iso_generation_s3.list_isos_in_s3') as mock_list_isos:
            mock_list_isos.return_value = 3  # 3 ISOs found
            
            # Call the function
            result = workflow_script.run_workflow(mock_args, mock_logger)
            
            # Verify the results
            assert result == 0  # Success
            mock_list_isos.assert_called_once_with(mock_s3_instance, mock_logger)
            mock_openshift_class.assert_not_called()  # OpenShift component should not be created in list-only mode

    @patch('scripts.workflow_iso_generation_s3.S3Component')
    @patch('scripts.workflow_iso_generation_s3.OpenShiftComponent')
    def test_run_workflow_full(self, mock_openshift_class, mock_s3_class, 
                              mock_args, mock_logger, mock_s3_component, mock_openshift_component):
        """Test run_workflow with full workflow execution"""
        # Configure mocks
        mock_s3_class.return_value = mock_s3_component
        mock_openshift_class.return_value = mock_openshift_component
        
        # Call the function
        result = workflow_script.run_workflow(mock_args, mock_logger)
        
        # Verify the results
        assert result == 0  # Success
        
        # Verify component phase calls
        mock_s3_component.discover.assert_called_once()
        mock_s3_component.process.assert_called_once()
        mock_s3_component.housekeep.assert_called_once()
        
        mock_openshift_component.discover.assert_called_once()
        mock_openshift_component.process.assert_called_once()
        mock_openshift_component.housekeep.assert_called_once()
