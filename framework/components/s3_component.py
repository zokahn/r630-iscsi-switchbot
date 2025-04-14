#!/usr/bin/env python3
"""
S3 Component for Discovery-Processing-Housekeeping Pattern

This module provides the S3Component for managing S3 storage operations,
including dual-bucket strategy and artifact management.
"""

import os
import sys
import json
import logging
import datetime
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# Add parent directory to the path to import framework
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.base_component import BaseComponent

# Try to import required packages
try:
    import boto3
    from botocore.exceptions import ClientError
    from boto3.resources.factory import ServiceResource
    from boto3.s3.transfer import TransferConfig
except ImportError:
    print("Error: boto3 package is required for S3Component.")
    print("Install with: pip install boto3")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv package is required for S3Component.")
    print("Install with: pip install python-dotenv")
    sys.exit(1)

class S3Component(BaseComponent):
    """
    Component for managing S3 storage operations.
    
    Implements dual-bucket strategy for private versioned storage and
    public anonymous access with artifact management.
    """
    
    # Default S3 configuration
    DEFAULT_CONFIG = {
        'private_bucket': 'r630-switchbot-private',
        'public_bucket': 'r630-switchbot-public',
        'endpoint': None,  # Will be loaded from env
        'access_key': None,  # Will be loaded from env
        'secret_key': None,  # Will be loaded from env
        'secure': True,  # Use HTTPS
        'folder_structure_private': [
            'isos/',
            'binaries/',
            'artifacts/'
        ],
        'folder_structure_public': [
            'isos/4.16/',
            'isos/4.17/',
            'isos/4.18/',
            'isos/stable/'
        ],
        'create_buckets_if_missing': False,
        'force_recreation': False
    }
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the S3 component.
        
        Args:
            config: Configuration dictionary for the component
            logger: Optional logger instance
        """
        # Merge provided config with defaults
        merged_config = {**self.DEFAULT_CONFIG, **config}
        
        # Load configuration from environment
        self._load_env_config(merged_config)
        
        # Initialize base component
        super().__init__(merged_config, logger)
        
        # Initialize S3 client and resource
        self.s3_client = None
        self.s3_resource = None
        
        # Bucket references
        self.private_bucket = None
        self.public_bucket = None
        
        self.logger.info(f"S3Component initialized with endpoint: {self.config.get('endpoint', 'default')}")
    
    def _load_env_config(self, config: Dict[str, Any]) -> None:
        """
        Load configuration from environment variables.
        
        Args:
            config: Configuration dictionary to update
        """
        # Load .env file if it exists
        env_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / '.env'
        load_dotenv(dotenv_path=env_path)
        
        # Load from environment
        if config.get('endpoint') is None:
            config['endpoint'] = os.getenv('S3_ENDPOINT', 'scratchy.omnisack.nl')
        
        if config.get('access_key') is None:
            config['access_key'] = os.getenv('S3_ACCESS_KEY')
        
        if config.get('secret_key') is None:
            config['secret_key'] = os.getenv('S3_SECRET_KEY')
    
    def discover(self) -> Dict[str, Any]:
        """
        Discovery phase: Examine the S3 environment.
        
        Checks connectivity, lists buckets, identifies bucket contents,
        and verifies access to both private and public buckets.
        
        Returns:
            Dictionary of discovery results
        """
        self.timestamps['discover_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting discovery phase for {self.component_name}")
        
        try:
            # Initialize discovery results
            self.discovery_results = {
                'connectivity': False,
                'buckets': {
                    'private': {
                        'exists': False,
                        'objects_count': 0,
                        'folders': []
                    },
                    'public': {
                        'exists': False,
                        'objects_count': 0,
                        'folders': []
                    }
                },
                'policies': {
                    'private': None,
                    'public': None
                },
                'versioning': {
                    'private': False,
                    'public': False
                }
            }
            
            # Check S3 connectivity
            self._check_s3_connectivity()
            
            # Discover buckets
            self._discover_buckets()
            
            # Mark as executed
            self.phases_executed['discover'] = True
            
            # Update timestamp
            self.timestamps['discover_end'] = datetime.datetime.now().isoformat()
            self.logger.info(f"Discovery phase completed for {self.component_name}")
            
            return self.discovery_results
            
        except Exception as e:
            self.logger.error(f"Error during discovery phase: {str(e)}")
            self.status['success'] = False
            self.status['error'] = str(e)
            self.status['message'] = f"Discovery phase failed: {str(e)}"
            
            # Update timestamp even on failure
            self.timestamps['discover_end'] = datetime.datetime.now().isoformat()
            
            raise
    
    def _check_s3_connectivity(self) -> None:
        """
        Check S3 connectivity and initialize clients.
        
        Raises:
            Exception: If connection fails
        """
        try:
            endpoint = self.config.get('endpoint')
            access_key = self.config.get('access_key')
            secret_key = self.config.get('secret_key')
            secure = self.config.get('secure', True)
            
            # Verify credentials are available
            if not access_key or not secret_key:
                raise ValueError("S3 credentials not found. Please set S3_ACCESS_KEY and S3_SECRET_KEY in .env file")
            
            # Initialize S3 client and resource
            self.s3_client = boto3.client(
                's3',
                endpoint_url=f"{'https' if secure else 'http'}://{endpoint}",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='us-east-1'  # Dummy region for compatibility
            )
            
            self.s3_resource = boto3.resource(
                's3',
                endpoint_url=f"{'https' if secure else 'http'}://{endpoint}",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='us-east-1'  # Dummy region for compatibility
            )
            
            # Test connectivity by listing buckets
            response = self.s3_client.list_buckets()
            
            self.discovery_results['connectivity'] = True
            self.discovery_results['bucket_count'] = len(response.get('Buckets', []))
            self.discovery_results['endpoint'] = endpoint
            
            self.logger.info(f"Successfully connected to S3 endpoint: {endpoint}")
            self.logger.info(f"Found {self.discovery_results['bucket_count']} buckets")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to S3: {str(e)}")
            self.discovery_results['connectivity'] = False
            self.discovery_results['error'] = str(e)
            raise
    
    def _discover_buckets(self) -> None:
        """
        Discover private and public buckets and their contents.
        """
        if not self.discovery_results['connectivity']:
            self.logger.warning("Cannot discover buckets without connectivity")
            return
        
        private_bucket_name = self.config.get('private_bucket')
        public_bucket_name = self.config.get('public_bucket')
        
        # Check if buckets exist
        all_buckets = self.s3_client.list_buckets()
        bucket_names = [b['Name'] for b in all_buckets.get('Buckets', [])]
        
        # Check private bucket
        private_exists = private_bucket_name in bucket_names
        self.discovery_results['buckets']['private']['exists'] = private_exists
        
        if private_exists:
            self.logger.info(f"Private bucket '{private_bucket_name}' exists")
            self.private_bucket = self.s3_resource.Bucket(private_bucket_name)
            
            # Get object count
            try:
                private_objects = list(self.private_bucket.objects.all())
                self.discovery_results['buckets']['private']['objects_count'] = len(private_objects)
                
                # Extract folder structure
                folders = set()
                for obj in private_objects:
                    parts = obj.key.split('/')
                    if len(parts) > 1:
                        folders.add(f"{parts[0]}/")
                
                self.discovery_results['buckets']['private']['folders'] = list(folders)
                
                # Check versioning
                try:
                    versioning = self.s3_client.get_bucket_versioning(Bucket=private_bucket_name)
                    self.discovery_results['versioning']['private'] = \
                        versioning.get('Status') == 'Enabled'
                except:
                    self.logger.warning(f"Could not get versioning for private bucket")
                
                # Check policy
                try:
                    policy = self.s3_client.get_bucket_policy(Bucket=private_bucket_name)
                    self.discovery_results['policies']['private'] = policy.get('Policy')
                except:
                    self.logger.info(f"No policy set for private bucket")
                
            except Exception as e:
                self.logger.error(f"Error listing objects in private bucket: {str(e)}")
        else:
            self.logger.info(f"Private bucket '{private_bucket_name}' does not exist")
        
        # Check public bucket
        public_exists = public_bucket_name in bucket_names
        self.discovery_results['buckets']['public']['exists'] = public_exists
        
        if public_exists:
            self.logger.info(f"Public bucket '{public_bucket_name}' exists")
            self.public_bucket = self.s3_resource.Bucket(public_bucket_name)
            
            # Get object count
            try:
                public_objects = list(self.public_bucket.objects.all())
                self.discovery_results['buckets']['public']['objects_count'] = len(public_objects)
                
                # Extract folder structure
                folders = set()
                for obj in public_objects:
                    parts = obj.key.split('/')
                    if len(parts) > 1:
                        folders.add(f"{parts[0]}/")
                
                self.discovery_results['buckets']['public']['folders'] = list(folders)
                
                # Check versioning
                try:
                    versioning = self.s3_client.get_bucket_versioning(Bucket=public_bucket_name)
                    self.discovery_results['versioning']['public'] = \
                        versioning.get('Status') == 'Enabled'
                except:
                    self.logger.warning(f"Could not get versioning for public bucket")
                
                # Check policy
                try:
                    policy = self.s3_client.get_bucket_policy(Bucket=public_bucket_name)
                    self.discovery_results['policies']['public'] = policy.get('Policy')
                except:
                    self.logger.info(f"No policy set for public bucket")
                    
            except Exception as e:
                self.logger.error(f"Error listing objects in public bucket: {str(e)}")
        else:
            self.logger.info(f"Public bucket '{public_bucket_name}' does not exist")
    
    def process(self) -> Dict[str, Any]:
        """
        Processing phase: Set up the dual-bucket system.
        
        Creates or configures buckets as needed, applies policies, and
        creates the folder structure.
        
        Returns:
            Dictionary of processing results
        """
        self.timestamps['process_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting processing phase for {self.component_name}")
        
        # Check if discovery has been run
        if not self.phases_executed['discover']:
            self.logger.warning("Processing without prior discovery may lead to unexpected results")
            # Run discovery to be safe
            self.discover()
        
        try:
            # Initialize processing results
            self.processing_results = {
                'actions': [],
                'buckets': {
                    'private': {
                        'created': False,
                        'configured': False,
                        'folders_created': []
                    },
                    'public': {
                        'created': False,
                        'configured': False,
                        'folders_created': []
                    }
                }
            }
            
            # Check if we need to create buckets
            create_buckets = self.config.get('create_buckets_if_missing', False)
            force_recreation = self.config.get('force_recreation', False)
            
            if create_buckets:
                # Set up private bucket
                self._setup_bucket(
                    'private', 
                    self.config.get('private_bucket'),
                    self.config.get('folder_structure_private', []),
                    force_recreation
                )
                
                # Set up public bucket
                self._setup_bucket(
                    'public', 
                    self.config.get('public_bucket'),
                    self.config.get('folder_structure_public', []),
                    force_recreation
                )
                
                # Set public bucket policy for anonymous access
                if self.discovery_results['buckets']['public']['exists'] or \
                   self.processing_results['buckets']['public']['created']:
                    self._configure_public_bucket_policy()
            else:
                self.logger.info("Skipping bucket creation - 'create_buckets_if_missing' is False")
                self.processing_results['actions'].append('skip_bucket_creation')
            
            # Mark as executed
            self.phases_executed['process'] = True
            
            # Update timestamp
            self.timestamps['process_end'] = datetime.datetime.now().isoformat()
            self.logger.info(f"Processing phase completed for {self.component_name}")
            
            return self.processing_results
            
        except Exception as e:
            self.logger.error(f"Error during processing phase: {str(e)}")
            self.status['success'] = False
            self.status['error'] = str(e)
            self.status['message'] = f"Processing phase failed: {str(e)}"
            
            # Update timestamp even on failure
            self.timestamps['process_end'] = datetime.datetime.now().isoformat()
            
            raise
    
    def _setup_bucket(self, bucket_type: str, bucket_name: str, 
                     folder_structure: List[str], force: bool) -> None:
        """
        Set up a bucket with the specified configuration.
        
        Args:
            bucket_type: 'private' or 'public'
            bucket_name: Name of the bucket
            folder_structure: List of folders to create
            force: Whether to force reconfiguration if the bucket exists
        """
        bucket_exists = self.discovery_results['buckets'][bucket_type]['exists']
        
        if not bucket_exists:
            # Create bucket
            try:
                self.s3_client.create_bucket(Bucket=bucket_name)
                self.logger.info(f"Created {bucket_type} bucket: {bucket_name}")
                self.processing_results['buckets'][bucket_type]['created'] = True
                self.processing_results['actions'].append(f'create_{bucket_type}_bucket')
                
                # Update reference
                if bucket_type == 'private':
                    self.private_bucket = self.s3_resource.Bucket(bucket_name)
                else:
                    self.public_bucket = self.s3_resource.Bucket(bucket_name)
                
                # Enable versioning for private bucket
                if bucket_type == 'private':
                    self.s3_client.put_bucket_versioning(
                        Bucket=bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    self.logger.info(f"Enabled versioning for {bucket_type} bucket")
                    self.processing_results['actions'].append(f'enable_versioning_{bucket_type}')
                
                # Create folder structure
                for folder in folder_structure:
                    self.s3_client.put_object(
                        Bucket=bucket_name,
                        Key=folder
                    )
                    self.processing_results['buckets'][bucket_type]['folders_created'].append(folder)
                    self.logger.info(f"Created folder {folder} in {bucket_type} bucket")
                
                self.processing_results['buckets'][bucket_type]['configured'] = True
                
            except Exception as e:
                self.logger.error(f"Failed to create {bucket_type} bucket: {str(e)}")
                raise
                
        elif force:
            self.logger.info(f"{bucket_type.capitalize()} bucket exists - reconfiguring due to force flag")
            self.processing_results['actions'].append(f'reconfigure_{bucket_type}_bucket')
            
            # Enable versioning for private bucket if not already enabled
            if bucket_type == 'private' and not self.discovery_results['versioning']['private']:
                try:
                    self.s3_client.put_bucket_versioning(
                        Bucket=bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    self.logger.info(f"Enabled versioning for {bucket_type} bucket")
                    self.processing_results['actions'].append(f'enable_versioning_{bucket_type}')
                except Exception as e:
                    self.logger.error(f"Failed to enable versioning: {str(e)}")
            
            # Create folder structure if needed
            existing_folders = self.discovery_results['buckets'][bucket_type]['folders']
            for folder in folder_structure:
                if folder not in existing_folders:
                    try:
                        self.s3_client.put_object(
                            Bucket=bucket_name,
                            Key=folder
                        )
                        self.processing_results['buckets'][bucket_type]['folders_created'].append(folder)
                        self.logger.info(f"Created folder {folder} in {bucket_type} bucket")
                    except Exception as e:
                        self.logger.error(f"Failed to create folder {folder}: {str(e)}")
            
            self.processing_results['buckets'][bucket_type]['configured'] = True
            
        else:
            self.logger.info(f"{bucket_type.capitalize()} bucket exists - skipping creation")
            self.processing_results['actions'].append(f'skip_{bucket_type}_bucket')
    
    def _configure_public_bucket_policy(self) -> None:
        """
        Configure the public bucket with a policy for anonymous read access.
        """
        public_bucket_name = self.config.get('public_bucket')
        
        # Create policy for anonymous GetObject
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{public_bucket_name}/isos/*"]
                }
            ]
        }
        
        try:
            self.s3_client.put_bucket_policy(
                Bucket=public_bucket_name,
                Policy=json.dumps(policy)
            )
            self.logger.info(f"Applied anonymous read policy to public bucket")
            self.processing_results['actions'].append('set_public_bucket_policy')
            self.processing_results['buckets']['public']['policy_configured'] = True
            
        except Exception as e:
            self.logger.error(f"Failed to set public bucket policy: {str(e)}")
            self.processing_results['buckets']['public']['policy_configured'] = False
            raise
    
    def housekeep(self) -> Dict[str, Any]:
        """
        Housekeeping phase: Verify configuration and prepare for usage.
        
        Verifies bucket configurations, checks accessibility, and creates
        metadata index if needed.
        
        Returns:
            Dictionary of housekeeping results
        """
        self.timestamps['housekeep_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting housekeeping phase for {self.component_name}")
        
        # Check if processing has been run
        if not self.phases_executed['process']:
            self.logger.warning("Housekeeping without prior processing may lead to unexpected results")
        
        try:
            # Initialize housekeeping results
            self.housekeeping_results = {
                'verification': {
                    'private_bucket': False,
                    'public_bucket': False,
                    'private_versioning': False,
                    'public_policy': False
                },
                'metadata_index': {
                    'created': False,
                    'entries': 0
                },
                'warnings': []
            }
            
            # Verify configurations
            self._verify_configurations()
            
            # Create metadata index if needed
            if self.config.get('create_metadata_index', False):
                self._create_metadata_index()
            else:
                self.housekeeping_results['warnings'].append(
                    "Metadata index creation skipped - 'create_metadata_index' is False"
                )
            
            # Clean up old artifacts if needed
            if self.config.get('cleanup_old_artifacts', False):
                max_age_days = self.config.get('max_artifact_age_days', 365)
                self._cleanup_old_artifacts(max_age_days)
            
            # Mark as executed
            self.phases_executed['housekeep'] = True
            
            # Process artifacts if any
            if self.artifacts:
                self._store_artifacts()
            
            # Update timestamp
            self.timestamps['housekeep_end'] = datetime.datetime.now().isoformat()
            self.logger.info(f"Housekeeping phase completed for {self.component_name}")
            
            return self.housekeeping_results
            
        except Exception as e:
            self.logger.error(f"Error during housekeeping phase: {str(e)}")
            self.status['success'] = False
            self.status['error'] = str(e)
            self.status['message'] = f"Housekeeping phase failed: {str(e)}"
            
            # Update timestamp even on failure
            self.timestamps['housekeep_end'] = datetime.datetime.now().isoformat()
            
            raise
    
    def _verify_configurations(self) -> None:
        """
        Verify bucket configurations during housekeeping.
        """
        private_bucket_name = self.config.get('private_bucket')
        public_bucket_name = self.config.get('public_bucket')
        
        # Verify private bucket
        try:
            self.s3_client.head_bucket(Bucket=private_bucket_name)
            self.housekeeping_results['verification']['private_bucket'] = True
            self.logger.info(f"Verified private bucket exists: {private_bucket_name}")
            
            # Verify versioning
            versioning = self.s3_client.get_bucket_versioning(Bucket=private_bucket_name)
            if versioning.get('Status') == 'Enabled':
                self.housekeeping_results['verification']['private_versioning'] = True
                self.logger.info(f"Verified private bucket has versioning enabled")
            else:
                self.logger.warning(f"Private bucket does not have versioning enabled")
                self.housekeeping_results['warnings'].append("Private bucket missing versioning")
                
        except Exception as e:
            self.logger.error(f"Failed to verify private bucket: {str(e)}")
            self.housekeeping_results['verification']['private_bucket'] = False
            self.housekeeping_results['warnings'].append(f"Private bucket verification failed: {str(e)}")
        
        # Verify public bucket
        try:
            self.s3_client.head_bucket(Bucket=public_bucket_name)
            self.housekeeping_results['verification']['public_bucket'] = True
            self.logger.info(f"Verified public bucket exists: {public_bucket_name}")
            
            # Verify policy
            try:
                policy = self.s3_client.get_bucket_policy(Bucket=public_bucket_name)
                policy_str = policy.get('Policy', '{}')
                
                # Check if policy allows anonymous GetObject
                policy_json = json.loads(policy_str)
                has_public_read = False
                
                for statement in policy_json.get('Statement', []):
                    principal = statement.get('Principal', {})
                    effect = statement.get('Effect')
                    action = statement.get('Action')
                    
                    if effect == 'Allow' and \
                       (principal.get('AWS') == '*' or principal == '*') and \
                       ('s3:GetObject' in action or action == 's3:GetObject'):
                        has_public_read = True
                        break
                
                if has_public_read:
                    self.housekeeping_results['verification']['public_policy'] = True
                    self.logger.info(f"Verified public bucket has anonymous read policy")
                else:
                    self.logger.warning(f"Public bucket does not have proper anonymous read policy")
                    self.housekeeping_results['warnings'].append("Public bucket missing anonymous read policy")
                    
            except Exception as e:
                self.logger.warning(f"Public bucket policy verification failed: {str(e)}")
                self.housekeeping_results['warnings'].append(f"Public bucket policy verification failed: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Failed to verify public bucket: {str(e)}")
            self.housekeeping_results['verification']['public_bucket'] = False
            self.housekeeping_results['warnings'].append(f"Public bucket verification failed: {str(e)}")
    
    def _create_metadata_index(self) -> None:
        """
        Create a metadata index of available objects.
        """
        private_bucket_name = self.config.get('private_bucket')
        
        try:
            # Get all objects from private bucket
            objects = list(self.private_bucket.objects.all())
            
            # Extract metadata
            metadata_entries = []
            
            for obj in objects:
                try:
                    # Skip folders
                    if obj.key.endswith('/'):
                        continue
                        
                    # Get object metadata
                    response = self.s3_client.head_object(
                        Bucket=private_bucket_name,
                        Key=obj.key
                    )
                    
                    # Extract useful metadata
                    metadata = response.get('Metadata', {})
                    
                    entry = {
                        'key': obj.key,
                        'size': response.get('ContentLength', 0),
                        'last_modified': response.get('LastModified').isoformat() \
                            if response.get('LastModified') else None,
                        'etag': response.get('ETag', '').strip('"'),
                        'metadata': metadata
                    }
                    
                    # Extract type from key
                    if obj.key.startswith('isos/'):
                        entry['type'] = 'iso'
                    elif obj.key.startswith('binaries/'):
                        entry['type'] = 'binary'
                    elif obj.key.startswith('artifacts/'):
                        entry['type'] = 'artifact'
                    else:
                        entry['type'] = 'other'
                    
                    metadata_entries.append(entry)
                    
                except Exception as e:
                    self.logger.warning(f"Error getting metadata for {obj.key}: {str(e)}")
            
            # Create index
            index = {
                'created': datetime.datetime.now().isoformat(),
                'bucket': private_bucket_name,
                'total_objects': len(metadata_entries),
                'objects': metadata_entries
            }
            
            # Save index to private bucket
            index_key = 'metadata/index.json'
            self.s3_client.put_object(
                Bucket=private_bucket_name,
                Key=index_key,
                Body=json.dumps(index, indent=2),
                ContentType='application/json'
            )
            
            self.housekeeping_results['metadata_index']['created'] = True
            self.housekeeping_results['metadata_index']['entries'] = len(metadata_entries)
            self.logger.info(f"Created metadata index with {len(metadata_entries)} entries")
            
        except Exception as e:
            self.logger.error(f"Failed to create metadata index: {str(e)}")
            self.housekeeping_results['metadata_index']['created'] = False
            self.housekeeping_results['warnings'].append(f"Metadata index creation failed: {str(e)}")
    
    def _cleanup_old_artifacts(self, max_age_days: int) -> None:
        """
        Clean up artifacts older than specified days.
        
        Args:
            max_age_days: Maximum age in days for artifacts
        """
        private_bucket_name = self.config.get('private_bucket')
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=max_age_days)
            self.logger.info(f"Cleaning up artifacts older than {max_age_days} days ({cutoff_date.isoformat()})")
            
            # Get all objects from private bucket
            objects = list(self.private_bucket.objects.all())
            
            # Track deleted objects
            deleted_count = 0
            
            for obj in objects:
                try:
                    # Skip folders
                    if obj.key.endswith('/'):
                        continue
                    
                    # Skip top-level metadata
                    if obj.key.startswith('metadata/'):
                        continue
                    
                    # Get object metadata
                    response = self.s3_client.head_object(
                        Bucket=private_bucket_name,
                        Key=obj.key
                    )
                    
                    # Get last modified date
                    last_modified = response.get('LastModified')
                    
                    if last_modified and last_modified.replace(tzinfo=None) < cutoff_date:
                        # Delete the object
                        self.s3_client.delete_object(
                            Bucket=private_bucket_name,
                            Key=obj.key
                        )
                        self.logger.info(f"Deleted old artifact: {obj.key}")
                        deleted_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"Error processing object {obj.key}: {str(e)}")
            
            self.housekeeping_results['cleanup'] = {
                'deleted_count': deleted_count,
                'cutoff_date': cutoff_date.isoformat()
            }
            self.logger.info(f"Deleted {deleted_count} old artifacts")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            self.housekeeping_results['warnings'].append(f"Cleanup failed: {str(e)}")
    
    def _store_artifacts(self) -> None:
        """
        Store artifacts in S3 buckets.
        
        This overrides the base implementation to use S3 storage.
        """
        if not self.artifacts:
            self.logger.debug("No artifacts to store")
            return
            
        self.logger.info(f"Storing {len(self.artifacts)} artifacts to S3")
        
        private_bucket_name = self.config.get('private_bucket')
        artifacts_stored = 0
        
        for artifact in self.artifacts:
            try:
                artifact_id = artifact['id']
                artifact_type = artifact['type']
                content = artifact['content']
                metadata = artifact['metadata']
                
                # Generate S3 key based on metadata
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                s3_key = f"artifacts/{artifact_type}/{timestamp}_{artifact_id}"
                
                # Handle different content types
                if isinstance(content, str) and os.path.isfile(content):
                    # Content is a file path
                    self.s3_client.upload_file(
                        Filename=content,
                        Bucket=private_bucket_name,
                        Key=s3_key,
                        ExtraArgs={'Metadata': {k: str(v) for k, v in metadata.items()}}
                    )
                    self.logger.info(f"Uploaded file artifact {artifact_id} to {s3_key}")
                    
                elif isinstance(content, str):
                    # Content is a string
                    self.s3_client.put_object(
                        Bucket=private_bucket_name,
                        Key=s3_key,
                        Body=content,
                        Metadata={k: str(v) for k, v in metadata.items()}
                    )
                    self.logger.info(f"Uploaded string artifact {artifact_id} to {s3_key}")
                    
                elif isinstance(content, bytes):
                    # Content is bytes
                    self.s3_client.put_object(
                        Bucket=private_bucket_name,
                        Key=s3_key,
                        Body=content,
                        Metadata={k: str(v) for k, v in metadata.items()}
                    )
                    self.logger.info(f"Uploaded bytes artifact {artifact_id} to {s3_key}")
                    
                elif isinstance(content, dict) or isinstance(content, list):
                    # Content is JSON-serializable
                    self.s3_client.put_object(
                        Bucket=private_bucket_name,
                        Key=s3_key,
                        Body=json.dumps(content),
                        ContentType='application/json',
                        Metadata={k: str(v) for k, v in metadata.items()}
                    )
                    self.logger.info(f"Uploaded JSON artifact {artifact_id} to {s3_key}")
                
                else:
                    self.logger.warning(f"Unsupported artifact content type for {artifact_id}")
                    continue
                
                artifacts_stored += 1
                
            except Exception as e:
                self.logger.error(f"Error storing artifact {artifact['id']}: {str(e)}")
        
        self.logger.info(f"Successfully stored {artifacts_stored}/{len(self.artifacts)} artifacts")
    
    # Additional S3-specific methods
    
    def upload_iso(self, iso_path: str, server_id: str, hostname: str, 
                   version: str, publish: bool = True) -> Dict[str, Any]:
        """
        Upload an ISO to S3 with proper metadata.
        
        Args:
            iso_path: Path to the ISO file
            server_id: Server ID (e.g., 01)
            hostname: Server hostname
            version: OpenShift version
            publish: Whether to publish to public bucket
            
        Returns:
            Dictionary with upload results
        """
        # Verify file exists
        if not os.path.isfile(iso_path):
            raise FileNotFoundError(f"ISO file not found: {iso_path}")
            
        # Generate timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        
        # Generate S3 key
        private_key = f"isos/server-{server_id}-{hostname}-{version}-{timestamp}.iso"
        
        # Upload to private bucket
        try:
            # Calculate MD5 for integrity verification
            md5_hash = hashlib.md5()
            with open(iso_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
            
            # Set metadata
            metadata = {
                'server_id': server_id,
                'hostname': hostname,
                'version': version,
                'timestamp': timestamp,
                'md5': md5_hash.hexdigest()
            }
            
            # Upload to private bucket
            self.s3_client.upload_file(
                Filename=iso_path,
                Bucket=self.config.get('private_bucket'),
                Key=private_key,
                ExtraArgs={'Metadata': metadata}
            )
            
            self.logger.info(f"Uploaded ISO to private bucket: {private_key}")
            
            # Sync to public bucket if requested
            public_key = None
            if publish:
                public_key = self.sync_to_public(private_key, version)
            
            return {
                'success': True,
                'private_key': private_key,
                'public_key': public_key,
                'metadata': metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error uploading ISO: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_to_public(self, private_key: str, version: str) -> Optional[str]:
        """
        Sync an object from private to public bucket with standardized naming.
        
        Args:
            private_key: Key in private bucket
            version: OpenShift version
            
        Returns:
            Public key if successful, None otherwise
        """
        try:
            # Determine target path in public bucket
            # Ensure version has format like "4.18" (major.minor)
            version_parts = version.split('.')
            if len(version_parts) >= 2:
                version_folder = f"isos/{version_parts[0]}.{version_parts[1]}/"
            else:
                version_folder = f"isos/{version}/"
            
            public_key = f"{version_folder}agent.x86_64.iso"
            
            # Copy from private to public
            copy_source = {
                'Bucket': self.config.get('private_bucket'),
                'Key': private_key
            }
            
            self.s3_client.copy_object(
                Bucket=self.config.get('public_bucket'),
                Key=public_key,
                CopySource=copy_source
            )
            
            self.logger.info(f"Synced ISO to public bucket: {public_key}")
            
            # Generate public URL
            endpoint = self.config.get('endpoint')
            public_bucket = self.config.get('public_bucket')
            public_url = f"http://{endpoint}/{public_bucket}/{public_key}"
            
            self.logger.info(f"Public URL: {public_url}")
            
            return public_key
            
        except Exception as e:
            self.logger.error(f"Error syncing to public bucket: {str(e)}")
            return None
    
    def unpublish(self, version: str) -> bool:
        """
        Remove an ISO from public access.
        
        Args:
            version: OpenShift version
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine path in public bucket
            version_parts = version.split('.')
            if len(version_parts) >= 2:
                version_folder = f"isos/{version_parts[0]}.{version_parts[1]}/"
            else:
                version_folder = f"isos/{version}/"
            
            public_key = f"{version_folder}agent.x86_64.iso"
            
            # Delete from public bucket
            self.s3_client.delete_object(
                Bucket=self.config.get('public_bucket'),
                Key=public_key
            )
            
            self.logger.info(f"Removed ISO from public access: {public_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unpublish: {str(e)}")
            return False
    
    def list_isos(self, server_id: Optional[str] = None, 
                 hostname: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List ISOs in the private bucket with optional filtering.
        
        Args:
            server_id: Optional server ID filter
            hostname: Optional hostname filter
            
        Returns:
            List of ISO objects with metadata
        """
        try:
            result = []
            
            # Get all objects from private bucket with isos/ prefix
            objects = list(self.s3_resource.Bucket(self.config.get('private_bucket')).
                          objects.filter(Prefix='isos/'))
            
            for obj in objects:
                # Skip folders
                if obj.key.endswith('/'):
                    continue
                    
                try:
                    # Get object metadata
                    response = self.s3_client.head_object(
                        Bucket=self.config.get('private_bucket'),
                        Key=obj.key
                    )
                    
                    # Extract useful metadata
                    metadata = response.get('Metadata', {})
                    
                    # Skip if not matching filters
                    if server_id and metadata.get('server_id') != server_id:
                        continue
                        
                    if hostname and metadata.get('hostname') != hostname:
                        continue
                    
                    # Add to result
                    result.append({
                        'key': obj.key,
                        'size': response.get('ContentLength', 0),
                        'last_modified': response.get('LastModified').isoformat() \
                            if response.get('LastModified') else None,
                        'metadata': metadata
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Error getting metadata for {obj.key}: {str(e)}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing ISOs: {str(e)}")
            return []

if __name__ == "__main__":
    # Example usage
    config = {
        'create_buckets_if_missing': True,
        'create_metadata_index': True
    }
    
    s3_component = S3Component(config)
    
    # Execute all phases
    results = s3_component.execute()
    
    print(json.dumps(results, indent=2))
