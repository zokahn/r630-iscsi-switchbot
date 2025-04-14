#!/usr/bin/env python3
"""
iSCSI Component for Discovery-Processing-Housekeeping Pattern

This component manages iSCSI targets on TrueNAS using the
discovery-processing-housekeeping pattern.

Enhanced with Python 3.12 type annotations and features.
"""

import os
import sys
import json
import logging
import requests
import urllib3
import datetime
from pathlib import Path
from typing import (
    Dict, Any, Optional, List, Tuple, Union, TypedDict, 
    Literal, Protocol, cast, NotRequired
)

# Import base component
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.base_component_py312 import BaseComponent, ComponentConfig

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# TypedDict definitions for iSCSI component
class ISCSIConfig(ComponentConfig, total=False):
    """TypedDict for iSCSI component configuration."""
    truenas_ip: str
    api_key: Optional[str]
    server_id: Optional[str]
    hostname: Optional[str]
    openshift_version: str
    zvol_size: str
    zfs_pool: str
    dry_run: bool
    discover_only: bool
    cleanup_unused: bool
    zvol_name: str
    target_name: str
    extent_name: str


class SystemInfo(TypedDict, total=False):
    """TypedDict for TrueNAS system information."""
    version: str
    hostname: str
    system_product: str
    uptime: str
    loadavg: List[float]
    physmem: int
    model: str
    cores: int
    physical_cores: int


class StoragePool(TypedDict, total=False):
    """TypedDict for ZFS storage pool information."""
    name: str
    guid: str
    id: int
    free: int
    healthy: bool
    status: str
    size: int
    used: Dict[str, Any]


class ZvolInfo(TypedDict, total=False):
    """TypedDict for ZFS volume information."""
    name: str
    type: str
    id: str
    volsize: Dict[str, Any]
    comments: Optional[str]
    path: str


class TargetInfo(TypedDict, total=False):
    """TypedDict for iSCSI target information."""
    id: int
    name: str
    alias: Optional[str]
    mode: str
    groups: List[Dict[str, Any]]


class ExtentInfo(TypedDict, total=False):
    """TypedDict for iSCSI extent information."""
    id: int
    name: str
    type: str
    disk: str
    blocksize: int
    pblocksize: bool
    comment: str
    insecure_tpc: bool
    xen: bool
    rpm: str
    ro: bool


class TargetExtentInfo(TypedDict, total=False):
    """TypedDict for target-extent association."""
    id: int
    target: int
    extent: int
    lunid: int


class SystemHealthInfo(TypedDict, total=False):
    """TypedDict for system health information."""
    cpu_usage: float
    memory_usage: int
    memory_total: int
    memory_percent: float
    alert_count: int
    critical_alert_count: int
    critical_alerts: List[str]
    error: str


class StorageCapacity(TypedDict, total=False):
    """TypedDict for storage capacity information."""
    pool: str
    free_bytes: int
    required_bytes: int
    sufficient: bool
    found: bool
    error: str


class DiscoveryResults(TypedDict, total=False):
    """TypedDict for iSCSI discovery results."""
    connectivity: bool
    system_health: Dict[str, Any]
    iscsi_service: bool
    pools: List[Dict[str, Any]]
    zvols: List[Dict[str, Any]]
    targets: List[Dict[str, Any]]
    extents: List[Dict[str, Any]]
    targetextents: List[Dict[str, Any]]
    system_info: SystemInfo
    connection_error: str
    iscsi_service_data: Dict[str, Any]
    storage_capacity: StorageCapacity


class ProcessingResults(TypedDict, total=False):
    """TypedDict for iSCSI processing results."""
    zvol_created: bool
    target_created: bool
    extent_created: bool
    association_created: bool
    target_id: Optional[int]
    extent_id: Optional[int]
    zvol_existed: bool
    target_existed: bool
    extent_existed: bool
    association_existed: bool
    zvol_error: str
    target_error: str
    extent_error: str
    association_error: str
    iscsi_service_error: str
    skipped: bool


class VerificationResults(TypedDict, total=False):
    """TypedDict for resource verification results."""
    zvol_verified: bool
    target_verified: bool
    extent_verified: bool
    association_verified: bool


class HousekeepingResults(TypedDict, total=False):
    """TypedDict for iSCSI housekeeping results."""
    resources_verified: bool
    unused_resources_found: int
    unused_resources_cleaned: int
    warnings: List[str]
    verification_error: str
    cleanup_error: str
    resource_details_stored: bool


class ResourceDetails(TypedDict, total=False):
    """TypedDict for resource details."""
    zvol_name: str
    target_name: str
    extent_name: str
    target_id: Optional[int]
    extent_id: Optional[int]
    connection_info: Dict[str, Any]
    created_at: str
    config: Dict[str, Any]


class ISCSIComponent(BaseComponent):
    """
    Component for managing iSCSI targets on TrueNAS.
    
    Manages discovering TrueNAS environment, creating iSCSI targets,
    and maintaining iSCSI resources.
    
    Enhanced with Python 3.12 type annotations.
    """
    
    # Default configuration
    DEFAULT_CONFIG: ISCSIConfig = {
        'truenas_ip': '192.168.2.245',
        'api_key': None,
        'server_id': None,
        'hostname': None,
        'openshift_version': 'stable',
        'zvol_size': '500G',
        'zfs_pool': 'test',
        'dry_run': False,
        'discover_only': False,
        'cleanup_unused': False
    }
    
    def __init__(self, config: ISCSIConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the iSCSI component.
        
        Args:
            config: Configuration dictionary for the component
            logger: Optional logger instance
        """
        # Merge provided config with defaults using Python 3.12 dict merge operator
        merged_config = self.DEFAULT_CONFIG | config
        
        # Initialize base component
        super().__init__(merged_config, logger)
        
        # Component-specific initialization
        self.session: Optional[requests.Session] = None
        self.api_url: Optional[str] = None
        
        # Initialize specific result types
        self.discovery_results: DiscoveryResults = {}
        self.processing_results: ProcessingResults = {}
        self.housekeeping_results: HousekeepingResults = {}
        
        # Format resource names
        self._format_resource_names()
        
        self.logger.info(f"ISCSIComponent initialized for server {self.config.get('server_id')}")
    
    def discover(self) -> Dict[str, Any]:
        """
        Discovery phase: Examine the TrueNAS environment.
        
        Checks connectivity, system health, and discovers existing
        iSCSI resources.
        
        Returns:
            Dictionary of discovery results
        """
        self.timestamps['discover_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting discovery phase for {self.component_name}")
        
        try:
            # Initialize discovery results
            self.discovery_results = {
                'connectivity': False,
                'system_health': {},
                'iscsi_service': False,
                'pools': [],
                'zvols': [],
                'targets': [],
                'extents': [],
                'targetextents': []
            }
            
            # 1. Set up API session
            self._setup_api_session()
            
            # 2. Check TrueNAS connectivity
            self._check_truenas_connectivity()
            
            # 3. Check system health
            self._check_system_health()
            
            # 4. Check iSCSI service
            self._check_iscsi_service()
            
            # 5. Discover resources
            self._discover_resources()
            
            # 6. Check storage capacity
            self._check_storage_capacity()
            
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
    
    def process(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processing phase: Create and configure iSCSI resources.
        
        Creates zvols, targets, extents, and associations on TrueNAS.
        
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
        
        # Skip processing if discover_only is set
        if self.config.get('discover_only', False):
            self.logger.info("Skipping processing phase - discover_only is set")
            self.processing_results = {'skipped': True}
            self.phases_executed['process'] = True
            self.timestamps['process_end'] = datetime.datetime.now().isoformat()
            return self.processing_results
        
        try:
            # Initialize processing results
            self.processing_results = {
                'zvol_created': False,
                'target_created': False,
                'extent_created': False,
                'association_created': False,
                'target_id': None,
                'extent_id': None
            }
            
            # 1. Create zvol
            self._create_zvol()
            
            # 2. Create target
            self._create_target()
            
            # 3. Create extent
            self._create_extent()
            
            # 4. Associate target with extent
            self._associate_target_extent()
            
            # 5. Ensure iSCSI service is running
            self._ensure_iscsi_service_running()
            
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
    
    def housekeep(self) -> Dict[str, Any]:
        """
        Housekeeping phase: Verify and clean up iSCSI resources.
        
        Verifies resource creation, performs optional cleanup, and
        records resource details.
        
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
                'resources_verified': False,
                'unused_resources_found': 0,
                'unused_resources_cleaned': 0,
                'warnings': []
            }
            
            # 1. Verify resources
            self._verify_resources()
            
            # 2. Perform cleanup if configured
            if self.config.get('cleanup_unused', False):
                self._cleanup_unused_resources()
            
            # 3. Store resource details as artifact
            self._store_resource_details()
            
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
    
    # Helper methods
    def _format_resource_names(self) -> None:
        """Format resource names based on configuration"""
        if not (server_id := self.config.get('server_id')):
            self.logger.warning("No server_id provided, using 'unknown' as default")
            server_id = 'unknown'
            
        version = self.config.get('openshift_version', 'stable')
        # Use Python 3.12 improved string operations
        version_format = version.replace(".", "_")
        
        # Update config with formatted names
        self.config['zvol_name'] = f"{self.config.get('zfs_pool')}/openshift_installations/r630_{server_id}_{version_format}"
        self.config['target_name'] = f"iqn.2005-10.org.freenas.ctl:iscsi.r630-{server_id}.openshift{version_format}"
        self.config['extent_name'] = f"openshift_r630_{server_id}_{version_format}_extent"
    
    def _setup_api_session(self) -> None:
        """Set up API session with authentication"""
        self.logger.info("Setting up API session")
        
        # Create requests session
        self.session = requests.Session()
        
        # Set up API URL
        truenas_ip = self.config.get('truenas_ip')
        self.api_url = f"https://{truenas_ip}:444/api/v2.0"
        
        # Add API key authentication
        if not (api_key := self.config.get('api_key')):
            self.logger.error("No API key provided for TrueNAS authentication")
            raise ValueError("TrueNAS API key is required")
            
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        
        # Disable SSL verification for self-signed certs
        self.session.verify = False
        
        self.logger.debug(f"API session set up for {self.api_url}")
    
    def _check_truenas_connectivity(self) -> None:
        """Check if TrueNAS API is accessible"""
        self.logger.info("Checking TrueNAS connectivity")
        
        if not self.session or not self.api_url:
            self.logger.error("API session not initialized")
            return
            
        try:
            # Try to get basic system information to validate connection
            response = self.session.get(f"{self.api_url}/system/info")
            response.raise_for_status()
            
            system_info: SystemInfo = response.json()
            self.logger.info(f"Connected to TrueNAS {system_info.get('version', 'unknown version')}")
            self.logger.info(f"System: {system_info.get('hostname', 'unknown')} ({system_info.get('system_product', 'unknown')})")
            
            # Store system info in discovery results
            self.discovery_results['system_info'] = system_info
            self.discovery_results['connectivity'] = True
            
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection Error: Unable to connect to TrueNAS API - {e}")
            self.discovery_results['connectivity'] = False
            self.discovery_results['connection_error'] = str(e)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.logger.error("Authentication Error: Invalid API key")
            else:
                self.logger.error(f"HTTP Error: {e}")
            self.discovery_results['connectivity'] = False
            self.discovery_results['connection_error'] = str(e)
            
        except Exception as e:
            self.logger.error(f"Error checking TrueNAS connectivity: {e}")
            self.discovery_results['connectivity'] = False
            self.discovery_results['connection_error'] = str(e)
    
    def _check_system_health(self) -> None:
        """Check TrueNAS system health"""
        self.logger.info("Checking system health")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping system health check - no connectivity")
            return
            
        try:
            # Check system resources
            response = self.session.get(f"{self.api_url}/reporting/get_data?graphs=cpu,memory,swap")
            response.raise_for_status()
            
            resource_data = response.json()
            health_info: SystemHealthInfo = {}
            
            # Using Python 3.12 dictionary operations for cleaner handling
            if resource_data.get('cpu', []):
                cpu_data = resource_data['cpu'][0].get('data', [])
                if cpu_data:
                    cpu_usage = cpu_data[-1][1]
                    self.logger.info(f"CPU Usage: {cpu_usage:.1f}%")
                    health_info['cpu_usage'] = cpu_usage
            
            if resource_data.get('memory', []):
                memory_data = resource_data['memory'][0].get('data', [])
                if memory_data:
                    memory_usage = memory_data[-1][1]
                    memory_total = memory_data[-1][2]
                    if memory_total > 0:
                        memory_percent = (memory_usage / memory_total) * 100
                        self.logger.info(f"Memory Usage: {memory_percent:.1f}% ({memory_usage/(1024*1024*1024):.1f}GB / {memory_total/(1024*1024*1024):.1f}GB)")
                        
                        # Update health info with Python 3.12 dict merge
                        health_info |= {
                            'memory_usage': memory_usage,
                            'memory_total': memory_total,
                            'memory_percent': memory_percent
                        }
            
            # Check alerts
            response = self.session.get(f"{self.api_url}/alert/list")
            response.raise_for_status()
            
            alerts = response.json()
            # Use Python 3.12 list comprehension with assignment expression 
            critical_alerts = [a for a in alerts if (level := a.get('level')) and level == 'CRITICAL']
            
            # Update with dict merge
            health_info |= {
                'alert_count': len(alerts),
                'critical_alert_count': len(critical_alerts)
            }
            
            if critical_alerts:
                self.logger.warning(f"{len(critical_alerts)} critical alerts found")
                health_info['critical_alerts'] = [a.get('formatted') for a in critical_alerts[:3]]  # first 3 only
            else:
                self.logger.info("No critical alerts found")
            
            self.discovery_results['system_health'] = health_info
            
        except Exception as e:
            self.logger.error(f"Error checking system health: {e}")
            if 'system_health' not in self.discovery_results:
                self.discovery_results['system_health'] = {}
            self.discovery_results['system_health']['error'] = str(e)
    
    def _check_iscsi_service(self) -> None:
        """Check if iSCSI service is running"""
        self.logger.info("Checking iSCSI service")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping iSCSI service check - no connectivity")
            return
            
        try:
            response = self.session.get(f"{self.api_url}/service/id/iscsitarget")
            response.raise_for_status()
            
            service_data = response.json()
            is_running = service_data.get('state') == 'RUNNING'
            
            if is_running:
                self.logger.info("iSCSI service is running")
            else:
                self.logger.warning("iSCSI service is not running")
                
            self.discovery_results['iscsi_service'] = is_running
            self.discovery_results['iscsi_service_data'] = service_data
            
        except Exception as e:
            self.logger.error(f"Error checking iSCSI service: {e}")
            self.discovery_results['iscsi_service'] = False
    
    def _discover_resources(self) -> None:
        """Discover TrueNAS resources"""
        self.logger.info("Discovering iSCSI resources")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping resource discovery - no connectivity")
            return
            
        try:
            # Discover storage pools
            self.logger.info("Discovering storage pools...")
            response = self.session.get(f"{self.api_url}/pool")
            if response.status_code == 200:
                pools = cast(List[StoragePool], response.json())
                self.discovery_results["pools"] = pools
                
                for pool in pools:
                    pool_name = pool.get('name')
                    free_bytes = pool.get('free', 0)
                    free_gb = free_bytes / (1024**3)
                    self.logger.info(f"Pool: {pool_name} ({free_gb:.1f} GB free)")
            
            # Discover existing zvols (volumes)
            self.logger.info("Discovering existing zvols...")
            response = self.session.get(f"{self.api_url}/pool/dataset?type=VOLUME")
            if response.status_code == 200:
                zvols = cast(List[ZvolInfo], response.json())
                self.discovery_results["zvols"] = zvols
                
                if zvols:
                    for zvol in zvols:
                        zvol_name = zvol.get('name')
                        if volsize := zvol.get('volsize', {}):
                            zvol_size = volsize.get('parsed', 0)
                            zvol_size_gb = zvol_size / (1024**3)
                            self.logger.info(f"Zvol: {zvol_name} ({zvol_size_gb:.1f} GB)")
                else:
                    self.logger.info("No zvols found")
            
            # Discover iSCSI targets
            self.logger.info("Discovering iSCSI targets...")
            response = self.session.get(f"{self.api_url}/iscsi/target")
            if response.status_code == 200:
                targets = cast(List[TargetInfo], response.json())
                self.discovery_results["targets"] = targets
                
                if targets:
                    for target in targets:
                        target_id = target.get('id')
                        target_name = target.get('name')
                        self.logger.info(f"Target: {target_name} (ID: {target_id})")
                else:
                    self.logger.info("No targets found")
            
            # Discover iSCSI extents
            self.logger.info("Discovering iSCSI extents...")
            response = self.session.get(f"{self.api_url}/iscsi/extent")
            if response.status_code == 200:
                extents = cast(List[ExtentInfo], response.json())
                self.discovery_results["extents"] = extents
                
                if extents:
                    for extent in extents:
                        extent_id = extent.get('id')
                        extent_name = extent.get('name')
                        extent_type = extent.get('type')
                        extent_path = extent.get('disk')
                        self.logger.info(f"Extent: {extent_name} (ID: {extent_id}, Type: {extent_type}, Path: {extent_path})")
                else:
                    self.logger.info("No extents found")
            
            # Discover target-extent associations
            self.logger.info("Discovering target-extent associations...")
            response = self.session.get(f"{self.api_url}/iscsi/targetextent")
            if response.status_code == 200:
                targetextents = cast(List[TargetExtentInfo], response.json())
                self.discovery_results["targetextents"] = targetextents
                
                if targetextents:
                    for te in targetextents:
                        te_id = te.get('id')
                        target_id = te.get('target')
                        extent_id = te.get('extent')
                        lun_id = te.get('lunid')
                        self.logger.info(f"Association: ID {te_id} (Target: {target_id}, Extent: {extent_id}, LUN: {lun_id})")
                else:
                    self.logger.info("No target-extent associations found")
                    
        except Exception as e:
            self.logger.error(f"Error during resource discovery: {e}")
    
    def _check_storage_capacity(self) -> None:
        """Check if storage pool has enough capacity"""
        self.logger.info("Checking storage capacity")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping storage capacity check - no connectivity")
            return
            
        pool_name = self.config.get('zfs_pool')
        zvol_size = self.config.get('zvol_size')
        
        try:
            # Convert human-readable size to bytes
            required_bytes = self._format_size(zvol_size)
            
            pools = self.discovery_results.get('pools', [])
            for pool in pools:
                if pool.get('name') == pool_name:
                    free_bytes = pool.get('free', 0)
                    free_gb = free_bytes / (1024**3)
                    required_gb = required_bytes / (1024**3)
                    
                    self.logger.info(f"Pool: {pool_name}")
                    self.logger.info(f"Free space: {free_gb:.1f} GB")
                    self.logger.info(f"Required space: {required_gb:.1f} GB")
                    
                    if free_bytes >= required_bytes:
                        self.logger.info(f"Pool {pool_name} has enough free space")
                        self.discovery_results['storage_capacity'] = {
                            'pool': pool_name,
                            'free_bytes': free_bytes,
                            'required_bytes': required_bytes,
                            'sufficient': True
                        }
                    else:
                        self.logger.warning(f"Pool {pool_name} has insufficient free space")
                        self.logger.warning(f"Need {required_gb:.1f} GB but only {free_gb:.1f} GB available")
                        self.discovery_results['storage_capacity'] = {
                            'pool': pool_name,
                            'free_bytes': free_bytes,
                            'required_bytes': required_bytes,
                            'sufficient': False
                        }
                    return
            
            self.logger.warning(f"Pool {pool_name} not found")
            self.discovery_results['storage_capacity'] = {
                'pool': pool_name,
                'found': False,
                'required_bytes': required_bytes
            }
            
        except Exception as e:
            self.logger.error(f"Error checking storage capacity: {e}")
            self.discovery_results['storage_capacity'] = {
                'error': str(e)
            }
    
    def _create_zvol(self) -> None:
        """Create a ZFS volume"""
        self.logger.info("Creating zvol")
        
        # Skip if in dry run mode
        if self.config.get('dry_run', False):
            self.logger.info(f"DRY RUN: Would create zvol {self.config.get('zvol_name')}")
            self.processing_results['zvol_created'] = True
            return
            
        try:
            # Check if zvol already exists
            zvol_name = self.config.get('zvol_name')
            check_url = f"{self.api_url}/pool/dataset/id/{zvol_name}"
            check_response = self.session.get(check_url)
            
            if check_response.status_code == 200:
                self.logger.info(f"Zvol {zvol_name} already exists - using existing zvol")
                # Update processing results with Python 3.12 dict merge
                self.processing_results |= {
                    'zvol_created': True,
                    'zvol_existed': True
                }
                return
                
            # Create parent directory structure first
            parent_path = zvol_name.rsplit('/', 1)[0]
            self._create_parent_directory(parent_path)
            
            # Format the size from human-readable to bytes
            size_bytes = self._format_size(self.config.get('zvol_size'))
            
            # Create the zvol
            payload = {
                "name": zvol_name,
                "type": "VOLUME",
                "volsize": size_bytes,
                "sparse": True
            }
            
            response = self.session.post(f"{self.api_url}/pool/dataset", json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Successfully created zvol {zvol_name}")
            self.processing_results['zvol_created'] = True
            
        except Exception as e:
            self.logger.error(f"Error creating zvol: {e}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
            
            self.processing_results['zvol_created'] = False
            self.processing_results['zvol_error'] = str(e)
            raise
    
    def _create_target(self) -> None:
        """Create an iSCSI target"""
        self.logger.info("Creating iSCSI target")
        
        # Skip if in dry run mode
        if self.config.get('dry_run', False):
            self.logger.info(f"DRY RUN: Would create iSCSI target {self.config.get('target_name')}")
            self.processing_results['target_created'] = True
            self.processing_results['target_id'] = 999  # Dummy ID
            return
            
        try:
            target_name = self.config.get('target_name')
            hostname = self.config.get('hostname', 'unknown')
            
            # Check if target already exists
            query_url = f"{self.api_url}/iscsi/target?name={target_name}"
            query_response = self.session.get(query_url)
            
            if query_response.status_code == 200 and query_response.json():
                targets = query_response.json()
                if targets:
                    target_id = targets[0]['id']
                    self.logger.info(f"Target {target_name} already exists with ID {target_id} - reusing")
                    
                    # Update processing results with Python 3.12 dict merge
                    self.processing_results |= {
                        'target_created': True,
                        'target_existed': True,
                        'target_id': target_id
                    }
                    return
            
            # Create the target
            payload = {
                "name": target_name,
                "alias": f"OpenShift {hostname}",
                "mode": "ISCSI",
                "groups": [{"portal": 3, "initiator": 3, "auth": None}]  # Portal ID 3 and Initiator ID 3 based on system config
            }
            
            response = self.session.post(f"{self.api_url}/iscsi/target", json=payload)
            response.raise_for_status()
            
            target_id = response.json()['id']
            self.logger.info(f"Successfully created target {target_name} with ID {target_id}")
            
            self.processing_results['target_created'] = True
            self.processing_results['target_id'] = target_id
            
        except Exception as e:
            self.logger.error(f"Error creating iSCSI target: {e}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
            
            self.processing_results['target_created'] = False
            self.processing_results['target_error'] = str(e)
            raise
    
    def _create_extent(self) -> None:
        """Create an iSCSI extent"""
        self.logger.info("Creating iSCSI extent")
        
        # Skip if in dry run mode
        if self.config.get('dry_run', False):
            self.logger.info(f"DRY RUN: Would create iSCSI extent {self.config.get('extent_name')}")
            self.processing_results['extent_created'] = True
            self.processing_results['extent_id'] = 999  # Dummy ID
            return
            
        try:
            extent_name = self.config.get('extent_name')
            zvol_name = self.config.get('zvol_name')
            hostname = self.config.get('hostname', 'unknown')
            
            # Check if extent already exists
            query_url = f"{self.api_url}/iscsi/extent?name={extent_name}"
            query_response = self.session.get(query_url)
            
            if query_response.status_code == 200 and query_response.json():
                extents = query_response.json()
                if extents:
                    extent_id = extents[0]['id']
                    self.logger.info(f"Extent {extent_name} already exists with ID {extent_id} - reusing")
                    
                    # Update processing results with Python 3.12 dict merge
                    self.processing_results |= {
                        'extent_created': True,
                        'extent_existed': True,
                        'extent_id': extent_id
                    }
                    return
            
            # Create the extent
            payload = {
                "name": extent_name,
                "type": "DISK",
                "disk": f"zvol/{zvol_name}",
                "blocksize": 512,
                "pblocksize": False,
                "comment": f"OpenShift {hostname} boot image",
                "insecure_tpc": True,
                "xen": False,
                "rpm": "SSD",
                "ro": False
            }
            
            response = self.session.post(f"{self.api_url}/iscsi/extent", json=payload)
            response.raise_for_status()
            
            extent_id = response.json()['id']
            self.logger.info(f"Successfully created extent {extent_name} with ID {extent_id}")
            
            self.processing_results['extent_created'] = True
            self.processing_results['extent_id'] = extent_id
            
        except Exception as e:
            self.logger.error(f"Error creating iSCSI extent: {e}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
            
            self.processing_results['extent_created'] = False
            self.processing_results['extent_error'] = str(e)
            raise
    
    def _associate_target_extent(self) -> None:
        """Associate an iSCSI target with an extent"""
        self.logger.info("Associating target with extent")
        
        # Skip if in dry run mode
        if self.config.get('dry_run', False):
            self.logger.info("DRY RUN: Would associate target with extent")
            self.processing_results['association_created'] = True
            return
            
        try:
            target_id = self.processing_results.get('target_id')
            extent_id = self.processing_results.get('extent_id')
            
            if not target_id or not extent_id:
                self.logger.error("Missing target_id or extent_id - cannot create association")
                self.processing_results['association_created'] = False
                self.processing_results['association_error'] = "Missing target_id or extent_id"
                return
                
            # Check if association already exists
            query_url = f"{self.api_url}/iscsi/targetextent?target={target_id}&extent={extent_id}"
            query_response = self.session.get(query_url)
            
            if query_response.status_code == 200 and query_response.json():
                associations = query_response.json()
                if associations:
                    self.logger.info(f"Target-extent association already exists - skipping")
                    self.processing_results['association_created'] = True
                    self.processing_results['association_existed'] = True
                    return
            
            # Create the association
            payload = {
                "target": target_id,
                "extent": extent_id,
                "lunid": 0
            }
            
            response = self.session.post(f"{self.api_url}/iscsi/targetextent", json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Successfully associated target {target_id} with extent {extent_id}")
            self.processing_results['association_created'] = True
            
        except Exception as e:
            self.logger.error(f"Error creating target-extent association: {e}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
            
            self.processing_results['association_created'] = False
            self.processing_results['association_error'] = str(e)
            raise
    
    def _ensure_iscsi_service_running(self) -> None:
        """Ensure iSCSI service is running"""
        self.logger.info("Ensuring iSCSI service is running")
        
        if self.config.get('dry_run', False):
            self.logger.info("DRY RUN: Would ensure iSCSI service is running")
            return
            
        try:
            # Check if service is already running
            service_url = f"{self.api_url}/service/id/iscsitarget"
            service_response = self.session.get(service_url)
            
            if service_response.status_code == 200:
                service_data = service_response.json()
                service_running = service_data.get('state') == 'RUNNING'
                
                if service_running:
                    self.logger.info("iSCSI service is already running")
                    return
                    
                # Service needs to be started
                self.logger.info("Starting iSCSI service...")
                start_url = f"{self.api_url}/service/start"
                start_payload = {"service": "iscsitarget"}
                
                start_response = self.session.post(start_url, json=start_payload)
                start_response.raise_for_status()
                self.logger.info("Successfully started iSCSI service")
                
            else:
                self.logger.warning(f"Could not check iSCSI service status: {service_response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error ensuring iSCSI service is running: {e}")
            self.processing_results['iscsi_service_error'] = str(e)
    
    def _verify_resources(self) -> None:
        """Verify iSCSI resources"""
        self.logger.info("Verifying resources")
        
        try:
            verification_results: VerificationResults = {
                'zvol_verified': False,
                'target_verified': False,
                'extent_verified': False,
                'association_verified': False
            }
            
            # Verify zvol
            zvol_name = self.config.get('zvol_name')
            check_url = f"{self.api_url}/pool/dataset/id/{zvol_name}"
            check_response = self.session.get(check_url)
            
            if check_response.status_code == 200:
                self.logger.info(f"Verified zvol {zvol_name} exists")
                verification_results['zvol_verified'] = True
            else:
                self.logger.warning(f"Could not verify zvol {zvol_name}")
                self.housekeeping_results['warnings'].append(f"Zvol {zvol_name} verification failed")
            
            # Verify target
            if target_id := self.processing_results.get('target_id'):
                check_url = f"{self.api_url}/iscsi/target/id/{target_id}"
                check_response = self.session.get(check_url)
                
                if check_response.status_code == 200:
                    self.logger.info(f"Verified target with ID {target_id} exists")
                    verification_results['target_verified'] = True
                else:
                    self.logger.warning(f"Could not verify target with ID {target_id}")
                    self.housekeeping_results['warnings'].append(f"Target {target_id} verification failed")
            
            # Verify extent
            if extent_id := self.processing_results.get('extent_id'):
                check_url = f"{self.api_url}/iscsi/extent/id/{extent_id}"
                check_response = self.session.get(check_url)
                
                if check_response.status_code == 200:
                    self.logger.info(f"Verified extent with ID {extent_id} exists")
                    verification_results['extent_verified'] = True
                else:
                    self.logger.warning(f"Could not verify extent with ID {extent_id}")
                    self.housekeeping_results['warnings'].append(f"Extent {extent_id} verification failed")
            
            # Verify association
            if (target_id := self.processing_results.get('target_id')) and (extent_id := self.processing_results.get('extent_id')):
                check_url = f"{self.api_url}/iscsi/targetextent?target={target_id}&extent={extent_id}"
                check_response = self.session.get(check_url)
                
                if check_response.status_code == 200 and check_response.json():
                    self.logger.info(f"Verified target-extent association exists")
                    verification_results['association_verified'] = True
                else:
                    self.logger.warning(f"Could not verify target-extent association")
                    self.housekeeping_results['warnings'].append(f"Target-extent association verification failed")
            
            # Store verification results
            self.housekeeping_results.update(verification_results)
            
            # Overall verification result
            all_verified = all(verification_results.values())
            self.housekeeping_results['resources_verified'] = all_verified
            
            if all_verified:
                self.logger.info("All resources verified successfully")
            else:
                self.logger.warning("Some resources could not be verified")
                
        except Exception as e:
            self.logger.error(f"Error verifying resources: {e}")
            self.housekeeping_results['resources_verified'] = False
            self.housekeeping_results['verification_error'] = str(e)
    
    def _cleanup_unused_resources(self) -> None:
        """Clean up unused iSCSI resources"""
        self.logger.info("Cleaning up unused resources")
        
        if self.config.get('dry_run', False):
            self.logger.info("DRY RUN: Would clean up unused resources")
            return
            
        try:
            unused_count = 0
            cleaned_count = 0
            
            # Find extents that are not associated with any target
            response = self.session.get(f"{self.api_url}/iscsi/extent")
            extents = response.json() if response.status_code == 200 else []
            
            response = self.session.get(f"{self.api_url}/iscsi/targetextent")
            targetextents = response.json() if response.status_code == 200 else []
            
            # Use Python 3.12 set comprehension for cleaner code
            extent_ids_in_use = {te.get('extent') for te in targetextents}
            unused_extents = [e for e in extents if e.get('id') not in extent_ids_in_use]
            
            if unused_extents:
                self.logger.info(f"Found {len(unused_extents)} unused extents")
                unused_count += len(unused_extents)
                
                for extent in unused_extents:
                    extent_id = extent.get('id')
                    extent_name = extent.get('name')
                    self.logger.info(f"Cleaning up unused extent: {extent_name} (ID: {extent_id})")
                    
                    try:
                        response = self.session.delete(f"{self.api_url}/iscsi/extent/id/{extent_id}")
                        if response.status_code == 200:
                            self.logger.info(f"Successfully deleted extent {extent_name}")
                            cleaned_count += 1
                        else:
                            self.logger.warning(f"Failed to delete extent {extent_name}: {response.text}")
                    except Exception as e:
                        self.logger.error(f"Error deleting extent {extent_name}: {e}")
            
            # Find targets that are not associated with any extent
            response = self.session.get(f"{self.api_url}/iscsi/target")
            targets = response.json() if response.status_code == 200 else []
            
            # Python 3.12 set comprehension
            target_ids_in_use = {te.get('target') for te in targetextents}
            unused_targets = [t for t in targets if t.get('id') not in target_ids_in_use]
            
            if unused_targets:
                self.logger.info(f"Found {len(unused_targets)} unused targets")
                unused_count += len(unused_targets)
                
                for target in unused_targets:
                    target_id = target.get('id')
                    target_name = target.get('name')
                    self.logger.info(f"Cleaning up unused target: {target_name} (ID: {target_id})")
                    
                    try:
                        response = self.session.delete(f"{self.api_url}/iscsi/target/id/{target_id}")
                        if response.status_code == 200:
                            self.logger.info(f"Successfully deleted target {target_name}")
                            cleaned_count += 1
                        else:
                            self.logger.warning(f"Failed to delete target {target_name}: {response.text}")
                    except Exception as e:
                        self.logger.error(f"Error deleting target {target_name}: {e}")
            
            self.housekeeping_results['unused_resources_found'] = unused_count
            self.housekeeping_results['unused_resources_cleaned'] = cleaned_count
            
            if unused_count == 0:
                self.logger.info("No unused resources found")
            else:
                self.logger.info(f"Cleaned up {cleaned_count} of {unused_count} unused resources")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up unused resources: {e}")
            self.housekeeping_results['cleanup_error'] = str(e)
    
    def _store_resource_details(self) -> None:
        """Store resource details as artifact"""
        self.logger.info("Storing resource details")
        
        # Collect resource details using Python 3.12 TypedDict
        resource_details: ResourceDetails = {
            'zvol_name': self.config.get('zvol_name'),
            'target_name': self.config.get('target_name'),
            'extent_name': self.config.get('extent_name'),
            'target_id': self.processing_results.get('target_id'),
            'extent_id': self.processing_results.get('extent_id'),
            'connection_info': {
                'server': self.config.get('truenas_ip'),
                'iqn': self.config.get('target_name'),
                'port': 3260
            },
            'created_at': datetime.datetime.now().isoformat(),
            'config': {
                'server_id': self.config.get('server_id'),
                'hostname': self.config.get('hostname'),
                'openshift_version': self.config.get('openshift_version'),
                'zvol_size': self.config.get('zvol_size')
            }
        }
        
        # Add artifact
        self.add_artifact('iscsi_resources', resource_details, {
            'type': 'iscsi_resources',
            'server_id': self.config.get('server_id'),
            'hostname': self.config.get('hostname'),
            'created_at': datetime.datetime.now().isoformat()
        })
        
        self.logger.info("Resource details stored as artifact")
        self.housekeeping_results['resource_details_stored'] = True
    
    def _format_size(self, size_str: str) -> int:
        """
        Convert a size string like 500G to bytes
        
        Args:
            size_str: Size string with unit suffix (K, M, G, T, P)
            
        Returns:
            Size in bytes
        """
        if isinstance(size_str, int):
            return size_str
            
        if not isinstance(size_str, str):
            raise ValueError(f"Invalid size format: {size_str}")
            
        size_str = size_str.upper()
        
        if size_str.endswith('B'):
            size_str = size_str[:-1]
            
        multipliers = {
            'K': 1024,
            'M': 1024 * 1024,
            'G': 1024 * 1024 * 1024,
            'T': 1024 * 1024 * 1024 * 1024,
            'P': 1024 * 1024 * 1024 * 1024 * 1024
        }
        
        # Using assignment expression (walrus operator) for cleaner code
        if size_str and (suffix := size_str[-1]) in multipliers:
            return int(float(size_str[:-1]) * multipliers[suffix])
        else:
            return int(size_str)
    
    def _create_parent_directory(self, path: str) -> bool:
        """
        Create parent directory structure recursively
        
        Args:
            path: Path to create
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Creating parent directory structure: {path}")
        
        if self.config.get('dry_run', False):
            self.logger.info(f"DRY RUN: Would create parent directory {path}")
            return True
            
        # Split path into components (e.g., "pool/dir1/dir2")
        parts = path.split('/')
        
        # Start with the first component (pool name)
        current_path = parts[0]
        
        # Process each directory level
        for i in range(1, len(parts)):
            current_path = f"{current_path}/{parts[i]}"
            
            # Check if this level exists
            check_url = f"{self.api_url}/pool/dataset/id/{current_path}"
            check_response = self.session.get(check_url)
            
            if check_response.status_code == 200:
                self.logger.debug(f"Directory {current_path} already exists")
                continue
                
            # Create this level
            self.logger.info(f"Creating directory {current_path}")
            
            payload = {
                "name": current_path,
                "type": "FILESYSTEM",
                "compression": "lz4",
                "atime": "off",
                "exec": "on"
            }
            
            try:
                response = self.session.post(f"{self.api_url}/pool/dataset", json=payload)
                response.raise_for_status()
                self.logger.info(f"Successfully created directory {current_path}")
            except Exception as e:
                self.logger.error(f"Failed to create directory {current_path}: {e}")
                if hasattr(e, 'response') and e.response:
                    self.logger.error(f"Response: {e.response.text}")
                return False
        
        return True
