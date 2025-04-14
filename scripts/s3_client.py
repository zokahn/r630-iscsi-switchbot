#!/usr/bin/env python3
"""
S3 Client Module for r630-iscsi-switchbot

This module provides functionality to interact with S3 storage (Minio)
for storing ISOs, OpenShift binaries, and deployment artifacts.
"""

import os
import sys
import logging
import datetime
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('s3_client')

# Default folder structure in S3
S3_FOLDERS = {
    'isos': 'isos/',
    'binaries': 'binaries/',
    'artifacts': 'artifacts/'
}

class S3Client:
    """Client for interacting with S3 storage (Minio-based)"""

    def __init__(self):
        """Initialize S3 client with credentials from environment"""
        # Load environment variables from .env file if it exists
        env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '.env'
        load_dotenv(dotenv_path=env_path)
        
        # Get S3 configuration from environment
        self.endpoint = os.getenv('S3_ENDPOINT', 'https://scratchy.omnisack.nl')
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        self.bucket = os.getenv('S3_BUCKET', 'r630-switchbot')
        self.region = os.getenv('S3_REGION', 'us-east-1')
        
        # Check required credentials
        if not self.access_key or not self.secret_key:
            logger.error("S3 credentials not found. Please set S3_ACCESS_KEY and S3_SECRET_KEY in .env file")
            raise ValueError("Missing S3 credentials")
        
        # Initialize S3 client
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )
        logger.info(f"Initialized S3 client for endpoint: {self.endpoint}")
    
    def list_objects(self, prefix=''):
        """List objects in the S3 bucket with optional prefix"""
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            return response.get('Contents', [])
        except ClientError as e:
            logger.error(f"Error listing objects: {e}")
            return []
    
    def upload_file(self, file_path, s3_key=None, metadata=None):
        """Upload a file to S3
        
        Args:
            file_path (str): Path to the local file
            s3_key (str, optional): Custom S3 key, if None uses filename
            metadata (dict, optional): Metadata to attach to the object
        
        Returns:
            bool: True if upload successful, False otherwise
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
        
        # Use filename as key if not specified
        if s3_key is None:
            s3_key = os.path.basename(file_path)
        
        # Ensure metadata is a dictionary
        if metadata is None:
            metadata = {}
        
        # Add creation date for lifecycle management
        metadata['CreationDate'] = datetime.datetime.now().strftime('%Y-%m-%d')
        
        try:
            self.s3.upload_file(
                file_path,
                self.bucket,
                s3_key,
                ExtraArgs={
                    'Metadata': metadata,
                }
            )
            logger.info(f"Successfully uploaded {file_path} to s3://{self.bucket}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading file: {e}")
            return False
    
    def download_file(self, s3_key, download_path):
        """Download a file from S3
        
        Args:
            s3_key (str): S3 object key
            download_path (str): Local path to save the file
        
        Returns:
            bool: True if download successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            
            self.s3.download_file(
                self.bucket,
                s3_key,
                download_path
            )
            logger.info(f"Successfully downloaded s3://{self.bucket}/{s3_key} to {download_path}")
            return True
        except ClientError as e:
            logger.error(f"Error downloading file: {e}")
            return False
    
    def delete_object(self, s3_key):
        """Delete an object from S3
        
        Args:
            s3_key (str): S3 object key
        
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            self.s3.delete_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            logger.info(f"Successfully deleted s3://{self.bucket}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting object: {e}")
            return False
    
    def object_exists(self, s3_key):
        """Check if an object exists in S3
        
        Args:
            s3_key (str): S3 object key
        
        Returns:
            bool: True if object exists, False otherwise
        """
        try:
            self.s3.head_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return True
        except ClientError:
            return False
    
    def get_object_metadata(self, s3_key):
        """Get metadata for an S3 object
        
        Args:
            s3_key (str): S3 object key
        
        Returns:
            dict: Object metadata or None if object doesn't exist
        """
        try:
            response = self.s3.head_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return response.get('Metadata', {})
        except ClientError:
            return None
    
    def cleanup_old_objects(self, prefix='', days=365):
        """Delete objects older than specified days
        
        Args:
            prefix (str): Only delete objects with this prefix
            days (int): Delete objects older than this many days
        
        Returns:
            tuple: (deleted_count, failed_count)
        """
        objects = self.list_objects(prefix)
        deleted_count = 0
        failed_count = 0
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        for obj in objects:
            s3_key = obj.get('Key')
            metadata = self.get_object_metadata(s3_key)
            
            if metadata and 'creationdate' in metadata:
                creation_date = metadata['creationdate']
                if creation_date < cutoff_str:
                    if self.delete_object(s3_key):
                        deleted_count += 1
                    else:
                        failed_count += 1
            
            # Also check LastModified as a fallback
            last_modified = obj.get('LastModified')
            if last_modified and last_modified.replace(tzinfo=None) < cutoff_date:
                if self.delete_object(s3_key):
                    deleted_count += 1
                else:
                    failed_count += 1
        
        logger.info(f"Cleanup completed. Deleted: {deleted_count}, Failed: {failed_count}")
        return (deleted_count, failed_count)

    # Convenience methods for specific object types
    
    def upload_iso(self, iso_path, server_id, hostname, version, metadata=None):
        """Upload an OpenShift ISO with standardized naming
        
        Args:
            iso_path (str): Path to the ISO file
            server_id (str): Server ID (e.g., 01)
            hostname (str): Server hostname
            version (str): OpenShift version
            metadata (dict, optional): Additional metadata
        
        Returns:
            bool: True if upload successful, False otherwise
        """
        # Generate timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d')
        
        # Create S3 key with convention: isos/server-01-humpty-4.18.0-20250414.iso
        s3_key = f"{S3_FOLDERS['isos']}server-{server_id}-{hostname}-{version}-{timestamp}.iso"
        
        # Add metadata
        if metadata is None:
            metadata = {}
        metadata.update({
            'server_id': server_id,
            'hostname': hostname,
            'openshift_version': version
        })
        
        return self.upload_file(iso_path, s3_key, metadata)
    
    def download_latest_iso(self, server_id, hostname, version, download_path):
        """Download the latest ISO for a specific server and version
        
        Args:
            server_id (str): Server ID (e.g., 01)
            hostname (str): Server hostname
            version (str): OpenShift version
            download_path (str): Path to save the ISO
        
        Returns:
            bool: True if download successful, False otherwise
        """
        # List ISO files for this server and version
        prefix = f"{S3_FOLDERS['isos']}server-{server_id}-{hostname}-{version}-"
        objects = self.list_objects(prefix)
        
        if not objects:
            logger.error(f"No ISO found for server-{server_id}-{hostname}-{version}")
            return False
        
        # Sort by last modified (newest first)
        objects.sort(key=lambda x: x.get('LastModified', datetime.datetime.min), reverse=True)
        latest_iso = objects[0]['Key']
        
        return self.download_file(latest_iso, download_path)
    
    def upload_binary(self, binary_path, binary_type, version, metadata=None):
        """Upload an OpenShift binary with standardized naming
        
        Args:
            binary_path (str): Path to the binary file
            binary_type (str): Binary type (e.g., openshift-install, oc)
            version (str): OpenShift version
            metadata (dict, optional): Additional metadata
        
        Returns:
            bool: True if upload successful, False otherwise
        """
        filename = os.path.basename(binary_path)
        s3_key = f"{S3_FOLDERS['binaries']}{binary_type}-{version}-{filename}"
        
        if metadata is None:
            metadata = {}
        metadata.update({
            'binary_type': binary_type,
            'version': version
        })
        
        return self.upload_file(binary_path, s3_key, metadata)
    
    def binary_exists(self, binary_type, version):
        """Check if a binary exists for a specific version
        
        Args:
            binary_type (str): Binary type (e.g., openshift-install, oc)
            version (str): OpenShift version
        
        Returns:
            bool: True if binary exists, False otherwise
        """
        prefix = f"{S3_FOLDERS['binaries']}{binary_type}-{version}-"
        objects = self.list_objects(prefix)
        return len(objects) > 0
    
    def download_binary(self, binary_type, version, download_path):
        """Download a binary for a specific version
        
        Args:
            binary_type (str): Binary type (e.g., openshift-install, oc)
            version (str): OpenShift version
            download_path (str): Path to save the binary
        
        Returns:
            bool: True if download successful, False otherwise
        """
        prefix = f"{S3_FOLDERS['binaries']}{binary_type}-{version}-"
        objects = self.list_objects(prefix)
        
        if not objects:
            logger.error(f"No binary found for {binary_type}-{version}")
            return False
        
        # Sort by last modified (newest first)
        objects.sort(key=lambda x: x.get('LastModified', datetime.datetime.min), reverse=True)
        latest_binary = objects[0]['Key']
        
        return self.download_file(latest_binary, download_path)
    
    def save_artifact(self, file_path, server_id, hostname, deployment_id, artifact_type, metadata=None):
        """Save a deployment artifact to S3
        
        Args:
            file_path (str): Path to the artifact file
            server_id (str): Server ID (e.g., 01)
            hostname (str): Server hostname
            deployment_id (str): Deployment identifier (e.g., timestamp)
            artifact_type (str): Type of artifact (e.g., config, log)
            metadata (dict, optional): Additional metadata
        
        Returns:
            bool: True if upload successful, False otherwise
        """
        filename = os.path.basename(file_path)
        s3_key = f"{S3_FOLDERS['artifacts']}server-{server_id}/{hostname}-{deployment_id}/{artifact_type}-{filename}"
        
        if metadata is None:
            metadata = {}
        metadata.update({
            'server_id': server_id,
            'hostname': hostname,
            'deployment_id': deployment_id,
            'artifact_type': artifact_type
        })
        
        return self.upload_file(file_path, s3_key, metadata)


def main():
    """CLI interface for S3 client"""
    import argparse
    
    parser = argparse.ArgumentParser(description='S3 Client for r630-iscsi-switchbot')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List objects in S3')
    list_parser.add_argument('--prefix', default='', help='Prefix to filter objects')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a file to S3')
    upload_parser.add_argument('file_path', help='Path to the file to upload')
    upload_parser.add_argument('--key', help='S3 key (defaults to filename)')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download a file from S3')
    download_parser.add_argument('s3_key', help='S3 object key')
    download_parser.add_argument('download_path', help='Path to save the file')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete an object from S3')
    delete_parser.add_argument('s3_key', help='S3 object key')
    
    # ISO commands
    iso_parser = subparsers.add_parser('iso', help='ISO operations')
    iso_subparsers = iso_parser.add_subparsers(dest='iso_command', help='ISO commands')
    
    # Upload ISO
    upload_iso_parser = iso_subparsers.add_parser('upload', help='Upload an ISO')
    upload_iso_parser.add_argument('iso_path', help='Path to the ISO file')
    upload_iso_parser.add_argument('--server-id', required=True, help='Server ID (e.g., 01)')
    upload_iso_parser.add_argument('--hostname', required=True, help='Server hostname')
    upload_iso_parser.add_argument('--version', required=True, help='OpenShift version')
    
    # Download latest ISO
    download_iso_parser = iso_subparsers.add_parser('download', help='Download the latest ISO')
    download_iso_parser.add_argument('--server-id', required=True, help='Server ID (e.g., 01)')
    download_iso_parser.add_argument('--hostname', required=True, help='Server hostname')
    download_iso_parser.add_argument('--version', required=True, help='OpenShift version')
    download_iso_parser.add_argument('--output', required=True, help='Output path')
    
    # List ISOs
    list_iso_parser = iso_subparsers.add_parser('list', help='List available ISOs')
    list_iso_parser.add_argument('--server-id', help='Filter by server ID')
    list_iso_parser.add_argument('--hostname', help='Filter by hostname')
    list_iso_parser.add_argument('--version', help='Filter by version')
    
    # Binary commands
    binary_parser = subparsers.add_parser('binary', help='Binary operations')
    binary_subparsers = binary_parser.add_subparsers(dest='binary_command', help='Binary commands')
    
    # Upload binary
    upload_binary_parser = binary_subparsers.add_parser('upload', help='Upload a binary')
    upload_binary_parser.add_argument('binary_path', help='Path to the binary file')
    upload_binary_parser.add_argument('--type', required=True, help='Binary type (e.g., openshift-install, oc)')
    upload_binary_parser.add_argument('--version', required=True, help='OpenShift version')
    
    # Download binary
    download_binary_parser = binary_subparsers.add_parser('download', help='Download a binary')
    download_binary_parser.add_argument('--type', required=True, help='Binary type (e.g., openshift-install, oc)')
    download_binary_parser.add_argument('--version', required=True, help='OpenShift version')
    download_binary_parser.add_argument('--output', required=True, help='Output path')
    
    # List binaries
    list_binary_parser = binary_subparsers.add_parser('list', help='List available binaries')
    list_binary_parser.add_argument('--type', help='Filter by binary type')
    list_binary_parser.add_argument('--version', help='Filter by version')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old objects')
    cleanup_parser.add_argument('--prefix', default='', help='Only clean up objects with this prefix')
    cleanup_parser.add_argument('--days', type=int, default=365, help='Clean up objects older than this many days')
    
    args = parser.parse_args()
    
    # Create S3 client
    try:
        s3_client = S3Client()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Process commands
    if args.command == 'list':
        objects = s3_client.list_objects(args.prefix)
        for obj in objects:
            print(f"{obj['Key']} ({obj['Size']} bytes, Last modified: {obj['LastModified']})")
        print(f"Total objects: {len(objects)}")
    
    elif args.command == 'upload':
        key = args.key if args.key else None
        if s3_client.upload_file(args.file_path, key):
            print(f"Successfully uploaded {args.file_path}")
        else:
            print(f"Failed to upload {args.file_path}")
            sys.exit(1)
    
    elif args.command == 'download':
        if s3_client.download_file(args.s3_key, args.download_path):
            print(f"Successfully downloaded {args.s3_key} to {args.download_path}")
        else:
            print(f"Failed to download {args.s3_key}")
            sys.exit(1)
    
    elif args.command == 'delete':
        if s3_client.delete_object(args.s3_key):
            print(f"Successfully deleted {args.s3_key}")
        else:
            print(f"Failed to delete {args.s3_key}")
            sys.exit(1)
    
    elif args.command == 'iso':
        if args.iso_command == 'upload':
            if s3_client.upload_iso(args.iso_path, args.server_id, args.hostname, args.version):
                print(f"Successfully uploaded ISO {args.iso_path}")
            else:
                print(f"Failed to upload ISO {args.iso_path}")
                sys.exit(1)
                
        elif args.iso_command == 'download':
            if s3_client.download_latest_iso(args.server_id, args.hostname, args.version, args.output):
                print(f"Successfully downloaded latest ISO to {args.output}")
            else:
                print(f"Failed to download ISO")
                sys.exit(1)
                
        elif args.iso_command == 'list':
            prefix = S3_FOLDERS['isos']
            if args.server_id:
                prefix += f"server-{args.server_id}-"
                if args.hostname:
                    prefix += f"{args.hostname}-"
                    if args.version:
                        prefix += f"{args.version}-"
            objects = s3_client.list_objects(prefix)
            for obj in objects:
                print(f"{obj['Key']} ({obj['Size']} bytes, Last modified: {obj['LastModified']})")
            print(f"Total ISOs: {len(objects)}")
    
    elif args.command == 'binary':
        if args.binary_command == 'upload':
            if s3_client.upload_binary(args.binary_path, args.type, args.version):
                print(f"Successfully uploaded binary {args.binary_path}")
            else:
                print(f"Failed to upload binary {args.binary_path}")
                sys.exit(1)
                
        elif args.binary_command == 'download':
            if s3_client.download_binary(args.type, args.version, args.output):
                print(f"Successfully downloaded binary to {args.output}")
            else:
                print(f"Failed to download binary")
                sys.exit(1)
                
        elif args.binary_command == 'list':
            prefix = S3_FOLDERS['binaries']
            if args.type:
                prefix += f"{args.type}-"
                if args.version:
                    prefix += f"{args.version}-"
            objects = s3_client.list_objects(prefix)
            for obj in objects:
                print(f"{obj['Key']} ({obj['Size']} bytes, Last modified: {obj['LastModified']})")
            print(f"Total binaries: {len(objects)}")
    
    elif args.command == 'cleanup':
        deleted, failed = s3_client.cleanup_old_objects(args.prefix, args.days)
        print(f"Cleanup completed. Deleted: {deleted}, Failed: {failed}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
