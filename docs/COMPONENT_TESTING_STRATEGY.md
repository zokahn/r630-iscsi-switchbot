# Component Testing Strategy

This document outlines the recommended testing approach for the component-based architecture using the discovery-processing-housekeeping pattern.

## Testing Philosophy

The discovery-processing-housekeeping pattern requires a unique testing approach that validates both individual phases and the flow between them. Our testing strategy follows these key principles:

1. **Phase Independence**: Each phase should be testable in isolation
2. **Dependency Mocking**: External dependencies should be properly mocked
3. **Error Path Coverage**: Test both successful and failure scenarios
4. **Integration Validation**: Test interactions between components
5. **Lifecycle Completeness**: Ensure full lifecycle testing with proper setup and teardown

## Testing Levels

### 1. Unit Tests

Unit tests validate individual components and their phases in isolation:

#### Base Component Tests

Test the core framework functionality:
- Phase execution sequencing
- Error handling and propagation
- Artifact management
- Result collection and formatting

```python
def test_base_component_lifecycle(self):
    component = BaseComponent(config)
    result = component.execute()
    
    self.assertTrue(component.phases_executed['discover'])
    self.assertTrue(component.phases_executed['process'])
    self.assertTrue(component.phases_executed['housekeep'])
```

#### Component-Specific Tests

For each specialized component (S3Component, OpenShiftComponent, etc.):

1. **Discovery Phase Tests**
   - Mock external service responses
   - Test proper detection of resources
   - Validate error handling during discovery
   
   ```python
   def test_s3_component_discovery(self):
       # Mock S3 responses
       self.mock_s3_client.list_buckets.return_value = {...}
       
       # Test discovery
       component = S3Component(config)
       results = component.discover()
       
       # Verify results
       self.assertEqual(results['bucket_count'], 2)
   ```

2. **Processing Phase Tests**
   - Test logic when discovery results are present
   - Validate resource creation/modification
   - Test error conditions during processing
   
3. **Housekeeping Phase Tests**
   - Verify cleanup operations
   - Test proper artifact storage
   - Validate state verification

### 2. Integration Tests

Integration tests validate interactions between components:

```python
def test_openshift_s3_integration(self):
    # Create components with real or mock dependencies
    s3_component = S3Component(s3_config)
    openshift_component = OpenShiftComponent(openshift_config, s3_component=s3_component)
    
    # Execute OpenShift component
    result = openshift_component.execute()
    
    # Verify S3 interactions occurred correctly
    self.assertTrue('s3_iso_path' in result['processing'])
```

### 3. Functional Tests

Functional tests validate end-to-end workflows:

```python
def test_full_deployment_workflow(self):
    # Create orchestration
    orchestrator = DeploymentOrchestrator(config)
    
    # Execute workflow
    result = orchestrator.deploy()
    
    # Verify outcomes
    self.assertTrue(result['success'])
    self.assertIsNotNone(result['deployment_id'])
```

## Mocking Strategies

### External Service Mocking

For components interacting with external services:

1. **API Response Mocking**

```python
# Mock boto3 for S3Component
@patch('boto3.client')
def test_s3_operations(self, mock_boto3_client):
    # Configure mock
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    mock_client.list_buckets.return_value = {
        'Buckets': [{'Name': 'test-bucket'}]
    }
    
    # Create component and test
    component = S3Component(config)
    results = component.discover()
    
    # Verify correct methods were called
    mock_client.list_buckets.assert_called_once()
```

2. **File System Mocking**

```python
# Mock filesystem for OpenShiftComponent
@patch('os.path.exists')
@patch('os.makedirs')
def test_iso_creation(self, mock_makedirs, mock_path_exists):
    # Configure mocks
    mock_path_exists.return_value = True
    
    # Create component and test
    component = OpenShiftComponent(config)
    results = component.process()
    
    # Verify file operations
    mock_makedirs.assert_called_with('/tmp/test-dir', exist_ok=True)
```

3. **Subprocess Mocking**

```python
# Mock subprocess for command execution
@patch('subprocess.run')
def test_command_execution(self, mock_run):
    # Configure mock
    mock_run.return_value = MagicMock(returncode=0, stdout="Success")
    
    # Create component and test
    component = OpenShiftComponent(config)
    results = component.process()
    
    # Verify command execution
    mock_run.assert_called_with(['openshift-install', '--version'], capture_output=True, text=True)
```

## Testing Error Handling

Properly testing error conditions is critical:

```python
def test_discovery_error_handling(self):
    # Configure mock to simulate an error
    self.mock_api.side_effect = ConnectionError("API unavailable")
    
    # Test component with error condition
    component = ISCSIComponent(config)
    
    # Option 1: Test direct error
    with self.assertRaises(ConnectionError):
        component.discover()
    
    # Option 2: Test error handling in execute
    result = component.execute()
    self.assertFalse(result['metadata']['status']['success'])
    self.assertIn("API unavailable", result['error'])
```

## Test Fixtures and Utilities

Create shared fixtures and utilities for common testing needs:

```python
# In conftest.py
@pytest.fixture
def s3_test_config():
    """Provide standard test configuration for S3Component."""
    return {
        'endpoint': 'test-endpoint.com',
        'access_key': 'test-access-key',
        'secret_key': 'test-secret-key',
        'private_bucket': 'test-private',
        'public_bucket': 'test-public',
        'component_id': 's3-test-component'
    }
```

## Continuous Integration

Configure CI for automated testing:

```yaml
# In GitHub Actions workflow
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-cov
          pip install -r requirements.txt
      - name: Run tests with coverage
        run: |
          pytest --cov=framework --cov-report=xml
      - name: Upload coverage report
        uses: codecov/codecov-action@v2
```

## Testing Implementation Checklist

When writing tests for a new component:

1. **Setup**
   - Create fixtures for common test data
   - Configure mocks for external dependencies
   - Prepare test environments (temp directories, etc.)

2. **Discovery Tests**
   - Test resource detection capability
   - Test connection verification
   - Test error conditions (service unavailable, invalid credentials)

3. **Processing Tests**
   - Test resource creation
   - Test modification operations
   - Test configuration generation
   - Test validation logic

4. **Housekeeping Tests**
   - Test cleanup operations
   - Test artifact creation and storage
   - Test metadata recording

5. **Integration Tests**
   - Test component interactions
   - Test data flow between components
   - Test orchestration workflows

6. **Error Handling Tests**
   - Test each potential error condition
   - Verify error recording
   - Test recovery procedures

## Example Test Structure

For a typical component, organize tests as follows:

```python
class TestISCSIComponent(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_truenas_api = patch('requests.post').start()
        
        # Set up test config
        self.config = {...}
        
        # Create component under test
        self.component = ISCSIComponent(self.config)
    
    def tearDown(self):
        # Clean up mocks
        patch.stopall()
    
    # Discovery tests
    def test_discovery_detects_existing_targets(self):
        # ...
    
    def test_discovery_handles_connection_error(self):
        # ...
    
    # Processing tests
    def test_process_creates_new_zvol(self):
        # ...
    
    def test_process_skips_existing_zvol(self):
        # ...
    
    # Housekeeping tests
    def test_housekeep_verifies_target_accessibility(self):
        # ...
    
    # Error handling tests
    def test_error_propagation_and_recording(self):
        # ...
```

## Performance Considerations

For testing performance-critical components:

1. **Use benchmark fixtures** to measure execution time
2. **Profile resource usage** for memory-intensive operations
3. **Test with realistic data volumes** to ensure scalability

## Security Testing

For components handling sensitive information:

1. **Validate secure credential handling**
2. **Test access controls** for S3/storage operations
3. **Verify secure cleanup** of sensitive data
