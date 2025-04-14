# Testing Improvements Guide

This document outlines the testing improvements made to the project, including mocking strategies, coverage reporting, and best practices.

## Table of Contents
1. [File System Mocking](#file-system-mocking)
2. [S3 Service Mocking](#s3-service-mocking)
3. [Coverage Reporting](#coverage-reporting)
4. [Moto Integration](#moto-integration)

## File System Mocking

The `mock_filesystem` fixture provides comprehensive mocking for file system operations. This is particularly useful for components that interact with the file system, such as OpenShiftComponent.

### Usage Example

```python
def test_generate_iso(mock_filesystem):
    # Configure the mock
    iso_path = create_mock_iso('/tmp/test-dir')
    mock_filesystem['exists'].return_value = True
    
    # Run the component method
    self.component.generate_iso()
    
    # Verify the expected file operations occurred
    mock_filesystem['chmod'].assert_called_with('/tmp/test-dir/openshift-install', 0o755)
```

### Available Mocks

The fixture provides these mock objects:
- `exists` - Mocks `os.path.exists`
- `isfile` - Mocks `os.path.isfile`
- `open` - Mocks `builtins.open`
- `makedirs` - Mocks `os.makedirs`
- `getsize` - Mocks `os.path.getsize`
- `copy2` - Mocks `shutil.copy2`
- `move` - Mocks `shutil.move`
- `rmtree` - Mocks `shutil.rmtree`
- `chmod` - Mocks `os.chmod`

### Helper Functions

- `create_mock_iso(temp_dir, filename)` - Creates a mock ISO path for testing

## S3 Service Mocking

The `mock_s3` fixture provides comprehensive mocking for AWS S3 operations. This is particularly useful for S3Component tests.

### Usage Example

```python
def test_sync_to_public(mock_s3):
    # Configure S3 mock
    mock_s3['private_bucket'].objects.filter.return_value = [
        MagicMock(key='isos/server-01-test-4.16.0.iso')
    ]
    
    # Run component method
    result = self.component.sync_to_public('isos/server-01-test-4.16.0.iso', '4.16.0')
    
    # Verify S3 operations
    mock_s3['client'].copy_object.assert_called_once()
```

### Available Mocks

The fixture provides these mock objects:
- `client` - Mock S3 client with pre-configured methods
- `resource` - Mock S3 resource with pre-configured methods
- `private_bucket` - Mock for the private bucket
- `public_bucket` - Mock for the public bucket
- `objects` - List of mock S3 objects

## Coverage Reporting

The project now includes comprehensive coverage reporting capabilities.

### Running Coverage Reports

```bash
# Basic coverage
./run_tests.sh -c

# HTML coverage report
./run_tests.sh -c -H
```

### .coveragerc Configuration

The `.coveragerc` file configures coverage to:
- Only measure coverage in the `framework` directory
- Exclude tests and other non-application code
- Exclude common non-testable code patterns
- Generate HTML reports in `coverage_html_report/`

## Moto Integration

For more realistic S3 testing, the project integrates with [Moto](https://github.com/spulec/moto), which mocks AWS services.

### Usage Example

```python
import boto3
from moto import mock_s3

@mock_s3
def test_with_moto():
    # Set up S3 buckets using the mocked AWS API
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='r630-switchbot-private')
    
    # Create component using the real boto3 (which is now mocked by moto)
    component = S3Component(self.config)
    
    # Test operations against the mocked S3
    result = component.discover()
    self.assertTrue(result['buckets']['private']['exists'])
```

### Benefits of Moto

- Simulates the entire AWS API, not just individual method calls
- Tests can use the actual boto3 API, making them more realistic
- Helps identify issues with boto3 usage that simple mocks might miss
