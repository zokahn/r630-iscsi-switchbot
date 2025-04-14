# MinIO Dual-Bucket Setup for OpenShift ISOs

This document provides detailed instructions for implementing the dual-bucket strategy in MinIO for OpenShift ISO storage.

## Architecture Overview

The implementation uses two distinct buckets:

1. **Private Bucket (r630-switchbot-private)**
   - Authenticated access only
   - Versioned storage with timestamps
   - Complete history with metadata
   - Used by administrative tools

2. **Public Bucket (r630-switchbot-public)**
   - Anonymous read access
   - Latest ISOs only with predictable URLs
   - Designed for PXE/iDRAC access
   - Minimalist structure

```
┌───────────────────────────┐                          ┌───────────────────┐
│  r630-switchbot-private   │                          │     R630 Servers  │
│                           │                          │                   │
│ ┌─────────────────────┐   │      ┌─────────────┐     │ ┌───────────────┐ │
│ │ ISO with Timestamps │   │      │             │     │ │ PXE Boot      │ │
│ │ server-01-humpty-   │   │      │   SYNC      │     │ │ Uses Public   │ │
│ │ 4.18.0-20250414.iso │──────────┤   PROCESS   │     │ │ ISO URLs      │ │
│ └─────────────────────┘   │      │             │     │ └───────────────┘ │
│                           │      └─────────────┘     │                   │
│ ┌─────────────────────┐   │            │             │ ┌───────────────┐ │
│ │ Versioned Storage   │   │            │             │ │ iDRAC Virtual │ │
│ │ with Metadata       │   │            │             │ │ Media Access  │ │
│ └─────────────────────┘   │            ▼             │ └───────────────┘ │
└───────────────────────────┘     ┌─────────────────┐  └───────────────────┘
                                  │ r630-switchbot- │  
                                  │     public      │         ┌───────────┐
                                  │                 │         │   Other   │
                                  │ ┌─────────────┐ │         │  Systems  │
                                  │ │ Predictable │ │         │           │
                                  │ │ URLs        │ │◄────────┤ Anonymous │
                                  │ │ 4.18/agent. │ │         │ Access    │
                                  │ │ x86_64.iso  │ │         │           │
                                  │ └─────────────┘ │         └───────────┘
                                  └─────────────────┘
```

## Discovery-Process-Housekeeping Pattern

Each operation in the setup follows a standardized pattern:

1. **Discovery Phase**: Examine the current environment
   - Check MinIO connectivity and credentials
   - Inventory existing buckets and objects
   - Discover OpenShift environment components

2. **Processing Phase**: Perform required operations
   - Create and configure buckets
   - Upload, sync, or manage objects
   - Apply bucket policies

3. **Housekeeping Phase**: Verify and finalize
   - Validate configurations
   - Perform cleanup operations
   - Provide usage guidance

## Setup and Configuration

### Prerequisites

- Running MinIO server (e.g., scratchy.omnisack.nl)
- Admin access to create buckets and policies
- Python 3.6+ with required packages:
  - `pip install minio python-dotenv`
- Environment file with S3 credentials

### Initial Environment Setup

Create a `.env` file in the project root with the following content:

```
S3_ENDPOINT=scratchy.omnisack.nl
S3_ACCESS_KEY=your_access_key_here
S3_SECRET_KEY=your_secret_key_here
S3_BUCKET=r630-switchbot-private
```

### Setting up Buckets

```bash
# Discover current MinIO environment only
./scripts/setup_minio_buckets.py --discover

# Setup both buckets with proper policies
./scripts/setup_minio_buckets.py --setup

# Force reconfiguration of existing buckets
./scripts/setup_minio_buckets.py --setup --force
```

### Bucket Configuration Details

The private bucket uses standard authenticated access with versioning enabled, while the public bucket has a policy that allows anonymous read-only access to ISO files.

Public bucket policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "*"},
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::r630-switchbot-public/isos/*"]
    }
  ]
}
```

## Usage Examples

### Uploading ISOs

```bash
# Upload ISO to private bucket only
./scripts/setup_minio_buckets.py --upload /path/to/openshift.iso \
  --server-id 01 --hostname humpty --version 4.18.0 --no-publish

# Upload ISO to private bucket and sync to public
./scripts/setup_minio_buckets.py --upload /path/to/openshift.iso \
  --server-id 01 --hostname humpty --version 4.18.0
```

The upload process:
1. Calculates MD5 hash for integrity verification
2. Uploads to private bucket with timestamp and metadata
3. Optionally syncs to public bucket with standardized naming
4. Verifies public access if published

### Managing Public Access

```bash
# Sync an existing ISO from private to public
./scripts/setup_minio_buckets.py --sync \
  --private-path isos/server-01-humpty-4.18.0-20250414.iso \
  --version 4.18.0

# Remove an ISO from public access
./scripts/setup_minio_buckets.py --unpublish \
  --version 4.18.0

# Verify public access to an ISO
./scripts/setup_minio_buckets.py --verify \
  --version 4.18.0
```

### Accessing ISOs

Private bucket (authenticated):
```
s3://r630-switchbot-private/isos/server-01-humpty-4.18.0-20250414.iso
```

Public bucket (anonymous):
```
http://scratchy.omnisack.nl/r630-switchbot-public/isos/4.18/agent.x86_64.iso
```

### Housekeeping Operations

```bash
# Clean up ISOs older than 365 days (default)
./scripts/setup_minio_buckets.py --cleanup

# Clean up ISOs older than 90 days
./scripts/setup_minio_buckets.py --cleanup --days 90

# Clean up only specific prefixes
./scripts/setup_minio_buckets.py --cleanup --prefix isos/ --days 180
```

## Integration with Other Tools

### PXE Configuration

Add the following to your PXE configuration to boot from the public ISO:

```
menuentry "OpenShift 4.18" {
  linux (http)/scratchy.omnisack.nl/r630-switchbot-public/isos/4.18/agent.x86_64.iso
}
```

### iDRAC Virtual Media

Configure Virtual Media in iDRAC with:

1. Access the iDRAC web interface
2. Navigate to **Virtual Media**
3. Select **Connect Virtual Media**
4. Enter the ISO URL: `http://scratchy.omnisack.nl/r630-switchbot-public/isos/4.18/agent.x86_64.iso`
5. Click **Connect**

### Integration with Existing Scripts

The `generate_minimal_iso.py` script has been enhanced to integrate with the dual-bucket system:

```bash
# Generate ISO and upload with auto-publish
./scripts/generate_minimal_iso.py --config config/deployments/r630-01-config.yaml \
  --use-s3 --s3-dual-bucket
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Check your S3 credentials in the `.env` file
   - Verify MinIO server is running and accessible

2. **Public Access Not Working**:
   - Verify bucket policy is correctly set
   - Check network access to MinIO server
   - Ensure the ISO has been synced to public bucket

3. **Missing Dependencies**:
   - Install required packages: `pip install minio python-dotenv`

### Checking MinIO Logs

To diagnose issues, check the MinIO server logs:

```bash
# If running MinIO in Docker
docker logs minio-server

# If running MinIO as a service
sudo journalctl -u minio.service
```

### Helpful Commands

```bash
# Direct access to MinIO command line (if mc client is installed)
mc ls scratchy/r630-switchbot-private/
mc ls scratchy/r630-switchbot-public/

# Verify object exists in public bucket
curl -I http://scratchy.omnisack.nl/r630-switchbot-public/isos/4.18/agent.x86_64.iso
```

## Advanced Usage

### Custom Endpoints

You can specify a custom MinIO endpoint:

```bash
./scripts/setup_minio_buckets.py --setup --endpoint custom.minio.server
```

### Using HTTP Instead of HTTPS

For development or internal environments:

```bash
./scripts/setup_minio_buckets.py --setup --insecure
```

### Full Discovery Details

For complete environment investigation:

```bash
./scripts/setup_minio_buckets.py --discover > minio_discovery.log
```
