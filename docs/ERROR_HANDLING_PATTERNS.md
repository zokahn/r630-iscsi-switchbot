# Error Handling Patterns in the Discovery-Processing-Housekeeping Framework

This document describes best practices for error handling in the component-based architecture that follows the discovery-processing-housekeeping pattern.

## Standard Error Handling Flow

The BaseComponent class provides a standard error handling mechanism where exceptions raised in any phase are caught at the `execute()` level, with error information captured in both the results dictionary and component status.

### Key Points

1. When an exception occurs in any phase method (`discover()`, `process()`, or `housekeep()`):
   - The exception is logged
   - The error message and status are recorded in the component's `status` dictionary
   - The exception is re-raised to be caught by the `execute()` method

2. The `execute()` method:
   - Catches any exceptions from phases
   - Adds the error message and traceback to the results dictionary
   - Preserves the component's execution state in metadata
   - Always returns a results dictionary, even on failure

### Standard Pattern Example

```python
# Component implementation
class MyComponent(BaseComponent):
    def discover(self):
        try:
            # Discovery logic
            if problem_detected:
                raise ValueError("Problem in discovery")
            # ...
            return self.discovery_results
        except Exception as e:
            # BaseComponent already handles recording the error
            raise
```

```python
# Client code
component = MyComponent(config)
result = component.execute()

# Error handling in client code
if not result.get('metadata', {}).get('status', {}).get('success', False):
    error_msg = result.get('error', 'Unknown error')
    print(f"Execution failed: {error_msg}")
```

## Advanced Error Handling Pattern

For more complex components, it's sometimes desirable to:
1. Continue execution even if one phase fails
2. Implement more nuanced error recording
3. Customize error recovery strategies

### Improved Pattern Example

```python
class BetterErrorHandlingComponent(BaseComponent):
    # Override execute for custom error handling
    def execute(self, phases=["discover", "process", "housekeep"]):
        self.timestamps['start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Executing {self.component_name} with phases: {', '.join(phases)}")
        
        results = {}
        error_occurred = False
        
        # Execute each phase with phase-specific error handling
        if "discover" in phases:
            try:
                results["discovery"] = self.discover()
            except Exception as e:
                # Record error but don't re-raise
                self.status['success'] = False
                self.status['error'] = str(e)
                self.status['message'] = f"Discovery phase failed: {str(e)}"
                self.logger.error(f"Error during discovery phase: {str(e)}")
                # Still mark as executed
                self.phases_executed['discover'] = True
                error_occurred = True
                # Add empty discovery results
                results["discovery"] = self.discovery_results
                
        # Continue with other phases even if discovery had an error
        if "process" in phases:
            try:
                results["processing"] = self.process()
            except Exception as e:
                # Similar error handling for process
                # ...
                error_occurred = True
        
        # Add execution metadata and finalize
        results["metadata"] = {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "timestamps": self.timestamps,
            "phases_executed": self.phases_executed,
            "status": self.status
        }
        
        return results
```

## Testing Error Handling

Testing error handling requires special consideration. Here are recommended approaches:

### 1. Testing Direct Exceptions

Use `assertRaises` to verify that a phase method raises the expected exception:

```python
def test_error_handling_with_assertraises(self):
    component = MyComponent(config)
    
    with self.assertRaises(ValueError) as cm:
        component.discover()
    
    self.assertEqual(str(cm.exception), "Expected error message")
```

### 2. Testing Execute Error Handling

Test how `execute()` handles and reports errors:

```python
def test_error_handling_in_execute(self):
    component = MyComponent(config)
    result = component.execute()
    
    # Check status
    self.assertFalse(component.status['success'])
    
    # Check result contains error information
    self.assertIn('error', result)
    self.assertEqual(result['error'], "Expected error message")
    self.assertIn('traceback', result)
```

### 3. Testing Custom Error Recovery

For components with custom error handling, test specific recovery paths:

```python
def test_recovery_from_error(self):
    component = CustomComponent(config)
    result = component.execute()
    
    # Verify discovery failed but process succeeded
    self.assertFalse(component.status['success'])
    self.assertEqual(component.status['error'], "Expected error message")
    self.assertTrue(component.phases_executed['discover'])
    self.assertTrue(component.phases_executed['process'])
```

## Best Practices

1. **Be Consistent**: Use either the standard or custom error handling pattern consistently within a component

2. **Clear Error Messages**: Include specific error codes or identifiers in error messages to aid troubleshooting

3. **Error Categorization**: Distinguish between different types of errors (validation, resource, connectivity)

4. **Graceful Degradation**: When possible, allow components to continue partial operation when non-critical errors occur

5. **Error Context**: Include relevant context (component state, input values) in error logging

6. **Recovery Guidance**: Where appropriate, include recovery suggestions in error messages

7. **Avoid Error Suppression**: Don't catch and ignore exceptions without logging or status updates

8. **Test Error Cases**: Write explicit tests for error conditions, not just the happy path
