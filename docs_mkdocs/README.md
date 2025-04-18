<div align="center">
  <img src="docs/assets/images/r630-iscsi-switchbot-banner.png" alt="R630 iSCSI SwitchBot Banner" width="100%">
  
  # OpenShift Multiboot System
  
  <img src="docs/assets/images/r630-iscsi-switchbot-new-logo.png" alt="R630 iSCSI SwitchBot Logo" width="250">
</div>

## Personal Sandbox Project by Bart van den Heuvel

This project is an Omnisack sandbox project created by Bart van den Heuvel to make a super cool lab environment. It's intended for others to see, enjoy, and maybe grab a few ideas from. This is a personal project for maintaining a lab environment and learning interesting things, rather than an official product.

## Overview

The Dell PowerEdge R630 OpenShift Multiboot System enables flexible deployment and switching between different OpenShift installations on Dell PowerEdge R630 servers using iSCSI storage. This solution provides administrators with the ability to:

- Instantly switch between different OpenShift versions
- Utilize network boot, local ISO, or iSCSI storage boot options
- Manage OpenShift deployments through a streamlined automation interface
- Securely store and manage configuration secrets

## Key Components

- **Multiboot System**: Switch between multiple OpenShift versions
- **Netboot Support**: Network boot capabilities for quick deployments
- **TrueNAS Integration**: iSCSI storage provisioning and management
- **Secrets Management**: Secure handling of sensitive information
- **GitHub Actions Workflows**: Automated CI/CD for deployment processes
- **Multi-Server Deployment Tracking**: Management of deployments across multiple R630 servers

## Security Features

The system includes robust security features such as:

- **Secrets Provider System**: Abstract secrets management with multiple backends
- **Secret References**: Reference secrets in configuration without exposing sensitive data
- **Configuration Sanitization**: Safe storage of configurations with sensitive data redacted
- **Self-hosted CI/CD**: Actions run on private, secure infrastructure

## Documentation

This documentation covers all aspects of the system:

- Implementation details for Multiboot and Netboot strategies
- Configuration guides for TrueNAS and OpenShift
- Security considerations and best practices
- Testing methodologies and results
- Troubleshooting guides and FAQs
- Deployment tracking across multiple servers

## Getting Started

Navigate to the sections in the sidebar to learn about specific components of the system:

- [Multiboot Implementation](docs/MULTIBOOT_IMPLEMENTATION.md)
- [Netboot Implementation](docs/NETBOOT_IMPLEMENTATION.md)
- [TrueNAS Authentication](docs/TRUENAS_AUTHENTICATION.md)
- [Secrets Provider System](docs/SECRETS_PROVIDER.md)
- [Deployment Tracking](docs/DEPLOYMENT_TRACKING.md)
