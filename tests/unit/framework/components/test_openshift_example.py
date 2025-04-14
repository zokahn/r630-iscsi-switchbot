#!/usr/bin/env python3
"""
Example tests for the OpenShiftComponent class using the mock_filesystem fixture.

This file demonstrates how to use the enhanced testing fixtures
for testing components that interact with the file system.
"""

import pytest
import os
import sys
import hashlib
from unittest.mock import patch, MagicMock, mock_open, ANY

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from framework.components.openshift_component import OpenShiftComponent


class TestOpenShiftComponentExample:
    """Example test cases showing how to use the mock_filesystem fixture."""

    @pytest.fixture
    def component(self, openshift_test_config, mock_logger):
        """Fixture to create a component instance with mocked S3 dependency."""
        # Create a mock S3Component
        mock_s3_component = MagicMock()
        mock_s3_component.s3_client = MagicMock()
        mock_s3_component.s3_resource = MagicMock()
        
        # Mock file objects filter
        mock_bucket = MagicMock()
        mock_bucket.objects.filter.return_value = []
        mock_s3_component.s3_resource.Bucket.return_value = mock_bucket
        
        # Create the component
        component = OpenShiftComponent(openshift_test_config, s3_component=mock_s3_component, logger=mock_logger)
        
        return component

    def test_process_phase_with_existing_installer(self, component, mock_filesystem):
        """Test the process phase with an existing installer using the mock_filesystem fixture."""
        # Set up discovery results
        component.discovery_results = {
            'installer_available': True,
            'installer_path': '/usr/local/bin/openshift-install',
            'pull_secret_available': True,
            'ssh_key_available': True,
            'temp_dir': '/tmp/test-temp-dir'
        }
        
        # Set necessary component properties directly
        component.temp_dir = '/tmp/test-temp-dir'
        
        # Set phase as executed
        component.phases_executed['discover'] = True
        
        # Create a mock ISO file using the helper function
        from tests.conftest import create_mock_iso
        iso_path = create_mock_iso('/tmp/test-temp-dir')
        
        # Configure the filesystem mock to handle file operations
        # - Existing installer
        mock_filesystem['exists'].side_effect = lambda path: True
        
        # No need to mock open specifically - it's already set up in the fixture
        # The fixture already patches builtins.open with mock_open(read_data=b'iso content')
        
        # Run processing
        result = component.process()
        
        # Check processing was successful
        assert component.phases_executed['process'] == True
        
        # Check installer was copied from existing path
        mock_filesystem['copy2'].assert_called_with('/usr/local/bin/openshift-install', '/tmp/test-temp-dir/openshift-install')
        mock_filesystem['chmod'].assert_called_with('/tmp/test-temp-dir/openshift-install', 0o755)
        
        # Check installer download status
        assert result['installer_downloaded'] == True
        assert result['installer_source'] == 'local'

    def test_housekeep_phase_with_mocking(self, component, mock_filesystem):
        """Test the housekeep phase with the mock_filesystem fixture."""
        # Set up component state as if discovery and process phases completed
        component.discovery_results = {
            'installer_available': True,
            'installer_path': '/usr/local/bin/openshift-install',
            'pull_secret_available': True,
            'ssh_key_available': True,
            'temp_dir': '/tmp/test-temp-dir'
        }
        component.temp_dir = '/tmp/test-temp-dir'
        component.iso_path = '/tmp/test-temp-dir/agent.x86_64.iso'
        component.processing_results = {
            'iso_generated': True,
            'iso_path': '/tmp/test-temp-dir/agent.x86_64.iso'
        }
        component.phases_executed['discover'] = True
        component.phases_executed['process'] = True
        
        # Mock file existence only - the open mock is already set up in the fixture
        mock_filesystem['exists'].return_value = True
        mock_filesystem['isfile'].return_value = True
        
        # Run housekeeping
        result = component.housekeep()
        
        # Check housekeeping was successful
        assert component.phases_executed['housekeep'] == True
        
        # Check ISO verification
        assert result['iso_verified'] == True
        assert result['iso_hash'] == hashlib.md5(b'iso content').hexdigest()
        
        # Check temporary directory cleanup
        assert result['temp_files_cleaned'] == True
        mock_filesystem['rmtree'].assert_called_with('/tmp/test-temp-dir')
        
        # Check artifacts
        assert len(component.artifacts) >= 1
        assert component.artifacts[0]['type'] == 'metadata'

    def test_with_output_dir_preservation(self, openshift_test_config, mock_filesystem, mock_logger):
        """Test output directory preservation with the mock_filesystem fixture."""
        # Create config with output_dir specified
        config = openshift_test_config.copy()
        config['output_dir'] = '/custom/output/dir'
        
        # Create a mock S3Component
        mock_s3_component = MagicMock()
        
        # Create the component with the modified config
        component = OpenShiftComponent(config, s3_component=mock_s3_component, logger=mock_logger)
        
        # Set up component state
        component.discovery_results = {
            'installer_available': True,
            'pull_secret_available': True,
            'ssh_key_available': True,
            'temp_dir': '/custom/output/dir'
        }
        component.temp_dir = '/custom/output/dir'
        component.iso_path = '/custom/output/dir/agent.x86_64.iso'
        component.processing_results = {
            'iso_generated': True,
            'iso_path': '/custom/output/dir/agent.x86_64.iso'
        }
        component.phases_executed['discover'] = True
        component.phases_executed['process'] = True
        
        # Mock file existence only - the open mock is already set up in the fixture
        mock_filesystem['exists'].return_value = True
        mock_filesystem['isfile'].return_value = True
        
        # Run housekeeping
        result = component.housekeep()
        
        # Check that rmtree was not called (since we're preserving the output directory)
        mock_filesystem['rmtree'].assert_not_called()
        
        # Check ISO verification still happened
        assert result['iso_verified'] == True
