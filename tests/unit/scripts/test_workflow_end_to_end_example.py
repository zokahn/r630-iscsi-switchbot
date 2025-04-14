#!/usr/bin/env python3
"""
Unit tests for the workflow_end_to_end_example.py script
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
import argparse

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the script under test
import scripts.workflow_end_to_end_example as workflow_script


class TestWorkflowEndToEndExample:
    """Test class for workflow_end_to_end_example.py script"""

    @pytest.fixture
    def mock_args(self):
        """Mock command-line arguments"""
        args = argparse.Namespace()
        args.server_id = "01"
        args.hostname = "test-server"
        args.node_ip = "192.168.1.100"
        args.openshift_version = "4.14.0"
        args.s3_endpoint = "test-endpoint.example.com"
        args.s3_access_key = "test-access-key"
        args.s3_secret_key = "test-secret-key"
        args.truenas_ip = "192.168.1.200"
        args.truenas_api_key = "test-api-key"
        args.idrac_ip = "192.168.1.201"
        args.idrac_username = "root"
        args.idrac_password = "test-password"
        args.domain = "lab.example.com"
        args.pull_secret_path = None
        args.ssh_key_path = None
        args.zvol_size = "20G"
        args.zfs_pool = "tank"
        args.skip_iso = False
        args.skip_iscsi = False
        args.skip_r630 = False
        args.temp_dir = None
        args.dry_run = True
        args.cleanup = False
        args.verbose = False
        return args

    @pytest.fixture
    def mock_logger(self):
        """Mock logger instance"""
        return MagicMock()

    def test_parse_arguments(self):
        """Test argument parsing functionality"""
        # Mock sys.argv
        test_args = [
            "workflow_end_to_end_example.py",
            "--server-id", "01",
            "--hostname", "test-server",
            "--node-ip", "192.168.1.100",
            "--openshift-version", "4.14.0",
            "--s3-endpoint", "minio.example.com",
            "--truenas-ip", "192.168.1.200",
            "--idrac-ip", "192.168.1.201",
            "--dry-run"
        ]
        
        with patch('sys.argv', test_args):
            args = workflow_script.parse_arguments()
            
            assert args.server_id == "01"
            assert args.hostname == "test-server"
            assert args.node_ip == "192.168.1.100"
            assert args.openshift_version == "4.14.0"
            assert args.s3_endpoint == "minio.example.com"
            assert args.truenas_ip == "192.168.1.200"
            assert args.idrac_ip == "192.168.1.201"
            assert args.dry_run is True
            assert args.skip_iso is False  # Default value
            assert args.domain == "lab.example.com"  # Default value

    def test_build_s3_config(self, mock_args):
        """Test S3 configuration creation"""
        config = workflow_script.build_s3_config(mock_args)
        
        assert config['endpoint'] == mock_args.s3_endpoint
        assert config['access_key'] == mock_args.s3_access_key
        assert config['secret_key'] == mock_args.s3_secret_key
        assert config['private_bucket'] == 'r630-switchbot-private'
        assert config['public_bucket'] == 'r630-switchbot-public'
        assert config['create_buckets_if_missing'] is True
        assert config['component_id'] == f's3-component-{mock_args.server_id}'
        assert config['dry_run'] is True

    def test_build_openshift_config(self, mock_args):
        """Test OpenShift configuration creation"""
        config = workflow_script.build_openshift_config(mock_args)
        
        assert config['openshift_version'] == mock_args.openshift_version
        assert config['domain'] == mock_args.domain
        assert config['rendezvous_ip'] == mock_args.node_ip
        assert config['node_ip'] == mock_args.node_ip
        assert config['server_id'] == mock_args.server_id
        assert config['hostname'] == mock_args.hostname
        assert config['pull_secret_path'] == mock_args.pull_secret_path
        assert config['ssh_key_path'] == mock_args.ssh_key_path
        assert config['component_id'] == f'openshift-component-{mock_args.server_id}'
        assert config['dry_run'] is True

    def test_build_iscsi_config(self, mock_args):
        """Test iSCSI configuration creation"""
        config = workflow_script.build_iscsi_config(mock_args)
        
        assert config['truenas_ip'] == mock_args.truenas_ip
        assert config['api_key'] == mock_args.truenas_api_key
        assert config['server_id'] == mock_args.server_id
        assert config['hostname'] == mock_args.hostname
        assert config['openshift_version'] == mock_args.openshift_version
        assert config['zvol_size'] == mock_args.zvol_size
        assert config['zfs_pool'] == mock_args.zfs_pool
        assert config['dry_run'] is True
        assert config['cleanup_unused'] is False
        assert config['component_id'] == f'iscsi-component-{mock_args.server_id}'

    def test_build_r630_config(self, mock_args):
        """Test R630 configuration creation"""
        config = workflow_script.build_r630_config(mock_args)
        
        assert config['idrac_ip'] == mock_args.idrac_ip
        assert config['idrac_username'] == mock_args.idrac_username
        assert config['idrac_password'] == mock_args.idrac_password
        assert config['server_id'] == mock_args.server_id
        assert config['boot_mode'] == 'iscsi'
        assert config['dry_run'] is True
        assert config['component_id'] == f'r630-component-{mock_args.server_id}'
