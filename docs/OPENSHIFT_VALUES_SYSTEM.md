# OpenShift Values System

This document explains the OpenShift values system that simplifies the configuration and deployment of OpenShift clusters, particularly Single-Node OpenShift (SNO) deployments.

## Overview

The OpenShift values system provides a structured way to define and manage configuration parameters for OpenShift installations. It offers several advantages:

1. **Standardized Configuration**: Consistent format for all OpenShift installations
2. **Reusability**: Easily reuse configurations across multiple deployments
3. **Version Control**: Track changes to configurations in Git
4. **CI/CD Integration**: Use configurations in automated pipelines with GitHub Actions
5. **Simplified Updates**: Central location to update parameters

## Values File Format

The values file follows the OpenShift install-config.yaml format with additional sections for SNO-specific configuration. It includes:

- Basic cluster information (name, domain)
- Networking configuration
- Single-node specifics (node IP, API VIP, Ingress VIP)
- Storage configuration

Example:

```yaml
apiVersion: v1
baseDomain: intranet.lab
compute:
- architecture: amd64
  hyperthreading: Enabled
  name: worker
  replicas: 0  # SNO has 0 worker nodes
controlPlane:
  architecture: amd64
  hyperthreading: Enabled
  name: master
  replicas: 1  # SNO has 1 master node
metadata:
  name: r630-sno
networking:
  clusterNetwork:
  - cidr: 10.128.0.0/14
    hostPrefix: 23
  machineNetwork:
  - cidr: 192.168.2.0/24
  networkType: OVNKubernetes
  serviceNetwork:
  - 172.30.0.0/16
platform:
  none: {}
publish: External
sno:
  nodeIP: 192.168.2.230
  apiVIP: 192.168.2.231
  ingressVIP: 192.168.2.232
  domain: apps.r630-sno.intranet.lab
  hostname: sno
```

## Generating Values Files

The `generate_openshift_values.py` script helps create customized values files:

```bash
./scripts/generate_openshift_values.py \
  --node-ip 192.168.2.230 \
  --cluster-name r630-sno \
  --base-domain intranet.lab
```

### Script Options

- `--cluster-name`: Name of the cluster (default: sno)
- `--base-domain`: Base domain for the cluster (default: example.com)
- `--hostname`: Hostname for the single node (default: sno)
- `--node-ip`: IP address of the single node (**required**)
- `--api-vip`: Virtual IP for the API server (default: node_ip + 1)
- `--ingress-vip`: Virtual IP for the ingress controller (default: node_ip + 2)
- `--output-dir`: Output directory (default: config directory)

The script will generate a values file named `openshift_install_values_<cluster-name>.yaml` in the config directory.

## Using Values Files with ISO Generation

### CLI Usage

You can use a values file with the ISO generation script:

```bash
./scripts/generate_openshift_iso.py \
  --version 4.18 \
  --rendezvous-ip 192.168.2.230 \
  --values-file config/openshift_install_values_r630-sno.yaml
```

When a values file is provided, it takes precedence over command-line arguments for parameters like domain and network settings.

### GitHub Actions Workflow

The GitHub Actions workflow supports values files:

```yaml
name: Generate ISO with Values File

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'OpenShift version'
        default: '4.18'
      values_file:
        description: 'Values file name (in config directory)'
        default: 'openshift_install_values_r630-sno.yaml'
```

You can trigger the workflow from the GitHub UI or using the GitHub CLI:

```bash
gh workflow run generate_iso.yml \
  -f version="4.18" \
  -f values_file="openshift_install_values_r630-sno.yaml"
```

Or generate values and run the workflow in one command:

```bash
# Generate values file
./scripts/generate_openshift_values.py --node-ip 192.168.2.230 --cluster-name r630-sno

# Trigger workflow with the generated values file
gh workflow run generate_iso.yml \
  -f version="4.18" \
  -f values_file="openshift_install_values_r630-sno.yaml"
```

## Values File Locations

The scripts will look for values files in the following locations:

1. Path specified in the `--values-file` argument
2. `config/openshift_install_values_<cluster-name>.yaml`

## Advanced Usage: Customizing Values Files

While the generator script creates standard values files, you can manually edit them to:

1. Add custom network configurations
2. Configure storage for the cluster
3. Set up additional authentication methods
4. Configure proxy settings
5. Define custom manifests

After editing, you can use the customized values file with the ISO generation process as described above.

## Integration with finalize_deployment.sh

The finalize_deployment.sh script has been updated to work with the values system:

```bash
# Generate values file for each OpenShift version
./scripts/generate_openshift_values.py --node-ip 192.168.2.230 --cluster-name r630-4.18

# Run deployment with values file
./scripts/finalize_deployment.sh --values-file openshift_install_values_r630-4.18.yaml
```

This ensures consistent configuration across different OpenShift versions and deployments.
