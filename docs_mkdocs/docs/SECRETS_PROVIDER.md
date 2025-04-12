<div align="center">
  <img src="assets/images/r630-iscsi-switchbot-new-logo.png" alt="R630 iSCSI SwitchBot Logo" width="150">
</div>

# Secrets Provider System

This document explains the secrets provider system that has been implemented to securely manage sensitive information in the OpenShift deployment process.

## Overview

The secrets provider system is an abstraction layer that handles secrets management through different backends. It allows the system to:

1. **Securely store secrets** in different storage backends
2. **Reference secrets** in configuration files without including their actual values
3. **Isolate sensitive information** from the codebase and configuration repositories
4. **Provide a migration path** to more robust secrets management solutions like HashiCorp Vault

## Architecture

The secrets provider is designed as an abstracted interface with pluggable backends:

```
┌─────────────────┐     ┌───────────────────┐     ┌────────────────────┐
│ Configuration   │     │ Secrets Provider  │     │ Storage Backends   │
│ with References │────▶│ Interface        │────▶│ (File/TrueNAS/Vault)│
└─────────────────┘     └───────────────────┘     └────────────────────┘
```

### Current Backends

1. **File Backend** (Default): Stores secrets in the local filesystem
   - Path: `~/.openshift/secrets/`
   - Simple and easy to use for development

2. **TrueNAS Backend**: Stores secrets on a TrueNAS server
   - Path: `/mnt/tank/openshift_secrets/`
   - Good for persistent storage in the lab environment

3. **Vault Backend** (Planned): Will store secrets in HashiCorp Vault
   - Provides enterprise-grade security features
   - Supports access control, auditing, and versioning

## Using Secret References

Configuration files can reference secrets using a special syntax:

```yaml
# Example OpenShift values file with secret references
apiVersion: v1
baseDomain: example.com
# ...other configuration...

# Reference secrets that will be injected
secretReferences:
  pullSecret: ${secret:openshift/pull-secret}
  sshKey: ${secret:openshift/ssh-key}
```

The format for secret references is:
- `${secret:path/to/secret}` - Simple secret reference
- `${secret:path/to/secret:key}` - Reference a key in a structured secret (JSON)

## CLI Interface

The secrets provider comes with a command-line interface for managing secrets:

```bash
# Get a secret
./scripts/secrets_provider.py get openshift/pull-secret

# Store a secret
./scripts/secrets_provider.py put openshift/ssh-key --file ~/.ssh/id_rsa.pub

# Check or set the provider type
./scripts/secrets_provider.py provider
./scripts/secrets_provider.py provider --type truenas
```

## Environment Variables

The system can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRETS_PROVIDER` | The backend provider to use | `file` |
| `LOCAL_SECRETS_DIR` | Directory for file-based secrets | `~/.openshift/secrets` |
| `TRUENAS_IP` | IP address of TrueNAS server | `192.168.2.245` |
| `TRUENAS_USER` | Username for TrueNAS SSH access | `root` |
| `TRUENAS_SECRETS_PATH` | Path on TrueNAS for secrets | `/mnt/tank/openshift_secrets` |

## Integration with GitHub Actions

The GitHub Actions workflow integrates with the secrets provider:

1. It sets up the secrets provider with GitHub Secrets as inputs
2. Stores OpenShift pull secret and SSH key in the local provider
3. Process any secret references in the values file
4. Backs up configurations to TrueNAS (with sensitive data sanitized)
5. Cleans up sensitive files after the workflow completes

## Migration to HashiCorp Vault

To migrate to HashiCorp Vault in the future:

1. Set up a Vault server and configure access
2. Import existing secrets into Vault
3. Implement the Vault backend in the secrets provider
4. Update environment variables to use Vault instead of file/TrueNAS

No changes to configuration files or workflows would be needed, as they use the abstraction layer through secret references.

## Security Considerations

- **Never commit** files containing secrets to Git
- The `.gitignore` file excludes patterns like `*secret*` and `*credential*`
- When using the TrueNAS backend, access controls should be configured on the TrueNAS server
- The system includes sanitization for logs and artifacts to prevent accidental exposure
- The GitHub Actions workflow includes cleanup steps to remove sensitive files
