#!/usr/bin/env python3
"""
Unit tests for the workflow_iso_generation_s3_py312.py script.

These tests verify that the Python 3.12 version of the workflow ISO generation script 
correctly handles various scenarios, including successful execution, error conditions,
and edge cases.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import argparse
import logging
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the script under test
import scripts.workflow_iso_generation_s3_py312 as workflow_script


class TestWorkflowIsoGenerationPy312(unittest.TestCase):
    """Test cases for the workflow_iso_generation_s3_py312.py script."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create dummy logger for tests
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.NullHandler())
        
        # Mock command line arguments
        self.mock_args = argparse.Namespace(
            version="4.14",
            domain="example.com",
            rendezvous_ip="192.168.1.100",
            pull_secret=None,
            ssh_key=None,
            s3_endpoint="minio.example.com",
            s3_access_key="test_access_key",
            s3_secret_key="test_secret_key",
            s3_secure=False,
            iso_bucket="test-isos",
            binary_bucket="test-binaries",
            skip_iso=False,
            skip_upload=False,
            list_only=False,
            temp_dir=None,
            server_id="01",
            hostname="test-server",
            verbose=False,
            dry_run=False
        )
        
    def test_create_s3_config(self):
        """Test that S3 configuration is correctly created from arguments."""
        # Act
        config = workflow_script.create_s3_config(self.mock_args)
        
        # Assert
        self.assertEqual(config['endpoint'], "minio.example.com")
        self.assertEqual(config['access_key'], "test_access_key")
        self.assertEqual(config['secret_key'], "test_secret_key")
        self.assertEqual(config['secure'], False)
        self.assertEqual(config['private_bucket'], "test-isos")
        self.assertEqual(config['public_bucket'], "test-isos")
        self.assertEqual(config['create_buckets_if_missing'], True)
        self.assertEqual(config['dry_run'], False)

    def test_create_openshift_config(self):
        """Test that OpenShift configuration is correctly created from arguments."""
        # Act
        config = workflow_script.create_openshift_config(self.mock_args)
        
        # Assert
        self.assertEqual(config['openshift_version'], "4.14")
        self.assertEqual(config['domain'], "example.com")
        self.assertEqual(config['rendezvous_ip'], "192.168.1.100")
        self.assertEqual(config['upload_to_s3'], True)
        self.assertEqual(config['skip_upload'], False)
        self.assertEqual(config['server_id'], "01")
        self.assertEqual(config['hostname'], "test-server")
        self.assertEqual(config['s3_config']['iso_bucket'], "test-isos")
        self.assertEqual(config['s3_config']['binary_bucket'], "test-binaries")

    @patch('scripts.workflow_iso_generation_s3_py312.S3Component')
    def test_list_isos_in_s3_success(self, mock_s3_component_class):
        """Test successfully listing ISOs in S3."""
        # Arrange
        mock_s3_component = MagicMock()
        mock_s3_component_class.return_value = mock_s3_component
        
        # Configure the mock to return a successful discovery
        mock_s3_component.phases_executed = {'discover': True}
        mock_s3_component.config = {'private_bucket': 'test-isos'}
        
        # Configure the mock to return a list of ISOs
        mock_s3_component.list_isos.return_value = [
            {
                'key': 'isos/server-01-test-4.14.0.iso',
                'size': 1024 * 1024 * 1024,  # 1 GB
                'last_modified': '2025-04-14'
            },
            {
                'key': 'isos/server-02-test-4.14.0.iso',
                'size': 2 * 1024 * 1024 * 1024,  # 2 GB
                'last_modified': '2025-04-13'
            }
        ]
        
        # Act
        result = workflow_script.list_isos_in_s3(mock_s3_component, self.logger)
        
        # Assert
        self.assertEqual(result, 2)
        mock_s3_component.list_isos.assert_called_once()

    @patch('scripts.workflow_iso_generation_s3_py312.S3Component')
    def test_list_isos_in_s3_discovery_failure(self, mock_s3_component_class):
        """Test handling of S3 discovery failure when listing ISOs."""
        # Arrange
        mock_s3_component = MagicMock()
        mock_s3_component_class.return_value = mock_s3_component
        
        # Configure the mock to need discovery and fail
        mock_s3_component.phases_executed = {'discover': False}
        mock_s3_component.discover.return_value = {
            'connectivity': False,
            'error': 'Failed to connect to S3'
        }
        
        # Act
        result = workflow_script.list_isos_in_s3(mock_s3_component, self.logger)
        
        # Assert
        self.assertEqual(result, 0)
        mock_s3_component.discover.assert_called_once()
        mock_s3_component.list_isos.assert_not_called()

    @patch('scripts.workflow_iso_generation_s3_py312.parse_arguments')
    @patch('scripts.workflow_iso_generation_s3_py312.setup_logging')
    @patch('scripts.workflow_iso_generation_s3_py312.run_workflow')
    def test_main_success(self, mock_run_workflow, mock_setup_logging, mock_parse_arguments):
        """Test main function with successful workflow execution."""
        # Arrange
        mock_parse_arguments.return_value = self.mock_args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_run_workflow.return_value = 0
        
        # Act
        exit_code = workflow_script.main()
        
        # Assert
        self.assertEqual(exit_code, 0)
        mock_parse_arguments.assert_called_once()
        mock_setup_logging.assert_called_once_with(False)
        mock_run_workflow.assert_called_once_with(self.mock_args, mock_logger)

    @patch('scripts.workflow_iso_generation_s3_py312.parse_arguments')
    @patch('scripts.workflow_iso_generation_s3_py312.setup_logging')
    @patch('scripts.workflow_iso_generation_s3_py312.run_workflow')
    def test_main_failure(self, mock_run_workflow, mock_setup_logging, mock_parse_arguments):
        """Test main function with workflow execution failure."""
        # Arrange
        mock_parse_arguments.return_value = self.mock_args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_run_workflow.return_value = 1
        
        # Act
        exit_code = workflow_script.main()
        
        # Assert
        self.assertEqual(exit_code, 1)
        mock_parse_arguments.assert_called_once()
        mock_setup_logging.assert_called_once_with(False)
        mock_run_workflow.assert_called_once_with(self.mock_args, mock_logger)
    
    @patch('scripts.workflow_iso_generation_s3_py312.parse_arguments')
    @patch('scripts.workflow_iso_generation_s3_py312.setup_logging')
    @patch('scripts.workflow_iso_generation_s3_py312.run_workflow')
    def test_main_exception(self, mock_run_workflow, mock_setup_logging, mock_parse_arguments):
        """Test main function handling an unexpected exception."""
        # Arrange
        mock_parse_arguments.return_value = self.mock_args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_run_workflow.side_effect = Exception("Unexpected error")
        
        # Act
        exit_code = workflow_script.main()
        
        # Assert
        self.assertEqual(exit_code, 1)
        mock_logger.error.assert_called()  # Error should be logged

    @patch('scripts.workflow_iso_generation_s3_py312.S3Component')
    @patch('scripts.workflow_iso_generation_s3_py312.OpenShiftComponent')
    def test_run_workflow_list_only(self, mock_openshift_class, mock_s3_class):
        """Test running workflow in list-only mode."""
        # Arrange
        mock_args = self.mock_args
        mock_args.list_only = True
        
        mock_s3 = MagicMock()
        mock_s3_class.return_value = mock_s3
        
        # Configure mocks for list_isos_in_s3
        mock_s3.phases_executed = {'discover': True}
        mock_s3.list_isos.return_value = [{'key': 'test.iso', 'size': 1024, 'last_modified': '2025-04-14'}]
        
        # Act
        result = workflow_script.run_workflow(mock_args, self.logger)
        
        # Assert
        self.assertEqual(result, 0)
        mock_openshift_class.assert_not_called()  # OpenShift component should not be initialized in list-only mode
        mock_s3_class.assert_called_once()
        mock_s3.discover.assert_not_called()  # Discover not called in main flow (handled by list_isos_in_s3)

    @patch('scripts.workflow_iso_generation_s3_py312.S3Component')
    @patch('scripts.workflow_iso_generation_s3_py312.OpenShiftComponent')
    def test_run_workflow_success_generate_iso(self, mock_openshift_class, mock_s3_class):
        """Test running workflow in full generation mode with successful execution."""
        # Arrange
        mock_s3 = MagicMock()
        mock_s3_class.return_value = mock_s3
        
        mock_openshift = MagicMock()
        mock_openshift_class.return_value = mock_openshift
        
        # Configure S3Component mock for successful discovery
        mock_s3.discover.return_value = {
            'connectivity': True,
            'buckets': {
                'private': {'exists': True},
                'public': {'exists': True}
            }
        }
        
        # Configure OpenShiftComponent mock for successful execution
        mock_openshift.discover.return_value = {
            'pull_secret_available': True,
            'ssh_key_available': True
        }
        
        mock_openshift.process.return_value = {
            'iso_generated': True,
            'iso_path': '/tmp/test.iso',
            'upload_status': 'success',
            's3_iso_path': 's3://test-isos/test.iso'
        }
        
        mock_openshift.housekeep.return_value = {
            'iso_verified': True,
            'temp_files_removed': True
        }
        
        # Act
        result = workflow_script.run_workflow(self.mock_args, self.logger)
        
        # Assert
        self.assertEqual(result, 0)
        mock_s3.discover.assert_called_once()
        mock_openshift.discover.assert_called_once()
        mock_openshift.process.assert_called_once()
        mock_openshift.housekeep.assert_called_once()
        mock_s3.process.assert_called_once()
        mock_s3.housekeep.assert_called_once()

    @patch('scripts.workflow_iso_generation_s3_py312.S3Component')
    def test_run_workflow_s3_discovery_failure(self, mock_s3_class):
        """Test handling of S3 discovery failure."""
        # Arrange
        mock_s3 = MagicMock()
        mock_s3_class.return_value = mock_s3
        
        # Configure S3Component mock for failed discovery
        mock_s3.discover.return_value = {
            'connectivity': False,
            'error': 'Failed to connect to S3'
        }
        
        # Act
        result = workflow_script.run_workflow(self.mock_args, self.logger)
        
        # Assert
        self.assertEqual(result, 1)
        mock_s3.discover.assert_called_once()
        mock_s3.process.assert_not_called()  # Process should not be called after discovery failure


if __name__ == '__main__':
    unittest.main()
