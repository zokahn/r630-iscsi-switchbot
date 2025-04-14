# r630-iscsi-switchbot Test Suite

This directory contains tests for the r630-iscsi-switchbot project, focusing on unit testing the component-based architecture that follows the discovery-processing-housekeeping pattern.

## Test Structure

The test suite is organized as follows:

```
tests/
├── __init__.py
├── conftest.py             # Shared test fixtures and configuration
├── README.md               # This file
├── test_values.yaml        # Test data values for functional tests
└── unit/                   # Unit tests
    ├── __init__.py
    ├── framework/          # Tests for the core framework
    │   ├── __init__.py
    │   ├── test_base_component.py  # Tests for BaseComponent
    │   └── components/     # Tests for specific components
    │       ├── __init__.py
    │       ├── test_s3_component.py
    │       └── ...         # Other component tests
```

## Running Tests

### Prerequisites

1. Install testing dependencies:

```bash
pip install pytest pytest-cov pytest-mock
```

2. Make sure your current working directory is the project root.

### Running All Tests

```bash
pytest
```

### Running Tests with Coverage

```bash
pytest --cov=framework
```

### Running Specific Test Files

```bash
# Run base component tests
pytest tests/unit/framework/test_base_component.py

# Run S3 component tests
pytest tests/unit/framework/components/test_s3_component.py
```

### Running Tests by Name Pattern

```bash
# Run all discover phase tests
pytest -k "discover"

# Run all tests for S3Component
pytest -k "S3Component"
```

## Creating New Tests

### Component Test Template

When adding tests for a new component, follow this pattern:

1. Create a new test file in `tests/unit/framework/components/` named `test_<component_name>.py`
2. Follow the structure of existing component tests, with proper mocking of dependencies
3. Add a test configuration fixture in `conftest.py`

### Test Organization

Each component test should include tests for:
1. Component initialization
2. The discover phase
3. The process phase
4. The housekeep phase
5. Component-specific methods
6. Error handling

### Example Test Structure

```python
class TestNewComponent(unittest.TestCase):
    def setUp(self):
        # Setup test fixture
        
    def tearDown(self):
        # Clean up after tests
        
    def test_initialization(self):
        # Test component initialization
        
    def test_discover_phase(self):
        # Test the discover phase
        
    def test_process_phase(self):
        # Test the process phase
        
    def test_housekeep_phase(self):
        # Test the housekeep phase
        
    def test_component_specific_methods(self):
        # Test methods specific to this component
        
    def test_error_handling(self):
        # Test error handling
```

## Mocking External Dependencies

Most components have external dependencies that should be mocked for unit tests:

- **S3Component**: Mock boto3 clients and responses
- **ISCSIComponent**: Mock TrueNAS API requests and responses
- **OpenShiftComponent**: Mock file operations and subprocess calls
- **R630Component**: Mock iDRAC API calls via Redfish
- **VaultComponent**: Mock Vault API requests and responses

Use the `unittest.mock` library for mocking:

```python
from unittest.mock import patch, MagicMock

# Example: mocking boto3 for S3Component tests
with patch('boto3.client') as mock_boto3_client:
    # Configure the mock
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    
    # Set up expected responses
    mock_client.list_buckets.return_value = {
        'Buckets': [{'Name': 'test-bucket'}]
    }
    
    # Test your component
    # ...
```

## Test Data

- `conftest.py` provides fixtures with standard test configurations
- Use these fixtures in your tests to maintain consistency
- Add new fixtures for any new components or shared test data

## Continuous Integration

The test suite is designed to run in CI environments with GitHub Actions. The CI workflow:

1. Installs dependencies
2. Runs all tests
3. Generates coverage reports
4. Fails if coverage falls below a set threshold

Make sure your new tests maintain or improve coverage metrics.
