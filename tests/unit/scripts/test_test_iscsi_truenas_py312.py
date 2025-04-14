#!/usr/bin/env python3
"""
Unit tests for the test_iscsi_truenas_py312.py script.

These tests verify that the Python 3.12 version of the TrueNAS iSCSI test script
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
import getpass

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the script under test
import scripts.test_iscsi_truenas_py312 as iscsi_script


class TestISCSITrueNasPy312(unittest.TestCase):
    """Test cases for the test_iscsi_truenas_py312.py script."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create dummy logger for tests
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.NullHandler())
        
        # Mock command line arguments
        self.mock_args = argparse.Namespace(
            truenas_ip="truenas.example.com",
            api_key="test_api_key",
            server_id="test01",
            hostname="test-server",
            openshift_version="4.14.0",
            zvol_size="1G",
            zfs_pool="test",
            create_test_zvol=False,
            cleanup=False,
            discover_only=False,
            verbose=False,
            dry_run=False
        )
        
    def test_create_iscsi_config(self):
        """Test that ISCSI configuration is correctly created from arguments."""
        # Act
        config = iscsi_script.create_iscsi_config(self.mock_args, "test_api_key")
        
        # Assert
        self.assertEqual(config['truenas_ip'], "truenas.example.com")
        self.assertEqual(config['api_key'], "test_api_key")
        self.assertEqual(config['server_id'], "test01")
        self.assertEqual(config['hostname'], "test-server")
        self.assertEqual(config['openshift_version'], "4.14.0")
        self.assertEqual(config['zvol_size'], "1G")
        self.assertEqual(config['zfs_pool'], "test")
        self.assertEqual(config['dry_run'], False)
        self.assertEqual(config['discover_only'], False)

    def test_display_discovery_results_successful_connectivity(self):
        """Test displaying discovery results when connectivity is successful."""
        # Arrange
        discovery_results = {
            'connectivity': True,
            'iscsi_service': True,
            'pools': [
                {'name': 'tank', 'free': 1024 * 1024 * 1024 * 100}  # 100 GB
            ],
            'zvols': [
                {'name': 'tank/test-zvol', 'volsize': {'parsed': 1024 * 1024 * 1024 * 10}}  # 10 GB
            ],
            'targets': [
                {'id': 1, 'name': 'test-target'}
            ],
            'storage_capacity': {
                'found': True,
                'sufficient': True
            }
        }
        
        # Act - verify no exceptions
        with patch.object(self.logger, 'info') as mock_info:
            iscsi_script.display_discovery_results(discovery_results, self.mock_args, self.logger)
            
            # Assert
            self.assertTrue(mock_info.called)
            # Verify we at least check connectivity in the output
            connectivity_message_found = False
            for call in mock_info.call_args_list:
                args, _ = call
                if args and 'TrueNAS connectivity: True' in args[0]:
                    connectivity_message_found = True
                    break
            self.assertTrue(connectivity_message_found)

    def test_display_discovery_results_failed_connectivity(self):
        """Test displaying discovery results when connectivity fails."""
        # Arrange
        discovery_results = {
            'connectivity': False,
            'connection_error': 'Test connection error'
        }
        
        # Act - verify no exceptions
        with patch.object(self.logger, 'error') as mock_error:
            iscsi_script.display_discovery_results(discovery_results, self.mock_args, self.logger)
            
            # Assert
            mock_error.assert_called_with('TrueNAS connectivity failed: Test connection error')

    def test_display_processing_results_successful(self):
        """Test displaying processing results for successful operations."""
        # Arrange
        processing_results = {
            'zvol_created': True,
            'target_created': True,
            'extent_created': True,
            'association_created': True,
            'target_id': 1,
            'extent_id': 2
        }
        
        # Act - verify no exceptions
        with patch.object(self.logger, 'info') as mock_info:
            iscsi_script.display_processing_results(processing_results, self.logger)
            
            # Assert
            self.assertTrue(mock_info.called)
            # Verify target ID is logged
            target_id_message_found = False
            for call in mock_info.call_args_list:
                args, _ = call
                if args and '- Target ID: 1' in args[0]:
                    target_id_message_found = True
                    break
            self.assertTrue(target_id_message_found)

    def test_display_processing_results_with_errors(self):
        """Test displaying processing results with errors."""
        # Arrange
        processing_results = {
            'zvol_created': False,
            'target_created': False,
            'extent_created': False,
            'association_created': False,
            'zvol_error': 'Failed to create zvol',
            'target_error': 'Failed to create target'
        }
        
        # Act - verify no exceptions
        with patch.object(self.logger, 'error') as mock_error:
            iscsi_script.display_processing_results(processing_results, self.logger)
            
            # Assert
            self.assertEqual(mock_error.call_count, 2)  # Two error messages should be logged

    def test_display_housekeeping_results_with_warnings(self):
        """Test displaying housekeeping results with warnings."""
        # Arrange
        housekeeping_results = {
            'resources_verified': True,
            'unused_resources_found': 2,
            'unused_resources_cleaned': 1,
            'warnings': ['Failed to clean resource X']
        }
        
        # Act - verify no exceptions
        with patch.object(self.logger, 'warning') as mock_warning:
            iscsi_script.display_housekeeping_results(housekeeping_results, self.logger)
            
            # Assert
            mock_warning.assert_called_with('  - Failed to clean resource X')

    @patch('scripts.test_iscsi_truenas_py312.getpass.getpass')
    @patch('scripts.test_iscsi_truenas_py312.ISCSIComponent')
    def test_main_with_api_key_arg(self, mock_iscsi_component_class, mock_getpass):
        """Test main function when API key is provided as argument."""
        # Arrange
        mock_iscsi_component = MagicMock()
        mock_iscsi_component_class.return_value = mock_iscsi_component
        
        # Configure discovery
        mock_iscsi_component.discover.return_value = {
            'connectivity': True,
            'iscsi_service': True
        }
        
        # Configure args
        mock_args = self.mock_args
        mock_args.discover_only = True  # Only do discovery to simplify test
        
        # Act
        with patch('scripts.test_iscsi_truenas_py312.parse_arguments', return_value=mock_args):
            with patch('scripts.test_iscsi_truenas_py312.setup_logging', return_value=self.logger):
                result = iscsi_script.main()
                
                # Assert
                self.assertEqual(result, 0)  # Should succeed
                mock_getpass.assert_not_called()  # API key provided, should not prompt
                mock_iscsi_component_class.assert_called_once()
                mock_iscsi_component.discover.assert_called_once()

    @patch('scripts.test_iscsi_truenas_py312.getpass.getpass')
    @patch('scripts.test_iscsi_truenas_py312.ISCSIComponent')
    def test_main_prompt_for_api_key(self, mock_iscsi_component_class, mock_getpass):
        """Test main function when API key is prompted."""
        # Arrange
        mock_iscsi_component = MagicMock()
        mock_iscsi_component_class.return_value = mock_iscsi_component
        
        # Configure discovery
        mock_iscsi_component.discover.return_value = {
            'connectivity': True,
            'iscsi_service': True
        }
        
        # Configure getpass to return API key
        mock_getpass.return_value = "prompted_api_key"
        
        # Configure args
        mock_args = self.mock_args
        mock_args.api_key = None  # No API key provided
        mock_args.discover_only = True  # Only do discovery to simplify test
        
        # Act
        with patch('scripts.test_iscsi_truenas_py312.parse_arguments', return_value=mock_args):
            with patch('scripts.test_iscsi_truenas_py312.setup_logging', return_value=self.logger):
                result = iscsi_script.main()
                
                # Assert
                self.assertEqual(result, 0)  # Should succeed
                mock_getpass.assert_called_once()  # Should prompt for API key
                mock_iscsi_component_class.assert_called_once()
                
                # Verify API key was passed correctly
                _, kwargs = mock_iscsi_component_class.call_args
                self.assertEqual(kwargs['config']['api_key'], "prompted_api_key")

    @patch('scripts.test_iscsi_truenas_py312.getpass.getpass')
    @patch('scripts.test_iscsi_truenas_py312.ISCSIComponent')
    def test_main_discovery_failure(self, mock_iscsi_component_class, mock_getpass):
        """Test main function when discovery fails."""
        # Arrange
        mock_iscsi_component = MagicMock()
        mock_iscsi_component_class.return_value = mock_iscsi_component
        
        # Configure discovery to fail
        mock_iscsi_component.discover.return_value = {
            'connectivity': False,
            'connection_error': 'Connection refused'
        }
        
        # Act
        with patch('scripts.test_iscsi_truenas_py312.parse_arguments', return_value=self.mock_args):
            with patch('scripts.test_iscsi_truenas_py312.setup_logging', return_value=self.logger):
                result = iscsi_script.main()
                
                # Assert
                self.assertEqual(result, 1)  # Should fail
                mock_iscsi_component.discover.assert_called_once()
                mock_iscsi_component.process.assert_not_called()  # Should not proceed to processing

    @patch('scripts.test_iscsi_truenas_py312.getpass.getpass')
    @patch('scripts.test_iscsi_truenas_py312.ISCSIComponent')
    def test_main_with_create_test_zvol(self, mock_iscsi_component_class, mock_getpass):
        """Test main function with create_test_zvol=True."""
        # Arrange
        mock_iscsi_component = MagicMock()
        mock_iscsi_component_class.return_value = mock_iscsi_component
        
        # Configure discovery
        mock_iscsi_component.discover.return_value = {
            'connectivity': True,
            'iscsi_service': True
        }
        
        # Configure processing
        mock_iscsi_component.process.return_value = {
            'zvol_created': True,
            'target_created': True,
            'extent_created': True,
            'association_created': True
        }
        
        # Configure args
        mock_args = self.mock_args
        mock_args.create_test_zvol = True
        mock_args.cleanup = False
        
        # Act
        with patch('scripts.test_iscsi_truenas_py312.parse_arguments', return_value=mock_args):
            with patch('scripts.test_iscsi_truenas_py312.setup_logging', return_value=self.logger):
                result = iscsi_script.main()
                
                # Assert
                self.assertEqual(result, 0)  # Should succeed
                mock_iscsi_component.discover.assert_called_once()
                mock_iscsi_component.process.assert_called_once()
                mock_iscsi_component.housekeep.assert_not_called()  # No cleanup requested

    @patch('scripts.test_iscsi_truenas_py312.getpass.getpass')
    @patch('scripts.test_iscsi_truenas_py312.ISCSIComponent')
    def test_main_with_create_and_cleanup(self, mock_iscsi_component_class, mock_getpass):
        """Test main function with create_test_zvol=True and cleanup=True."""
        # Arrange
        mock_iscsi_component = MagicMock()
        mock_iscsi_component_class.return_value = mock_iscsi_component
        
        # Configure discovery
        mock_iscsi_component.discover.return_value = {
            'connectivity': True,
            'iscsi_service': True
        }
        
        # Configure processing
        mock_iscsi_component.process.return_value = {
            'zvol_created': True,
            'target_created': True,
            'extent_created': True,
            'association_created': True
        }
        
        # Configure housekeeping
        mock_iscsi_component.housekeep.return_value = {
            'resources_verified': True,
            'unused_resources_found': 0,
            'unused_resources_cleaned': 0,
            'warnings': []
        }
        
        # Configure args
        mock_args = self.mock_args
        mock_args.create_test_zvol = True
        mock_args.cleanup = True
        
        # Act
        with patch('scripts.test_iscsi_truenas_py312.parse_arguments', return_value=mock_args):
            with patch('scripts.test_iscsi_truenas_py312.setup_logging', return_value=self.logger):
                result = iscsi_script.main()
                
                # Assert
                self.assertEqual(result, 0)  # Should succeed
                mock_iscsi_component.discover.assert_called_once()
                mock_iscsi_component.process.assert_called_once()
                mock_iscsi_component.housekeep.assert_called_once()  # Cleanup was requested


if __name__ == '__main__':
    unittest.main()
