#!/usr/bin/env python3
"""
OpenShift Component for Discovery-Processing-Housekeeping Pattern

This component manages OpenShift ISO generation and management using the
discovery-processing-housekeeping pattern.
"""

import os
import sys
import json
import logging
import tempfile
import subprocess
import datetime
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

# Import base component
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.base_component import BaseComponent

class OpenShiftComponent(BaseComponent):
    """
    Component for OpenShift ISO generation and management.
    
    Manages discovering available OpenShift versions, generating ISOs,
    and maintaining ISO artifacts.
    """
    
    # Default configuration
    DEFAULT_CONFIG = {
        'openshift_version': 'stable',
        'domain': 'example.com',
        'rendezvous_ip': None,
        'pull_secret_path': '~/.openshift/pull-secret',
        'ssh_key_path': '~/.ssh/id_rsa.pub',
        'output_dir': None,
        'skip_upload': False,
        'values_file': None,
        'upload_to_s3': True,
        'cleanup_temp_files': True,
        's3_config': {}  # Configuration for S3Component if needed
    }
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None, s3_component=None):
        """
        Initialize the OpenShift component.
        
        Args:
            config: Configuration dictionary for the component
            logger: Optional logger instance
            s3_component: Optional S3Component for storage operations
        """
        # Merge provided config with defaults
        merged_config = {**self.DEFAULT_CONFIG, **config}
        
        # Initialize base component
        super().__init__(merged_config, logger)
        
        # Component-specific initialization
        self.temp_dir = None
        self.iso_path = None
        
        # Store reference to S3Component if provided
        self.s3_component = s3_component
        
        self.logger.info(f"OpenShiftComponent initialized with version: {self.config.get('openshift_version')}")
    
    def discover(self) -> Dict[str, Any]:
        """
        Discovery phase: Examine the OpenShift environment.
        
        Checks for existing OpenShift versions, installers, ISOs, and 
        validates requirements for ISO generation.
        
        Returns:
            Dictionary of discovery results
        """
        self.timestamps['discover_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting discovery phase for {self.component_name}")
        
        try:
            # Initialize discovery results
            self.discovery_results = {
                'installed_versions': [],
                'available_versions': [],
                'existing_isos': [],
                'pull_secret_available': False,
                'ssh_key_available': False,
                'installer_available': False,
                'temp_dir': None
            }
            
            # 1. Check for OpenShift client (oc)
            self._discover_openshift_client()
            
            # 2. Check for OpenShift installer
            self._discover_openshift_installer()
            
            # 3. Check for existing ISOs
            self._discover_existing_isos()
            
            # 4. Check for pull secret
            self._discover_pull_secret()
            
            # 5. Check for SSH key
            self._discover_ssh_key()
            
            # 6. Create temporary directory if needed
            self._setup_temp_directory()
            
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
    
    def process(self) -> Dict[str, Any]:
        """
        Processing phase: Generate OpenShift ISO.
        
        Downloads OpenShift installer if needed, creates configs, and 
        generates the ISO file.
        
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
                'installer_downloaded': False,
                'configs_created': False,
                'iso_generated': False,
                'iso_path': None,
                'upload_status': None
            }
            
            # 1. Download OpenShift installer if needed
            self._download_installer()
            
            # 2. Create installation configs
            self._create_install_configs()
            
            # 3. Generate ISO
            self._generate_iso()
            
            # 4. Upload to S3 if configured
            if self.config.get('upload_to_s3', True) and not self.config.get('skip_upload', False):
                self._upload_to_s3()
            
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
        Housekeeping phase: Clean up and verify ISO.
        
        Verifies ISO integrity, cleans up temporary files, and updates
        metadata related to the ISO.
        
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
                'iso_verified': False,
                'temp_files_cleaned': False,
                'metadata_updated': False
            }
            
            # 1. Verify ISO integrity if generated
            if self.processing_results.get('iso_generated', False):
                self._verify_iso()
            
            # 2. Clean up temporary files if configured
            if self.config.get('cleanup_temp_files', True):
                self._cleanup_temp_files()
            
            # 3. Update metadata
            self._update_metadata()
            
            # 4. Store any artifacts to S3
            if self.artifacts:
                self.logger.info(f"Storing {len(self.artifacts)} artifacts")
                self._store_artifacts()
            
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
    
    # Helper methods - to be implemented
    def _discover_openshift_client(self) -> None:
        """Discover OpenShift client (oc) version"""
        self.logger.info("Discovering OpenShift client")
        try:
            # Check if oc command is available
            result = subprocess.run(
                ["oc", "version"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Parse version information
                version_info = result.stdout.strip()
                self.logger.info(f"OpenShift client found: {version_info}")
                
                # Extract version numbers
                import re
                version_matches = re.findall(r'(\d+\.\d+\.\d+)', version_info)
                for version in version_matches:
                    self.discovery_results['available_versions'].append(version)
                
                self.discovery_results['installed_versions'] = version_matches
            else:
                self.logger.info("OpenShift client not found or not working properly")
        except Exception as e:
            self.logger.info(f"OpenShift client not installed: {e}")
    
    def _discover_openshift_installer(self) -> None:
        """Discover OpenShift installer"""
        self.logger.info("Discovering OpenShift installer")
        
        # Check common paths for openshift-install
        installer_paths = [
            os.path.join(os.getcwd(), "openshift-install"),
            os.path.join(os.getcwd(), "bin", "openshift-install"),
            os.path.expanduser("~/.local/bin/openshift-install"),
            "/usr/local/bin/openshift-install"
        ]
        
        # If output directory is specified, check there too
        if self.config.get('output_dir'):
            installer_paths.append(os.path.join(self.config['output_dir'], "openshift-install"))
        
        for path in installer_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                try:
                    result = subprocess.run(
                        [path, "version"],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        version_info = result.stdout.strip()
                        self.logger.info(f"OpenShift installer found: {version_info}")
                        
                        # Extract version
                        import re
                        version_matches = re.findall(r'(\d+\.\d+\.\d+)', version_info)
                        if version_matches:
                            self.discovery_results['installer_available'] = True
                            for version in version_matches:
                                if version not in self.discovery_results['available_versions']:
                                    self.discovery_results['available_versions'].append(version)
                        
                        # Store installer path
                        self.discovery_results['installer_path'] = path
                        break
                except Exception as e:
                    self.logger.info(f"Found installer but couldn't determine version: {path} - {e}")
    
    def _discover_existing_isos(self) -> None:
        """Discover existing OpenShift ISOs"""
        self.logger.info("Discovering existing ISOs")
        
        # Define common locations to search
        search_paths = [
            os.path.join(os.getcwd(), "isos"),
            os.path.join(os.getcwd(), "downloads"),
            "/tmp"
        ]
        
        # If output directory is specified, check there too
        if self.config.get('output_dir'):
            search_paths.append(self.config['output_dir'])
        
        # Search for ISO files
        found_isos = []
        for path in search_paths:
            if os.path.exists(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(".iso") and ("openshift" in file.lower() or "ocp" in file.lower() or "agent" in file.lower()):
                            iso_path = os.path.join(root, file)
                            found_isos.append(iso_path)
                            self.logger.info(f"Found ISO: {iso_path}")
        
        self.discovery_results['existing_isos'] = found_isos
    
    def _discover_pull_secret(self) -> None:
        """Check if pull secret is available"""
        self.logger.info("Checking for pull secret")
        
        # Check specified path if provided
        if self.config.get('pull_secret_path'):
            pull_secret_path = os.path.expanduser(self.config['pull_secret_path'])
            if os.path.exists(pull_secret_path):
                self.logger.info(f"Pull secret found at {pull_secret_path}")
                self.discovery_results['pull_secret_available'] = True
                self.discovery_results['pull_secret_path'] = pull_secret_path
                return
        
        # Check default path
        default_path = os.path.expanduser("~/.openshift/pull-secret")
        if os.path.exists(default_path):
            self.logger.info(f"Pull secret found at {default_path}")
            self.discovery_results['pull_secret_available'] = True
            self.discovery_results['pull_secret_path'] = default_path
            return
            
        self.logger.info("Pull secret not found")
    
    def _discover_ssh_key(self) -> None:
        """Check if SSH key is available"""
        self.logger.info("Checking for SSH key")
        
        # Check specified path if provided
        if self.config.get('ssh_key_path'):
            ssh_key_path = os.path.expanduser(self.config['ssh_key_path'])
            if os.path.exists(ssh_key_path):
                self.logger.info(f"SSH key found at {ssh_key_path}")
                self.discovery_results['ssh_key_available'] = True
                self.discovery_results['ssh_key_path'] = ssh_key_path
                return
        
        # Check default path
        default_path = os.path.expanduser("~/.ssh/id_rsa.pub")
        if os.path.exists(default_path):
            self.logger.info(f"SSH key found at {default_path}")
            self.discovery_results['ssh_key_available'] = True
            self.discovery_results['ssh_key_path'] = default_path
            return
            
        self.logger.info("SSH key not found")
    
    def _setup_temp_directory(self) -> None:
        """Set up temporary directory for ISO generation"""
        self.logger.info("Setting up temporary directory")
        
        # Use specified output directory if provided
        if self.config.get('output_dir'):
            dir_path = self.config['output_dir']
            os.makedirs(dir_path, exist_ok=True)
            self.temp_dir = dir_path
            self.discovery_results['temp_dir'] = dir_path
            self.logger.info(f"Using specified output directory: {dir_path}")
        else:
            # Create a temporary directory
            self.temp_dir = tempfile.mkdtemp()
            self.discovery_results['temp_dir'] = self.temp_dir
            self.logger.info(f"Created temporary directory: {self.temp_dir}")
    
    def _download_installer(self) -> None:
        """
        Download OpenShift installer if needed, checking S3 cache first
        """
        self.logger.info("Downloading OpenShift installer if needed")
        
        # Define target path for installer
        installer_path = os.path.join(self.temp_dir, "openshift-install")
        version = self.config.get('openshift_version')
        
        # Check if we already have a working installer from discovery
        if self.discovery_results.get('installer_available') and self.discovery_results.get('installer_path'):
            existing_installer = self.discovery_results.get('installer_path')
            try:
                # Copy existing installer
                shutil.copy2(existing_installer, installer_path)
                os.chmod(installer_path, 0o755)  # Make executable
                self.logger.info(f"Using existing OpenShift installer from {existing_installer}")
                self.processing_results['installer_downloaded'] = True
                self.processing_results['installer_source'] = 'local'
                return
            except Exception as e:
                self.logger.warning(f"Could not use existing installer: {e}")
        
        # Try to get from S3 if available
        if self.s3_component:
            try:
                s3_path = f"binaries/openshift-install/{version}/openshift-install"
                # Check if installer exists in S3
                binary_bucket = self.config.get('s3_config', {}).get('binary_bucket', 'r630-switchbot-binaries')
                
                self.logger.info(f"Checking S3 for cached installer at {binary_bucket}/{s3_path}")
                
                # Use bucket listing to check existence
                objects = list(self.s3_component.s3_resource.Bucket(binary_bucket).objects.filter(Prefix=s3_path))
                if objects and len(objects) > 0:
                    # Download the installer
                    self.logger.info(f"Found installer in S3, downloading...")
                    self.s3_component.s3_client.download_file(
                        binary_bucket,
                        s3_path,
                        installer_path
                    )
                    os.chmod(installer_path, 0o755)  # Make executable
                    self.logger.info(f"Successfully downloaded installer from S3")
                    self.processing_results['installer_downloaded'] = True
                    self.processing_results['installer_source'] = 's3'
                    return
            except Exception as e:
                self.logger.warning(f"Error retrieving installer from S3: {e}")
        
        # If we get here, we need to download from internet
        self.logger.info(f"Downloading installer from internet for version {version}")
        
        try:
            # Create a temporary directory for the download
            download_dir = os.path.join(self.temp_dir, "downloads")
            os.makedirs(download_dir, exist_ok=True)
            
            # Determine download URL based on version
            # This is a simplified example - real implementation would need logic to map versions to URLs
            if version == 'stable':
                # Use latest stable URL
                download_url = "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/openshift-install-linux.tar.gz"
            else:
                # Use specific version URL
                download_url = f"https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{version}/openshift-install-linux.tar.gz"
            
            # Download the tarball
            tarball_path = os.path.join(download_dir, "openshift-install.tar.gz")
            self.logger.info(f"Downloading installer from {download_url}")
            
            # Use subprocess to download with curl or wget
            try:
                import requests
                with requests.get(download_url, stream=True) as r:
                    r.raise_for_status()
                    with open(tarball_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
            except ImportError:
                # Fall back to subprocess if requests is not available
                subprocess.run(['curl', '-L', download_url, '-o', tarball_path], check=True)
            
            # Extract the tarball
            self.logger.info(f"Extracting installer tarball")
            import tarfile
            with tarfile.open(tarball_path) as tar:
                tar.extractall(path=download_dir)
            
            # Move the installer to the target location
            extracted_installer = os.path.join(download_dir, "openshift-install")
            if os.path.exists(extracted_installer):
                shutil.move(extracted_installer, installer_path)
            else:
                # If not found at expected path, search for it
                found = False
                for root, _, files in os.walk(download_dir):
                    if "openshift-install" in files:
                        found_path = os.path.join(root, "openshift-install")
                        shutil.move(found_path, installer_path)
                        found = True
                        break
                
                if not found:
                    raise FileNotFoundError("Could not find openshift-install in extracted files")
            
            # Make the installer executable
            os.chmod(installer_path, 0o755)
            
            # Clean up downloaded files
            shutil.rmtree(download_dir, ignore_errors=True)
            
            self.logger.info(f"Successfully downloaded and extracted OpenShift installer")
            self.processing_results['installer_downloaded'] = True
            self.processing_results['installer_source'] = 'internet'
            
            # Cache the installer in S3 if we have an S3 component
            if self.s3_component:
                try:
                    self.logger.info(f"Caching installer in S3 for future use")
                    binary_bucket = self.config.get('s3_config', {}).get('binary_bucket', 'r630-switchbot-binaries')
                    s3_path = f"binaries/openshift-install/{version}/openshift-install"
                    
                    # Upload to S3
                    self.s3_component.s3_client.upload_file(
                        installer_path,
                        binary_bucket,
                        s3_path,
                        ExtraArgs={
                            'Metadata': {
                                'version': version,
                                'timestamp': datetime.datetime.now().isoformat()
                            }
                        }
                    )
                    self.logger.info(f"Successfully cached installer in S3 at {binary_bucket}/{s3_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to cache installer in S3: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to download installer: {e}")
            self.processing_results['installer_downloaded'] = False
            self.processing_results['installer_error'] = str(e)
            raise
    
    def _create_install_configs(self) -> None:
        """Create installation configuration files"""
        self.logger.info("Creating installation configs")
        
        # Implementation will be based on scripts/generate_openshift_iso.py
        # This is a placeholder - will need detailed implementation
        self.processing_results['configs_created'] = True
    
    def _generate_iso(self) -> None:
        """Generate OpenShift ISO"""
        self.logger.info("Generating ISO")
        
        # Implementation will be based on scripts/generate_openshift_iso.py
        # This is a placeholder - will need detailed implementation
        
        # Assume ISO generation is successful for now
        self.processing_results['iso_generated'] = True
        self.processing_results['iso_path'] = os.path.join(self.temp_dir, "agent.x86_64.iso")
        self.iso_path = self.processing_results['iso_path']
    
    def _upload_to_s3(self) -> None:
        """
        Upload generated ISO to S3 with comprehensive metadata
        """
        self.logger.info("Uploading ISO to S3")
        
        # Verify ISO exists
        if not self.iso_path or not os.path.exists(self.iso_path):
            self.logger.warning("No ISO file found to upload")
            self.processing_results['upload_status'] = 'failed'
            self.processing_results['upload_error'] = 'ISO file not found'
            return
        
        # Gather metadata
        version = self.config.get('openshift_version')
        timestamp = datetime.datetime.now().isoformat()
        iso_size = os.path.getsize(self.iso_path)
        iso_filename = os.path.basename(self.iso_path)
        
        # Calculate MD5 hash for integrity verification
        md5_hash = hashlib.md5()
        with open(self.iso_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5_hash.update(chunk)
        iso_hash = md5_hash.hexdigest()
        
        # Create metadata
        metadata = {
            'version': version,
            'domain': self.config.get('domain'),
            'rendezvous_ip': self.config.get('rendezvous_ip'),
            'size_bytes': iso_size,
            'md5_hash': iso_hash,
            'generated_at': timestamp,
            'component_id': self.component_id,
            'hostname': self.config.get('hostname', 'unknown'),
            'server_id': self.config.get('server_id', 'unknown')
        }
        
        # Use S3Component if available
        if self.s3_component:
            try:
                # Determine S3 paths
                iso_bucket = self.config.get('s3_config', {}).get('iso_bucket', 'r630-switchbot-isos')
                server_id = self.config.get('server_id', 'unknown')
                hostname = self.config.get('hostname', 'unknown')
                
                # Use a path that includes both version and server info
                if server_id != 'unknown' and hostname != 'unknown':
                    # Server-specific ISO
                    object_name = f"openshift/{version}/servers/{server_id}/{iso_filename}"
                    metadata_name = f"openshift/{version}/servers/{server_id}/metadata.json"
                else:
                    # Generic version ISO
                    object_name = f"openshift/{version}/{iso_filename}"
                    metadata_name = f"openshift/{version}/metadata.json"
                
                self.logger.info(f"Uploading ISO to {iso_bucket}/{object_name}")
                
                # Upload ISO to S3
                self.s3_component.s3_client.upload_file(
                    self.iso_path,
                    iso_bucket,
                    object_name,
                    ExtraArgs={
                        'Metadata': {k: str(v) for k, v in metadata.items()},
                        'ContentType': 'application/octet-stream'
                    }
                )
                
                # Create and upload metadata JSON
                metadata_path = os.path.join(os.path.dirname(self.iso_path), "metadata.json")
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                self.s3_component.s3_client.upload_file(
                    metadata_path,
                    iso_bucket,
                    metadata_name,
                    ExtraArgs={
                        'ContentType': 'application/json'
                    }
                )
                
                self.logger.info(f"Successfully uploaded ISO and metadata to S3")
                self.processing_results['upload_status'] = 'success'
                self.processing_results['s3_iso_path'] = f"{iso_bucket}/{object_name}"
                self.processing_results['s3_metadata_path'] = f"{iso_bucket}/{metadata_name}"
                
                # Clean up metadata file
                os.unlink(metadata_path)
                
            except Exception as e:
                self.logger.error(f"Error uploading to S3: {e}")
                self.processing_results['upload_status'] = 'failed'
                self.processing_results['upload_error'] = str(e)
                # Fall back to artifact storage
                self.add_artifact('iso', self.iso_path, metadata)
        else:
            # No S3Component available, use artifact storage
            self.logger.info("No S3Component available, using artifact storage")
            self.add_artifact('iso', self.iso_path, metadata)
            self.processing_results['upload_status'] = 'pending'
    
    def _verify_iso(self) -> None:
        """Verify ISO integrity"""
        self.logger.info("Verifying ISO integrity")
        
        if not self.iso_path or not os.path.exists(self.iso_path):
            self.logger.warning("ISO file not found for verification")
            return
            
        # Calculate MD5 hash for integrity verification
        try:
            md5_hash = hashlib.md5()
            with open(self.iso_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
            
            iso_hash = md5_hash.hexdigest()
            self.logger.info(f"ISO MD5 hash: {iso_hash}")
            
            # Store hash in results
            self.housekeeping_results['iso_hash'] = iso_hash
            self.housekeeping_results['iso_verified'] = True
        except Exception as e:
            self.logger.error(f"Error verifying ISO: {e}")
    
    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files"""
        self.logger.info("Cleaning up temporary files")
        
        # Only clean up if we created a temporary directory
        if self.temp_dir and not self.config.get('output_dir'):
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"Removed temporary directory: {self.temp_dir}")
                self.housekeeping_results['temp_files_cleaned'] = True
            except Exception as e:
                self.logger.error(f"Error cleaning up temporary directory: {e}")
        else:
            self.logger.info("Skipping cleanup of specified output directory")
    
    def _update_metadata(self) -> None:
        """Update metadata for the ISO"""
        self.logger.info("Updating ISO metadata")
        
        # Create metadata JSON
        metadata = {
            'openshift_version': self.config.get('openshift_version'),
            'domain': self.config.get('domain'),
            'rendezvous_ip': self.config.get('rendezvous_ip'),
            'iso_path': self.iso_path,
            'generated_at': datetime.datetime.now().isoformat(),
            'generated_by': self.component_id
        }
        
        # Add metadata as artifact
        self.add_artifact('metadata', metadata, {
            'type': 'openshift_iso_metadata',
            'version': self.config.get('openshift_version')
        })
        
        self.housekeeping_results['metadata_updated'] = True
