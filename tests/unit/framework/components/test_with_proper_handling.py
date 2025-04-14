#!/usr/bin/env python3
"""
Example test with proper error handling approach for BaseComponent.

This demonstrates the correct way to test error handling with the BaseComponent
discovery-processing-housekeeping pattern.
"""

import unittest
import logging
import sys
import os
import datetime
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from framework.base_component import BaseComponent

class TestErrorHandling(unittest.TestCase):
    """Test cases for BaseComponent error handling."""

    def setUp(self):
        """Set up test fixtures."""
        # Configure logging to prevent output during tests
        logging.basicConfig(level=logging.CRITICAL)
        
        # Basic configuration for testing
        self.config = {
            'component_id': 'test-component-001',
            'test_param': 'test_value'
        }

    def test_error_handling_with_assertraises(self):
        """Test error handling using assertRaises - shows the normal exception flow."""
        # Create a component that raises an exception during discovery
        class ErrorComponent(BaseComponent):
            def discover(self):
                raise ValueError("Test error")
        
        error_component = ErrorComponent(self.config)
        
        # Method 1: Check if discover method raises exception directly
        with self.assertRaises(ValueError) as cm:
            error_component.discover()
        
        # Check the exception message
        self.assertEqual(str(cm.exception), "Test error")

    def test_error_handling_in_execute(self):
        """Test error handling during execute - captures errors in results."""
        # Create a component that raises an exception during discovery
        class ErrorComponent(BaseComponent):
            def discover(self):
                raise ValueError("Test error")
        
        error_component = ErrorComponent(self.config)
        
        # Execute should catch the exception and include it in the result
        result = error_component.execute()
        
        # Check the status
        self.assertFalse(error_component.status['success'])
        
        # Check error is included in the result dictionary
        self.assertIn('error', result)
        self.assertEqual(result['error'], "Test error")
        self.assertIn('traceback', result)

    def test_modified_component_with_better_error_handling(self):
        """Test with a component that has better error handling."""
        # Create a component with improved error handling
        class BetterErrorComponent(BaseComponent):
            # Override execute instead of discover to prevent status['success'] being reset
            def execute(self, phases=["discover", "process", "housekeep"]):
                """Override execute to properly handle errors."""
                self.timestamps['start'] = datetime.datetime.now().isoformat()
                self.logger.info(f"Executing {self.component_name} with phases: {', '.join(phases)}")
                
                results = {}
                error_occurred = False
                
                # Execute requested phases
                if "discover" in phases:
                    try:
                        # Simulate an error in discovery
                        raise ValueError("Test error")
                    except Exception as e:
                        # Record error but don't re-raise
                        self.status['success'] = False
                        self.status['error'] = str(e)
                        self.status['message'] = f"Discovery phase failed: {str(e)}"
                        self.logger.error(f"Error during discovery phase: {str(e)}")
                        # Still mark as executed
                        self.phases_executed['discover'] = True
                        error_occurred = True
                    
                    # Add discovery results even though there was an error
                    results["discovery"] = self.discovery_results
                        
                # Continue with other phases even if discovery had an error
                if "process" in phases:
                    results["processing"] = self.process()
                    
                if "housekeep" in phases:
                    results["housekeeping"] = self.housekeep()
                    
                # Only mark as successful if no errors occurred
                if not error_occurred:
                    self.status['success'] = True
                    self.status['message'] = "Execution completed successfully"
                
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
        
        error_component = BetterErrorComponent(self.config)
        
        # Execute all phases
        result = error_component.execute()
        
        # Now we can check status directly
        self.assertFalse(error_component.status['success'])
        self.assertEqual(error_component.status['error'], "Test error")
        
        # Check the result still includes metadata
        self.assertIn('metadata', result)
        self.assertEqual(result['metadata']['status']['error'], "Test error")


if __name__ == '__main__':
    unittest.main()
