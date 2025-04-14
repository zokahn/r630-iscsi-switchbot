# S3 Storage Integration

This documentation outlines how S3-compatible storage is integrated into the r630-iscsi-switchbot project for persistent storage needs.

## Overview

The project uses S3-compatible storage (specifically MinIO via the endpoint https://scratchy.omnisack.nl) to store persistent data required across different stages of the workflow:

- OpenShift ISOs: Generated agent-based installation ISOs
- OpenShift binaries: Cached installer and client binaries
- Temporary storage: For passing artifacts between workflow stages
- Other data: Generated configurations, logs, and metrics

## Architecture

The system uses a component-based architecture to interact with S3:

1. **S3Component**: Handles all S3 interactions including bucket management, object uploads/downloads
2. **OpenShiftComponent**: Generates ISOs and uses S3Component for storage
3. **Workflow orchestration**: Scripts that coordinate components for complete workflows

## S3 Buckets Structure

The S3 storage is organized into multiple buckets:

- **r630-switchbot-isos**: Stores OpenShift ISO images
  - `/openshift/{version}/agent.x86_64.iso`: Generated OpenShift ISOs
  - `/openshift/{version}/metadata.json`: Metadata for each ISO
  
- **r630-switchbot-binaries**: Caches OpenShift binaries to avoid repeated downloads
  - `/openshift-install/{version}/openshift-install`: OpenShift installer binaries
  - `/openshift-client/{version}/oc`: OpenShift client binaries
  
- **r630-switchbot-temp**: Temporary storage for workflow artifacts
  - `/workflows/{workflow_id}/`: Directories for specific workflow runs
  
## Usage

### Setting Up S3 Storage

To set up and manage the S3 buckets, use the provided `setup_minio_buckets.py` script:

```bash
# Initialize all required buckets
./scripts/setup_minio_buckets.py --access-key YOUR_ACCESS_KEY --secret-key YOUR_SECRET_KEY --init-all

# Test the buckets with a simple upload
./scripts/setup_minio_buckets.py --access-key YOUR_ACCESS_KEY --secret-key YOUR_SECRET_KEY --upload-example

# View current buckets and their contents (no changes)
./scripts/setup_minio_buckets.py --access-key YOUR_ACCESS_KEY --secret-key YOUR_SECRET_KEY
```

### Generating and Storing OpenShift ISOs

The workflow script `workflow_iso_generation_s3.py` demonstrates how to generate OpenShift ISOs and store them in S3:

```bash
# Generate an OpenShift ISO and store in S3
./scripts/workflow_iso_generation_s3.py \
  --version 4.14 \
  --rendezvous-ip 192.168.1.100 \
  --pull-secret ~/.openshift/pull-secret \
  --s3-access-key YOUR_ACCESS_KEY \
  --s3-secret-key YOUR_SECRET_KEY

# List existing ISOs in S3 without generating a new one
./scripts/workflow_iso_generation_s3.py \
  --list-only \
  --s3-access-key YOUR_ACCESS_KEY \
  --s3-secret-key YOUR_SECRET_KEY
```

### Integration with Components

The project now uses a standardized component architecture with the discovery-process-housekeep pattern. Components that need S3 storage interact with the S3Component:

```python
from framework.components.s3_component import S3Component

# Initialize the S3 Component
s3_config = {
    'private_bucket': 'r630-switchbot-private',
    'public_bucket': 'r630-switchbot-public',
    'endpoint': 'scratchy.omnisack.nl',
    'access_key': 'YOUR_ACCESS_KEY',  
    'secret_key': 'YOUR_SECRET_KEY',
    'secure': False,  # Set to True for HTTPS
    'create_buckets_if_missing': True,
    'folder_structure_private': [
        'isos/',
        'binaries/',
        'artifacts/'
    ],
    'folder_structure_public': [
        'isos/4.16/',
        'isos/4.17/',
        'isos/4.18/',
        'isos/stable/'
    ]
}
s3_component = S3Component(s3_config)

# Run the component lifecycle
discovery_results = s3_component.discover()  # Examine the S3 environment
process_results = s3_component.process()    # Create buckets if needed
housekeep_results = s3_component.housekeep() # Verify configuration and clean up

# Or execute all phases at once
results = s3_component.execute()

# Upload an ISO with proper metadata
upload_result = s3_component.upload_iso(
    iso_path='/path/to/generated.iso',
    server_id='01',
    hostname='r630-01.example.com',
    version='4.14',
    publish=True  # Also sync to public bucket
)

# List available ISOs by server
isos = s3_component.list_isos(server_id='01')

# Add a general artifact (automatically stored during housekeep phase)
s3_component.add_artifact(
    artifact_type='config',
    content=json.dumps(config_data),
    metadata={
        'version': '4.14',
        'server_id': '01',
        'timestamp': datetime.datetime.now().isoformat()
    }
)
```

### OpenShift Component S3 Integration

The OpenShiftComponent automatically uses S3 for ISO storage when provided with an S3Component:

```python
from framework.components.s3_component import S3Component
from framework.components.openshift_component import OpenShiftComponent

# Initialize components
s3_component = S3Component(s3_config)
s3_component.discover()
s3_component.process()

# Configure OpenShift component with S3 reference
openshift_config = {
    'openshift_version': '4.14',
    'domain': 'example.com',
    'rendezvous_ip': '192.168.1.100',
    'pull_secret_path': '~/.openshift/pull-secret',
    's3_config': {
        'iso_bucket': 'r630-switchbot-isos',
        'binary_bucket': 'r630-switchbot-binaries'
    }
}

# Pass S3Component as a parameter
openshift_component = OpenShiftComponent(openshift_config, s3_component=s3_component)

# Generate ISO and automatically store in S3
openshift_component.discover()
openshift_component.process()  # Includes ISO generation and S3 upload
openshift_component.housekeep()
```

## Credential Management

The project now supports multiple methods for credential management:

### 1. HashiCorp Vault Integration

For production deployments, you can store credentials in HashiCorp Vault and use the secrets_provider utility:

```python
from scripts.secrets_provider import init, get_secret, process_references

# Initialize the secrets provider
init(vault_addr='http://vault-server:8200', vault_token='s.token')

# Get credentials
s3_credentials = get_secret('s3/credentials')
access_key = s3_credentials['access_key']
secret_key = s3_credentials['secret_key']

# Or use reference resolution in configuration
config = {
    's3': {
        'endpoint': 'scratchy.omnisack.nl',
        'access_key': 'secret:s3/credentials:access_key',
        'secret_key': 'secret:s3/credentials:secret_key'
    }
}

# Process all secret references
resolved_config = process_references(config)
```

### 2. Environment Variables

For development and testing, credentials can be stored in a `.env` file:

```
# S3/MinIO Configuration
S3_ENDPOINT=scratchy.omnisack.nl
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key

# HashiCorp Vault Configuration
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=your_vault_token
```

Use the provided `.env.example` as a template:

```bash
cp .env.example .env
# Edit .env with your credentials
```

## Bucket Configurations and Policies

These are the standard bucket policies used in the project:

1. **ISO Bucket**: Contains OpenShift ISOs that should be retained for longer periods
   - **Lifecycle Policy**: ISOs older than 60 days are moved to archival storage
   - **Access**: Read-only for most systems, write access for generation workflows

2. **Binary Bucket**: Contains cached binaries to speed up deployments
   - **Lifecycle Policy**: Binaries not accessed for 30 days are deleted
   - **Access**: Read/write for all components

3. **Temp Bucket**: For ephemeral storage between workflow steps
   - **Lifecycle Policy**: Objects older than 24 hours are automatically deleted
   - **Access**: Read/write for all components

## Best Practices

1. **Use Structured Object Names**: Follow the convention of `/{category}/{sub-category}/{identifier}`
2. **Add Metadata**: All uploads should include metadata for versioning and tracking
3. **Check Before Download**: Verify if resources exist before downloading to reduce bandwidth
4. **Clean Up Temporary Data**: Always clean up temporary objects after workflows complete
5. **Versioning**: Use version tags for immutable artifacts like ISOs and binaries

## Monitoring and Management

For bucket monitoring and manual management, you can use:

1. **MinIO Console**: A web-based interface for the S3 buckets
2. **MinIO Client (mc)**: Command-line tool for bucket operations
   ```bash
   # Configure MinIO client
   mc alias set scratchy https://scratchy.omnisack.nl YOUR_ACCESS_KEY YOUR_SECRET_KEY
   
   # List buckets
   mc ls scratchy/
   
   # List objects in a bucket
   mc ls scratchy/r630-switchbot-isos
   ```

## Troubleshooting

Common issues with S3 storage and their solutions:

1. **Connection Failures**:
   - Verify endpoint URL is correct
   - Check credentials are valid
   - Ensure network connectivity to the endpoint

2. **Permission Denied**:
   - Verify the access key has appropriate permissions for the operation
   - Check bucket policies that might restrict operations

3. **Bucket Not Found**:
   - Ensure the bucket name is correct
   - Verify the bucket exists (it may need to be created first)

4. **Object Not Found**:
   - Check the object path is correct including all prefixes
   - Verify the object exists using `mc ls` or S3 component
