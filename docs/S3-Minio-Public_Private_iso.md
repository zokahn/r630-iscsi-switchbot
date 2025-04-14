# S3/Minio Public and Private ISO Storage

This document outlines the approach for implementing a dual-bucket strategy for ISO storage, with separate public and private buckets to support different access patterns.

## Overview

We need to store OpenShift ISOs in S3 (Minio) with two different access patterns:

1. **Private bucket (r630-switchbot-private)**: 
   - For versioned storage of all ISOs
   - Requires authentication
   - Stores history and metadata
   - Used by admin tools and scripts

2. **Public bucket (r630-switchbot-public)**:
   - Contains only the latest version of each ISO
   - Anonymous access for PXE/iDRAC usage
   - Predictable URLs without timestamps
   - Minimal metadata

## Implementation Strategy

The implementation follows a "write to private, sync to public" pattern:

1. Upload ISO to private bucket with timestamps and metadata
2. Optionally copy latest ISO to public bucket with fixed naming
3. Use private bucket for admin tools and backups
4. Use public bucket for PXE menus and iDRAC

## Bucket Policies

### Private Bucket (r630-switchbot-private)

- Standard authenticated access
- 365-day retention policy
- Full versioning and metadata

### Public Bucket (r630-switchbot-public)

- Anonymous read-only access
- No versioning (only latest)
- Only certain paths/objects accessible
- Simple directory structure

## Synchronization Process

When a new ISO is uploaded to the private bucket:

1. Determine if it should be published publicly
2. If yes, copy to public bucket with standardized name
3. Update metadata in both buckets
4. Handle cleanup of old public ISOs

## URL Patterns

### Private URLs
```
s3://r630-switchbot-private/isos/server-01-humpty-4.18.0-20250414.iso
```

### Public URLs
```
http://scratchy.omnisack.nl/r630-switchbot-public/isos/4.18/agent.x86_64.iso
```

## Access Control Implementation

The public bucket will be configured with a bucket policy that allows anonymous GetObject requests but restricts ListBucket and other operations to authenticated users.
