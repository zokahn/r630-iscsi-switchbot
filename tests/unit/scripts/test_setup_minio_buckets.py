#!/usr/bin/env python3
"""
Unit tests for the setup_minio_buckets.py script
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
import argparse

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the script under test
import scripts.setup_minio_buckets as minio_script


class TestSetupMinioBuckets:
    """Test class for setup_minio_buckets.py script"""

    @pytest.fixture
    def mock_args(self):
        """Mock command-line arguments"""
        args = argparse.Namespace()
        args.endpoint = "test-endpoint.example.com"
        args.access_key = "test-access-key"
        args.secret_key = "test-secret-key"
        args.secure = False
        args.iso_bucket = "test-iso-bucket"
        args.binary_bucket = "test-binary-bucket"
        args.temp_bucket = "test-temp-bucket"
        args.init_all = True
        args.upload_example = False
        args.clean = False
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
            'endpoint': 'test-endpoint.example.com',
            'buckets': {
                'private': {
                    'exists': True,
                    'objects_count': 5,
                    'folders': ['isos/', 'binaries/']
                },
                'public': {
                    'exists': True,
                    'objects_count': 3,
                    'folders': ['isos/4.14/']
                }
            }
        }
        mock.process.return_value = {
            'buckets': {
                'private': {
                    'created': False,
                    'configured': True,
                    'folders_created': []
                },
                'public': {
                    'created': False,
                    'configured': True,
                    'folders_created': []
                }
            }
        }
        mock.housekeep.return_value = {
            'verification': {
                'private_bucket': True,
                'public_bucket': True
            },
            'warnings': []
        }
        return mock

    def test_parse_arguments(self):
        """Test argument parsing functionality"""
        # Mock sys.argv
        test_args = [
            "setup_minio_buckets.py",
            "--endpoint", "minio.example.com",
            "--iso-bucket", "custom-iso-bucket",
            "--init-all",
            "--dry-run"
        ]
        
        with patch('sys.argv', test_args):
            args = minio_script.parse_arguments()
            
            assert args.endpoint == "minio.example.com"
            assert args.iso_bucket == "custom-iso-bucket"
            assert args.init_all is True
            assert args.dry_run is True
            assert args.upload_example is False  # Default value

    def test_create_s3_config(self, mock_args):
        """Test S3 configuration creation"""
        config = minio_script.create_s3_config(mock_args)
        
        assert config['endpoint'] == mock_args.endpoint
        assert config['access_key'] == mock_args.access_key
        assert config['secret_key'] == mock_args.secret_key
        assert config['secure'] == mock_args.secure
        assert config['private_bucket'] == mock_args.iso_bucket
        assert config['public_bucket'] == mock_args.binary_bucket
        assert config['create_buckets_if_missing'] == mock_args.init_all
        assert config['dry_run'] == mock_args.dry_run
        assert 'folder_structure_private' in config
        assert 'folder_structure_public' in config

    def test_create_example_file(self):
        """Test creation of example file"""
        with patch('builtins.open', new_callable=MagicMock) as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            
            # Call the function
            result = minio_script.create_example_file()
            
            # Verify the results
            assert result == os.path.join(os.getcwd(), "example.txt")
            mock_open.assert_called_once()

    @patch('scripts.setup_minio_buckets.create_example_file')
    @patch('os.path.exists')
    @patch('os.unlink')
    def test_upload_example_files(self, mock_unlink, mock_path_exists, mock_create_example, 
                                  mock_args, mock_logger, mock_s3_component):
        """Test upload_example_files functionality"""
        # Configure mocks
        mock_create_example.return_value = "/tmp/example.txt"
        mock_path_exists.return_value = True
        
        # Call the function
        result = minio_script.upload_example_files(mock_s3_component, mock_args, mock_logger)
        
        # Verify the results
        assert result is True
        mock_create_example.assert_called_once()
        mock_s3_component.add_artifact.assert_called()
        mock_s3_component.housekeep.assert_called_once()
        mock_unlink.assert_called_once_with("/tmp/example.txt")

    @patch('scripts.setup_minio_buckets.S3Component')
    def test_run_setup_success(self, mock_s3_class, mock_args, mock_logger, mock_s3_component):
        """Test run_setup with successful execution"""
        # Configure mocks
        mock_s3_class.return_value = mock_s3_component
        
        # Call the function
        result = minio_script.run_setup(mock_args, mock_logger)
        
        # Verify the results
        assert result == 0  # Success
        
        # Verify component phase calls
        mock_s3_component.discover.assert_called_once()
        
        # Since init_all is True, process should be called
        mock_s3_component.process.assert_called_once()
        
        # Since clean is False, housekeep should not be called for cleanup
        # But it might be called for other reasons
        assert mock_s3_component.housekeep.call_count <= 1

    @patch('scripts.setup_minio_buckets.S3Component')
    def test_run_setup_with_example(self, mock_s3_class, mock_args, mock_logger, mock_s3_component):
        """Test run_setup with example upload"""
        # Configure mocks
        mock_s3_class.return_value = mock_s3_component
        mock_args.upload_example = True
        
        # Mock upload_example_files
        with patch('scripts.setup_minio_buckets.upload_example_files') as mock_upload:
            mock_upload.return_value = True
            
            # Call the function
            result = minio_script.run_setup(mock_args, mock_logger)
            
            # Verify the results
            assert result == 0  # Success
            mock_upload.assert_called_once_with(mock_s3_component, mock_args, mock_logger)

    @patch('scripts.setup_minio_buckets.S3Component')
    def test_run_setup_discovery_error(self, mock_s3_class, mock_args, mock_logger):
        """Test run_setup with discovery error"""
        # Configure mocks
        mock_s3_instance = MagicMock()
        mock_s3_class.return_value = mock_s3_instance
        mock_s3_instance.discover.return_value = {
            'connectivity': False,
            'error': 'Connection failed'
        }
        
        # Call the function
        result = minio_script.run_setup(mock_args, mock_logger)
        
        # Verify the results
        assert result == 1  # Failure
        mock_s3_instance.discover.assert_called_once()
        mock_s3_instance.process.assert_not_called()

    @patch('scripts.setup_minio_buckets.S3Component')
    def test_run_setup_exception(self, mock_s3_class, mock_args, mock_logger):
        """Test run_setup with exception"""
        # Configure mocks
        mock_s3_instance = MagicMock()
        mock_s3_class.return_value = mock_s3_instance
        mock_s3_instance.discover.side_effect = Exception("Test exception")
        
        # Call the function
        result = minio_script.run_setup(mock_args, mock_logger)
        
        # Verify the results
        assert result == 1  # Failure
        mock_s3_instance.discover.assert_called_once()
        mock_s3_instance.process.assert_not_called()
