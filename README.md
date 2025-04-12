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
- **TrueNAS Integration**: iSCSI storage provisioning and management
- **Secrets Management**: Secure handling of sensitive information
- **GitHub Actions Workflows**: Automated CI/CD for deployment processes
- **Multi-Server Deployment Tracking**: Management of deployments across multiple R630 servers

## Documentation

Comprehensive documentation is available in two formats:

1. **Markdown files** in the `docs/` directory for direct GitHub viewing
2. **MkDocs site** for a more polished documentation experience (generated from `docs_mkdocs/`)

Key documentation files:

- [Deployment Tracking](docs/DEPLOYMENT_TRACKING.md): Managing multiple servers and deployments
- [OpenShift Values System](docs/OPENSHIFT_VALUES_SYSTEM.md): Configuration management
- [GitHub Actions Usage](docs/GITHUB_ACTIONS_USAGE.md): Setting up workflows
- [TrueNAS Authentication](docs/TRUENAS_AUTHENTICATION.md): Storage setup
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md): Common issues and solutions

## Getting Started

To use this system in your own environment:

1. Clone this repository
2. Set up TrueNAS Scale with iSCSI support
3. Configure your R630 server(s) for iSCSI boot
4. Set up GitHub Actions for automation (optional)
5. Generate your first OpenShift configuration:

```bash
./scripts/generate_openshift_values.py \
  --node-ip 192.168.2.230 \
  --server-id 01 \
  --cluster-name sno \
  --base-domain lab.local
```

6. Run a deployment:

```bash
./scripts/finalize_deployment.sh \
  --server-id 01 \
  --deployment-name sno
```

## Learning and Inspiration

This project may serve as inspiration for your own lab setup or enterprise deployment system. Feel free to explore the code, adapt it to your needs, and learn from the implementation.
