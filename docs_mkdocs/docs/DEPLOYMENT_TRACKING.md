# Deployment Tracking and Artifact Management

This document explains the deployment tracking system used for maintaining multiple R630 OpenShift installations with different configurations.

## Deployment Identification

Each deployment is uniquely identified using the following format:
```
r630-{server_id}-{cluster_type}-{timestamp}
```

- **server_id**: Numeric identifier for the physical server (e.g., 01, 02)
- **cluster_type**: Type of deployment (sno, ha, etc.)
- **timestamp**: YYYYMMDDHHMMSS format timestamp when deployment was initiated

Example: `r630-01-sno-20250415103025`

## System Overview

The deployment tracking system consists of several integrated components:

1. **Configuration Management**:
   - Server-specific configuration files in organized directories
   - Timestamped file naming for version tracking
   - Metadata embedded in configuration files

2. **Artifact Collection**:
   - Automatic collection of logs, credentials, and metadata
   - Secure storage on TrueNAS Scale
   - Standardized directory structure across servers

3. **Script Integration**:
   - Command-line flags for specifying server IDs
   - Automatic artifact uploading at deployment completion
   - GitHub Actions workflow integration

## Configuration Storage

Deployment configuration files are stored in:
```
config/deployments/{server-id}/{deployment-id}.yaml
```

For example:
```
config/deployments/r630-01/r630-01-sno-20250412160745.yaml
```

## Artifact Storage on TrueNAS

For each deployment, artifacts are automatically collected and stored on TrueNAS Scale:
```
/mnt/tank/deployment_artifacts/{server-id}/{deployment-id}/
```

The artifacts directory structure includes:
```
r630-01/
└── r630-01-sno-20250412160745/
    ├── logs/
    │   └── deployment_r630-01-sno-20250412160745.log
    ├── auth/
    │   └── kubeconfig
    └── metadata/
        └── metadata.json
```

Artifacts include:
- **logs/**: All installation logs
- **auth/**: Kubeconfig and authentication information
- **metadata.json**: Detailed information about the deployment

## Security Considerations

### Private vs. Public Information

This deployment system maintains a clear separation between:

1. **Private Information** (stored only on TrueNAS Scale):
   - OpenShift pull secrets
   - SSH keys
   - Kubeadmin passwords
   - Full, unredacted logs
   - Kubeconfig files with connection details

2. **Public Information** (may appear in GitHub):
   - Deployment structure and scripts
   - Configuration templates (without credentials)
   - Sanitized examples and documentation
   - Workflow definitions (using GitHub Secrets for credentials)

### Safe Usage Guidelines

When working with this system:

1. **Never commit** files containing:
   - TrueNAS credentials
   - OpenShift pull secrets
   - SSH private keys
   - Kubeadmin passwords
   - Kubeconfig files
   
2. **Always use GitHub Secrets** for:
   - API tokens
   - Authentication credentials
   - Pull secrets
   - Any sensitive environment variables
   
3. **Review logs and outputs** before publishing examples to ensure they don't contain:
   - Internal IP addresses
   - Hostnames
   - Authentication tokens
   - Session cookies

## Using the System

### Creating a New Deployment

1. Generate a values file with server identifier:
   ```bash
   ./scripts/generate_openshift_values.py \
     --node-ip 192.168.2.230 \
     --cluster-name sno \
     --server-id 01 \
     --base-domain intranet.lab
   ```

2. Generate and upload the ISO with artifact collection:
   ```bash
   ./scripts/generate_openshift_iso.py \
     --version 4.18 \
     --values-file config/deployments/r630-01/r630-01-sno-20250415103025.yaml
   ```

3. Run the deployment:
   ```bash
   ./scripts/finalize_deployment.sh \
     --server-id 01 \
     --deployment-name sno \
     --values-file config/deployments/r630-01/r630-01-sno-20250415103025.yaml
   ```

### Testing the System

A test script is available to verify the deployment tracking functionality without performing an actual deployment:

```bash
./scripts/test_deployment_tracking.sh
```

This script:
- Creates mock configuration files with server IDs
- Generates sample deployment artifacts (logs, kubeconfig)
- Tests metadata collection and artifact organization
- Verifies the upload process in mock mode

### Manual Artifact Upload

You can manually upload deployment artifacts using:

```bash
./scripts/upload_deployment_artifacts.sh \
  --server-id 01 \
  --deployment-name sno \
  --log-file path/to/deployment.log \
  --kubeconfig path/to/kubeconfig \
  --metadata version=4.18 \
  --metadata status=COMPLETE
```

Options include:
- `--server-id`: Server identifier (required)
- `--deployment-name`: Type of deployment (default: sno)
- `--timestamp`: Custom timestamp (default: current time)
- `--log-file`: Path to deployment log
- `--kubeconfig`: Path to kubeconfig file
- `--metadata`: Add custom metadata (can be specified multiple times)
- `--mock-mode`: Test mode - don't connect to TrueNAS

### Accessing Deployment Information

1. Via the web dashboard on TrueNAS: http://192.168.2.245/deployments/
2. Directly on TrueNAS: `/mnt/tank/deployment_artifacts/{server-id}/{deployment-id}/`

### Managing Multiple Servers

Each physical server gets its own ID and separate configuration paths, allowing for parallel deployments and distinct configuration tracking:

- **Server-01**: `r630-01/`
  - Configurations: `config/deployments/r630-01/`
  - Artifacts: `/mnt/tank/deployment_artifacts/r630-01/`
 
- **Server-02**: `r630-02/`
  - Configurations: `config/deployments/r630-02/`
  - Artifacts: `/mnt/tank/deployment_artifacts/r630-02/`

## TrueNAS Setup

The TrueNAS environment is automatically configured with the appropriate directory structure:

```bash
# Run on TrueNAS server
./scripts/setup_truenas.sh
```

This will create:
- Basic dataset structure for deployment artifacts
- Server-specific directories for multiple R630 servers
- Appropriate permissions for secure access
