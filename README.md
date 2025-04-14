# OpenShift Multiboot System

<div align="center">
  <img src="docs_mkdocs/docs/assets/images/r630-iscsi-switchbot-banner.png" alt="R630 iSCSI SwitchBot Banner" width="100%">
</div>

## Personal Sandbox Project by Bart van den Heuvel

This project is an Omnisack sandbox project created by Bart van den Heuvel to make a super cool lab environment. It's intended for others to see, enjoy, and maybe grab a few ideas from. This is a personal project for maintaining a lab environment and learning interesting things, rather than an official product.

## Overview

The Dell PowerEdge R630 OpenShift Multiboot System enables flexible deployment and switching between different OpenShift installations on Dell PowerEdge R630 servers using iSCSI storage. This solution provides administrators with the ability to:

- Instantly switch between different OpenShift versions
- Utilize network boot, local ISO, or iSCSI storage boot options
- Manage OpenShift deployments through a streamlined automation interface
- Securely store and manage configuration secrets
- Track and maintain deployments across multiple R630 servers

## Key Components

- **Multiboot System**: Switch between multiple OpenShift versions
- **Netboot Support**: Network boot capabilities for quick deployments
- **S3 Storage Integration**: 
  - Dual-bucket strategy for private versioning and public access
  - Persistent storage for ISOs, binaries, and deployment artifacts
- **TrueNAS Integration**: iSCSI storage provisioning and management
- **Configuration Validation**: Automated validation of OpenShift configurations
- **Secrets Management**: Secure handling of sensitive information
- **GitHub Actions Workflows**: Automated CI/CD for deployment processes
- **Multi-Server Deployment Tracking**: Management of deployments across multiple R630 servers
- **Test Deployment Tools**: Streamlined testing with standardized input data

## Documentation

Comprehensive documentation is available in two formats:

1. **Markdown files** in the `docs/` directory for direct GitHub viewing
2. **MkDocs site** for a more polished documentation experience (generated from `docs_mkdocs/`)

Key documentation files:

- [Deployment Tracking](docs/DEPLOYMENT_TRACKING.md): Managing multiple servers and deployments
- [OpenShift Values System](docs/OPENSHIFT_VALUES_SYSTEM.md): Configuration management
- [S3 Storage Integration](docs/S3_STORAGE.md): Persistent storage for ISOs and artifacts
- [iSCSI Redfish Integration](docs/ISCSI_REDFISH_INTEGRATION.md): Advanced iSCSI boot configuration
- [GitHub Actions Usage](docs/GITHUB_ACTIONS_USAGE.md): Setting up workflows
- [TrueNAS Authentication](docs/TRUENAS_AUTHENTICATION.md): Storage setup
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md): Common issues and solutions

## Getting Started

To use this system in your own environment:

1. Clone this repository
2. Set up TrueNAS Scale with iSCSI support
3. Configure your R630 server(s) for iSCSI boot
4. Set up S3 storage for artifacts (see below)
5. Set up GitHub Actions for automation (optional)
6. Generate your first OpenShift configuration:

```bash
./scripts/generate_openshift_values.py \
  --node-ip 192.168.2.230 \
  --server-id 01 \
  --cluster-name sno \
  --base-domain lab.local
```

7. Run a deployment:

```bash
./scripts/finalize_deployment.sh \
  --server-id 01 \
  --deployment-name sno
```

## S3 Storage and Secrets Management

This project now includes comprehensive S3 storage integration and HashiCorp Vault support for secrets management.

### Setting Up S3 Storage

1. Copy the environment template and add your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your MinIO/S3 credentials
   ```

2. Initialize your S3 buckets:
   ```bash
   python scripts/setup_minio_buckets.py \
     --endpoint scratchy.omnisack.nl \
     --access-key YOUR_ACCESS_KEY \
     --secret-key YOUR_SECRET_KEY \
     --init-all
   ```

3. Test your S3 connection:
   ```bash
   python scripts/test_s3_minio.py \
     --endpoint scratchy.omnisack.nl \
     --access-key YOUR_ACCESS_KEY \
     --secret-key YOUR_SECRET_KEY \
     --list-only
   ```

### Working with OpenShift ISOs and S3

Generate and store OpenShift ISOs in S3:

```bash
python scripts/workflow_iso_generation_s3.py \
  --version 4.14 \
  --rendezvous-ip 192.168.1.100 \
  --pull-secret ~/.openshift/pull-secret \
  --s3-endpoint scratchy.omnisack.nl \
  --s3-access-key YOUR_ACCESS_KEY \
  --s3-secret-key YOUR_SECRET_KEY
```

List available ISOs in S3:

```bash
python scripts/workflow_iso_generation_s3.py \
  --list-only \
  --s3-endpoint scratchy.omnisack.nl \
  --s3-access-key YOUR_ACCESS_KEY \
  --s3-secret-key YOUR_SECRET_KEY
```

### Using HashiCorp Vault for Secrets (Optional)

If you have a HashiCorp Vault server:

1. Add your Vault configuration to .env:
   ```
   VAULT_ADDR=http://your-vault-server:8200
   VAULT_TOKEN=your-token
   ```

2. Use the secrets provider in your scripts:
   ```python
   from scripts.secrets_provider import get_secret
   
   # Get a secret from Vault (or environment variables as fallback)
   s3_key = get_secret('s3/credentials', 'access_key')
   ```

3. Use secret references in your configuration:
   ```yaml
   s3:
     endpoint: scratchy.omnisack.nl
     access_key: secret:s3/credentials:access_key
     secret_key: secret:s3/credentials:secret_key
   ```

## Testing Deployments

The system includes a testing framework for validating deployments with various network configurations:

1. Prepare test input data in the standardized format:
```
api.cluster.domain          192.168.2.90
api-int.cluster.domain      192.168.2.90
*.apps.cluster.domain       192.168.2.90
idrac ip                    192.168.2.230
MAC (interface)             e4:43:4b:44:5b:10
DHCP configuration          [details]
gateway/DNS information     [details]
```

2. Run an integrated test with automatic validation:
```bash
./scripts/test_deployment.sh \
  --name humpty \
  --domain omnisack.nl \
  --node-ip 192.168.2.90 \
  --idrac-ip 192.168.2.230 \
  --mac-address e4:43:4b:44:5b:10 \
  --boot-method iscsi \
  --test-type check-only
```

3. Validate configurations separately:
```bash
./scripts/validate_openshift_config.sh \
  --config config/deployments/r630-01/r630-01-humpty-20250412223919.yaml
```

For detailed testing procedures, see [Test Plan](docs/TEST_PLAN.md).

## Learning and Inspiration

This project may serve as inspiration for your own lab setup or enterprise deployment system. Feel free to explore the code, adapt it to your needs, and learn from the implementation.

## Project Roadmap: Discovery-Processing-Housekeeping Implementation

We're transitioning to a component-based architecture with a consistent discovery-processing-housekeeping pattern. This task list tracks our progress.

### Phase 1: Core Framework (Estimated: 2-3 days)
- [x] Create framework directory structure
- [x] Implement BaseComponent class with discovery-processing-housekeeping pattern
- [x] Add logging and configuration utilities
- [x] Create S3 artifact management utilities
- [x] Write unit tests for framework
- [x] Document framework architecture

### Phase 2: Initial Component Implementation (Estimated: 1 week)
- [x] Implement S3Component using the new framework
- [x] Add S3 artifact indexing and metadata management
- [x] Create dual-bucket synchronization in the new framework
- [x] Document S3Component usage
- [x] Write unit tests for S3Component
- [x] Create example usage scripts

### Phase 3: Additional Components (Current Phase)
- [x] Implement OpenShiftComponent
  - [x] Discovery methods for OpenShift environment
  - [x] Processing methods for OpenShift ISO creation
  - [x] Housekeeping methods for cleanup and verification
- [x] Implement ISCSIComponent
  - [x] Discovery methods for TrueNAS/iSCSI environment
  - [x] Processing methods for iSCSI target creation and configuration
  - [x] Housekeeping methods for verification and cleanup
- [x] Implement R630Component
  - [x] Discovery methods for Dell R630 hardware
  - [x] Processing methods for hardware configuration
  - [x] Housekeeping methods for verification and reboot management
- [x] Implement VaultComponent for secrets management
  - [x] Discovery methods for Vault environment
  - [x] Processing methods for secret creation and validation
  - [x] Housekeeping methods for token renewal and verification
- [x] Write unit tests for all components
- [x] Document component interfaces and usage patterns

### Phase 4: Orchestration Layer (Current Phase)
- [x] Create orchestration scripts for common workflows
- [x] Implement workflow for ISO generation and S3 storage
- [x] Add workflow artifact management
- [x] Add CI/CD pipeline integration with GitHub Actions
- [x] Document orchestration usage

### Phase 5: Migration and Documentation (Ongoing)
- [x] Update existing scripts to use new components where applicable
  - [x] Created [Script Migration Plan](docs/SCRIPT_MIGRATION_PLAN.md) with guidelines and examples
  - [x] Migrated high-priority scripts (workflow_iso_generation_s3.py, setup_minio_buckets.py, test_iscsi_truenas.py)
  - [x] Migrated medium-priority scripts (generate_openshift_iso.py)
  - [x] Migrated lower-priority scripts:
    - [x] reboot_server.py → reboot_server_component.py (using R630Component)
    - [x] set_boot_order.py → set_boot_order_component.py (using R630Component)
- [x] Maintain backward compatibility through parallel implementation
  - [x] Created component-based scripts alongside original scripts
  - [x] New component-based scripts provide enhanced functionality while preserving CLI interfaces
- [x] Complete comprehensive documentation for the new architecture
  - [x] Added [Component Tutorial](docs/COMPONENT_TUTORIAL.md) with end-to-end workflow examples
  - [x] Created [Testing Improvements](docs/TESTING_IMPROVEMENTS.md) guide
  - [x] Created [Component Architecture Guide](docs/COMPONENT_ARCHITECTURE_GUIDE.md) with detailed design patterns and best practices
- [x] Update MkDocs configuration for the new documentation
- [x] Create usage examples and tutorials
  - [x] Added example implementation in the component tutorial
  - [x] Created [Component Script Usage Guide](docs/COMPONENT_SCRIPT_USAGE.md) with comparison between original and component-based scripts

## Unit Testing

The project now includes a comprehensive unit testing framework for the component-based architecture:

```
tests/
├── __init__.py
├── conftest.py            # Shared test fixtures and configuration
├── README.md              # Testing documentation
├── test_values.yaml       # Functional test data
└── unit/                  # Unit tests
    ├── framework/         # Framework tests
    │   ├── test_base_component.py
    │   └── components/    # Component tests
    │       ├── test_s3_component.py
    │       ├── test_openshift_component.py
    │       └── ...
```

### Running Tests

Execute the test suite with the included helper script:

```bash
# Run all tests
./run_tests.sh

# Run with coverage report
./run_tests.sh -c

# Test only specific components
./run_tests.sh -b  # BaseComponent
./run_tests.sh -s  # S3Component
./run_tests.sh -o  # OpenShiftComponent

# Show help for more options
./run_tests.sh -h
```

Or use pytest directly:

```bash
# Install requirements
pip install pytest pytest-cov pytest-mock

# Run specific tests
pytest tests/unit/framework/test_base_component.py
pytest tests/unit/framework/components/test_s3_component.py
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

## Continuous Integration

The project uses GitHub Actions for comprehensive CI workflows that follow modern best practices:

### Enhanced CI Workflows

- **[CI - Unit Tests](.github/workflows/ci-unit-tests.yml)**: Matrix testing across multiple Python versions with parallel execution
- **[CI - Component Tests](.github/workflows/ci-component-tests.yml)**: Containerized testing of framework components
- **[CI - Integration Tests](.github/workflows/ci-integration-tests.yml)**: End-to-end tests with parallel component testing
- **[CI - ISO Generation](.github/workflows/ci-iso-generation.yml)**: Parallel building of OpenShift ISOs for multiple versions
- **[CI - Python 3.12 Tests](.github/workflows/ci-unit-tests-python312.yml)**: Specialized testing for Python 3.12 components

### Key CI Features

- **Smart Stages**: Multi-stage pipelines with proper dependencies
- **Parallelization**: Matrix strategies for efficient resource utilization
- **Non-Intrusive Quality Checks**: Warning-only linting that never modifies code
- **Containerized Testing**: Isolated test environments for consistent results
- **Comprehensive Reporting**: Detailed test reports and artifacts

For more details, see:
- [CI Implementation Plan](docs/CI_IMPLEMENTATION.md): Complete CI architecture and workflows
- [CI Workflow Testing](docs/CI_WORKFLOW_TESTING.md): Step-by-step guide for testing CI workflows
- [Linting Policy](docs/LINTING_POLICY.md): Our philosophy on non-intrusive code quality checks
- [GitHub Actions Usage](docs/GITHUB_ACTIONS_USAGE.md): How to use GitHub Actions with this project

A helper script for testing workflows is provided:
```bash
# Test all workflows
./scripts/test_github_workflows.sh --all

# Test only unit and component tests
./scripts/test_github_workflows.sh --unit --component

# Test ISO generation with multiple versions
./scripts/test_github_workflows.sh --iso --openshift-version 4.17,4.18

# Show all options
./scripts/test_github_workflows.sh --help
```

Note: While CI (Continuous Integration) is fully automated, deployments remain ad hoc rather than using CD (Continuous Deployment) automation.

## Python 3.12 Support

The project has been fully migrated to Python 3.12, leveraging the latest language features and performance improvements.

### Migration Status - COMPLETED

- ✅ **Core Components**: All components migrated with Python 3.12 features
- ✅ **High-Priority Scripts**: 5 key scripts fully migrated
- ✅ **Testing Infrastructure**: Docker and CI pipeline support added
- ✅ **Documentation**: Comprehensive migration guides available
- ✅ **Verification System**: Easy-to-use verification script for testing components

### Python 3.12 Benefits

- **Enhanced Type Safety**: Comprehensive type annotations with TypedDict
- **Pattern Matching**: Cleaner conditional logic and error handling
- **Performance Improvements**: 5% overall speed boost, 2x faster comprehensions
- **Improved Developer Experience**: Better code completion and error reporting
- **Modern Syntax**: Dictionary merging, assignment expressions, and enhanced string formatting

### Using Python 3.12 Components

Python 3.12 versions are available alongside original components:

```python
# Original component
from framework.components.s3_component import S3Component

# Python 3.12 component
from framework.components.s3_component_py312 import S3Component as S3ComponentPy312
```

Similarly, scripts are available with `_py312` suffix:

```bash
# Run original script
python scripts/workflow_iso_generation_s3.py --help

# Run Python 3.12 version
python scripts/workflow_iso_generation_s3_py312.py --help
```

### Testing Python 3.12 Code

Run Python 3.12 tests using the dedicated test script:

```bash
# Run all Python 3.12 tests
./scripts/run_py312_tests.sh

# Run with Docker Compose
docker compose -f docker-compose.python312.yml up --build

# Test specific component
docker compose -f docker-compose.python312.yml run python312 python scripts/test_s3_component_py312.py
```

For more details, see:
- [Python 3.12 Migration Guide](docs/PYTHON312_MIGRATION.md): Overview and implementation plan
- [Python 3.12 Migration Progress](docs/PYTHON312_MIGRATION_PROGRESS.md): Current status and timeline
- [Script Migration Results](docs/SCRIPT_MIGRATION_RESULTS.md): Detailed improvements in migrated scripts
