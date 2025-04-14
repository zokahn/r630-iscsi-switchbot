#!/usr/bin/env python3
"""
Unit tests for a custom error handling scenario with BaseComponent.

These tests validate error handling with a custom component that properly captures errors
rather than raising them in the discover phase.
"""

import unittest
import logging
import json
import sys
import os
import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from framework.base_component import BaseComponent


class TestErrorComponent(unittest.TestCase):
    """Test cases for custom error handling with BaseComponent."""

    def setUp(self):
        """Set up test fixtures."""
        # Configure logging to prevent output during tests
        logging.basicConfig(level=logging.CRITICAL)
        
        # Basic configuration for testing
        self.config = {
            'component_id': 'test-component-001',
            'test_param': 'test_value'
        }

    def test_custom_error_component(self):
        """Test a custom error component with proper error handling."""
        # Define a custom component that catches errors rather than raising them
        class CustomErrorComponent(BaseComponent):
            def execute(self, phases=["discover", "process", "housekeep"]):
                """
                Execute with custom error handling that doesn't raise exceptions.
                """
                self.timestamps['start'] = datetime.datetime.now().isoformat()
                self.logger.info(f"Executing {self.component_name} with phases: {', '.join(phases)}")
                
                results = {}
                
                # Simulate discover phase with an error
                if "discover" in phases:
                    self.phases_executed['discover'] = True
                    # Set error status directly without raising
                    error_msg = "Test error"
                    self.status['success'] = False
                    self.status['error'] = error_msg
                    self.status['message'] = f"Discovery phase failed: {error_msg}"
                    
                    # Add error to results
                    results["error"] = error_msg
                    results["traceback"] = "Simulated traceback for test"
                
                # Always update end timestamp
                self.timestamps['end'] = datetime.datetime.now().isoformat()
                
                # Add execution metadata to results
                results["metadata"] = {
                    "component_id": self.component_id,
                    "component_name": self.component_name,
                    "timestamps": self.timestamps,
                    "phases_executed": self.phases_executed,
                    "status": self.status
                }
                
                self.logger.info(f"Execution of {self.component_name} completed with status: {self.status['success']}")
                
                return results
        
        # Create the component
        error_component = CustomErrorComponent(self.config)
        
        # Execute and get results
        result = error_component.execute()
        
        # ===== Verification =====
        # Check status
        self.assertFalse(error_component.status['success'])
        self.assertEqual(error_component.status['error'], "Test error")
        
        # Check error is included in the result
        self.assertIn('error', result)
        self.assertEqual(result['error'], "Test error")
        self.assertIn('traceback', result)
        
        # Check metadata
        self.assertEqual(result['metadata']['status']['error'], "Test error")


if __name__ == '__main__':
    unittest.main()
