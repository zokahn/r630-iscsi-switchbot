# Using GitHub Actions for OpenShift ISO Generation and Testing

This document explains how to use GitHub Actions to generate OpenShift ISOs on x86_64 runners and run integration tests, which is particularly useful when developing on non-x86_64 machines (like Apple Silicon Macs).

## Why Use GitHub Actions?

The OpenShift installer is designed for x86_64 architectures, and running it on ARM-based systems (like Apple Silicon Macs) can be problematic and slow. By leveraging GitHub Actions:

1. ISOs are generated on x86_64 GitHub-hosted or self-hosted runners
2. The process is faster and more reliable
3. We avoid architecture compatibility issues
4. The generated ISOs can be uploaded directly to TrueNAS
5. Integration tests can be run automatically

## Prerequisites

Before using the GitHub Actions workflow, ensure you have:

1. **GitHub CLI Installed**:
   ```bash
   # macOS (Homebrew)
   brew install gh
   
   # Linux
   sudo apt install gh
   ```

2. **GitHub CLI Authenticated**:
   ```bash
   gh auth login
   ```

3. **Required GitHub Secrets Set Up**:
   - `OPENSHIFT_PULL_SECRET`: Your Red Hat OpenShift pull secret
   - `TRUENAS_SSH_KEY`: SSH private key for TrueNAS access
   - `TRUENAS_KNOWN_HOSTS`: Known hosts entry for TrueNAS server

## How to Configure GitHub Secrets

1. Go to your GitHub repository settings
2. Navigate to "Secrets and variables" → "Actions"
3. Add the following repository secrets:

   - **OPENSHIFT_PULL_SECRET**:
     - Content: Your OpenShift pull secret (from https://console.redhat.com/openshift/install/pull-secret)
     - Format: JSON string

   - **TRUENAS_SSH_KEY**:
     - Content: SSH private key for TrueNAS access
     - To generate:
       ```bash
       ssh-keygen -t ed25519 -f truenas_key -N ""
       # Then copy the public key to TrueNAS
       ssh-copy-id -i truenas_key.pub root@192.168.2.245
       # Use the private key content for the secret
       cat truenas_key
       ```

   - **TRUENAS_KNOWN_HOSTS**:
     - Content: SSH known hosts entry for TrueNAS
     - To generate:
       ```bash
       ssh-keyscan -H 192.168.2.245
       ```

## Available Workflows

This repository includes the following GitHub Actions workflows:

1. **generate_iso.yml**: Generates OpenShift ISOs for deployment
2. **test_integration.yml**: Runs integration tests on the system components

## Setting Up a Self-Hosted Runner (Optional but Recommended)

Using a self-hosted x86_64 runner provides the best performance for ISO generation and testing. To set up a local runner:

1. **In GitHub**:
   - Go to your repository settings
   - Navigate to "Actions" → "Runners"
   - Click "New self-hosted runner"
   - Select "Linux" and "x64" architecture
   - Follow the instructions to download and configure the runner

2. **Important Labels**:
   - Make sure your runner has the `self-hosted` label
   - This is required for our workflows to target your local runner

3. **Verify your runner**:
   - Run our test script to check runner status:
   ```bash
   ./scripts/test_github_actions.sh
   ```

## Using the Workflows

### Method 1: Using finalize_deployment.sh

The simplest way to use the GitHub Actions workflows is through the updated `finalize_deployment.sh` script, which automatically:

1. Detects if a local runner is available
2. Triggers the workflow for each OpenShift version
3. Monitors workflow progress
4. Runs integration tests
5. Verifies the ISOs are available on TrueNAS

```bash
./scripts/finalize_deployment.sh
```

### Method 2: Manually Triggering Workflows

You can also manually trigger workflows using the GitHub CLI:

```bash
# Get your repository name
REPO_NAME=$(git remote get-url origin | sed -n 's/.*github.com[:/]\(.*\).git/\1/p')

# Trigger the ISO generation workflow for OpenShift 4.18
gh workflow run generate_iso.yml -R "$REPO_NAME" \
  -f version="4.18" \
  -f rendezvous_ip="192.168.2.230" \
  -f truenas_ip="192.168.2.245"

# Trigger the integration test workflow
gh workflow run test_integration.yml -R "$REPO_NAME" \
  -f server_ip="192.168.2.230" \
  -f truenas_ip="192.168.2.245"
```

Or through the GitHub web interface:

1. Go to the "Actions" tab in your repository
2. Select "Generate OpenShift ISOs" workflow
3. Click "Run workflow"
4. Enter parameters:
   - Version (e.g., 4.18)
   - Rendezvous IP (e.g., 192.168.2.230)
   - TrueNAS IP (e.g., 192.168.2.245)
   - Skip upload (optional)
5. Click "Run workflow"

## Testing Workflow Setup

We provide a test script to verify your GitHub Actions setup:

```bash
./scripts/test_github_actions.sh
```

This script:
- Checks if GitHub CLI is installed and authenticated
- Verifies workflow files exist
- Detects if a local runner is active
- Validates required GitHub secrets
- Lists available workflows
- Provides commands for testing workflows

## Workflow Outputs

The workflows produce the following outputs:

### ISO Generation Workflow
1. **GitHub Artifacts**: The ISO is uploaded as a GitHub artifact, available for 7 days
2. **TrueNAS Upload**: The ISO is uploaded to TrueNAS at `/mnt/tank/openshift_isos/{version}/agent.x86_64.iso`
3. **HTTP Access**: The ISO is accessible via HTTP at `http://{truenas_ip}/openshift_isos/{version}/agent.x86_64.iso`

### Integration Test Workflow
1. **Test Results**: The workflow outputs the results of various system component tests
2. **Workflow Logs**: Detailed logs of all test steps available in GitHub Actions UI

## Troubleshooting

If the workflow fails, check:

1. **Workflow Logs**: Examine the workflow logs in GitHub Actions for error messages
2. **Secret Values**: Verify that all secrets are correctly set up
3. **TrueNAS Connectivity**: Ensure the TrueNAS server is accessible from GitHub Actions runners
4. **SSH Key Permissions**: Verify the SSH key has proper permissions on TrueNAS

If you need to debug the workflow locally, you can use the following approach:

```bash
# Run the script with the --skip-upload flag to test ISO generation without uploading
./scripts/generate_openshift_iso.py --version 4.18 --rendezvous-ip 192.168.2.230 --skip-upload
```

## Conclusion

Using GitHub Actions for OpenShift ISO generation provides a reliable, architecture-independent method to prepare ISOs for deployment on Dell PowerEdge R630 servers. This approach is especially valuable for developers using non-x86_64 machines like Apple Silicon Macs.
