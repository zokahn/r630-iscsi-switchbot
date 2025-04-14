# Testing the Component Framework

This document provides instructions for testing the various components in the r630-iscsi-switchbot project.

## Overview

The project includes test scripts to verify the functionality of each component:

- **test_s3_minio.py**: Tests S3Component with MinIO or other S3-compatible storage
- **test_iscsi_truenas.py**: Tests ISCSIComponent with TrueNAS
- **setup_minio_buckets.py**: Sets up MinIO buckets and performs basic tests

These test scripts follow the discover-process-housekeep pattern used by all components.

## Prerequisites

Before running the tests, ensure you have:

1. Access to a TrueNAS instance with API access (for iSCSI tests)
2. Access to a MinIO/S3 instance with proper credentials (for S3 tests)
3. Python 3.6+ with required dependencies installed

## Testing the S3Component

The S3Component can be tested using the `test_s3_minio.py` script, which verifies:
- Connection to MinIO/S3
- Bucket creation
- File upload/download
- Metadata handling

### Basic Usage

```bash
# List existing buckets (read-only)
python scripts/test_s3_minio.py \
  --endpoint scratchy.omnisack.nl \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --list-only

# Perform a full test with a 1MB file
python scripts/test_s3_minio.py \
  --endpoint scratchy.omnisack.nl \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --file-size 1048576 \
  --cleanup
```

### Test Options

- `--endpoint`: MinIO/S3 endpoint (required)
- `--access-key`: Access key for authentication (required)
- `--secret-key`: Secret key for authentication (required)
- `--secure`: Use HTTPS instead of HTTP
- `--test-bucket`: Bucket name to use for testing (default: auto-generated)
- `--file-size`: Size of test file in bytes (default: 1KB)
- `--create-buckets`: Create standard project buckets
- `--list-only`: Only list buckets without running tests
- `--cleanup`: Remove test resources after testing
- `--verbose`: Enable verbose logging
- `--dry-run`: Show operations without executing them

### Expected Output

A successful test will show:
1. Discovery results (endpoint connection and bucket listing)
2. Test file creation
3. Upload/download verification
4. Cleanup confirmation

Example output:
```
INFO:s3-test:Initializing S3Component with endpoint scratchy.omnisack.nl
INFO:s3-test:Starting discovery phase...
INFO:s3-test:Discovery completed:
INFO:s3-test:- Endpoint: scratchy.omnisack.nl
INFO:s3-test:- Connected: True
INFO:s3-test:Found 3 existing buckets:
INFO:s3-test:  - r630-switchbot-isos
INFO:s3-test:  - r630-switchbot-binaries
INFO:s3-test:  - r630-switchbot-temp
INFO:s3-test:Starting processing phase...
INFO:s3-test:Creating test file of 1024 bytes
INFO:s3-test:Created test file at /tmp/tmp12345
INFO:s3-test:Ensuring test bucket test-bucket-abc12345 exists
INFO:s3-test:Created test bucket test-bucket-abc12345
INFO:s3-test:Uploading test file to test-bucket-abc12345/test-files/test-xyz12345.dat
INFO:s3-test:Uploaded test file successfully
INFO:s3-test:Verifying uploaded file...
INFO:s3-test:File exists in bucket with size 1024 bytes
INFO:s3-test:Downloading file to /tmp/download-xyz12345.dat
INFO:s3-test:Downloaded file size: 1024 bytes
INFO:s3-test:Download verification successful - file sizes match
INFO:s3-test:Cleaning up test resources...
INFO:s3-test:Removing test file test-files/test-xyz12345.dat from bucket
INFO:s3-test:Removing test bucket test-bucket-abc12345
INFO:s3-test:Removed local test file /tmp/tmp12345
INFO:s3-test:S3/MinIO component test completed successfully
```

## Testing the ISCSIComponent

The ISCSIComponent can be tested using the `test_iscsi_truenas.py` script, which verifies:
- Connection to TrueNAS
- Storage pool discovery
- iSCSI service status
- ZVOL and iSCSI target creation (optional)

### Basic Usage

```bash
# Discovery only (no changes)
python scripts/test_iscsi_truenas.py \
  --truenas-ip 192.168.2.245 \
  --api-key YOUR_API_KEY \
  --discover-only

# Create a test zvol and clean it up
python scripts/test_iscsi_truenas.py \
  --truenas-ip 192.168.2.245 \
  --api-key YOUR_API_KEY \
  --create-test-zvol \
  --cleanup \
  --zvol-size 1G \
  --zfs-pool tank
```

### Test Options

- `--truenas-ip`: TrueNAS IP address (required)
- `--api-key`: TrueNAS API key (if not provided, will prompt)
- `--server-id`: Server ID for test zvol (default: test01)
- `--hostname`: Hostname for test zvol (default: test-server)
- `--openshift-version`: OpenShift version for test zvol (default: 4.14.0)
- `--zvol-size`: Size of test zvol (default: 1G)
- `--zfs-pool`: ZFS pool name (default: test)
- `--create-test-zvol`: Create a test zvol
- `--cleanup`: Clean up test resources
- `--discover-only`: Only perform discovery
- `--verbose`: Enable verbose logging
- `--dry-run`: Show operations without executing them

### Expected Output

A successful discovery test will show:
1. TrueNAS connection status
2. iSCSI service status
3. Storage pools with available space
4. Existing zvols and targets

Example output:
```
INFO:iscsi-test:Initializing ISCSIComponent for TrueNAS at 192.168.2.245
INFO:iscsi-test:Starting discovery phase...
INFO:iscsi-test:Discovery completed:
INFO:iscsi-test:- TrueNAS connectivity: True
INFO:iscsi-test:- iSCSI service running: True
INFO:iscsi-test:Found 2 storage pools:
INFO:iscsi-test:  - tank (900.5 GB free)
INFO:iscsi-test:  - test (150.2 GB free)
INFO:iscsi-test:Found 3 existing zvols:
INFO:iscsi-test:  - tank/openshift_installations/r630_01_4_14_0 (500.0 GB)
INFO:iscsi-test:  - tank/openshift_installations/r630_02_4_14_0 (500.0 GB)
INFO:iscsi-test:  - test/openshift_installations/r630_test01_4_14_0 (10.0 GB)
INFO:iscsi-test:Found 3 existing iSCSI targets:
INFO:iscsi-test:  - iqn.2005-10.org.freenas.ctl:iscsi.r630-01.openshift4_14_0 (ID: 1)
INFO:iscsi-test:  - iqn.2005-10.org.freenas.ctl:iscsi.r630-02.openshift4_14_0 (ID: 2)
INFO:iscsi-test:  - iqn.2005-10.org.freenas.ctl:iscsi.r630-test01.openshift4_14_0 (ID: 3)
INFO:iscsi-test:Storage capacity is sufficient for test zvol
INFO:iscsi-test:Discovery-only mode, skipping processing phase
INFO:iscsi-test:TrueNAS iSCSI component test completed successfully
```

If you run the test with `--create-test-zvol`, you'll also see the processing results:
```
INFO:iscsi-test:Starting processing phase to create test zvol...
INFO:iscsi-test:Processing results:
INFO:iscsi-test:- Zvol created: True
INFO:iscsi-test:- Target created: True
INFO:iscsi-test:- Extent created: True
INFO:iscsi-test:- Association created: True
INFO:iscsi-test:- Target ID: 4
INFO:iscsi-test:- Extent ID: 4
```

## Setting Up MinIO Buckets

The `setup_minio_buckets.py` script provides a way to initialize and test the standard bucket structure:

```bash
# Initialize all required buckets
python scripts/setup_minio_buckets.py \
  --endpoint scratchy.omnisack.nl \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --init-all

# Test with a simple upload
python scripts/setup_minio_buckets.py \
  --endpoint scratchy.omnisack.nl \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --upload-example
```

## Troubleshooting

### S3/MinIO Connection Issues

1. **Connection Failed**:
   - Verify the endpoint URL is correct
   - Check if the endpoint is accessible from your network
   - For HTTP-only endpoints, make sure not to use the `--secure` flag

2. **Authentication Failed**:
   - Double-check access key and secret key
   - Verify the account has appropriate permissions

3. **Bucket Creation Failed**:
   - Check if you have permission to create buckets
   - Verify the bucket name follows naming conventions (lowercase, no special chars)

### TrueNAS Connection Issues

1. **API Connection Failed**:
   - Verify the TrueNAS IP address is correct
   - Check if TrueNAS is accessible from your network
   - Confirm the API service is running on TrueNAS (port 444)

2. **Authentication Failed**:
   - Ensure the API key is correctly copied
   - Verify the API key has appropriate permissions

3. **ZVOL Creation Failed**:
   - Check if the specified pool exists
   - Verify there's enough space in the pool
   - Ensure the path doesn't already exist

4. **iSCSI Service Issues**:
   - Verify the iSCSI service is enabled in TrueNAS
   - Check if the service is running

## Permissions Required

### S3/MinIO

- `s3:ListAllMyBuckets` - To list buckets
- `s3:CreateBucket` - To create test buckets
- `s3:ListBucket` - To list objects in buckets
- `s3:PutObject` - To upload test files
- `s3:GetObject` - To download and verify files
- `s3:DeleteObject` - To clean up test files
- `s3:DeleteBucket` - To remove test buckets

### TrueNAS

The API key needs permissions for:
- Storage pool access
- ZFS dataset creation/deletion
- iSCSI target management

## Conclusion

These test scripts provide a way to verify the functionality of each component before using them in production. They follow the same pattern as the components themselves, making them easy to understand and extend.

If you encounter any issues not covered by the troubleshooting section, check the component's implementation for more detailed error handling and logging.
