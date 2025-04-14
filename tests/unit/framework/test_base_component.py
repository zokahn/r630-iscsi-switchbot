#!/usr/bin/env python3
"""
Unit tests for the BaseComponent class.

These tests validate the core functionality of the discovery-processing-housekeeping
pattern implementation in the BaseComponent class.
"""

import unittest
import logging
import json
from unittest.mock import patch, MagicMock
import sys
import os
import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from framework.base_component import BaseComponent

class TestBaseComponent(unittest.TestCase):
    """Test cases for the BaseComponent class."""

    def setUp(self):
        """Set up test fixtures."""
        # Configure logging to prevent output during tests
        logging.basicConfig(level=logging.CRITICAL)
        
        # Basic configuration for testing
        self.config = {
            'component_id': 'test-component-001',
            'test_param': 'test_value'
        }
        
        # Create a test component
        self.component = BaseComponent(self.config)

    def test_initialization(self):
        """Test component initialization."""
        # Test basic properties
        self.assertEqual(self.component.component_id, 'test-component-001')
        self.assertEqual(self.component.component_name, 'BaseComponent')
        self.assertEqual(self.component.config, self.config)
        
        # Test initialization of result dictionaries
        self.assertEqual(self.component.discovery_results, {})
        self.assertEqual(self.component.processing_results, {})
        self.assertEqual(self.component.housekeeping_results, {})
        
        # Test phase execution tracking
        self.assertEqual(self.component.phases_executed, {
            'discover': False,
            'process': False,
            'housekeep': False
        })
        
        # Test artifact list initialization
        self.assertEqual(self.component.artifacts, [])

    def test_discover_phase(self):
        """Test the discover phase execution."""
        # The base implementation should just return an empty dict and log a warning
        with self.assertLogs(level='WARNING') as cm:
            result = self.component.discover()
            
        # Check warning was logged
        self.assertIn('Default discovery implementation called', cm.output[0])
        
        # Check phase was marked as executed
        self.assertTrue(self.component.phases_executed['discover'])
        
        # Check timestamps were set
        self.assertIsNotNone(self.component.timestamps['discover_start'])
        self.assertIsNotNone(self.component.timestamps['discover_end'])
        
        # Check result is the discovery_results
        self.assertEqual(result, self.component.discovery_results)

    def test_process_phase(self):
        """Test the process phase execution."""
        # The base implementation should just return an empty dict and log a warning
        with self.assertLogs(level='WARNING') as cm:
            result = self.component.process()
            
        # Check warnings were logged (both about default implementation and no prior discovery)
        warning_messages = '\n'.join(cm.output)
        self.assertIn('Default processing implementation called', warning_messages)
        self.assertIn('Processing without prior discovery', warning_messages)
        
        # Check phase was marked as executed
        self.assertTrue(self.component.phases_executed['process'])
        
        # Check timestamps were set
        self.assertIsNotNone(self.component.timestamps['process_start'])
        self.assertIsNotNone(self.component.timestamps['process_end'])
        
        # Check result is the processing_results
        self.assertEqual(result, self.component.processing_results)

    def test_housekeep_phase(self):
        """Test the housekeep phase execution."""
        # The base implementation should just return an empty dict and log a warning
        with self.assertLogs(level='WARNING') as cm:
            result = self.component.housekeep()
            
        # Check warnings were logged (both about default implementation and no prior processing)
        warning_messages = '\n'.join(cm.output)
        self.assertIn('Default housekeeping implementation called', warning_messages)
        self.assertIn('Housekeeping without prior processing', warning_messages)
        
        # Check phase was marked as executed
        self.assertTrue(self.component.phases_executed['housekeep'])
        
        # Check timestamps were set
        self.assertIsNotNone(self.component.timestamps['housekeep_start'])
        self.assertIsNotNone(self.component.timestamps['housekeep_end'])
        
        # Check result is the housekeeping_results
        self.assertEqual(result, self.component.housekeeping_results)

    def test_execute_all_phases(self):
        """Test execution of all phases."""
        result = self.component.execute()
        
        # Check all phases were executed
        self.assertTrue(self.component.phases_executed['discover'])
        self.assertTrue(self.component.phases_executed['process'])
        self.assertTrue(self.component.phases_executed['housekeep'])
        
        # Check overall execution timestamps
        self.assertIsNotNone(self.component.timestamps['start'])
        self.assertIsNotNone(self.component.timestamps['end'])
        
        # Check status
        self.assertTrue(self.component.status['success'])
        self.assertIsNone(self.component.status['error'])
        
        # Check result structure
        self.assertIn('discovery', result)
        self.assertIn('processing', result)
        self.assertIn('housekeeping', result)
        self.assertIn('metadata', result)

    def test_execute_specific_phases(self):
        """Test execution of specific phases."""
        # Only execute discover
        result = self.component.execute(phases=['discover'])
        
        # Check only discover was executed
        self.assertTrue(self.component.phases_executed['discover'])
        self.assertFalse(self.component.phases_executed['process'])
        self.assertFalse(self.component.phases_executed['housekeep'])
        
        # Check result structure
        self.assertIn('discovery', result)
        self.assertNotIn('processing', result)
        self.assertNotIn('housekeeping', result)
        self.assertIn('metadata', result)

    def test_execution_error_handling(self):
        """Test error handling during execution."""
        # Create a component that raises an exception during discovery
        class ErrorComponent(BaseComponent):
            def discover(self):
                # Simulate an error in discover phase
                raise ValueError("Test error")
        
        error_component = ErrorComponent(self.config)
        
        # Execute should catch the exception and include it in the result
        result = error_component.execute()
        
        # Check status
        self.assertFalse(error_component.status['success'])
        
        # When a phase raises an exception, the error details are added to the result dictionary
        # but not necessarily updated in the status (due to re-raising)
        self.assertIn('error', result)
        self.assertEqual(result['error'], "Test error")
        self.assertIn('traceback', result)

    def test_add_artifact(self):
        """Test adding artifacts."""
        # Add a test artifact
        artifact_id = self.component.add_artifact(
            artifact_type='test',
            content='Test content',
            metadata={'test_key': 'test_value'}
        )
        
        # Check artifact was added
        self.assertEqual(len(self.component.artifacts), 1)
        
        # Check artifact structure
        artifact = self.component.artifacts[0]
        self.assertEqual(artifact['id'], artifact_id)
        self.assertEqual(artifact['type'], 'test')
        self.assertEqual(artifact['content'], 'Test content')
        self.assertEqual(artifact['metadata']['test_key'], 'test_value')
        self.assertEqual(artifact['metadata']['component_id'], 'test-component-001')
        self.assertEqual(artifact['metadata']['component_name'], 'BaseComponent')
        self.assertIn('timestamp', artifact['metadata'])

    def test_to_json(self):
        """Test JSON serialization."""
        # Add an artifact for testing
        self.component.add_artifact('test', 'content', {'key': 'value'})
        
        # Get JSON
        json_str = self.component.to_json()
        
        # Parse JSON to check structure
        data = json.loads(json_str)
        
        # Check basic structure
        self.assertEqual(data['component_id'], 'test-component-001')
        self.assertEqual(data['component_name'], 'BaseComponent')
        self.assertIn('timestamps', data)
        self.assertIn('phases_executed', data)
        self.assertIn('status', data)
        self.assertIn('discovery_results', data)
        self.assertIn('processing_results', data)
        self.assertIn('housekeeping_results', data)
        self.assertIn('artifacts', data)
        
        # Check artifact representation
        self.assertEqual(len(data['artifacts']), 1)
        self.assertEqual(data['artifacts'][0]['type'], 'test')
        self.assertEqual(data['artifacts'][0]['metadata']['key'], 'value')

    def test_get_execution_summary(self):
        """Test execution summary generation."""
        # Run a discovery to have something in the summary
        self.component.discover()
        
        # Get summary
        summary = self.component.get_execution_summary()
        
        # Check summary structure
        self.assertEqual(summary['component_id'], 'test-component-001')
        self.assertEqual(summary['component_name'], 'BaseComponent')
        self.assertIn('status', summary)
        self.assertIn('timestamps', summary)
        self.assertIn('phases_executed', summary)
        self.assertEqual(summary['artifacts_count'], 0)
        self.assertEqual(summary['discovery_results_count'], 0)
        self.assertEqual(summary['processing_results_count'], 0)
        self.assertEqual(summary['housekeeping_results_count'], 0)


if __name__ == '__main__':
    unittest.main()
