#!/usr/bin/env python3
"""
Unit tests for the setup_minio_buckets_py312.py script.

These tests verify that the Python 3.12 version of the MinIO bucket setup script 
correctly handles various scenarios, including successful execution, error conditions,
and different command-line options.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open
import argparse
import logging
from pathlib import Path
import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the script under test
import scripts.setup_minio_buckets_py312 as minio_script


class TestSetupMinioBucketsPy312(unittest.TestCase):
    """Test cases for the setup_minio_buckets_py312.py script."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create dummy logger for tests
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.NullHandler())
        
        # Mock command line arguments
        self.mock_args = argparse.Namespace(
            endpoint="minio.example.com",
            access_key="test_access_key",
            secret_key="test_secret_key",
            secure=False,
            iso_bucket="test-isos",
            binary_bucket="test-binaries",
            temp_bucket="test-temp",
            init_all=False,
            upload_example=False,
            clean=False,
            verbose=False,
            dry_run=False
        )
        
    def test_create_s3_config(self):
        """Test that S3 configuration is correctly created from arguments."""
        # Act
        config = minio_script.create_s3_config(self.mock_args)
        
        # Assert
        self.assertEqual(config['endpoint'], "minio.example.com")
        self.assertEqual(config['access_key'], "test_access_key")
        self.assertEqual(config['secret_key'], "test_secret_key")
        self.assertEqual(config['secure'], False)
        self.assertEqual(config['private_bucket'], "test-isos")
        self.assertEqual(config['public_bucket'], "test-binaries")
        self.assertEqual(config['create_buckets_if_missing'], False)
        self.assertEqual(config['dry_run'], False)
        self.assertIn('folder_structure_private', config)
        self.assertIn('folder_structure_public', config)

    def test_create_s3_config_with_env_vars(self):
        """Test S3 configuration created with environment variables when args not provided."""
        # Arrange
        args_without_keys = argparse.Namespace(
            endpoint="minio.example.com",
            access_key=None,
            secret_key=None,
            secure=False,
            iso_bucket="test-isos",
            binary_bucket="test-binaries",
            temp_bucket="test-temp",
            init_all=False,
            upload_example=False,
            clean=False,
            verbose=False,
            dry_run=False
        )
        
        # Mock environment variables
        with patch.dict('os.environ', {
            'S3_ACCESS_KEY': 'env_access_key',
            'S3_SECRET_KEY': 'env_secret_key'
        }):
            # Act
            config = minio_script.create_s3_config(args_without_keys)
            
            # Assert
            self.assertEqual(config['access_key'], "env_access_key")
            self.assertEqual(config['secret_key'], "env_secret_key")

    @patch('scripts.setup_minio_buckets_py312.Path')
    @patch('builtins.open', new_callable=mock_open)
    def test_create_example_file(self, mock_open_func, mock_path):
        """Test creating an example file for testing uploads."""
        # Arrange
        mock_cwd_path = MagicMock()
        mock_cwd_path.__truediv__.return_value = Path("example.txt")
        mock_path.cwd.return_value = mock_cwd_path
        
        # Act
        result = minio_script.create_example_file()
        
        # Assert
        mock_open_func.assert_called_once()
        self.assertTrue(mock_open_func().write.called)
        self.assertEqual(result, str(Path("example.txt")))

    @patch('scripts.setup_minio_buckets_py312.create_example_file')
    @patch('scripts.setup_minio_buckets_py312.Path')
    def test_upload_example_files_success(self, mock_path, mock_create_file):
        """Test successfully uploading example files to buckets."""
        # Arrange
        mock_s3_component = MagicMock()
        mock_create_file.return_value = "/tmp/example.txt"
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Act
        result = minio_script.upload_example_files(mock_s3_component, self.mock_args, self.logger)
        
        # Assert
        self.assertTrue(result)
        mock_create_file.assert_called_once()
        self.assertEqual(mock_s3_component.add_artifact.call_count, 3)  # One for each bucket
        mock_s3_component.housekeep.assert_called_once()
        mock_path_instance.unlink.assert_called_once()

    @patch('scripts.setup_minio_buckets_py312.create_example_file')
    @patch('scripts.setup_minio_buckets_py312.Path')
    def test_upload_example_files_failure(self, mock_path, mock_create_file):
        """Test handling of failures when uploading example files."""
        # Arrange
        mock_s3_component = MagicMock()
        mock_create_file.return_value = "/tmp/example.txt"
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Configure component to raise an exception during housekeeping
        mock_s3_component.housekeep.side_effect = Exception("Upload failed")
        
        # Act
        result = minio_script.upload_example_files(mock_s3_component, self.mock_args, self.logger)
        
        # Assert
        self.assertFalse(result)
        mock_create_file.assert_called_once()
        mock_path_instance.unlink.assert_called_once()

    @patch('scripts.setup_minio_buckets_py312.S3Component')
    def test_run_setup_successful_discovery(self, mock_s3_component_class):
        """Test successful execution of run_setup with discovery only."""
        # Arrange
        mock_s3_component = MagicMock()
        mock_s3_component_class.return_value = mock_s3_component
        
        # Configure S3Component mock for successful discovery
        mock_s3_component.discover.return_value = {
            'connectivity': True,
            'endpoint': 'minio.example.com',
            'buckets': {
                'private': {
                    'exists': True,
                    'objects_count': 5,
                    'folders': ['isos/', 'binaries/']
                },
                'public': {
                    'exists': True,
                    'objects_count': 3,
                    'folders': ['isos/4.16/', 'isos/stable/']
                }
            }
        }
        
        # Act
        result = minio_script.run_setup(self.mock_args, self.logger)
        
        # Assert
        self.assertEqual(result, 0)
        mock_s3_component.discover.assert_called_once()
        mock_s3_component.process.assert_not_called()  # Should not be called since init_all=False
        mock_s3_component.housekeep.assert_not_called()  # Should not be called since clean=False

    @patch('scripts.setup_minio_buckets_py312.S3Component')
    def test_run_setup_discovery_failure(self, mock_s3_component_class):
        """Test handling of S3 discovery failure in run_setup."""
        # Arrange
        mock_s3_component = MagicMock()
        mock_s3_component_class.return_value = mock_s3_component
        
        # Configure S3Component mock for failed discovery
        mock_s3_component.discover.return_value = {
            'connectivity': False,
            'error': 'Connection refused'
        }
        
        # Act
        result = minio_script.run_setup(self.mock_args, self.logger)
        
        # Assert
        self.assertEqual(result, 1)  # Should return 1 to indicate failure
        mock_s3_component.discover.assert_called_once()
        mock_s3_component.process.assert_not_called()
        mock_s3_component.housekeep.assert_not_called()

    @patch('scripts.setup_minio_buckets_py312.S3Component')
    def test_run_setup_with_init_all(self, mock_s3_component_class):
        """Test run_setup with init_all=True to create buckets."""
        # Arrange
        mock_s3_component = MagicMock()
        mock_s3_component_class.return_value = mock_s3_component
        
        # Configure S3Component mock for successful discovery
        mock_s3_component.discover.return_value = {
            'connectivity': True,
            'endpoint': 'minio.example.com',
            'buckets': {
                'private': {'exists': False},
                'public': {'exists': False}
            }
        }
        
        # Configure S3Component mock for successful processing
        mock_s3_component.process.return_value = {
            'buckets': {
                'private': {
                    'created': True,
                    'folders_created': ['isos/', 'binaries/', 'artifacts/']
                },
                'public': {
                    'created': True,
                    'folders_created': ['isos/4.16/', 'isos/stable/']
                }
            }
        }
        
        # Set init_all=True for this test
        args_with_init = self.mock_args
        args_with_init.init_all = True
        
        # Act
        result = minio_script.run_setup(args_with_init, self.logger)
        
        # Assert
        self.assertEqual(result, 0)
        mock_s3_component.discover.assert_called_once()
        mock_s3_component.process.assert_called_once()
        mock_s3_component.housekeep.assert_not_called()  # Should not be called since clean=False

    @patch('scripts.setup_minio_buckets_py312.S3Component')
    def test_run_setup_with_clean(self, mock_s3_component_class):
        """Test run_setup with clean=True to invoke housekeeping."""
        # Arrange
        mock_s3_component = MagicMock()
        mock_s3_component_class.return_value = mock_s3_component
        
        # Configure S3Component mocks
        mock_s3_component.discover.return_value = {
            'connectivity': True,
            'endpoint': 'minio.example.com',
            'buckets': {
                'private': {'exists': True},
                'public': {'exists': True}
            }
        }
        
        mock_s3_component.housekeep.return_value = {
            'verification': {
                'private_bucket': True,
                'public_bucket': True
            },
            'warnings': []
        }
        
        # Set clean=True for this test
        args_with_clean = self.mock_args
        args_with_clean.clean = True
        
        # Act
        result = minio_script.run_setup(args_with_clean, self.logger)
        
        # Assert
        self.assertEqual(result, 0)
        mock_s3_component.discover.assert_called_once()
        mock_s3_component.process.assert_not_called()  # Process not called since init_all=False
        mock_s3_component.housekeep.assert_called_once()

    @patch('scripts.setup_minio_buckets_py312.upload_example_files')
    @patch('scripts.setup_minio_buckets_py312.S3Component')
    def test_run_setup_with_upload_example(self, mock_s3_component_class, mock_upload_example):
        """Test run_setup with upload_example=True to test file uploads."""
        # Arrange
        mock_s3_component = MagicMock()
        mock_s3_component_class.return_value = mock_s3_component
        
        # Configure S3Component mock for successful discovery
        mock_s3_component.discover.return_value = {
            'connectivity': True,
            'endpoint': 'minio.example.com',
            'buckets': {
                'private': {'exists': True},
                'public': {'exists': True}
            }
        }
        
        # Configure mock for upload_example_files
        mock_upload_example.return_value = True
        
        # Set upload_example=True for this test
        args_with_upload = self.mock_args
        args_with_upload.upload_example = True
        
        # Act
        result = minio_script.run_setup(args_with_upload, self.logger)
        
        # Assert
        self.assertEqual(result, 0)
        mock_s3_component.discover.assert_called_once()
        mock_upload_example.assert_called_once_with(mock_s3_component, args_with_upload, self.logger)

    @patch('scripts.setup_minio_buckets_py312.parse_arguments')
    @patch('scripts.setup_minio_buckets_py312.setup_logging')
    @patch('scripts.setup_minio_buckets_py312.run_setup')
    def test_main_success(self, mock_run_setup, mock_setup_logging, mock_parse_arguments):
        """Test main function with successful execution."""
        # Arrange
        mock_parse_arguments.return_value = self.mock_args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_run_setup.return_value = 0
        
        # Act
        exit_code = minio_script.main()
        
        # Assert
        self.assertEqual(exit_code, 0)
        mock_parse_arguments.assert_called_once()
        mock_setup_logging.assert_called_once_with(False)
        mock_run_setup.assert_called_once_with(self.mock_args, mock_logger)

    @patch('scripts.setup_minio_buckets_py312.parse_arguments')
    @patch('scripts.setup_minio_buckets_py312.setup_logging')
    @patch('scripts.setup_minio_buckets_py312.run_setup')
    def test_main_exception(self, mock_run_setup, mock_setup_logging, mock_parse_arguments):
        """Test main function handling an unexpected exception."""
        # Arrange
        mock_parse_arguments.return_value = self.mock_args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_run_setup.side_effect = Exception("Unexpected error")
        
        # Act
        exit_code = minio_script.main()
        
        # Assert
        self.assertEqual(exit_code, 1)
        mock_logger.error.assert_called()  # Error should be logged


if __name__ == '__main__':
    unittest.main()
