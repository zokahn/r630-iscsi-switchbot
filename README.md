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
- [ ] Write unit tests for framework
- [x] Document framework architecture

### Phase 2: Initial Component Implementation (Estimated: 1 week)
- [x] Implement S3Component using the new framework
- [x] Add S3 artifact indexing and metadata management
- [x] Create dual-bucket synchronization in the new framework
- [x] Document S3Component usage
- [ ] Write unit tests for S3Component
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
- [ ] Update existing scripts to use new components where applicable
- [ ] Maintain backward compatibility interfaces
- [ ] Create comprehensive documentation for the new architecture
- [ ] Update MkDocs configuration for the new documentation
- [ ] Create usage examples and tutorials
