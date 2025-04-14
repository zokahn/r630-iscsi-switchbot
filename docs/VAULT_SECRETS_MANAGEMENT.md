# HashiCorp Vault Integration

This documentation outlines how HashiCorp Vault is integrated into the r630-iscsi-switchbot project for secure secrets management.

## Overview

The project uses HashiCorp Vault to securely store and manage sensitive credentials and configuration data:

- S3/MinIO access keys and secrets
- TrueNAS API keys
- OpenShift pull secrets
- Other sensitive configuration values

This approach eliminates the need to store sensitive data in configuration files or hard-code them in scripts, improving security and maintainability.

## Architecture

The system uses a component-based architecture to interact with Vault:

1. **VaultComponent**: Handles all Vault interactions including authentication, secret management, and token renewal
2. **secrets_provider.py**: A simplified utility that uses VaultComponent for accessing secrets with fallback to environment variables
3. **Other components**: Reference secrets indirectly through the secrets provider

## Setup and Configuration

### Prerequisites

1. A running HashiCorp Vault server (development or production)
2. Authentication credentials (token or AppRole)
3. A KV secrets engine mounted (v1 or v2, though v2 is recommended)

### Basic Configuration

The Vault integration can be configured through environment variables or directly in code:

```bash
# Environment Variables
export VAULT_ADDR=http://vault-server:8200
export VAULT_TOKEN=your-vault-token
# Or for AppRole authentication
# export VAULT_ROLE_ID=your-role-id
# export VAULT_SECRET_ID=your-secret-id
```

Or using a `.env` file:

```
# HashiCorp Vault Configuration
VAULT_ADDR=http://vault-server:8200
VAULT_TOKEN=your-vault-token
```

## Usage

### Using the VaultComponent Directly

For advanced use cases, you can work with the VaultComponent directly:

```python
from framework.components.vault_component import VaultComponent

# Initialize the Vault Component
vault_config = {
    'vault_addr': 'http://vault-server:8200',
    'vault_token': 'your-vault-token',  # Or use AppRole authentication
    'vault_mount_point': 'secret',
    'vault_path_prefix': 'r630-switchbot'
}
vault_component = VaultComponent(vault_config)

# Run the component lifecycle
discovery_results = vault_component.discover()  # Check connectivity and authentication
process_results = vault_component.process()     # Verify permissions and paths
housekeep_results = vault_component.housekeep() # Check token status and renewal

# Or execute all phases at once
results = vault_component.execute()

# Store a secret
vault_component.put_secret('s3/credentials', {
    'access_key': 'AKIAIOSFODNN7EXAMPLE',
    'secret_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
    'endpoint': 'scratchy.omnisack.nl'
})

# Retrieve a secret
credentials = vault_component.get_secret('s3/credentials')
# Or a specific key
access_key = vault_component.get_secret('s3/credentials', 'access_key')

# List available secrets
secrets = vault_component.list_secrets('s3')

# Delete a secret
vault_component.delete_secret('s3/credentials')
```

### Using the Secrets Provider Utility

For most cases, the simplified secrets_provider utility is recommended:

```python
from scripts.secrets_provider import init, get_secret, process_references

# Initialize the secrets provider
init(vault_addr='http://vault-server:8200', vault_token='your-vault-token')
# Or using environment variables
init(env_file='.env')

# Get a complete secret object
s3_credentials = get_secret('s3/credentials')
access_key = s3_credentials['access_key']
secret_key = s3_credentials['secret_key']

# Or get a specific key directly
access_key = get_secret('s3/credentials', 'access_key')
```

#### Secret References in Configuration

One of the most powerful features is the ability to use secret references in configuration files:

```python
from scripts.secrets_provider import process_references

# Configuration with secret references
config = {
    's3': {
        'endpoint': 'scratchy.omnisack.nl',
        'access_key': 'secret:s3/credentials:access_key',
        'secret_key': 'secret:s3/credentials:secret_key'
    },
    'truenas': {
        'url': 'https://truenas.local',
        'api_key': 'secret:truenas/api_credentials:api_key'
    }
}

# Process all secret references
resolved_config = process_references(config)
# Now you can use resolved_config safely
```

### Command-line Usage

The secrets provider can also be used as a command-line tool:

```bash
# Initialize to check Vault connectivity
python scripts/secrets_provider.py --init \
  --vault-addr http://vault-server:8200 \
  --vault-token your-vault-token

# Store a secret
python scripts/secrets_provider.py \
  --put s3/credentials \
  --data '{"access_key": "AKIAIOSFODNN7EXAMPLE", "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}'

# Retrieve a secret
python scripts/secrets_provider.py --get s3/credentials

# Retrieve a specific key from a secret
python scripts/secrets_provider.py --get s3/credentials:access_key
```

## Best Practices

1. **Use Structured Paths**: Follow the convention of `/{category}/{identifier}` for secret paths
2. **Least Privilege**: Use AppRole authentication with specific policies when possible
3. **Environment Variable Fallback**: Provide fallback to environment variables for development and testing
4. **Token Renewal**: Ensure tokens are renewable and have appropriate TTL values
5. **Versioning**: Use KV v2 secrets engine to maintain secret history

## Secure Storage for Specific Project Secrets

### S3/MinIO Credentials

Store S3 credentials under the `s3/credentials` path:

```bash
python scripts/secrets_provider.py --put s3/credentials --data '{
  "access_key": "YOUR_ACCESS_KEY",
  "secret_key": "YOUR_SECRET_KEY", 
  "endpoint": "scratchy.omnisack.nl"
}'
```

### TrueNAS API Credentials

Store TrueNAS API credentials under the `truenas/api_credentials` path:

```bash
python scripts/secrets_provider.py --put truenas/api_credentials --data '{
  "api_key": "YOUR_API_KEY",
  "url": "https://truenas.local/api/v2.0"
}'
```

### OpenShift Pull Secrets

Store OpenShift pull secrets under the `openshift/pull_secret` path:

```bash
# First save the pull secret to a temporary file
cat ~/.openshift/pull-secret > /tmp/pull-secret.json

# Then store it in Vault
python scripts/secrets_provider.py --put openshift/pull_secret --data "$(cat /tmp/pull-secret.json)"

# Clean up the temporary file
rm /tmp/pull-secret.json
```

## Troubleshooting

Common issues with Vault integration and their solutions:

1. **Connection Failures**:
   - Verify Vault server is running and accessible
   - Check VAULT_ADDR is correct with proper protocol (http/https)
   - Ensure network connectivity to the Vault server

2. **Authentication Failures**:
   - Verify token is valid and not expired
   - For AppRole, check that role_id and secret_id are correct
   - Check that authentication method is properly enabled on Vault server

3. **Permission Denied**:
   - Verify token has appropriate policies for the requested operation
   - Check path is correct including mount point and prefix

4. **Secret Not Found**:
   - Ensure the secret path is correct
   - Verify the secret exists in Vault
   - For KV v2, ensure you're using the correct path structure (data/ vs metadata/)

5. **Token Expiration**:
   - Ensure token is renewable if long-lived access is needed
   - Implement token renewal logic for long-running applications
   - VaultComponent includes automatic token status checking and renewal

## Security Considerations

When using Vault in this project, consider these security aspects:

1. **Production Deployments**: Use TLS for Vault communications
2. **Token Management**: Store tokens securely and rotate regularly
3. **Audit Logging**: Enable audit logging in Vault for production environments
4. **Backup**: Ensure proper Vault backup procedures are in place
5. **Unsealing**: Have a secure process for unsealing Vault after restarts
