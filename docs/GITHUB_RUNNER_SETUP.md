# GitHub Runner Setup Guide

This document provides instructions for setting up a local GitHub Actions runner and configuring the required secrets for the R630 iSCSI SwitchBot project.

## Setting Up a Local GitHub Runner

Our test has detected that a local GitHub runner is not active. Here's how to set up and configure a runner:

### 1. Create a Runner in GitHub

1. Navigate to your GitHub repository (`zokahn/r630-iscsi-switchbot`)
2. Go to **Settings** > **Actions** > **Runners**
3. Click **New self-hosted runner**
4. Select **Linux** and **x64** architecture
5. Follow the download and configuration instructions provided by GitHub

### 2. Configure and Start the Runner

Execute the provided commands to download, configure, and start the runner:

```bash
# Create a folder for the runner
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download the runner package
curl -o actions-runner-linux-x64-2.312.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.312.0/actions-runner-linux-x64-2.312.0.tar.gz

# Extract the installer
tar xzf ./actions-runner-linux-x64-2.312.0.tar.gz

# Configure the runner with the expected name
./config.sh --url https://github.com/zokahn/r630-iscsi-switchbot --token YOUR_TOKEN --name r630-switchbot-runner

# Start the runner
./run.sh
```

Replace `YOUR_TOKEN` with the token provided in the GitHub runner setup page.

> **IMPORTANT**: The runner must be named `r630-switchbot-runner` as this is the name expected by our test scripts and configuration.

### 3. Install the Runner as a Service (Optional but Recommended)

To run the GitHub Actions runner as a service:

```bash
# Install the service
sudo ./svc.sh install

# Start the service
sudo ./svc.sh start

# Check status
sudo ./svc.sh status
```

### 4. Add Required Labels

Our workflows expect the runner to have the `self-hosted` label. This should be added automatically during setup, but you can verify it in the GitHub UI.

## Setting Up Required Secrets

Our test detected missing secrets that are required for the workflows to function properly. Here's how to set them up:

### 1. OpenShift Pull Secret

1. Visit [Red Hat OpenShift Cluster Manager](https://console.redhat.com/openshift/install/pull-secret)
2. Log in with your Red Hat account
3. Download or copy your pull secret (JSON format)
4. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**
5. Create a new repository secret:
   - Name: `OPENSHIFT_PULL_SECRET`
   - Value: Paste the entire JSON content of your pull secret

### 2. TrueNAS SSH Key

Generate an SSH key for TrueNAS access and add it as a secret:

```bash
# Generate a new key
ssh-keygen -t ed25519 -f truenas_key -N ""

# Copy the public key to TrueNAS
ssh-copy-id -i truenas_key.pub root@192.168.2.245

# Add the private key as a secret
cat truenas_key
```

1. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**
2. Create a new repository secret:
   - Name: `TRUENAS_SSH_KEY`
   - Value: Copy the entire content of the private key file (`truenas_key`)

### 3. TrueNAS Known Hosts

Generate a known hosts entry for TrueNAS and add it as a secret:

```bash
# Generate the known hosts entry
ssh-keyscan -H 192.168.2.245
```

1. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**
2. Create a new repository secret:
   - Name: `TRUENAS_KNOWN_HOSTS`
   - Value: Copy the output from the ssh-keyscan command

## Verification

After completing the setup steps above, run the test script again to verify everything is working correctly:

```bash
./scripts/test_github_actions.sh
```

## Committing and Pushing the Workflows

Our newly created workflow files need to be pushed to GitHub:

```bash
# Add the workflow files
git add .github/workflows/generate_iso.yml
git add .github/workflows/test_integration.yml
git add scripts/test_github_actions.sh
git add scripts/finalize_deployment.sh
git add docs/GITHUB_ACTIONS_USAGE.md
git add docs/GITHUB_RUNNER_SETUP.md

# Commit the changes
git commit -m "Add GitHub Actions workflows for ISO generation and testing"

# Push to GitHub
git push origin main
```

After pushing, verify that the workflows appear in the **Actions** tab of your GitHub repository.

## Testing the Workflows

Once everything is set up, you can test the workflows:

```bash
# Test the ISO generation workflow with skip_upload set to true
gh workflow run generate_iso.yml -f version="4.18" -f rendezvous_ip="192.168.2.230" -f truenas_ip="192.168.2.245" -f skip_upload="true"

# Test the integration test workflow
gh workflow run test_integration.yml -f server_ip="192.168.2.230" -f truenas_ip="192.168.2.245"
```

Or use the full deployment script:

```bash
./scripts/finalize_deployment.sh
```
