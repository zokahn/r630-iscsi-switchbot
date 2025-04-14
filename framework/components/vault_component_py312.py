#!/usr/bin/env python3
"""
Vault Component for Discovery-Processing-Housekeeping Pattern

This component manages Hashicorp Vault integration for secure secret storage
using the discovery-processing-housekeeping pattern.

Enhanced with Python 3.12 type annotations and features.
"""

import os
import sys
import json
import logging
import datetime
import requests
import tempfile
from typing import (
    Dict, Any, Optional, List, Union, Tuple, TypedDict, 
    Literal, cast, Protocol, NotRequired
)

# Import base component
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.base_component_py312 import BaseComponent, ComponentConfig

# TypedDict definitions for Vault component
class VaultConfig(ComponentConfig, total=False):
    """TypedDict for Vault component configuration."""
    vault_addr: str
    vault_token: Optional[str]
    vault_role_id: Optional[str]
    vault_secret_id: Optional[str]
    vault_auth_method: Literal['token', 'approle']
    vault_mount_point: str
    vault_path_prefix: str
    vault_namespace: Optional[str]
    verify_ssl: bool
    create_path_prefix: bool
    min_token_ttl: int


class TokenData(TypedDict, total=False):
    """TypedDict for token data."""
    ttl: int
    renewable: bool
    policies: List[str]
    accessor: str
    creation_time: int
    expire_time: Optional[str]
    display_name: str


class VaultHealthData(TypedDict):
    """TypedDict for Vault health data."""
    initialized: bool
    sealed: bool
    standby: bool
    performance_standby: bool
    replication_performance_mode: str
    replication_dr_mode: str
    server_time_utc: int
    version: str
    cluster_name: str
    cluster_id: str


class MountInfo(TypedDict):
    """TypedDict for mount information."""
    path: str
    type: str
    description: str
    options: Dict[str, Any]


class AuthMethodInfo(TypedDict):
    """TypedDict for auth method information."""
    path: str
    type: str
    description: str


class DiscoveryResults(TypedDict, total=False):
    """TypedDict for Vault discovery results."""
    connected: bool
    vault_version: Optional[str]
    mounts: List[MountInfo]
    auth_methods: List[AuthMethodInfo] 
    kv_version: Optional[str]
    namespace: Optional[str]
    mount_point_exists: bool
    token_valid: bool
    token_ttl: int
    token_policies: List[str]
    sealed: bool
    connection_error: str
    auth_error: str
    auth_method: str
    authenticated: bool
    token_error: str
    mounts_error: str
    auth_methods_error: str
    kv_version_error: str


class ProcessingResults(TypedDict, total=False):
    """TypedDict for Vault processing results."""
    initialized: bool
    path_created: bool
    permissions_verified: bool
    error: str
    permissions_error: str


class HousekeepingResults(TypedDict, total=False):
    """TypedDict for Vault housekeeping results."""
    token_status: Literal['valid', 'invalid', 'missing', 'error', 'unknown']
    token_renewable: bool
    token_ttl: int
    renewed: bool
    token_policies: List[str]
    token_error: str
    new_ttl: int
    renew_error: str


class VaultComponent(BaseComponent):
    """
    Component for Hashicorp Vault integration.
    
    Manages secure storage and retrieval of secrets using Hashicorp Vault.
    Provides transparent access to secrets for other components.
    
    Enhanced with Python 3.12 type annotations.
    """
    
    # Default configuration
    DEFAULT_CONFIG: VaultConfig = {
        'vault_addr': os.environ.get('VAULT_ADDR', 'http://127.0.0.1:8200'),
        'vault_token': os.environ.get('VAULT_TOKEN'),
        'vault_role_id': os.environ.get('VAULT_ROLE_ID'),
        'vault_secret_id': os.environ.get('VAULT_SECRET_ID'),
        'vault_auth_method': 'token',  # token, approle
        'vault_mount_point': 'secret',  # KV secrets engine mount point
        'vault_path_prefix': 'r630-switchbot',  # Path prefix for secrets
        'vault_namespace': os.environ.get('VAULT_NAMESPACE'),
        'verify_ssl': True
    }
    
    def __init__(self, config: VaultConfig, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the Vault component.
        
        Args:
            config: Configuration dictionary for the component
            logger: Optional logger instance
        """
        # Merge provided config with defaults using Python 3.12 dict merge operator
        merged_config = self.DEFAULT_CONFIG | config
        
        # Initialize base component
        super().__init__(merged_config, logger)
        
        # Set up base URL and headers
        self.base_url: str = self.config['vault_addr'].rstrip('/')
        self.headers: Dict[str, str] = {'X-Vault-Token': self.config.get('vault_token', '')}
        self.verify_ssl: bool = self.config.get('verify_ssl', True)
        
        # Initialize connection state
        self.connected: bool = False
        self.client_token: Optional[str] = self.config.get('vault_token')
        self.kv_version: Optional[str] = None
        
        # Initialize specific result types
        self.discovery_results: DiscoveryResults = {}
        self.processing_results: ProcessingResults = {}
        self.housekeeping_results: HousekeepingResults = {}
        
        self.logger.info(f"VaultComponent initialized with addr: {self.config.get('vault_addr')}")
    
    def discover(self) -> Dict[str, Any]:
        """
        Discovery phase: Examine the Vault environment.
        
        Checks connectivity, auth methods, secrets engines, and verifies access.
        
        Returns:
            Dictionary of discovery results
        """
        self.timestamps['discover_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting discovery phase for {self.component_name}")
        
        try:
            # Initialize discovery results
            self.discovery_results = {
                'connected': False,
                'vault_version': None,
                'mounts': [],
                'auth_methods': [],
                'kv_version': None,
                'namespace': self.config.get('vault_namespace'),
                'mount_point_exists': False,
                'token_valid': False
            }
            
            # Check connectivity to Vault
            self._check_vault_connectivity()
            
            # Check auth methods if connected
            if self.connected:
                # Perform authentication if needed
                if not self.client_token and self.config.get('vault_auth_method') == 'approle':
                    self._authenticate_approle()
                
                # Check token validity
                self._check_token_validity()
                
                # Get available mounts
                self._get_mounts()
                
                # Get available auth methods
                self._get_auth_methods()
                
                # Check KV version
                self._check_kv_version()
                
                # Create initial metadata
                self._create_metadata()
            
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
    
    def _check_vault_connectivity(self) -> None:
        """
        Check connectivity to Vault server.
        """
        try:
            # Health check doesn't require authentication
            headers: Dict[str, str] = {}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            response = requests.get(
                f"{self.base_url}/v1/sys/health",
                headers=headers,
                verify=self.verify_ssl
            )
            
            # Status codes that indicate Vault is running (in various states)
            valid_status_codes = [200, 429, 472, 473, 501, 503]
            
            if response.status_code in valid_status_codes:
                # Connection successful
                health_data: VaultHealthData = response.json()
                
                # Update discovery results with Python 3.12 dict update
                self.discovery_results |= {
                    'connected': True,
                    'vault_version': health_data.get('version'),
                    'sealed': health_data.get('sealed', False)
                }
                
                self.connected = True
                self.logger.info(f"Connected to Vault server version {health_data.get('version')}")
            else:
                self.logger.error(f"Failed to connect to Vault server: HTTP {response.status_code}")
                self.discovery_results['connection_error'] = f"HTTP Error: {response.status_code}"
                self.connected = False
        except Exception as e:
            self.logger.error(f"Error connecting to Vault: {str(e)}")
            self.discovery_results['connection_error'] = str(e)
            self.connected = False
    
    def _authenticate_approle(self) -> None:
        """
        Authenticate using AppRole method.
        """
        try:
            role_id = self.config.get('vault_role_id')
            secret_id = self.config.get('vault_secret_id')
            
            if not role_id or not secret_id:
                self.logger.error("Missing role_id or secret_id for AppRole authentication")
                self.discovery_results['auth_error'] = "Missing AppRole credentials"
                return
            
            headers: Dict[str, str] = {}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
            
            data = {
                'role_id': role_id,
                'secret_id': secret_id
            }
            
            response = requests.post(
                f"{self.base_url}/v1/auth/approle/login",
                json=data,
                headers=headers,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                self.client_token = auth_data.get('auth', {}).get('client_token')
                if self.client_token:
                    self.headers['X-Vault-Token'] = self.client_token
                    self.logger.info("Successfully authenticated using AppRole")
                    self.discovery_results['auth_method'] = 'approle'
                    self.discovery_results['authenticated'] = True
                else:
                    self.logger.error("AppRole authentication succeeded but no token returned")
                    self.discovery_results['auth_error'] = "No token returned"
            else:
                self.logger.error(f"AppRole authentication failed: HTTP {response.status_code}")
                self.discovery_results['auth_error'] = f"HTTP Error: {response.status_code}"
                if response.text:
                    self.logger.debug(f"Response: {response.text}")
        except Exception as e:
            self.logger.error(f"Error during AppRole authentication: {str(e)}")
            self.discovery_results['auth_error'] = str(e)
    
    def _check_token_validity(self) -> None:
        """
        Check if the token is valid.
        """
        if not self.client_token:
            self.logger.warning("No token available to check")
            self.discovery_results['token_valid'] = False
            return
            
        try:
            headers = {'X-Vault-Token': self.client_token}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            response = requests.get(
                f"{self.base_url}/v1/auth/token/lookup-self",
                headers=headers,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                token_data: TokenData = response.json().get('data', {})
                ttl = token_data.get('ttl', 0)
                policies = token_data.get('policies', [])
                
                # Update discovery results with Python 3.12 dict update
                self.discovery_results |= {
                    'token_valid': True,
                    'token_ttl': ttl,
                    'token_policies': policies
                }
                
                self.logger.info(f"Token is valid (TTL: {ttl}s, Policies: {', '.join(policies)})")
            else:
                self.logger.warning(f"Token is invalid or expired: HTTP {response.status_code}")
                self.discovery_results['token_valid'] = False
                self.discovery_results['token_error'] = f"HTTP Error: {response.status_code}"
        except Exception as e:
            self.logger.error(f"Error checking token validity: {str(e)}")
            self.discovery_results['token_valid'] = False
            self.discovery_results['token_error'] = str(e)
    
    def _get_mounts(self) -> None:
        """
        Get available secret engine mounts.
        """
        try:
            headers = {'X-Vault-Token': self.client_token or ''}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            response = requests.get(
                f"{self.base_url}/v1/sys/mounts",
                headers=headers,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                mounts_data = response.json()
                
                # Process mount points
                mounts: List[MountInfo] = []
                mount_point = self.config.get('vault_mount_point', '')
                mount_point_exists = False
                
                # Use Python 3.12 pattern matching for dict items
                for path, info in mounts_data.items():
                    # Clean up path (remove trailing slash)
                    clean_path = path.rstrip('/')
                    
                    # Store mount info
                    mount_info: MountInfo = {
                        'path': clean_path,
                        'type': info.get('type', ''),
                        'description': info.get('description', ''),
                        'options': info.get('options', {})
                    }
                    mounts.append(mount_info)
                    
                    # Check if our configured mount point exists
                    if clean_path == mount_point:
                        mount_point_exists = True
                        
                        # For KV secret engines, get the version
                        if info.get('type') == 'kv':
                            kv_version = info.get('options', {}).get('version', '1')
                            self.kv_version = kv_version
                            self.discovery_results['kv_version'] = kv_version
                
                self.discovery_results['mounts'] = mounts
                self.discovery_results['mount_point_exists'] = mount_point_exists
                
                self.logger.info(f"Found {len(mounts)} secret engine mounts")
                if mount_point_exists:
                    self.logger.info(f"Mount point '{mount_point}' exists (KV version: {self.kv_version})")
                else:
                    self.logger.warning(f"Mount point '{mount_point}' does not exist")
            else:
                self.logger.error(f"Failed to get mounts: HTTP {response.status_code}")
                self.discovery_results['mounts_error'] = f"HTTP Error: {response.status_code}"
        except Exception as e:
            self.logger.error(f"Error getting mounts: {str(e)}")
            self.discovery_results['mounts_error'] = str(e)
    
    def _get_auth_methods(self) -> None:
        """
        Get available authentication methods.
        """
        try:
            headers = {'X-Vault-Token': self.client_token or ''}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            response = requests.get(
                f"{self.base_url}/v1/sys/auth",
                headers=headers,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                
                # Process auth methods - optimized with list comprehension in Python 3.12
                auth_methods: List[AuthMethodInfo] = [
                    {
                        'path': path.rstrip('/'),
                        'type': info.get('type', ''),
                        'description': info.get('description', '')
                    }
                    for path, info in auth_data.items()
                ]
                
                self.discovery_results['auth_methods'] = auth_methods
                self.logger.info(f"Found {len(auth_methods)} authentication methods")
            else:
                self.logger.error(f"Failed to get auth methods: HTTP {response.status_code}")
                self.discovery_results['auth_methods_error'] = f"HTTP Error: {response.status_code}"
        except Exception as e:
            self.logger.error(f"Error getting auth methods: {str(e)}")
            self.discovery_results['auth_methods_error'] = str(e)
    
    def _check_kv_version(self) -> None:
        """
        Check KV secrets engine version.
        """
        mount_point = self.config.get('vault_mount_point', '')
        
        # If we already got KV version from mounts, use that
        if self.kv_version:
            self.logger.info(f"KV version {self.kv_version} detected from mount information")
            return
            
        # Otherwise try to determine by behavior
        try:
            # Try KV v2 metadata endpoint
            headers = {'X-Vault-Token': self.client_token or ''}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            response = requests.get(
                f"{self.base_url}/v1/{mount_point}/metadata",
                headers=headers,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                # KV v2 supports metadata endpoint
                self.kv_version = '2'
                self.discovery_results['kv_version'] = '2'
                self.logger.info(f"KV version 2 detected based on metadata endpoint")
                return
            
            # Try KV v1 direct access
            response = requests.get(
                f"{self.base_url}/v1/{mount_point}",
                headers=headers,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                # Likely KV v1
                self.kv_version = '1'
                self.discovery_results['kv_version'] = '1'
                self.logger.info(f"KV version 1 detected based on direct access")
                return
                
            # If neither worked, set to default
            self.logger.warning("Could not determine KV version, defaulting to version 2")
            self.kv_version = '2'
            self.discovery_results['kv_version'] = '2'
            
        except Exception as e:
            self.logger.error(f"Error checking KV version: {str(e)}")
            self.discovery_results['kv_version_error'] = str(e)
            # Default to v2 if we can't determine
            self.kv_version = '2'
            self.discovery_results['kv_version'] = '2'
    
    def _create_metadata(self) -> None:
        """
        Create initial metadata about Vault configuration.
        """
        # Nothing to do in discovery phase
        pass
    
    def process(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processing phase: Configure Vault access.
        
        Sets up authentication, creates necessary paths, and verifies permissions.
        
        Args:
            config: Optional additional configuration for processing
            
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
                'initialized': False,
                'path_created': False,
                'permissions_verified': False
            }
            
            # Check if we are connected and authenticated
            if not self.connected or not self.discovery_results.get('token_valid', False):
                self.logger.error("Not connected or authenticated to Vault")
                self.processing_results['error'] = "Not connected or authenticated"
                return self.processing_results
            
            # For Vault component, processing phase is mainly about verification
            # and initial setup of path structure
            
            # Create path prefix if configured to do so
            if self.config.get('create_path_prefix', False):
                self._create_path_prefix()
            
            # Verify permissions
            self._verify_permissions()
            
            # Mark component as initialized
            self.processing_results['initialized'] = True
            
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
    
    def _create_path_prefix(self) -> None:
        """
        Create path prefix structure in Vault.
        """
        path_prefix = self.config.get('vault_path_prefix')
        if not path_prefix:
            self.logger.info("No path prefix configured, skipping creation")
            return
            
        # For KV v2, we might want to create metadata structure
        # But KV engines automatically create paths when data is written
        # so there's nothing to do here for now
        self.logger.info(f"Path prefix '{path_prefix}' will be created automatically when data is written")
        self.processing_results['path_created'] = True
    
    def _verify_permissions(self) -> None:
        """
        Verify that we have necessary permissions for the configured paths.
        """
        mount_point = self.config.get('vault_mount_point', '')
        path_prefix = self.config.get('vault_path_prefix', '')
        
        # Test writing and reading a secret
        test_key = f"test-{datetime.datetime.now().timestamp()}"
        test_value = f"test-value-{datetime.datetime.now().timestamp()}"
        
        try:
            # Write test secret
            secret_path = f"{path_prefix}/test"
            result = self.put_secret(secret_path, {test_key: test_value})
            
            if not result:
                self.logger.error(f"Failed to write test secret to {secret_path}")
                self.processing_results['permissions_verified'] = False
                self.processing_results['permissions_error'] = "Write permission denied"
                return
                
            # Read test secret
            secret_data = self.get_secret(secret_path)
            if not secret_data or not isinstance(secret_data, dict):
                self.logger.error(f"Failed to read test secret from {secret_path}")
                self.processing_results['permissions_verified'] = False
                self.processing_results['permissions_error'] = "Read permission denied"
                return
                
            # Verify value
            if secret_data.get(test_key) != test_value:
                self.logger.error(f"Test secret verification failed - values don't match")
                self.processing_results['permissions_verified'] = False
                self.processing_results['permissions_error'] = "Value verification failed"
                return
                
            # Delete test secret (KV v2 only)
            if self.kv_version == '2':
                headers = {'X-Vault-Token': self.client_token or ''}
                if vault_namespace := self.config.get('vault_namespace'):
                    headers['X-Vault-Namespace'] = vault_namespace
                    
                response = requests.delete(
                    f"{self.base_url}/v1/{mount_point}/data/{secret_path}",
                    headers=headers,
                    verify=self.verify_ssl
                )
                
                if response.status_code not in [204, 200]:
                    self.logger.warning(f"Failed to delete test secret: HTTP {response.status_code}")
            
            # If we got here, permissions are verified
            self.logger.info(f"Successfully verified read/write permissions")
            self.processing_results['permissions_verified'] = True
            
        except Exception as e:
            self.logger.error(f"Error verifying permissions: {str(e)}")
            self.processing_results['permissions_verified'] = False
            self.processing_results['permissions_error'] = str(e)
    
    def housekeep(self) -> Dict[str, Any]:
        """
        Housekeeping phase: Verify and clean up.
        
        For Vault, this is mainly about checking token status and ensuring
        the component can continue to function.
        
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
                'token_status': 'unknown',
                'token_renewable': False,
                'token_ttl': 0,
                'renewed': False
            }
            
            # Check token status
            self._check_token_status()
            
            # Renew token if needed and possible
            if (self.housekeeping_results.get('token_renewable', False) and 
                self.housekeeping_results.get('token_ttl', 0) < self.config.get('min_token_ttl', 3600)):
                self._renew_token()
            
            # Mark as executed
            self.phases_executed['housekeep'] = True
            
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
    
    def _check_token_status(self) -> None:
        """
        Check current token status.
        """
        if not self.client_token:
            self.logger.warning("No token available to check")
            self.housekeeping_results['token_status'] = 'missing'
            return
            
        try:
            headers = {'X-Vault-Token': self.client_token}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            response = requests.get(
                f"{self.base_url}/v1/auth/token/lookup-self",
                headers=headers,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                token_data: TokenData = response.json().get('data', {})
                ttl = token_data.get('ttl', 0)
                renewable = token_data.get('renewable', False)
                policies = token_data.get('policies', [])
                
                # Update housekeeping results with Python 3.12 dict update
                self.housekeeping_results |= {
                    'token_status': 'valid',
                    'token_ttl': ttl,
                    'token_renewable': renewable,
                    'token_policies': policies
                }
                
                self.logger.info(f"Token is valid (TTL: {ttl}s, Renewable: {renewable})")
            else:
                self.logger.warning(f"Token is invalid or expired: HTTP {response.status_code}")
                self.housekeeping_results['token_status'] = 'invalid'
                self.housekeeping_results['token_error'] = f"HTTP Error: {response.status_code}"
        except Exception as e:
            self.logger.error(f"Error checking token status: {str(e)}")
            self.housekeeping_results['token_status'] = 'error'
            self.housekeeping_results['token_error'] = str(e)
    
    def _renew_token(self) -> None:
        """
        Renew the current token.
        """
        try:
            headers = {'X-Vault-Token': self.client_token or ''}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            response = requests.post(
                f"{self.base_url}/v1/auth/token/renew-self",
                headers=headers,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                renew_data = response.json()
                ttl = renew_data.get('auth', {}).get('lease_duration', 0)
                
                # Update housekeeping results with Python 3.12 dict update
                self.housekeeping_results |= {
                    'renewed': True,
                    'new_ttl': ttl
                }
                
                self.logger.info(f"Successfully renewed token (New TTL: {ttl}s)")
            else:
                self.logger.warning(f"Failed to renew token: HTTP {response.status_code}")
                self.housekeeping_results['renewed'] = False
                self.housekeeping_results['renew_error'] = f"HTTP Error: {response.status_code}"
        except Exception as e:
            self.logger.error(f"Error renewing token: {str(e)}")
            self.housekeeping_results['renewed'] = False
            self.housekeeping_results['renew_error'] = str(e)
    
    # Public methods for secret management
    
    def get_secret(self, path: str, key: Optional[str] = None) -> Union[Dict[str, Any], Any, None]:
        """
        Get a secret from Vault.
        
        Args:
            path: Path to the secret without the mount prefix
            key: Optional specific key to retrieve from the secret
            
        Returns:
            The secret data, a specific value if key was provided, or None if not found
        """
        if not self.connected or not self.client_token:
            self.logger.warning("Not connected or authenticated to Vault")
            return None
            
        mount_point = self.config.get('vault_mount_point', '')
        path_prefix = self.config.get('vault_path_prefix', '')
        
        # Use path prefix if not starting with /
        if path_prefix and not path.startswith('/'):
            full_path = f"{path_prefix}/{path}"
        else:
            full_path = path.lstrip('/')
            
        try:
            headers = {'X-Vault-Token': self.client_token}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            # KV v2 API
            if self.kv_version == '2':
                response = requests.get(
                    f"{self.base_url}/v1/{mount_point}/data/{full_path}",
                    headers=headers,
                    verify=self.verify_ssl
                )
            # KV v1 API
            else:
                response = requests.get(
                    f"{self.base_url}/v1/{mount_point}/{full_path}",
                    headers=headers,
                    verify=self.verify_ssl
                )
                
            if response.status_code == 200:
                secret_data = response.json()
                
                # Extract data based on KV version
                if self.kv_version == '2':
                    data = secret_data.get('data', {}).get('data', {})
                else:
                    data = secret_data.get('data', {})
                
                # Return specific key if requested
                if key is not None:
                    return data.get(key)
                    
                return data
                
            elif response.status_code == 404:
                self.logger.warning(f"Secret not found at {full_path}")
                return None
            else:
                self.logger.error(f"Failed to get secret: HTTP {response.status_code}")
                if response.text:
                    self.logger.debug(f"Response: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving secret: {str(e)}")
            return None
    
    def put_secret(self, path: str, data: Dict[str, Any]) -> bool:
        """
        Store a secret in Vault.
        
        Args:
            path: Path to store the secret without the mount prefix
            data: Dictionary of key/value pairs to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not self.client_token:
            self.logger.warning("Not connected or authenticated to Vault")
            return False
            
        mount_point = self.config.get('vault_mount_point', '')
        path_prefix = self.config.get('vault_path_prefix', '')
        
        # Use path prefix if not starting with /
        if path_prefix and not path.startswith('/'):
            full_path = f"{path_prefix}/{path}"
        else:
            full_path = path.lstrip('/')
            
        try:
            headers = {'X-Vault-Token': self.client_token}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            # KV v2 API
            if self.kv_version == '2':
                # Create payload with data wrapped in 'data' field
                payload = {'data': data}
                
                response = requests.post(
                    f"{self.base_url}/v1/{mount_point}/data/{full_path}",
                    headers=headers,
                    json=payload,
                    verify=self.verify_ssl
                )
            # KV v1 API
            else:
                response = requests.post(
                    f"{self.base_url}/v1/{mount_point}/{full_path}",
                    headers=headers,
                    json=data,
                    verify=self.verify_ssl
                )
                
            if response.status_code in [200, 201, 204]:
                self.logger.info(f"Successfully stored secret at {full_path}")
                return True
            else:
                self.logger.error(f"Failed to store secret: HTTP {response.status_code}")
                if response.text:
                    self.logger.debug(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error storing secret: {str(e)}")
            return False
    
    def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from Vault.
        
        Args:
            path: Path to the secret without the mount prefix
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not self.client_token:
            self.logger.warning("Not connected or authenticated to Vault")
            return False
            
        mount_point = self.config.get('vault_mount_point', '')
        path_prefix = self.config.get('vault_path_prefix', '')
        
        # Use path prefix if not starting with /
        if path_prefix and not path.startswith('/'):
            full_path = f"{path_prefix}/{path}"
        else:
            full_path = path.lstrip('/')
            
        try:
            headers = {'X-Vault-Token': self.client_token}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            # KV v2 API
            if self.kv_version == '2':
                response = requests.delete(
                    f"{self.base_url}/v1/{mount_point}/data/{full_path}",
                    headers=headers,
                    verify=self.verify_ssl
                )
            # KV v1 API
            else:
                response = requests.delete(
                    f"{self.base_url}/v1/{mount_point}/{full_path}",
                    headers=headers,
                    verify=self.verify_ssl
                )
                
            if response.status_code in [200, 204]:
                self.logger.info(f"Successfully deleted secret at {full_path}")
                return True
            elif response.status_code == 404:
                self.logger.warning(f"Secret not found at {full_path}")
                return False
            else:
                self.logger.error(f"Failed to delete secret: HTTP {response.status_code}")
                if response.text:
                    self.logger.debug(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting secret: {str(e)}")
            return False
    
    def list_secrets(self, path: str = "") -> List[str]:
        """
        List secrets at a specific path in Vault.
        
        Args:
            path: Path to list secrets at (without mount prefix)
            
        Returns:
            List of secret names or paths
        """
        if not self.connected or not self.client_token:
            self.logger.warning("Not connected or authenticated to Vault")
            return []
            
        mount_point = self.config.get('vault_mount_point', '')
        path_prefix = self.config.get('vault_path_prefix', '')
        
        # Use path prefix if not starting with / and path is not empty
        if path_prefix and path and not path.startswith('/'):
            full_path = f"{path_prefix}/{path}"
        elif path_prefix and not path:
            full_path = path_prefix
        else:
            full_path = path.lstrip('/')
            
        try:
            headers = {'X-Vault-Token': self.client_token}
            if vault_namespace := self.config.get('vault_namespace'):
                headers['X-Vault-Namespace'] = vault_namespace
                
            # KV v2 API
            if self.kv_version == '2':
                # For KV v2, list uses metadata endpoint
                response = requests.request(
                    "LIST",
                    f"{self.base_url}/v1/{mount_point}/metadata/{full_path}",
                    headers=headers,
                    verify=self.verify_ssl
                )
            # KV v1 API
            else:
                response = requests.request(
                    "LIST",
                    f"{self.base_url}/v1/{mount_point}/{full_path}",
                    headers=headers,
                    verify=self.verify_ssl
                )
                
            if response.status_code == 200:
                data = response.json()
                keys = data.get('data', {}).get('keys', [])
                
                self.logger.info(f"Listed {len(keys)} secrets at {full_path}")
                return keys
            elif response.status_code == 404:
                self.logger.warning(f"Path not found: {full_path}")
                return []
            else:
                self.logger.error(f"Failed to list secrets: HTTP {response.status_code}")
                if response.text:
                    self.logger.debug(f"Response: {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error listing secrets: {str(e)}")
            return []
