#!/usr/bin/env python3
"""
Unit tests for the generate_openshift_iso_py312.py script.

These tests verify that the Python 3.12 version of the OpenShift ISO generation script 
correctly handles various scenarios, including successful execution, error conditions,
and different command-line options.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open
import argparse
import logging
import yaml
import tempfile
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the script under test
import scripts.generate_openshift_iso_py312 as iso_script


class TestGenerateOpenShiftIsoPy312(unittest.TestCase):
    """Test cases for the generate_openshift_iso_py312.py script."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create dummy logger for tests
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.NullHandler())
        
        # Mock command line arguments
        self.mock_args = argparse.Namespace(
            version="4.18.0",
            domain="example.com",
            rendezvous_ip="192.168.1.100",
            pull_secret="test_pull_secret_path",
            ssh_key="test_ssh_key_path",
            values_file=None,
            truenas_ip="192.168.2.245",
            truenas_user="root",
            private_key=None,
            skip_upload=False,
            output_dir=None,
            verbose=False,
            dry_run=False
        )
        
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='apiVersion: v1\nbaseDomain: test.com')
    def test_load_values_from_file_success(self, mock_file, mock_exists):
        """Test loading values from a valid YAML file."""
        # Setup
        mock_exists.return_value = True
        
        # Act
        result = iso_script.load_values_from_file("test_values.yaml")
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.get('baseDomain'), 'test.com')
        mock_file.assert_called_once()

    @patch('pathlib.Path.exists')
    def test_load_values_from_file_nonexistent(self, mock_exists):
        """Test loading values from a non-existent file."""
        # Setup
        mock_exists.return_value = False
        
        # Act
        result = iso_script.load_values_from_file("nonexistent.yaml")
        
        # Assert
        self.assertIsNone(result)

    @patch('yaml.safe_load')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_values_from_file_invalid_yaml(self, mock_file, mock_exists, mock_yaml_load):
        """Test loading values from an invalid YAML file."""
        # Setup
        mock_exists.return_value = True
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
        
        # Act
        result = iso_script.load_values_from_file("invalid_yaml.yaml")
        
        # Assert
        self.assertIsNone(result)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_get_ssh_key_from_path(self, mock_read_text, mock_exists):
        """Test getting SSH key from the provided path."""
        # Setup
        mock_exists.return_value = True
        mock_read_text.return_value = "ssh-rsa AAAAB3Nz..."
        
        # Act
        result = iso_script.get_ssh_key("test_ssh_key.pub")
        
        # Assert
        self.assertEqual(result, "ssh-rsa AAAAB3Nz...")
        mock_exists.assert_called_once()
        mock_read_text.assert_called_once()

    @patch('pathlib.Path.exists')
    def test_get_ssh_key_nonexistent(self, mock_exists):
        """Test getting SSH key from a non-existent path."""
        # Setup
        mock_exists.return_value = False
        
        # Act
        result = iso_script.get_ssh_key("nonexistent_ssh_key.pub")
        
        # Assert
        self.assertIsNone(result)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.home')
    def test_get_ssh_key_default_location(self, mock_home, mock_read_text, mock_exists):
        """Test getting SSH key from the default location."""
        # Setup - custom path doesn't exist, but default path does
        mock_exists.side_effect = [False, True]
        mock_read_text.return_value = "ssh-rsa AAAAB3Nz..."
        mock_home_path = MagicMock()
        mock_home.return_value = mock_home_path
        mock_home_path.__truediv__.return_value.__truediv__.return_value = Path("/home/user/.ssh/id_rsa.pub")
        
        # Act
        result = iso_script.get_ssh_key()
        
        # Assert
        self.assertEqual(result, "ssh-rsa AAAAB3Nz...")
        mock_read_text.assert_called_once()

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_get_pull_secret_from_path(self, mock_read_text, mock_exists):
        """Test getting pull secret from the provided path."""
        # Setup
        mock_exists.return_value = True
        mock_read_text.return_value = '{"auths": {...}}'
        
        # Act
        result = iso_script.get_pull_secret("test_pull_secret.json")
        
        # Assert
        self.assertEqual(result, '{"auths": {...}}')
        mock_exists.assert_called_once()
        mock_read_text.assert_called_once()

    @patch('scripts.generate_openshift_iso_py312.get_secret')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.home')
    def test_get_pull_secret_from_secrets_provider(self, mock_home, mock_exists, mock_get_secret):
        """Test getting pull secret from the secrets provider."""
        # Setup - no path provided, default path doesn't exist, but secret provider works
        mock_exists.return_value = False
        mock_get_secret.return_value = '{"auths": {...}}'
        mock_home_path = MagicMock()
        mock_home.return_value = mock_home_path
        mock_home_path.__truediv__.return_value.__truediv__.return_value = Path("/home/user/.openshift/pull-secret")
        
        # Act
        result = iso_script.get_pull_secret()
        
        # Assert
        self.assertEqual(result, '{"auths": {...}}')
        mock_get_secret.assert_called_once_with('openshift/pull-secret')

    @patch('subprocess.run')
    def test_upload_to_truenas_success(self, mock_run):
        """Test successful upload to TrueNAS."""
        # Setup
        mock_run.return_value = MagicMock(returncode=0)
        
        # Act
        result = iso_script.upload_to_truenas(
            iso_path="test.iso",
            version="4.18.0",
            truenas_ip="192.168.2.245",
            username="root"
        )
        
        # Assert
        self.assertTrue(result)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][0], "scp")  # First command should be scp
        self.assertEqual(kwargs["check"], True)

    @patch('subprocess.run')
    def test_upload_to_truenas_with_private_key(self, mock_run):
        """Test upload to TrueNAS with a private key."""
        # Setup
        mock_run.return_value = MagicMock(returncode=0)
        
        # Act
        result = iso_script.upload_to_truenas(
            iso_path="test.iso",
            version="4.18.0",
            truenas_ip="192.168.2.245",
            username="root",
            private_key="~/.ssh/id_rsa"
        )
        
        # Assert
        self.assertTrue(result)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][1], "-i")  # Second argument should be -i
        self.assertEqual(args[0][2], "~/.ssh/id_rsa")  # Third argument should be the key path

    @patch('subprocess.run')
    def test_upload_to_truenas_failure(self, mock_run):
        """Test failed upload to TrueNAS."""
        # Setup
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, 
            cmd=["scp", "test.iso", "root@192.168.2.245:/mnt/tank/openshift_isos/4.18/agent.x86_64.iso"],
            stderr="Connection refused"
        )
        
        # Act
        result = iso_script.upload_to_truenas(
            iso_path="test.iso",
            version="4.18.0",
            truenas_ip="192.168.2.245",
            username="root"
        )
        
        # Assert
        self.assertFalse(result)
        mock_run.assert_called_once()

    def test_create_openshift_config_basic(self):
        """Test creating OpenShift configuration from basic arguments."""
        # Setup - mock pull_secret and ssh_key to avoid file system operations
        with patch('scripts.generate_openshift_iso_py312.get_pull_secret', return_value='{"auths": {...}}'), \
             patch('scripts.generate_openshift_iso_py312.get_ssh_key', return_value='ssh-rsa AAAAB3Nz...'):
            
            # Act
            config = iso_script.create_openshift_config(self.mock_args)
            
            # Assert
            self.assertEqual(config['openshift_version'], "4.18.0")
            self.assertEqual(config['domain'], "example.com")
            self.assertEqual(config['rendezvous_ip'], "192.168.1.100")
            self.assertEqual(config['node_ip'], "192.168.1.100")
            self.assertEqual(config['pull_secret_content'], '{"auths": {...}}')
            self.assertEqual(config['ssh_key_content'], 'ssh-rsa AAAAB3Nz...')
            self.assertEqual(config['component_id'], 'openshift-iso-component')
            self.assertFalse(config['dry_run'])

    def test_create_openshift_config_with_values(self):
        """Test creating OpenShift configuration with values from file."""
        # Setup
        values = {
            'baseDomain': 'test-domain.com',
            'sno': {
                'nodeIP': '192.168.1.200',
                'hostname': 'test-node',
                'server_id': 'test-server',
                'installationDisk': '/dev/sda'
            },
            'pullSecret': '{"auths": {"test": "value"}}',
            'sshKey': 'ssh-rsa TEST_KEY'
        }
        
        # Act
        config = iso_script.create_openshift_config(self.mock_args, values)
        
        # Assert
        self.assertEqual(config['domain'], 'test-domain.com')
        self.assertEqual(config['rendezvous_ip'], '192.168.1.200')
        self.assertEqual(config['node_ip'], '192.168.1.200')
        self.assertEqual(config['hostname'], 'test-node')
        self.assertEqual(config['server_id'], 'test-server')
        self.assertEqual(config['installation_disk'], '/dev/sda')
        self.assertEqual(config['pull_secret_content'], '{"auths": {"test": "value"}}')
        self.assertEqual(config['ssh_key_content'], 'ssh-rsa TEST_KEY')
        self.assertEqual(config['values_file_content'], values)

    @patch('scripts.generate_openshift_iso_py312.OpenShiftComponent')
    def test_run_workflow_discovery_failure(self, mock_openshift_component_class):
        """Test run_workflow when discovery fails."""
        # Setup
        mock_component = MagicMock()
        mock_openshift_component_class.return_value = mock_component
        
        # Configure OpenShift component to fail discovery
        mock_component.discover.return_value = {
            'pull_secret_available': False,
            'ssh_key_available': True,
            'error': 'Pull secret verification failed'
        }
        
        # Mock the dependencies to avoid real filesystem interactions
        with patch('scripts.generate_openshift_iso_py312.get_pull_secret', return_value='{"auths": {}}'), \
             patch('scripts.generate_openshift_iso_py312.get_ssh_key', return_value='ssh-key'):
            
            # Act
            result = iso_script.run_workflow(self.mock_args, self.logger)
            
            # Assert
            self.assertEqual(result, 1)  # Should fail
            mock_component.discover.assert_called_once()
            mock_component.process.assert_not_called()  # Process not called on discovery failure

    @patch('scripts.generate_openshift_iso_py312.OpenShiftComponent')
    @patch('scripts.generate_openshift_iso_py312.upload_to_truenas')
    def test_run_workflow_success_with_upload(self, mock_upload, mock_openshift_component_class):
        """Test run_workflow with successful ISO generation and upload."""
        # Setup
        mock_component = MagicMock()
        mock_openshift_component_class.return_value = mock_component
        
        # Configure discovery success
        mock_component.discover.return_value = {
            'pull_secret_available': True,
            'ssh_key_available': True
        }
        
        # Configure processing success with ISO path
        mock_component.process.return_value = {
            'iso_generated': True,
            'iso_path': '/tmp/agent.x86_64.iso'
        }
        
        # Configure housekeeping success
        mock_component.housekeep.return_value = {
            'temp_files_removed': True
        }
        
        # Configure upload success
        mock_upload.return_value = True
        
        # Mock dependencies to avoid filesystem interactions
        with patch('scripts.generate_openshift_iso_py312.get_pull_secret', return_value='{"auths": {}}'), \
             patch('scripts.generate_openshift_iso_py312.get_ssh_key', return_value='ssh-key'):
            
            # Act
            result = iso_script.run_workflow(self.mock_args, self.logger)
            
            # Assert
            self.assertEqual(result, 0)  # Should succeed
            mock_component.discover.assert_called_once()
            mock_component.process.assert_called_once()
            mock_component.housekeep.assert_called_once()
            mock_upload.assert_called_once()

    @patch('scripts.generate_openshift_iso_py312.OpenShiftComponent')
    def test_run_workflow_skip_upload(self, mock_openshift_component_class):
        """Test run_workflow with upload skipped."""
        # Setup
        mock_component = MagicMock()
        mock_openshift_component_class.return_value = mock_component
        
        # Configure discovery and processing success
        mock_component.discover.return_value = {
            'pull_secret_available': True,
            'ssh_key_available': True
        }
        mock_component.process.return_value = {
            'iso_generated': True,
            'iso_path': '/tmp/agent.x86_64.iso'
        }
        mock_component.housekeep.return_value = {
            'temp_files_removed': True
        }
        
        # Set skip_upload flag
        args = self.mock_args
        args.skip_upload = True
        
        # Mock dependencies to avoid filesystem interactions
        with patch('scripts.generate_openshift_iso_py312.get_pull_secret', return_value='{"auths": {}}'), \
             patch('scripts.generate_openshift_iso_py312.get_ssh_key', return_value='ssh-key'), \
             patch('scripts.generate_openshift_iso_py312.upload_to_truenas') as mock_upload:
            
            # Act
            result = iso_script.run_workflow(args, self.logger)
            
            # Assert
            self.assertEqual(result, 0)  # Should succeed
            mock_upload.assert_not_called()  # Upload should not be called

    @patch('scripts.generate_openshift_iso_py312.parse_arguments')
    @patch('scripts.generate_openshift_iso_py312.setup_logging')
    @patch('scripts.generate_openshift_iso_py312.run_workflow')
    def test_main_success(self, mock_run_workflow, mock_setup_logging, mock_parse_arguments):
        """Test main function with successful workflow execution."""
        # Setup
        mock_parse_arguments.return_value = self.mock_args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_run_workflow.return_value = 0
        
        # Act
        with patch('pathlib.Path.mkdir'):  # Mock directory creation
            result = iso_script.main()
        
        # Assert
        self.assertEqual(result, 0)
        mock_parse_arguments.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_run_workflow.assert_called_once_with(self.mock_args, mock_logger)

    @patch('scripts.generate_openshift_iso_py312.parse_arguments')
    @patch('scripts.generate_openshift_iso_py312.setup_logging')
    @patch('scripts.generate_openshift_iso_py312.run_workflow')
    def test_main_with_output_dir(self, mock_run_workflow, mock_setup_logging, mock_parse_arguments):
        """Test main function with output directory specified."""
        # Setup
        args = self.mock_args
        args.output_dir = "/tmp/openshift-iso"
        mock_parse_arguments.return_value = args
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_run_workflow.return_value = 0
        
        # Act
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            result = iso_script.main()
        
        # Assert
        self.assertEqual(result, 0)
        mock_mkdir.assert_called_once()
        mock_run_workflow.assert_called_once_with(args, mock_logger)


if __name__ == '__main__':
    unittest.main()
