# Component Architecture Guide

This comprehensive guide explains the component-based architecture implemented in the r630-iscsi-switchbot project. It covers the core patterns, components, and best practices for using and extending the system.

## Table of Contents

1. [Introduction](#introduction)
2. [Discovery-Processing-Housekeeping Pattern](#discovery-processing-housekeeping-pattern)
3. [Component Architecture Overview](#component-architecture-overview)
4. [Component Layers](#component-layers)
5. [Core Components](#core-components)
   - [BaseComponent](#basecomponent)
   - [S3Component](#s3component)
   - [OpenShiftComponent](#openshiftcomponent)
   - [ISCSIComponent](#iscsicomponent)
   - [R630Component](#r630component)
   - [VaultComponent](#vaultcomponent)
6. [Using Components in Scripts](#using-components-in-scripts)
7. [Creating New Components](#creating-new-components)
8. [Testing Components](#testing-components)
9. [Orchestration Patterns](#orchestration-patterns)
10. [Best Practices](#best-practices)

## Introduction

The component-based architecture represents a major evolution in the project's design, moving from traditional procedural scripts to a more modular, maintainable, and testable approach. This architecture provides:

- **Consistent patterns** for all operations
- **Better error handling and reporting**
- **Standardized interfaces** between components
- **Improved testability** with clear component boundaries
- **Self-documenting code** through standardized methods
- **Artifact management** with proper metadata

By understanding this architecture, you'll be able to effectively use the existing components, create new ones, and design workflows that integrate multiple components together.

## Discovery-Processing-Housekeeping Pattern

Every component in the system follows the discovery-processing-housekeeping (DPH) pattern, a three-phase approach that ensures operations are performed safely and consistently:

### 1. Discovery Phase

The discovery phase is responsible for examining the current environment without making changes. It's designed to:

- Verify connectivity to required services (e.g., S3, TrueNAS, iDRAC)
- Check for existing resources (e.g., buckets, iSCSI targets, boot devices)
- Identify available and required components
- Detect current configurations
- Validate prerequisites
- Gather relevant system information

The key principle is that discovery should never change state - it only observes and reports.

### 2. Processing Phase

The processing phase performs the actual work requested by the user, based on the information gathered during discovery:

- Create or update resources
- Configure systems
- Generate files or artifacts
- Deploy configurations
- Make necessary changes to the environment

Processing is where state changes occur, and should only proceed if discovery has validated that the necessary preconditions are met.

### 3. Housekeeping Phase

The housekeeping phase verifies, cleans up, and finalizes the component's work:

- Validate changes were successful
- Clean up temporary resources
- Update configuration repositories
- Perform final verifications
- Archive artifacts with metadata
- Prepare for next execution

Housekeeping ensures that the system remains in a clean, well-documented state after operations.

## Component Architecture Overview

The architecture is divided into three main layers:

```
┌─────────────────────────────────────────────────────────────┐
│                     Orchestration Layer                     │
│                                                             │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│ │ Full        │  │ OpenShift   │  │ iSCSI Boot  │  ...      │
│ │ Deployment  │  │ Only        │  │ Only        │           │
│ └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                     Component Layer                         │
│                                                             │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────┐  │
│ │ OpenShift   │  │ iSCSI       │  │ Dell R630   │  │ S3  │  │
│ │ Component   │  │ Component   │  │ Component   │  │ ... │  │
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                     Core Framework Layer                    │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│ │ Discovery   │  │ Processing  │  │ Housekeeping│  ...      │
│ │ Framework   │  │ Framework   │  │ Framework   │           │
│ └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

Each layer builds upon the lower layers, with the Core Framework providing the foundational patterns, the Component Layer implementing specific functionality, and the Orchestration Layer coordinating multiple components to achieve complex workflows.

## Component Layers

### Core Framework Layer

The core framework layer provides:

- The BaseComponent class with the DPH pattern implementation
- Configuration management
- Logging utilities
- Error handling patterns
- Artifact management
- Result formatting

These core capabilities are inherited by all components.

### Component Layer

The component layer contains specialized components for different aspects of the system:

- **S3Component**: Manages S3 storage, buckets, and artifacts
- **OpenShiftComponent**: Handles OpenShift ISO generation and configuration
- **ISCSIComponent**: Manages iSCSI target creation and configuration
- **R630Component**: Controls Dell R630 hardware configuration
- **VaultComponent**: Handles secrets management through HashiCorp Vault

Each component focuses on a specific domain and provides a clean interface for operations in that domain.

### Orchestration Layer

The orchestration layer contains scripts and workflows that coordinate multiple components to achieve complex tasks:

- **workflow_iso_generation_s3.py**: Combines OpenShiftComponent and S3Component
- **reboot_server_component.py**: Uses R630Component for server management
- **set_boot_order_component.py**: Uses R630Component for boot configuration

Orchestration scripts tie components together while providing user-friendly interfaces.

## Core Components

### BaseComponent

The BaseComponent is the foundation of the architecture. All other components inherit from it.

**Key Features**:
- Implementation of the discovery-processing-housekeeping pattern
- Configuration management
- Logging setup
- Artifact collection and metadata handling
- Status tracking
- Phase execution management

**Usage Example**:
```python
class MyComponent(BaseComponent):
    def __init__(self, config, logger=None):
        super().__init__(config, logger)
        
    def discover(self):
        # Implement discovery logic
        return self.discovery_results
        
    def process(self):
        # Implement processing logic
        return self.processing_results
        
    def housekeep(self):
        # Implement housekeeping logic
        return self.housekeeping_results
```

### S3Component

The S3Component manages S3/MinIO storage operations.

**Key Features**:
- S3 connectivity checks
- Bucket creation and management
- Dual-bucket strategy (private/public)
- Object upload, download, and listing
- Artifact indexing and metadata management

**Usage Example**:
```python
s3_config = {
    'endpoint': 'scratchy.omnisack.nl',
    'access_key': 'YOUR_ACCESS_KEY',
    'secret_key': 'YOUR_SECRET_KEY',
    'private_bucket': 'r630-switchbot-private',
    'public_bucket': 'r630-switchbot-public'
}

s3_component = S3Component(s3_config)

# Discover S3 resources
discovery_results = s3_component.discover()

# Process (create buckets, prepare structure)
processing_results = s3_component.process()

# Upload an artifact
s3_component.add_artifact(
    name='my-artifact',
    content='/path/to/file.txt',
    metadata={'type': 'document', 'version': '1.0'}
)

# Housekeeping (upload artifacts, verify)
housekeeping_results = s3_component.housekeep()
```

### OpenShiftComponent

The OpenShiftComponent manages OpenShift ISO generation and configuration.

**Key Features**:
- OpenShift version detection
- ISO generation with agent-based installer
- Pull secret and SSH key management
- Integration with S3 for ISO storage
- Verification of generated ISOs

**Usage Example**:
```python
openshift_config = {
    'openshift_version': '4.14',
    'domain': 'example.com',
    'rendezvous_ip': '192.168.2.230',
    'pull_secret_path': '~/.openshift/pull-secret',
    'output_dir': './isos'
}

openshift_component = OpenShiftComponent(openshift_config)

# Discover OpenShift resources
discovery_results = openshift_component.discover()

# Generate ISO
processing_results = openshift_component.process()

# Verify and cleanup
housekeeping_results = openshift_component.housekeep()
```

### ISCSIComponent

The ISCSIComponent manages iSCSI target creation and configuration on TrueNAS.

**Key Features**:
- TrueNAS API connectivity
- ZFS pool and dataset management
- iSCSI target and LUN creation
- Target group management
- Verification of target accessibility

**Usage Example**:
```python
iscsi_config = {
    'truenas_ip': '192.168.2.245',
    'api_key': 'YOUR_API_KEY',
    'server_id': 'r630-01',
    'hostname': 'my-server',
    'zfs_pool': 'tank'
}

iscsi_component = ISCSIComponent(iscsi_config)

# Discover TrueNAS and iSCSI resources
discovery_results = iscsi_component.discover()

# Create iSCSI targets
processing_results = iscsi_component.process()

# Verify target accessibility
housekeeping_results = iscsi_component.housekeep()
```

### R630Component

The R630Component manages Dell R630 server hardware configuration.

**Key Features**:
- iDRAC connectivity and authentication
- BIOS settings management
- Boot order configuration
- Server reboot control
- Hardware information collection

**Usage Example**:
```python
r630_config = {
    'idrac_ip': '192.168.2.230',
    'idrac_username': 'root',
    'idrac_password': 'calvin',
    'server_id': 'r630-01',
    'boot_devices': ['Boot0004', 'Boot0002']  # iSCSI first, then PXE
}

r630_component = R630Component(r630_config)

# Discover server hardware
discovery_results = r630_component.discover()

# Configure boot order
processing_results = r630_component.process()

# Verify changes
housekeeping_results = r630_component.housekeep()
```

### VaultComponent

The VaultComponent manages secrets through HashiCorp Vault.

**Key Features**:
- Vault connectivity and authentication
- Secret storage and retrieval
- Token renewal
- Secret versioning
- Integration with environment variables as fallback

**Usage Example**:
```python
vault_config = {
    'vault_addr': 'http://vault.example.com:8200',
    'vault_token': 'YOUR_VAULT_TOKEN',
    'secret_paths': ['s3/credentials', 'truenas/api_key']
}

vault_component = VaultComponent(vault_config)

# Discover Vault connectivity and secrets
discovery_results = vault_component.discover()

# Store or update secrets
processing_results = vault_component.process()

# Renew tokens, verify
housekeeping_results = vault_component.housekeep()
```

## Using Components in Scripts

Components can be integrated into scripts following this general pattern:

1. **Import the component**:
   ```python
   from framework.components.s3_component import S3Component
   ```

2. **Configure the component**:
   ```python
   s3_config = {
       'endpoint': args.s3_endpoint,
       'access_key': args.s3_access_key,
       'secret_key': args.s3_secret_key,
       'private_bucket': args.iso_bucket,
       'public_bucket': args.iso_bucket
   }
   ```

3. **Initialize the component**:
   ```python
   s3_component = S3Component(s3_config, logger)
   ```

4. **Execute the discovery phase**:
   ```python
   discovery_results = s3_component.discover()
   
   # Check discovery results
   if not discovery_results.get('connectivity', False):
       logger.error(f"Failed to connect to S3: {discovery_results.get('error')}")
       return 1
   ```

5. **Execute the processing phase**:
   ```python
   processing_results = s3_component.process()
   
   # Check processing results
   if not processing_results.get('buckets_created', False):
       logger.error("Failed to create S3 buckets")
       return 1
   ```

6. **Execute the housekeeping phase**:
   ```python
   housekeeping_results = s3_component.housekeep()
   
   # Check housekeeping results
   if not housekeeping_results.get('verification_successful', False):
       logger.warning("S3 verification failed")
   ```

7. **Handle multiple components by passing dependencies**:
   ```python
   # Initialize S3 component first
   s3_component = S3Component(s3_config, logger)
   s3_component.discover()
   s3_component.process()
   
   # Initialize OpenShift component with a reference to S3
   openshift_component = OpenShiftComponent(openshift_config, logger, s3_component)
   openshift_component.discover()
   openshift_component.process()
   openshift_component.housekeep()
   
   # Complete S3 housekeeping after all artifacts are added
   s3_component.housekeep()
   ```

## Creating New Components

To create a new component:

1. **Create a new file** in the `framework/components/` directory:
   ```python
   # my_component.py
   from framework.base_component import BaseComponent
   
   class MyComponent(BaseComponent):
       """
       MyComponent provides custom functionality for X.
       
       This component manages X resources and performs Y operations
       following the discovery-processing-housekeeping pattern.
       """
       
       # Default configuration with documentation
       DEFAULT_CONFIG = {
           'required_setting': None,  # Required setting for X
           'optional_setting': 'default',  # Optional setting with default value
           'dry_run': False  # Whether to perform actual changes
       }
       
       def __init__(self, config, logger=None):
           """Initialize the component with configuration."""
           # Merge provided config with defaults
           merged_config = {**self.DEFAULT_CONFIG, **config}
           
           # Initialize base component
           super().__init__(merged_config, logger)
           
           # Component-specific initialization
           self.logger.info(f"MyComponent initialized with ID {self.component_id}")
           
       def discover(self):
           """
           Discovery phase: Examine the environment without making changes.
           
           Checks X, validates Y, and identifies Z in the current environment.
           
           Returns:
               Dictionary of discovery results
           """
           self.logger.info(f"Starting discovery phase for {self.component_name}")
           
           try:
               # Initialize discovery results
               self.discovery_results = {
                   'connectivity': False,
                   'resources_found': []
               }
               
               # Implement discovery logic here
               
               # Mark as executed
               self.phases_executed['discover'] = True
               
               return self.discovery_results
               
           except Exception as e:
               self.logger.error(f"Error during discovery phase: {str(e)}")
               self.status['success'] = False
               self.status['error'] = str(e)
               raise
       
       def process(self):
           """
           Processing phase: Perform the core work of the component.
           
           Creates or updates resources based on discovery results.
           
           Returns:
               Dictionary of processing results
           """
           self.logger.info(f"Starting processing phase for {self.component_name}")
           
           # Check if discovery has been run
           if not self.phases_executed['discover']:
               self.logger.warning("Processing without prior discovery may lead to unexpected results")
               # Run discovery to be safe
               self.discover()
           
           try:
               # Initialize processing results
               self.processing_results = {
                   'changes_made': False,
                   'resources_created': []
               }
               
               # Implement processing logic here
               
               # Mark as executed
               self.phases_executed['process'] = True
               
               return self.processing_results
               
           except Exception as e:
               self.logger.error(f"Error during processing phase: {str(e)}")
               self.status['success'] = False
               self.status['error'] = str(e)
               raise
       
       def housekeep(self):
           """
           Housekeeping phase: Verify, clean up, and finalize work.
           
           Verifies changes were applied correctly and cleans up temporary resources.
           
           Returns:
               Dictionary of housekeeping results
           """
           self.logger.info(f"Starting housekeeping phase for {self.component_name}")
           
           # Check if processing has been run
           if not self.phases_executed['process']:
               self.logger.warning("Housekeeping without prior processing may lead to unexpected results")
           
           try:
               # Initialize housekeeping results
               self.housekeeping_results = {
                   'verification_successful': False,
                   'resources_cleaned': []
               }
               
               # Implement housekeeping logic here
               
               # Mark as executed
               self.phases_executed['housekeep'] = True
               
               return self.housekeeping_results
               
           except Exception as e:
               self.logger.error(f"Error during housekeeping phase: {str(e)}")
               self.status['success'] = False
               self.status['error'] = str(e)
               raise
   ```

2. **Create unit tests** in the `tests/unit/framework/components/` directory:
   ```python
   # test_my_component.py
   import pytest
   from unittest.mock import MagicMock, patch
   from framework.components.my_component import MyComponent
   
   @pytest.fixture
   def mock_config():
       """Mock configuration for testing."""
       return {
           'required_setting': 'test_value',
           'optional_setting': 'custom_value',
           'component_id': 'test-my-component'
       }
   
   @pytest.fixture
   def my_component(mock_config):
       """MyComponent fixture for testing."""
       return MyComponent(mock_config)
   
   def test_discover_success(my_component):
       """Test successful discovery phase."""
       # Mock any external calls
       with patch('framework.components.my_component.some_external_function') as mock_external:
           mock_external.return_value = {'success': True}
           
           # Run discovery
           result = my_component.discover()
           
           # Check results
           assert result.get('connectivity') is True
           assert len(result.get('resources_found', [])) > 0
           assert my_component.phases_executed['discover'] is True
   
   def test_process_success(my_component):
       """Test successful processing phase."""
       # Setup discovery results
       my_component.discovery_results = {
           'connectivity': True,
           'resources_found': ['resource1', 'resource2']
       }
       my_component.phases_executed['discover'] = True
       
       # Mock any external calls
       with patch('framework.components.my_component.some_external_function') as mock_external:
           mock_external.return_value = {'success': True}
           
           # Run processing
           result = my_component.process()
           
           # Check results
           assert result.get('changes_made') is True
           assert len(result.get('resources_created', [])) > 0
           assert my_component.phases_executed['process'] is True
   
   def test_housekeep_success(my_component):
       """Test successful housekeeping phase."""
       # Setup discovery and processing results
       my_component.discovery_results = {'connectivity': True}
       my_component.processing_results = {'changes_made': True}
       my_component.phases_executed['discover'] = True
       my_component.phases_executed['process'] = True
       
       # Run housekeeping
       result = my_component.housekeep()
       
       # Check results
       assert result.get('verification_successful') is True
       assert my_component.phases_executed['housekeep'] is True
   ```

3. **Document your component** by updating:
   - Component doc strings
   - `docs/COMPONENT_ARCHITECTURE.md`
   - `docs/COMPONENT_TUTORIAL.md` with examples

## Testing Components

Components should be thoroughly tested using pytest. The project includes a comprehensive testing framework with fixtures for common dependencies.

### Unit Testing Approach

1. **Mock external dependencies**:
   ```python
   @patch('framework.components.s3_component.boto3.client')
   def test_discover_connection_success(mock_boto3_client, s3_component):
       mock_client = MagicMock()
       mock_boto3_client.return_value = mock_client
       mock_client.list_buckets.return_value = {'Buckets': []}
       
       result = s3_component.discover()
       
       assert result['connectivity'] is True
   ```

2. **Test each phase independently**:
   ```python
   def test_discover_phase(component):
       result = component.discover()
       assert 'connectivity' in result
       assert component.phases_executed['discover'] is True
       
   def test_process_phase(component):
       # Setup discovery state
       component.discovery_results = {'connectivity': True}
       component.phases_executed['discover'] = True
       
       result = component.process()
       assert 'changes_made' in result
       assert component.phases_executed['process'] is True
       
   def test_housekeep_phase(component):
       # Setup discovery and processing state
       component.discovery_results = {'connectivity': True}
       component.processing_results = {'changes_made': True}
       component.phases_executed['discover'] = True
       component.phases_executed['process'] = True
       
       result = component.housekeep()
       assert 'verification_successful' in result
       assert component.phases_executed['housekeep'] is True
   ```

3. **Test error handling**:
   ```python
   def test_discover_handles_connection_error(component):
       with patch('some.external.api', side_effect=ConnectionError('Simulated error')):
           result = component.discover()
           
           assert result['connectivity'] is False
           assert 'connection_error' in result
   ```

4. **Run with coverage**:
   ```bash
   # Run all tests with coverage
   ./run_tests.sh -c
   
   # Run specific component tests with coverage
   ./run_tests.sh -c -s  # S3Component
   ```

## Orchestration Patterns

Components can be orchestrated in various ways to achieve complex workflows:

### Sequential Orchestration

Execute components one after another:

```python
# Initialize components
s3_component = S3Component(s3_config)
openshift_component = OpenShiftComponent(openshift_config)
iscsi_component = ISCSIComponent(iscsi_config)

# Run discovery for all components
s3_discovery = s3_component.discover()
openshift_discovery = openshift_component.discover()
iscsi_discovery = iscsi_component.discover()

# Check if all discovery phases succeeded
if all([
    s3_discovery.get('connectivity'), 
    openshift_discovery.get('pull_secret_available'),
    iscsi_discovery.get('connectivity')
]):
    # Run processing phases
    s3_component.process()
    openshift_component.process()
    iscsi_component.process()
    
    # Run housekeeping phases
    s3_component.housekeep()
    openshift_component.housekeep()
    iscsi_component.housekeep()
```

### Component Dependency

Pass one component as a dependency to another:

```python
# Initialize storage component
s3_component = S3Component(s3_config)
s3_component.discover()
s3_component.process()

# Initialize OpenShift component with S3 component as dependency
openshift_component = OpenShiftComponent(openshift_config, logger, s3_component)
openshift_component.discover()

# Process will automatically use S3 for storage
openshift_component.process()
openshift_component.housekeep()

# Finalize S3 operations after all artifacts are added
s3_component.housekeep()
```

### Conditional Execution

Execute components based on conditions:

```python
# Initialize components
s3_component = S3Component(s3_config)
openshift_component = OpenShiftComponent(openshift_config)

# Discover S3 resources
s3_discovery = s3_component.discover()

# Only proceed if S3 connectivity is successful
if s3_discovery.get('connectivity'):
    s3_component.process()
    
    # Check if ISO already exists
    iso_exists = any(
        iso.get('key', '').endswith(f"openshift-{args.version}.iso")
        for iso in s3_discovery.get('objects', [])
    )
    
    # Generate ISO only if it doesn't exist or force is specified
    if not iso_exists or args.force:
        openshift_component.discover()
        openshift_component.process()
        openshift_component.housekeep()
    
    s3_component.housekeep()
```

## Best Practices

When working with the component architecture, follow these best practices:

### 1. Component Design

- **Single responsibility**: Each component should focus on one domain
- **Clear interfaces**: Components should have well-defined public methods
- **Default configuration**: Provide sensible defaults in DEFAULT_CONFIG
- **Documentation**: Document the component's purpose and usage
- **Phase separation**: Keep discovery, processing, and housekeeping logic separate

### 2. Error Handling

- **Consistent error reporting**: Return structured error information in result dictionaries
- **Fail early**: Check prerequisites in discovery phase
- **Graceful degradation**: Handle partial failures when possible
- **Detailed logging**: Log errors with context information
- **Exception handling**: Catch and handle specific exceptions

### 3. Testing

- **Mock external dependencies**: Don't rely on live services for unit tests
- **Test each phase**: Verify discovery, processing, and housekeeping independently
- **Test error paths**: Ensure errors are handled properly
- **Integration tests**: Test component combinations for workflow validation

### 4. Script Integration

- **CLI argument mapping**: Map CLI arguments to component configurations
- **Use all three phases**: Always run discovery, processing, and housekeeping
- **Check phase results**: Validate the output of each phase before proceeding
- **Provide verbose output**: Allow users to see detailed logs with --verbose

### 5. Orchestration

- **Component dependencies**: Pass related components to each other
- **Resource reuse**: Share resources between components
- **Artifact management**: Use add_artifact for storing outputs
- **Result propagation**: Pass results from one component to the next

## Conclusion

The component-based architecture provides a solid foundation for building robust, maintainable automated workflows. By following the discovery-processing-housekeeping pattern and leveraging the existing components, you can quickly create powerful tools for managing OpenShift deployments, iSCSI storage, and Dell R630 servers.

This architecture will continue to evolve as new components are added and existing ones are enhanced. The modular design ensures that improvements in one component benefit all scripts that use it, promoting code reuse and consistency across the project.
