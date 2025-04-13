# TrueNAS Scale Authentication Guide

This document explains the authentication methods for TrueNAS Scale with a focus on API-based authentication used in our OpenShift multiboot system.

## Authentication Methods

TrueNAS Scale supports several authentication methods:

1. **Web UI Authentication**: Interactive login using username/password
2. **API Authentication**: REST API access using either:
   - Username/password (Basic Authentication)
   - API keys (Bearer Authentication)

Our scripts exclusively use the REST API authentication with API keys as it's the most suitable for automation.

## Setting Up API Key Authentication (Required)

API keys provide a secure way to authenticate without storing passwords in scripts or exposing them in command-line arguments.

### Creating an API Key

1. Log in to the TrueNAS Scale web interface (typically https://your-truenas-ip)
2. Navigate to the user menu (top right) → "My API Keys"
3. Click "Add"
4. Provide the following information:
   - Name: "OpenShift Multiboot Automation"
   - Expiration date (optional): Set an expiration for security
   - IP addresses (optional): Restrict to specific client IPs for added security
5. Click "Save"
6. Copy the generated API key and store it securely

### API Documentation

The TrueNAS SCALE API documentation is available at:
- https://your-truenas-ip/api/docs/

You can use this documentation to explore available endpoints and test API calls directly.

### Using the API Key with Our Scripts

Once you have an API key, you can use it with our scripts:

```bash
# Create iSCSI target using API
./scripts/create_iscsi_target_api.py --server-id 01 --hostname my-server --api-key "YOUR_API_KEY_HERE"

# Integrate with OpenShift
./scripts/integrate_iscsi_openshift.py --server-id 01 --hostname my-server --node-ip 192.168.1.100 --mac-address 00:11:22:33:44:55 --truenas-api-key "YOUR_API_KEY_HERE"
```

## Creating a Secure Authentication File

For convenience and security, you can create a configuration file for authentication:

1. Create a file in a secure location (with restricted permissions):

```bash
mkdir -p ~/.config/truenas
touch ~/.config/truenas/auth.json
chmod 600 ~/.config/truenas/auth.json
```

2. Add your authentication information:

```json
{
  "host": "192.168.2.245",
  "api_key": "YOUR_API_KEY_HERE"
}
```

3. Create a wrapper script to use this configuration:

```bash
#!/bin/bash
# truenas_wrapper.sh

AUTH_FILE="$HOME/.config/truenas/auth.json"

if [ ! -f "$AUTH_FILE" ]; then
  echo "Authentication file not found: $AUTH_FILE"
  exit 1
fi

# Extract host and API key from JSON
HOST=$(jq -r '.host' < "$AUTH_FILE")
API_KEY=$(jq -r '.api_key' < "$AUTH_FILE")

# Pass to the actual script
./scripts/create_iscsi_target_api.py --truenas-ip "$HOST" --api-key "$API_KEY" "$@"
```

## Port and Protocol Configuration

TrueNAS SCALE typically serves its web interface and API on the following ports:

- HTTP: Port 80 (default insecure)
- HTTPS: Port 443 (default secure)

However, some installations may use custom port configurations:

- Our specific installation uses **HTTPS on port 444**
- You can use the `scripts/test_truenas_connection.py` script to detect the correct settings:
  ```bash
  ./scripts/test_truenas_connection.py --host 192.168.2.245 --api-key "YOUR_API_KEY"
  ```

## Admin Access Best Practices

1. **Use API keys** instead of username/password authentication
2. **Rotate API keys** periodically (every 90 days)
3. **Set expiration dates** for API keys to limit their validity period
4. **Use a dedicated user account** instead of `root` when possible
5. **Enable 2FA** for web UI access
6. **Store credentials securely** (encrypted when at rest)
7. **Use restrictive file permissions** on any files containing credentials
8. **Keep credentials out of version control** (use the .gitignore file)
9. **Restrict API keys by IP address** when possible

## Credential Handling and Version Control

The repository includes a `.gitignore` file configured to prevent sensitive data from being committed to version control:

```
# TrueNAS authentication files
.truenas_auth
.truenas_config
*auth.json
*credentials.json
.config/truenas/

# API keys and sensitive data
*.key
*.pem
*.crt
*api_key*
*apikey*
*secret*
*password*
*credential*
```

When using the secure authentication file approach, your credentials will be stored in `~/.config/truenas/auth.json` which is automatically excluded from git. This ensures your sensitive information stays secure and local to your machine.

### Recommended Workflow for Teams

If working with a team:

1. **Never commit real credentials** to the repository
2. Use environment variables or secure credential storage whenever possible
3. Provide example configuration files with placeholders instead of real values
4. Document the credential setup process for other team members

## Credential Management in Scripts

Our implementation handles credentials in the following ways:

1. **No hardcoded credentials** in any script
2. **API key support** for secure non-interactive authentication
3. **Environment variable support** for CI/CD integration

## Testing Authentication

To verify your authentication is working correctly:

```bash
# Test API authentication with a discovery-only operation
./scripts/create_iscsi_target_api.py --truenas-ip 192.168.2.245 --api-key "YOUR_API_KEY" --discover-only
```

## Troubleshooting

If you encounter authentication issues:

1. **API key errors**:
   - Verify the API key is correct and not expired
   - Ensure the API key has the necessary permissions

2. **Connection issues**:
   - Verify TrueNAS is running and accessible
   - Check the port configuration
   - Ensure there are no network blocks or firewall issues

3. **Permission denied errors**:
   - Verify you're using an account with administrative privileges
   - Check the API key permissions on TrueNAS Scale
