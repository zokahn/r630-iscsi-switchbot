#!/usr/bin/env python3
"""
Unit tests for the config_iscsi_boot_py312.py script.

These tests verify that the Python 3.12 version of the iSCSI boot configuration script 
correctly handles various scenarios, including successful execution, error conditions,
and different command-line options.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open
import argparse
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the script under test
import scripts.config_iscsi_boot_py312 as boot_script


class TestConfigISCSIBootPy312(unittest.TestCase):
    """Test cases for the config_iscsi_boot_py312.py script."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create dummy logger for tests
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.NullHandler())
        
        # Mock command line arguments
        self.mock_args = argparse.Namespace(
            server="192.168.2.230",
            user="root",
            password="calvin",
            nic="NIC.Integrated.1-1-1",
            target="test-iscsi-target",
            secondary_target=None,
            initiator_name=None,
            gateway=None,
            no_reboot=False,
            list_targets=False,
            validate_only=False,
            reset_iscsi=False,
            verbose=False
        )
        
        # Mock target configuration
        self.mock_target = {
            "name": "test-iscsi-target",
            "description": "Test iSCSI Target for Unit Tests",
            "iqn": "iqn.2023-01.com.example:storage:test",
            "ip": "192.168.2.200",
            "port": 3260,
            "lun": 0
        }
        
        # Mock targets file data
        self.mock_targets_data = {
            "targets": [self.mock_target]
        }
        
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"targets": []}')
    def test_load_targets_success(self, mock_file, mock_exists):
        """Test loading targets configuration successfully."""
        # Setup
        mock_exists.return_value = True
        
        # Act
        result = boot_script.load_targets()
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIn("targets", result)
        mock_file.assert_called_once()

    @patch('pathlib.Path.exists')
    def test_load_targets_file_not_found(self, mock_exists):
        """Test loading targets when the file doesn't exist."""
        # Setup
        mock_exists.return_value = False
        
        # Act and Assert
        with self.assertRaises(SystemExit):
            boot_script.load_targets()

    @patch('json.load')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', mock_open())
    def test_load_targets_invalid_json(self, mock_exists, mock_json_load):
        """Test loading targets with invalid JSON."""
        # Setup
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        # Act and Assert
        with self.assertRaises(SystemExit):
            boot_script.load_targets()

    def test_get_target_config_found(self):
        """Test getting target configuration when it exists."""
        # Act
        result = boot_script.get_target_config(self.mock_targets_data, "test-iscsi-target")
        
        # Assert
        self.assertEqual(result, self.mock_target)

    def test_get_target_config_not_found(self):
        """Test getting target configuration when it doesn't exist."""
        # Act and Assert
        with self.assertRaises(SystemExit):
            boot_script.get_target_config(self.mock_targets_data, "non-existent-target")

    def test_create_r630_config(self):
        """Test creating R630 configuration from arguments."""
        # Act
        config = boot_script.create_r630_config(self.mock_args)
        
        # Assert
        self.assertEqual(config['idrac_ip'], "192.168.2.230")
        self.assertEqual(config['username'], "root")
        self.assertEqual(config['password'], "calvin")
        self.assertEqual(config['nic_id'], "NIC.Integrated.1-1-1")
        self.assertTrue(config['reboot'])  # no_reboot=False, so reboot=True
        self.assertEqual(config['component_id'], "r630-iscsi-boot")

    def test_create_r630_config_no_reboot(self):
        """Test creating R630 configuration with no reboot."""
        # Setup
        args = self.mock_args
        args.no_reboot = True
        
        # Act
        config = boot_script.create_r630_config(args)
        
        # Assert
        self.assertFalse(config['reboot'])

    def test_create_iscsi_config_basic(self):
        """Test creating iSCSI configuration with basic settings."""
        # Act
        config = boot_script.create_iscsi_config(self.mock_args, self.mock_target)
        
        # Assert
        self.assertEqual(config['server_id'], "r630-230")
        self.assertEqual(config['iscsi_server'], "192.168.2.230")
        self.assertEqual(config['target_id'], "test-iscsi-target")
        self.assertEqual(config['iqn'], "iqn.2023-01.com.example:storage:test")
        self.assertEqual(config['ip'], "192.168.2.200")
        self.assertEqual(config['port'], 3260)
        self.assertEqual(config['lun'], 0)
        self.assertEqual(config['component_id'], "iscsi-boot-component")

    def test_create_iscsi_config_with_auth(self):
        """Test creating iSCSI configuration with authentication."""
        # Setup
        target_with_auth = self.mock_target.copy()
        target_with_auth.update({
            "auth_method": "CHAP",
            "chap_username": "test-user",
            "chap_secret": "test-password"
        })
        
        # Act
        config = boot_script.create_iscsi_config(self.mock_args, target_with_auth)
        
        # Assert
        self.assertEqual(config['auth_method'], "CHAP")
        self.assertEqual(config['chap_username'], "test-user")
        self.assertEqual(config['chap_secret'], "test-password")

    def test_create_iscsi_config_with_initiator_and_gateway(self):
        """Test creating iSCSI configuration with custom initiator name and gateway."""
        # Setup
        args = self.mock_args
        args.initiator_name = "custom:initiator:name"
        args.gateway = "192.168.2.1"
        
        # Act
        config = boot_script.create_iscsi_config(args, self.mock_target)
        
        # Assert
        self.assertEqual(config['initiator_name'], "custom:initiator:name")
        self.assertEqual(config['gateway'], "192.168.2.1")

    def test_create_iscsi_config_with_secondary_target(self):
        """Test creating iSCSI configuration with secondary target."""
        # Setup
        secondary_target = {
            "name": "secondary-target",
            "description": "Secondary iSCSI Target",
            "iqn": "iqn.2023-01.com.example:storage:secondary",
            "ip": "192.168.2.201",
            "port": 3260,
            "lun": 1
        }
        
        # Act
        config = boot_script.create_iscsi_config(self.mock_args, self.mock_target, secondary_target)
        
        # Assert
        self.assertIn('secondary_target', config)
        self.assertEqual(config['secondary_target']['iqn'], "iqn.2023-01.com.example:storage:secondary")
        self.assertEqual(config['secondary_target']['ip'], "192.168.2.201")
        self.assertEqual(config['secondary_target']['port'], 3260)
        self.assertEqual(config['secondary_target']['lun'], 1)

    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_check_r630_hardware_success(self, mock_r630_component_class):
        """Test checking R630 hardware successfully."""
        # Setup
        mock_component = MagicMock()
        mock_component.discover.return_value = {
            'connectivity': True,
            'server_info': {
                'Model': 'PowerEdge R630'
            },
            'idrac_info': {
                'FirmwareVersion': '2.30.30.30'
            }
        }
        
        # Act
        result = boot_script.check_r630_hardware(mock_component, self.logger)
        
        # Assert
        self.assertTrue(result)
        mock_component.discover.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_check_r630_hardware_not_r630(self, mock_r630_component_class):
        """Test checking hardware when it's not an R630."""
        # Setup
        mock_component = MagicMock()
        mock_component.discover.return_value = {
            'connectivity': True,
            'server_info': {
                'Model': 'PowerEdge R640'
            },
            'idrac_info': {
                'FirmwareVersion': '2.30.30.30'
            }
        }
        
        # Act
        result = boot_script.check_r630_hardware(mock_component, self.logger)
        
        # Assert
        self.assertTrue(result)  # Still returns True, just with a warning
        mock_component.discover.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_check_r630_hardware_no_connectivity(self, mock_r630_component_class):
        """Test checking hardware with no connectivity."""
        # Setup
        mock_component = MagicMock()
        mock_component.discover.return_value = {
            'connectivity': False,
            'error': 'Connection refused'
        }
        
        # Act
        result = boot_script.check_r630_hardware(mock_component, self.logger)
        
        # Assert
        self.assertFalse(result)
        mock_component.discover.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.validate_iscsi_configuration')
    @patch('scripts.config_iscsi_boot_py312.ISCSIComponent')
    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_configure_iscsi_boot_success(self, mock_r630_class, mock_iscsi_class, mock_validate):
        """Test successful iSCSI boot configuration."""
        # Setup
        mock_r630 = MagicMock()
        mock_iscsi = MagicMock()
        
        # Configure R630 discovery
        mock_r630.discover.return_value = {
            'connectivity': True,
            'system_info': {
                'PowerState': 'On'
            }
        }
        
        # Configure iSCSI discovery
        mock_iscsi.discover.return_value = {
            'connectivity': True
        }
        
        # Configure process results
        mock_iscsi.process.return_value = {
            'iscsi_configured': True
        }
        
        mock_r630.process.return_value = {
            'configuration_applied': True,
            'reboot_scheduled': True
        }
        
        # Configure validation
        mock_validate.return_value = True
        
        # Act
        result = boot_script.configure_iscsi_boot(
            mock_r630, 
            mock_iscsi, 
            self.mock_target,
            None,
            self.logger
        )
        
        # Assert
        self.assertTrue(result)
        mock_r630.discover.assert_called_once()
        mock_iscsi.discover.assert_called_once()
        mock_iscsi.process.assert_called_once()
        mock_r630.process.assert_called_once()
        mock_validate.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.validate_iscsi_configuration')
    @patch('scripts.config_iscsi_boot_py312.ISCSIComponent')
    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_configure_iscsi_boot_r630_connectivity_failure(self, mock_r630_class, mock_iscsi_class, mock_validate):
        """Test iSCSI boot configuration with R630 connectivity failure."""
        # Setup
        mock_r630 = MagicMock()
        mock_iscsi = MagicMock()
        
        # Configure R630 discovery failure
        mock_r630.discover.return_value = {
            'connectivity': False,
            'error': 'Connection refused'
        }
        
        # Act
        result = boot_script.configure_iscsi_boot(
            mock_r630, 
            mock_iscsi, 
            self.mock_target,
            None,
            self.logger
        )
        
        # Assert
        self.assertFalse(result)
        mock_r630.discover.assert_called_once()
        mock_iscsi.discover.assert_not_called()  # Should not proceed to iSCSI discovery
        mock_iscsi.process.assert_not_called()

    @patch('scripts.config_iscsi_boot_py312.validate_iscsi_configuration')
    @patch('scripts.config_iscsi_boot_py312.ISCSIComponent')
    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_configure_iscsi_boot_iscsi_process_failure(self, mock_r630_class, mock_iscsi_class, mock_validate):
        """Test iSCSI boot configuration with iSCSI process failure."""
        # Setup
        mock_r630 = MagicMock()
        mock_iscsi = MagicMock()
        
        # Configure successful discovery
        mock_r630.discover.return_value = {
            'connectivity': True,
            'system_info': {
                'PowerState': 'On'
            }
        }
        
        mock_iscsi.discover.return_value = {
            'connectivity': True
        }
        
        # Configure iSCSI process failure
        mock_iscsi.process.return_value = {
            'iscsi_configured': False,
            'error': 'Failed to configure iSCSI'
        }
        
        # Act
        result = boot_script.configure_iscsi_boot(
            mock_r630, 
            mock_iscsi, 
            self.mock_target,
            None,
            self.logger
        )
        
        # Assert
        self.assertFalse(result)
        mock_r630.discover.assert_called_once()
        mock_iscsi.discover.assert_called_once()
        mock_iscsi.process.assert_called_once()
        mock_r630.process.assert_not_called()  # Should not proceed to R630 process

    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_reset_iscsi_configuration_success(self, mock_r630_class):
        """Test successful reset of iSCSI configuration."""
        # Setup
        mock_r630 = MagicMock()
        
        # Configure process_iscsi_reset success
        mock_r630.process_iscsi_reset.return_value = {
            'reset_successful': True,
            'reboot_scheduled': True
        }
        
        # Act
        result = boot_script.reset_iscsi_configuration(mock_r630, self.logger)
        
        # Assert
        self.assertTrue(result)
        mock_r630.process_iscsi_reset.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_reset_iscsi_configuration_failure(self, mock_r630_class):
        """Test failed reset of iSCSI configuration."""
        # Setup
        mock_r630 = MagicMock()
        
        # Configure process_iscsi_reset failure
        mock_r630.process_iscsi_reset.return_value = {
            'reset_successful': False,
            'error': 'Reset failed'
        }
        
        # Act
        result = boot_script.reset_iscsi_configuration(mock_r630, self.logger)
        
        # Assert
        self.assertFalse(result)
        mock_r630.process_iscsi_reset.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_validate_iscsi_configuration_success(self, mock_r630_class):
        """Test successful validation of iSCSI configuration."""
        # Setup
        mock_r630 = MagicMock()
        
        # Configure get_iscsi_configuration success
        mock_r630.get_iscsi_configuration.return_value = {
            'configuration': {
                'iSCSIBoot': {
                    'PrimaryTargetName': 'iqn.2023-01.com.example:storage:test',
                    'PrimaryTargetIPAddress': '192.168.2.200',
                    'PrimaryLUN': 0
                }
            },
            'iscsi_enabled': True
        }
        
        # Act
        result = boot_script.validate_iscsi_configuration(
            mock_r630, 
            'iqn.2023-01.com.example:storage:test',
            self.logger
        )
        
        # Assert
        self.assertTrue(result)
        mock_r630.get_iscsi_configuration.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_validate_iscsi_configuration_iqn_mismatch(self, mock_r630_class):
        """Test validation with IQN mismatch."""
        # Setup
        mock_r630 = MagicMock()
        
        # Configure get_iscsi_configuration with IQN mismatch
        mock_r630.get_iscsi_configuration.return_value = {
            'configuration': {
                'iSCSIBoot': {
                    'PrimaryTargetName': 'iqn.2023-01.com.example:storage:different',
                    'PrimaryTargetIPAddress': '192.168.2.200',
                    'PrimaryLUN': 0
                }
            },
            'iscsi_enabled': True
        }
        
        # Act
        result = boot_script.validate_iscsi_configuration(
            mock_r630, 
            'iqn.2023-01.com.example:storage:test',
            self.logger
        )
        
        # Assert
        self.assertTrue(result)  # Still returns True (with warnings) for R630 compatibility
        mock_r630.get_iscsi_configuration.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_validate_iscsi_configuration_missing_fields(self, mock_r630_class):
        """Test validation with missing required fields."""
        # Setup
        mock_r630 = MagicMock()
        
        # Configure get_iscsi_configuration with missing fields
        mock_r630.get_iscsi_configuration.return_value = {
            'configuration': {
                'iSCSIBoot': {
                    'PrimaryTargetName': 'iqn.2023-01.com.example:storage:test'
                    # Missing PrimaryTargetIPAddress and PrimaryLUN
                }
            },
            'iscsi_enabled': True
        }
        
        # Act
        result = boot_script.validate_iscsi_configuration(
            mock_r630, 
            'iqn.2023-01.com.example:storage:test',
            self.logger
        )
        
        # Assert
        self.assertFalse(result)
        mock_r630.get_iscsi_configuration.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.R630Component')
    def test_validate_iscsi_configuration_not_enabled(self, mock_r630_class):
        """Test validation when iSCSI is not enabled."""
        # Setup
        mock_r630 = MagicMock()
        
        # Configure get_iscsi_configuration with iSCSI not enabled
        mock_r630.get_iscsi_configuration.return_value = {
            'configuration': {
                'iSCSIBoot': {}
            },
            'iscsi_enabled': False
        }
        
        # Act
        result = boot_script.validate_iscsi_configuration(
            mock_r630, 
            'iqn.2023-01.com.example:storage:test',
            self.logger
        )
        
        # Assert
        self.assertFalse(result)
        mock_r630.get_iscsi_configuration.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.list_available_targets')
    @patch('scripts.config_iscsi_boot_py312.setup_logging')
    @patch('scripts.config_iscsi_boot_py312.parse_arguments')
    def test_main_list_targets(self, mock_parse_args, mock_setup_logging, mock_list_targets):
        """Test main function with list_targets option."""
        # Setup
        args = self.mock_args
        args.list_targets = True
        mock_parse_args.return_value = args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        
        # Act
        result = boot_script.main()
        
        # Assert
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_list_targets.assert_called_once_with(mock_logger)

    @patch('scripts.config_iscsi_boot_py312.validate_iscsi_configuration')
    @patch('scripts.config_iscsi_boot_py312.check_r630_hardware')
    @patch('scripts.config_iscsi_boot_py312.R630Component')
    @patch('scripts.config_iscsi_boot_py312.setup_logging')
    @patch('scripts.config_iscsi_boot_py312.parse_arguments')
    def test_main_validate_only(self, mock_parse_args, mock_setup_logging, mock_r630_class, 
                               mock_check_hardware, mock_validate):
        """Test main function with validate_only option."""
        # Setup
        args = self.mock_args
        args.validate_only = True
        args.target = None  # Not required for validate_only
        mock_parse_args.return_value = args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_r630 = MagicMock()
        mock_r630_class.return_value = mock_r630
        mock_check_hardware.return_value = True
        mock_validate.return_value = True
        
        # Act
        result = boot_script.main()
        
        # Assert
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_r630_class.assert_called_once()
        mock_check_hardware.assert_called_once()
        mock_validate.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.reset_iscsi_configuration')
    @patch('scripts.config_iscsi_boot_py312.check_r630_hardware')
    @patch('scripts.config_iscsi_boot_py312.R630Component')
    @patch('scripts.config_iscsi_boot_py312.setup_logging')
    @patch('scripts.config_iscsi_boot_py312.parse_arguments')
    def test_main_reset_iscsi(self, mock_parse_args, mock_setup_logging, mock_r630_class, 
                             mock_check_hardware, mock_reset):
        """Test main function with reset_iscsi option."""
        # Setup
        args = self.mock_args
        args.reset_iscsi = True
        args.target = None  # Not required for reset_iscsi
        mock_parse_args.return_value = args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_r630 = MagicMock()
        mock_r630_class.return_value = mock_r630
        mock_check_hardware.return_value = True
        mock_reset.return_value = True
        
        # Act
        result = boot_script.main()
        
        # Assert
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_r630_class.assert_called_once()
        mock_check_hardware.assert_called_once()
        mock_reset.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.configure_iscsi_boot')
    @patch('scripts.config_iscsi_boot_py312.ISCSIComponent')
    @patch('scripts.config_iscsi_boot_py312.get_target_config')
    @patch('scripts.config_iscsi_boot_py312.load_targets')
    @patch('scripts.config_iscsi_boot_py312.check_r630_hardware')
    @patch('scripts.config_iscsi_boot_py312.R630Component')
    @patch('scripts.config_iscsi_boot_py312.setup_logging')
    @patch('scripts.config_iscsi_boot_py312.parse_arguments')
    def test_main_configure_iscsi_boot(self, mock_parse_args, mock_setup_logging, mock_r630_class, 
                                      mock_check_hardware, mock_load_targets, mock_get_target,
                                      mock_iscsi_class, mock_configure_boot):
        """Test main function configuring iSCSI boot."""
        # Setup
        mock_parse_args.return_value = self.mock_args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_r630 = MagicMock()
        mock_r630_class.return_value = mock_r630
        mock_check_hardware.return_value = True
        mock_load_targets.return_value = self.mock_targets_data
        mock_get_target.return_value = self.mock_target
        mock_iscsi = MagicMock()
        mock_iscsi_class.return_value = mock_iscsi
        mock_configure_boot.return_value = True
        
        # Act
        result = boot_script.main()
        
        # Assert
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_r630_class.assert_called_once()
        mock_check_hardware.assert_called_once()
        mock_load_targets.assert_called_once()
        mock_get_target.assert_called_once()
        mock_iscsi_class.assert_called_once()
        mock_configure_boot.assert_called_once()

    @patch('scripts.config_iscsi_boot_py312.configure_iscsi_boot')
    @patch('scripts.config_iscsi_boot_py312.ISCSIComponent')
    @patch('scripts.config_iscsi_boot_py312.get_target_config')
    @patch('scripts.config_iscsi_boot_py312.load_targets')
    @patch('scripts.config_iscsi_boot_py312.check_r630_hardware')
    @patch('scripts.config_iscsi_boot_py312.R630Component')
    @patch('scripts.config_iscsi_boot_py312.setup_logging')
    @patch('scripts.config_iscsi_boot_py312.parse_arguments')
    def test_main_configure_iscsi_boot_failure(self, mock_parse_args, mock_setup_logging, mock_r630_class, 
                                             mock_check_hardware, mock_load_targets, mock_get_target,
                                             mock_iscsi_class, mock_configure_boot):
        """Test main function when iSCSI boot configuration fails."""
        # Setup
        mock_parse_args.return_value = self.mock_args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_r630 = MagicMock()
        mock_r630_class.return_value = mock_r630
        mock_check_hardware.return_value = True
        mock_load_targets.return_value = self.mock_targets_data
        mock_get_target.return_value = self.mock_target
        mock_iscsi = MagicMock()
        mock_iscsi_class.return_value = mock_iscsi
        mock_configure_boot.return_value = False  # Configuration fails
        
        # Act
        result = boot_script.main()
        
        # Assert
        self.assertEqual(result, 1)  # Should return non-zero for failure
        mock_configure_boot.assert_called_once()


if __name__ == '__main__':
    unittest.main()
