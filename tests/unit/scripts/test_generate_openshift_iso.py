#!/usr/bin/env python3
"""
Unit tests for the generate_openshift_iso.py script
"""

import os
import sys
import pytest
import subprocess
from unittest.mock import MagicMock, patch
import argparse
import yaml

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the script under test
import scripts.generate_openshift_iso as iso_script


class TestGenerateOpenShiftISO:
    """Test class for generate_openshift_iso.py script"""

    @pytest.fixture
    def mock_args(self):
        """Mock command-line arguments"""
        args = argparse.Namespace()
        args.version = "4.18"
        args.domain = "example.com"
        args.rendezvous_ip = "192.168.1.100"
        args.pull_secret = None
        args.ssh_key = None
        args.values_file = None
        args.truenas_ip = "192.168.2.245"
        args.truenas_user = "root"
        args.private_key = None
        args.skip_upload = False
        args.output_dir = None
        args.verbose = False
        args.dry_run = True
        return args

    @pytest.fixture
    def mock_logger(self):
        """Mock logger instance"""
        return MagicMock()

    @pytest.fixture
    def mock_openshift_component(self):
        """Mock OpenShiftComponent instance"""
        mock = MagicMock()
        mock.discover.return_value = {
            'pull_secret_available': True,
            'ssh_key_available': True,
            'installer_available': True,
            'available_versions': ['4.18.0']
        }
        mock.process.return_value = {
            'iso_generated': True,
            'iso_path': '/tmp/test-dir/agent.x86_64.iso'
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
            "generate_openshift_iso.py",
            "--version", "4.18.5",
            "--domain", "test.local",
            "--rendezvous-ip", "192.168.1.100",
            "--truenas-ip", "192.168.2.245",
            "--dry-run"
        ]
        
        with patch('sys.argv', test_args):
            args = iso_script.parse_arguments()
            
            assert args.version == "4.18.5"
            assert args.domain == "test.local"
            assert args.rendezvous_ip == "192.168.1.100"
            assert args.truenas_ip == "192.168.2.245"
            assert args.dry_run is True
            assert args.skip_upload is False  # Default value

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=MagicMock)
    def test_get_ssh_key_with_path(self, mock_open, mock_exists):
        """Test getting SSH key with provided path"""
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "ssh-rsa TESTKEY"
        mock_open.return_value = mock_file
        
        result = iso_script.get_ssh_key("/path/to/key.pub")
        
        assert result == "ssh-rsa TESTKEY"
        mock_exists.assert_called_with("/path/to/key.pub")
        mock_open.assert_called_with("/path/to/key.pub", 'r')

    @patch('os.path.exists')
    def test_get_ssh_key_not_found(self, mock_exists):
        """Test getting SSH key when file doesn't exist"""
        mock_exists.return_value = False
        
        result = iso_script.get_ssh_key("/path/to/key.pub")
        
        assert result is None
        mock_exists.assert_called_with("/path/to/key.pub")

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=MagicMock)
    def test_get_pull_secret_with_path(self, mock_open, mock_exists):
        """Test getting pull secret with provided path"""
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = '{"auth":{"cloud":{"token":"TESTTOKEN"}}}'
        mock_open.return_value = mock_file
        
        result = iso_script.get_pull_secret("/path/to/pull-secret")
        
        assert result == '{"auth":{"cloud":{"token":"TESTTOKEN"}}}'
        mock_exists.assert_called_with("/path/to/pull-secret")
        mock_open.assert_called_with("/path/to/pull-secret", 'r')

    @patch('subprocess.run')
    def test_upload_to_truenas_success(self, mock_run):
        """Test successful upload to TrueNAS"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = iso_script.upload_to_truenas(
            "/path/to/iso.iso",
            "4.18",
            "192.168.2.245",
            "root"
        )
        
        assert result is True
        mock_run.assert_called_once()
        # Verify the command has the right structure
        args, kwargs = mock_run.call_args
        assert args[0][0] == "scp"
        assert args[0][-2] == "/path/to/iso.iso"
        assert "root@192.168.2.245" in args[0][-1]

    @patch('subprocess.run')
    def test_upload_to_truenas_with_key(self, mock_run):
        """Test upload to TrueNAS with private key"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = iso_script.upload_to_truenas(
            "/path/to/iso.iso",
            "4.18",
            "192.168.2.245",
            "root",
            "/path/to/private_key"
        )
        
        assert result is True
        mock_run.assert_called_once()
        # Verify the command includes the private key
        args, kwargs = mock_run.call_args
        assert args[0][0] == "scp"
        assert args[0][1] == "-i"
        assert args[0][2] == "/path/to/private_key"

    @patch('subprocess.run')
    def test_upload_to_truenas_failure(self, mock_run):
        """Test upload to TrueNAS failure"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "scp")
        
        result = iso_script.upload_to_truenas(
            "/path/to/iso.iso",
            "4.18",
            "192.168.2.245",
            "root"
        )
        
        assert result is False

    def test_create_openshift_config(self, mock_args):
        """Test OpenShift configuration creation"""
        # Mock the helper functions
        with patch('scripts.generate_openshift_iso.get_pull_secret') as mock_pull_secret, \
             patch('scripts.generate_openshift_iso.get_ssh_key') as mock_ssh_key:
            mock_pull_secret.return_value = '{"auth":{"cloud":{"token":"TESTTOKEN"}}}'
            mock_ssh_key.return_value = "ssh-rsa TESTKEY"
            
            # Test basic config creation
            config = iso_script.create_openshift_config(mock_args)
            
            assert config['openshift_version'] == mock_args.version
            assert config['domain'] == mock_args.domain
            assert config['rendezvous_ip'] == mock_args.rendezvous_ip
            assert config['pull_secret_content'] == '{"auth":{"cloud":{"token":"TESTTOKEN"}}}'
            assert config['ssh_key_content'] == "ssh-rsa TESTKEY"
            assert config['dry_run'] is True

    def test_create_openshift_config_with_values(self, mock_args):
        """Test OpenShift configuration creation with values file"""
        # Mock the values file content
        values = {
            'baseDomain': 'test.local',
            'sno': {
                'nodeIP': '192.168.1.101',
                'hostname': 'test-node',
                'server_id': '01'
            },
            'pullSecret': '{"auth":{"cloud":{"token":"FILETOKEN"}}}',
            'sshKey': 'ssh-rsa FILEKEY',
            'bootstrapInPlace': {
                'installationDisk': '/dev/sda'
            }
        }
        
        # Test config creation with values file
        config = iso_script.create_openshift_config(mock_args, values)
        
        assert config['openshift_version'] == mock_args.version
        assert config['domain'] == 'test.local'  # From values file
        assert config['rendezvous_ip'] == '192.168.1.101'  # From values file
        assert config['hostname'] == 'test-node'  # From values file
        assert config['server_id'] == '01'  # From values file
        assert config['installation_disk'] == '/dev/sda'  # From values file
        assert config['pull_secret_content'] == '{"auth":{"cloud":{"token":"FILETOKEN"}}}'
        assert config['ssh_key_content'] == 'ssh-rsa FILEKEY'
        assert config['values_file_content'] == values

    @patch('scripts.generate_openshift_iso.OpenShiftComponent')
    def test_run_workflow_success(self, mock_openshift_class, mock_args, mock_logger, mock_openshift_component):
        """Test successful workflow execution"""
        # Configure mocks
        mock_openshift_class.return_value = mock_openshift_component
        
        # Mock helper functions
        with patch('scripts.generate_openshift_iso.create_openshift_config') as mock_create_config, \
             patch('scripts.generate_openshift_iso.upload_to_truenas') as mock_upload:
            
            mock_create_config.return_value = {
                'openshift_version': '4.18',
                'domain': 'example.com',
                'rendezvous_ip': '192.168.1.100',
                'pull_secret_content': '{"auth":{"cloud":{"token":"TESTTOKEN"}}}',
                'ssh_key_content': 'ssh-rsa TESTKEY',
                'dry_run': True
            }
            mock_upload.return_value = True
            
            # Run the workflow
            result = iso_script.run_workflow(mock_args, mock_logger)
            
            # Verify the results
            assert result == 0  # Success
            mock_openshift_class.assert_called_once()
            mock_openshift_component.discover.assert_called_once()
            mock_openshift_component.process.assert_called_once()
            mock_openshift_component.housekeep.assert_called_once()
            mock_upload.assert_called_once()

    @patch('scripts.generate_openshift_iso.OpenShiftComponent')
    def test_run_workflow_skip_upload(self, mock_openshift_class, mock_args, mock_logger, mock_openshift_component):
        """Test workflow with skip_upload option"""
        # Configure mocks
        mock_openshift_class.return_value = mock_openshift_component
        mock_args.skip_upload = True
        
        # Mock helper functions
        with patch('scripts.generate_openshift_iso.create_openshift_config') as mock_create_config, \
             patch('scripts.generate_openshift_iso.upload_to_truenas') as mock_upload:
            
            mock_create_config.return_value = {
                'openshift_version': '4.18',
                'domain': 'example.com',
                'rendezvous_ip': '192.168.1.100',
                'pull_secret_content': '{"auth":{"cloud":{"token":"TESTTOKEN"}}}',
                'ssh_key_content': 'ssh-rsa TESTKEY',
                'dry_run': True
            }
            
            # Run the workflow
            result = iso_script.run_workflow(mock_args, mock_logger)
            
            # Verify the results
            assert result == 0  # Success
            mock_openshift_component.discover.assert_called_once()
            mock_openshift_component.process.assert_called_once()
            mock_openshift_component.housekeep.assert_called_once()
            mock_upload.assert_not_called()  # Upload should be skipped

    @patch('scripts.generate_openshift_iso.OpenShiftComponent')
    def test_run_workflow_missing_pull_secret(self, mock_openshift_class, mock_args, mock_logger):
        """Test workflow with missing pull secret"""
        # Mock helper functions
        with patch('scripts.generate_openshift_iso.create_openshift_config') as mock_create_config:
            mock_create_config.return_value = {
                'openshift_version': '4.18',
                'domain': 'example.com',
                'rendezvous_ip': '192.168.1.100',
                'pull_secret_content': None,  # Missing pull secret
                'ssh_key_content': 'ssh-rsa TESTKEY'
            }
            
            # Run the workflow
            result = iso_script.run_workflow(mock_args, mock_logger)
            
            # Verify the results
            assert result == 1  # Failure
            mock_openshift_class.assert_not_called()
