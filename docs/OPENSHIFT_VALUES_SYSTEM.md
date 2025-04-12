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
  hostname: humpty
  # Network interface configuration
  interface: eno2
  macAddress: e4:43:4b:44:5b:10
  useDhcp: true
  dnsServers:
    - 192.168.2.254
bootstrapInPlace:
  installationDisk: "/dev/disk/by-id/scsi-SIBM-207x_ST600MM0088_W420JEKL0000E7428HZB"
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

## Network Interface Configuration

The values system now supports detailed network interface configuration for the OpenShift agent-based installer. These options allow you to precisely define how the network interface should be configured:

```yaml
sno:
  # Basic SNO configuration
  nodeIP: 192.168.2.230
  apiVIP: 192.168.2.231
  ingressVIP: 192.168.2.232
  
  # Network interface configuration
  interface: eno2             # Network interface name (e.g., eno1, eno2, eth0)
  macAddress: e4:43:4b:44:5b:10  # MAC address for DHCP reservations
  useDhcp: true              # Whether to use DHCP (true) or static IP (false)
  prefixLength: 24           # Subnet mask as prefix length (for static IP)
  dnsServers:                # DNS servers
    - 192.168.2.254
```

These options control how the agent-config.yaml file is generated, which follows the NMState format expected by the OpenShift installer. The configuration is translated into the proper format required by the OpenShift agent-based installer.

## Bootstrap-in-Place Disk Configuration

For Single-Node OpenShift (SNO) deployments, you must specify the disk to use for the installation. The bootstrapInPlace section allows you to define the target installation disk:

```yaml
bootstrapInPlace:
  installationDisk: "/dev/disk/by-id/scsi-SIBM-207x_ST600MM0088_W420JEKL0000E7428HZB"
```

It's recommended to use persistent disk identifiers from `/dev/disk/by-id/` rather than device names like `/dev/sda` to ensure consistency across reboots. You can find the disk ID using commands like:

```bash
ls -la /dev/disk/by-id/
```

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

## Multi-Server Deployment Tracking

For environments with multiple R630 servers, we've added server identifier support:

```bash
# Generate values file with server ID
./scripts/generate_openshift_values.py \
  --node-ip 192.168.2.230 \
  --cluster-name sno \
  --server-id 01 \
  --base-domain intranet.lab

# Run deployment with server tracking
./scripts/finalize_deployment.sh \
  --server-id 01 \
  --deployment-name sno \
  --values-file config/deployments/r630-01/r630-01-sno-20250412155030.yaml
```

The system will:
1. Generate server-specific configuration files in `config/deployments/r630-XX/`
2. Create timestamped log files for each deployment 
3. Store deployment artifacts (logs, kubeconfigs) on TrueNAS for future reference

For more details, see [Deployment Tracking](DEPLOYMENT_TRACKING.md).
