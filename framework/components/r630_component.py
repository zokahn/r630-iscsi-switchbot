#!/usr/bin/env python3
"""
Dell R630 Component for Discovery-Processing-Housekeeping Pattern

This component manages Dell R630 hardware configuration using the
discovery-processing-housekeeping pattern and Redfish API.
"""

import os
import sys
import json
import logging
import requests
import time
import warnings
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# Import base component
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.base_component import BaseComponent

# Disable SSL warnings for self-signed certs
warnings.filterwarnings("ignore")

class R630Component(BaseComponent):
    """
    Component for managing Dell R630 server configurations.
    
    Manages hardware settings, BIOS configuration, and boot order
    using the Redfish API through iDRAC.
    """
    
    # Default configuration
    DEFAULT_CONFIG = {
        'idrac_ip': None,
        'idrac_username': 'root',
        'idrac_password': None,
        'verify_cert': False,
        'boot_devices': None,  # List of boot devices in desired order
        'server_id': None,
        'hostname': None,
        'reboot_required': True,
        'wait_for_job_completion': True,
        'job_wait_timeout': 1800,  # 30 minutes in seconds
        'dry_run': False
    }
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the R630 component.
        
        Args:
            config: Configuration dictionary for the component
            logger: Optional logger instance
        """
        # Merge provided config with defaults
        merged_config = {**self.DEFAULT_CONFIG, **config}
        
        # Initialize base component
        super().__init__(merged_config, logger)
        
        # Component-specific initialization
        self.session = requests.Session()
        self.session.verify = self.config.get('verify_cert', False)
        
        self.logger.info(f"R630Component initialized for server {self.config.get('server_id')} at {self.config.get('idrac_ip')}")
    
    def discover(self) -> Dict[str, Any]:
        """
        Discovery phase: Examine the R630 server configuration.
        
        Checks connectivity, retrieves server info, and discovers current
        boot order and BIOS settings.
        
        Returns:
            Dictionary of discovery results
        """
        self.timestamps['discover_start'] = datetime.datetime.now().isoformat()
        self.logger.info(f"Starting discovery phase for {self.component_name}")
        
        try:
            # Initialize discovery results
            self.discovery_results = {
                'connectivity': False,
                'server_info': {},
                'system_generation': None,
                'boot_mode': None,
                'current_boot_order': [],
                'boot_devices': [],
                'power_state': None,
                'bios_settings': {}
            }
            
            # 1. Check iDRAC connectivity
            self._check_idrac_connectivity()
            
            # 2. Get server generation
            self._get_server_generation()
            
            # 3. Get system information
            self._get_system_info()
            
            # 4. Get current boot mode
            self._get_boot_mode()
            
            # 5. Get current boot order
            self._get_current_boot_order()
            
            # 6. Get BIOS settings
            self._get_bios_settings()
            
            # 7. Get network configuration
            self._get_network_config()
            
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
        Processing phase: Configure the R630 server.
        
        Sets boot order, configures BIOS settings, and applies
        necessary configuration changes.
        
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
                'boot_order_changed': False,
                'bios_settings_changed': False,
                'network_settings_changed': False,
                'reboot_triggered': False,
                'job_id': None
            }
            
            # Skip if dry run
            if self.config.get('dry_run', False):
                self.logger.info("DRY RUN: Would configure server")
                self.processing_results['dry_run'] = True
                self.phases_executed['process'] = True
                self.timestamps['process_end'] = datetime.datetime.now().isoformat()
                return self.processing_results
            
            # 1. Change boot order if specified
            if self.config.get('boot_devices'):
                self._change_boot_order()
            
            # 2. Configure BIOS settings if specified
            if self.config.get('bios_settings'):
                self._configure_bios_settings()
            
            # 3. Configure network settings if specified
            if self.config.get('network_settings'):
                self._configure_network_settings()
            
            # 4. Reboot server if required and requested
            if self.config.get('reboot_required', True) and (
                self.processing_results.get('boot_order_changed', False) or 
                self.processing_results.get('bios_settings_changed', False)
            ):
                self._reboot_server()
            
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
        Housekeeping phase: Verify and monitor server configuration.
        
        Verifies changes were applied, monitors job status, and
        records final server configuration.
        
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
                'job_completed': False,
                'changes_verified': False,
                'final_state': {},
                'warnings': []
            }
            
            # Skip if dry run
            if self.config.get('dry_run', False) or self.processing_results.get('dry_run', False):
                self.logger.info("DRY RUN: Would verify configuration changes")
                self.housekeeping_results['dry_run'] = True
                self.phases_executed['housekeep'] = True
                self.timestamps['housekeep_end'] = datetime.datetime.now().isoformat()
                return self.housekeeping_results
            
            # 1. Check job status if a job was created
            if self.processing_results.get('job_id'):
                self._check_job_status()
            
            # 2. Verify configuration changes
            self._verify_configuration_changes()
            
            # 3. Get final configuration
            self._get_final_configuration()
            
            # 4. Store configuration as artifact
            self._store_configuration_details()
            
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
    
    # Helper methods for discovery phase
    def _check_idrac_connectivity(self) -> None:
        """Check if iDRAC is accessible"""
        self.logger.info("Checking iDRAC connectivity")
        
        idrac_ip = self.config.get('idrac_ip')
        if not idrac_ip:
            self.logger.error("No iDRAC IP address provided")
            raise ValueError("iDRAC IP address is required")
            
        try:
            # Test connectivity with a simple GET request
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1"
            
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                self.logger.info(f"Successfully connected to iDRAC at {idrac_ip}")
                self.discovery_results['connectivity'] = True
            elif response.status_code == 401:
                self.logger.error("Authentication failed - invalid credentials")
                self.discovery_results['connection_error'] = "Authentication failed"
                self.discovery_results['connectivity'] = False
            else:
                self.logger.error(f"Connection failed with status code {response.status_code}")
                self.discovery_results['connection_error'] = f"Status code: {response.status_code}"
                self.discovery_results['connectivity'] = False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Connection to iDRAC failed: {e}")
            self.discovery_results['connection_error'] = str(e)
            self.discovery_results['connectivity'] = False
    
    def _get_server_generation(self) -> None:
        """Determine the server generation"""
        self.logger.info("Getting server generation")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping server generation check - no connectivity")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            url = f"https://{idrac_ip}/redfish/v1/Managers/iDRAC.Embedded.1?$select=Model"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                model = data.get('Model', '')
                self.logger.info(f"Server model: {model}")
                
                # Determine iDRAC version/generation
                if "12" in model or "13" in model:
                    self.discovery_results['system_generation'] = 12
                    self.logger.info("Detected 12th/13th generation server (iDRAC 8)")
                elif "14" in model or "15" in model or "16" in model:
                    self.discovery_results['system_generation'] = 14
                    self.logger.info("Detected 14th/15th/16th generation server (iDRAC 9)")
                else:
                    self.discovery_results['system_generation'] = 0
                    self.logger.warning(f"Unknown server generation: {model}")
                    
            else:
                self.logger.error(f"Failed to get server model: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error getting server generation: {e}")
    
    def _get_system_info(self) -> None:
        """Get system information"""
        self.logger.info("Getting system information")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping system info retrieval - no connectivity")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant information
                system_info = {
                    'manufacturer': data.get('Manufacturer'),
                    'model': data.get('Model'),
                    'serial_number': data.get('SerialNumber'),
                    'part_number': data.get('PartNumber'),
                    'power_state': data.get('PowerState'),
                    'status': data.get('Status'),
                    'processors': data.get('ProcessorSummary'),
                    'memory': data.get('MemorySummary')
                }
                
                self.discovery_results['server_info'] = system_info
                self.discovery_results['power_state'] = data.get('PowerState')
                
                self.logger.info(f"System: {system_info['manufacturer']} {system_info['model']}")
                self.logger.info(f"Serial: {system_info['serial_number']}")
                self.logger.info(f"Power state: {system_info['power_state']}")
                
            else:
                self.logger.error(f"Failed to get system information: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error getting system information: {e}")
    
    def _get_boot_mode(self) -> None:
        """Get current boot mode"""
        self.logger.info("Getting boot mode")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping boot mode retrieval - no connectivity")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/Bios"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                
                try:
                    boot_mode = data['Attributes']['BootMode']
                    self.discovery_results['boot_mode'] = boot_mode
                    self.logger.info(f"Current boot mode: {boot_mode}")
                except:
                    self.logger.error("Unable to find BootMode attribute in BIOS settings")
                    
            else:
                self.logger.error(f"Failed to get BIOS settings: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error getting boot mode: {e}")
    
    def _get_current_boot_order(self) -> None:
        """Get current boot order"""
        self.logger.info("Getting current boot order")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping boot order retrieval - no connectivity")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/BootOptions?$expand=*($levels=1)"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                members = data.get('Members', [])
                
                boot_devices = []
                for device in members:
                    # Extract relevant boot device information
                    boot_device = {
                        'id': device.get('@odata.id', '').split('/')[-1],
                        'name': device.get('DisplayName', 'Unknown'),
                        'enabled': device.get('Enabled', False),
                        'current_assigned_sequence': device.get('BootOptionReference', '')
                    }
                    boot_devices.append(boot_device)
                
                self.discovery_results['boot_devices'] = boot_devices
                
                # Get the current boot order sequence
                url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1"
                response = self.session.get(url, auth=auth)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'Boot' in data and 'BootOrder' in data['Boot']:
                        boot_order = data['Boot']['BootOrder']
                        self.discovery_results['current_boot_order'] = boot_order
                        self.logger.info(f"Current boot order: {boot_order}")
                    else:
                        self.logger.warning("Boot order information not found in system data")
                else:
                    self.logger.error(f"Failed to get system boot order: {response.status_code}")
                    
            else:
                self.logger.error(f"Failed to get boot options: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error getting boot order: {e}")
    
    def _get_bios_settings(self) -> None:
        """Get current BIOS settings"""
        self.logger.info("Getting BIOS settings")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping BIOS settings retrieval - no connectivity")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/Bios"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'Attributes' in data:
                    # Filter for relevant BIOS settings
                    bios_settings = {
                        # Common iSCSI-related BIOS settings
                        'BootMode': data['Attributes'].get('BootMode'),
                        'EmbNic1Enabled': data['Attributes'].get('EmbNic1Enabled'),
                        'EmbNic2Enabled': data['Attributes'].get('EmbNic2Enabled'),
                        'IscsiInitiatorName': data['Attributes'].get('IscsiInitiatorName'),
                        'SriovGlobalEnable': data['Attributes'].get('SriovGlobalEnable'),
                        'ProcVirtualization': data['Attributes'].get('ProcVirtualization')
                    }
                    
                    # Add other iSCSI-related settings if they exist
                    for key, value in data['Attributes'].items():
                        if 'Iscsi' in key or 'iSCSI' in key:
                            bios_settings[key] = value
                    
                    self.discovery_results['bios_settings'] = bios_settings
                    self.logger.info(f"Retrieved {len(bios_settings)} BIOS settings")
                else:
                    self.logger.warning("No BIOS attributes found")
                    
            else:
                self.logger.error(f"Failed to get BIOS settings: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error getting BIOS settings: {e}")
    
    def _get_network_config(self) -> None:
        """Get network configuration"""
        self.logger.info("Getting network configuration")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.warning("Skipping network configuration retrieval - no connectivity")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'Members' in data:
                    # Get details of each network interface
                    network_interfaces = []
                    
                    for member in data['Members']:
                        member_url = member.get('@odata.id')
                        if member_url:
                            member_url = f"https://{idrac_ip}{member_url}"
                            member_response = self.session.get(member_url, auth=auth)
                            
                            if member_response.status_code == 200:
                                interface_data = member_response.json()
                                
                                interface = {
                                    'id': interface_data.get('Id'),
                                    'name': interface_data.get('Name'),
                                    'mac_address': interface_data.get('MACAddress'),
                                    'status': interface_data.get('Status'),
                                    'link_status': interface_data.get('LinkStatus'),
                                    'speed_mbps': interface_data.get('SpeedMbps'),
                                    'ipv4_addresses': interface_data.get('IPv4Addresses', []),
                                    'ipv6_addresses': interface_data.get('IPv6Addresses', [])
                                }
                                
                                network_interfaces.append(interface)
                                self.logger.info(f"Found interface: {interface['name']} ({interface['mac_address']})")
                    
                    self.discovery_results['network_interfaces'] = network_interfaces
                    
            else:
                self.logger.error(f"Failed to get network interfaces: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error getting network configuration: {e}")
    
    # Helper methods for processing phase
    def _change_boot_order(self) -> None:
        """Change boot order"""
        self.logger.info("Changing boot order")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.error("Cannot change boot order - no connectivity")
            return
            
        boot_devices = self.config.get('boot_devices', [])
        if not boot_devices:
            self.logger.warning("No boot devices specified")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            # Determine the correct URL based on server generation
            system_generation = self.discovery_results.get('system_generation', 0)
            
            if system_generation >= 14:  # iDRAC 9 and newer
                url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/Settings"
            else:  # iDRAC 8
                url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1"
            
            # Prepare payload
            payload = {"Boot": {"BootOrder": boot_devices}}
            
            # Make the request
            headers = {'content-type': 'application/json'}
            response = self.session.patch(url, data=json.dumps(payload), headers=headers, auth=auth)
            
            if response.status_code in [200, 202]:
                self.logger.info("Successfully submitted boot order change request")
                self.processing_results['boot_order_changed'] = True
                
                # Extract job ID if available
                job_id = None
                if 'Location' in response.headers:
                    job_id = response.headers['Location'].split('/')[-1]
                elif '@Message.ExtendedInfo' in response.json():
                    # Extract job ID from response message for older iDRACs
                    for message in response.json()['@Message.ExtendedInfo']:
                        if 'MessageId' in message and 'JID' in message.get('MessageArgs', []):
                            for arg in message.get('MessageArgs', []):
                                if arg.startswith('JID_'):
                                    job_id = arg
                                    break
                
                if job_id:
                    self.logger.info(f"Job ID for boot order change: {job_id}")
                    self.processing_results['job_id'] = job_id
                else:
                    self.logger.warning("No job ID found for boot order change")
                    
            else:
                self.logger.error(f"Failed to change boot order: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Error changing boot order: {e}")
            raise
    
    def _configure_bios_settings(self) -> None:
        """Configure BIOS settings"""
        self.logger.info("Configuring BIOS settings")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.error("Cannot configure BIOS settings - no connectivity")
            return
            
        bios_settings = self.config.get('bios_settings', {})
        if not bios_settings:
            self.logger.warning("No BIOS settings specified")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            # Determine the correct URL based on server generation
            system_generation = self.discovery_results.get('system_generation', 0)
            
            if system_generation >= 14:  # iDRAC 9 and newer
                url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/Bios/Settings"
            else:  # iDRAC 8
                url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/Bios"
            
            # Prepare payload
            payload = {"Attributes": bios_settings}
            
            # Make the request
            headers = {'content-type': 'application/json'}
            response = self.session.patch(url, data=json.dumps(payload), headers=headers, auth=auth)
            
            if response.status_code in [200, 202]:
                self.logger.info("Successfully submitted BIOS settings change request")
                self.processing_results['bios_settings_changed'] = True
                
                # Extract job ID if available
                job_id = self.processing_results.get('job_id')
                
                # If we already have a job ID, don't overwrite it
                if not job_id and 'Location' in response.headers:
                    job_id = response.headers['Location'].split('/')[-1]
                    self.logger.info(f"Job ID for BIOS settings change: {job_id}")
                    self.processing_results['job_id'] = job_id
                    
            else:
                self.logger.error(f"Failed to change BIOS settings: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Error configuring BIOS settings: {e}")
            raise
    
    def _configure_network_settings(self) -> None:
        """Configure network settings"""
        self.logger.info("Configuring network settings")
        
        # This is a placeholder - network configuration is complex and should be implemented
        # based on the specific requirements of the project
        self.logger.warning("Network configuration not implemented in this skeleton version")
        pass
    
    def _reboot_server(self) -> None:
        """Reboot the server to apply changes"""
        self.logger.info("Rebooting server to apply changes")
        
        if not self.discovery_results.get('connectivity', False):
            self.logger.error("Cannot reboot server - no connectivity")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            # Get current power state
            power_state = self.discovery_results.get('power_state')
            
            if not power_state:
                # Refresh power state if not available
                url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1"
                response = self.session.get(url, auth=auth)
                
                if response.status_code == 200:
                    data = response.json()
                    power_state = data.get('PowerState')
                    self.logger.info(f"Current power state: {power_state}")
                else:
                    self.logger.error(f"Failed to get power state: {response.status_code}")
                    return
            
            # Prepare for reboot
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset"
            
            if power_state == "On":
                # Graceful shutdown and restart
                payload = {'ResetType': 'GracefulRestart'}
                self.logger.info("Performing graceful restart")
            else:
                # Power on
                payload = {'ResetType': 'On'}
                self.logger.info("Powering on server")
            
            # Send reboot request
            headers = {'content-type': 'application/json'}
            response = self.session.post(url, data=json.dumps(payload), headers=headers, auth=auth)
            
            if response.status_code in [200, 202, 204]:
                self.logger.info("Successfully initiated server reboot")
                self.processing_results['reboot_triggered'] = True
            else:
                self.logger.error(f"Failed to reboot server: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Error rebooting server: {e}")
            raise
    
    # Helper methods for housekeeping phase
    def _check_job_status(self) -> None:
        """Check status of a configuration job"""
        self.logger.info("Checking job status")
        
        job_id = self.processing_results.get('job_id')
        if not job_id:
            self.logger.warning("No job ID to check")
            return
            
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            url = f"https://{idrac_ip}/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/{job_id}"
            
            start_time = datetime.datetime.now()
            timeout = self.config.get('job_wait_timeout', 1800)  # 30 minutes default
            wait_for_completion = self.config.get('wait_for_job_completion', True)
            
            while True:
                response = self.session.get(url, auth=auth)
                
                if response.status_code == 200:
                    data = response.json()
                    job_status = data.get('JobState', '')
                    percent_complete = data.get('PercentComplete', 0)
                    message = data.get('Message', '')
                    
                    self.logger.info(f"Job status: {job_status} ({percent_complete}%) - {message}")
                    
                    # Check if job completed
                    if job_status == 'Completed':
                        self.logger.info("Job completed successfully")
                        self.housekeeping_results['job_completed'] = True
                        self.housekeeping_results['job_details'] = data
                        break
                    elif job_status in ['Failed', 'CompletedWithErrors']:
                        self.logger.error(f"Job failed: {message}")
                        self.housekeeping_results['job_completed'] = False
                        self.housekeeping_results['job_details'] = data
                        self.housekeeping_results['job_error'] = message
                        break
                    elif not wait_for_completion:
                        # If not waiting for completion, just record current status
                        self.logger.info("Not waiting for job completion")
                        self.housekeeping_results['job_in_progress'] = True
                        self.housekeeping_results['job_details'] = data
                        break
                        
                    # Check timeout
                    current_time = datetime.datetime.now()
                    elapsed_seconds = (current_time - start_time).total_seconds()
                    
                    if elapsed_seconds > timeout:
                        self.logger.error(f"Job status check timed out after {timeout} seconds")
                        self.housekeeping_results['job_timeout'] = True
                        self.housekeeping_results['job_details'] = data
                        break
                        
                    # Wait before next check
                    time.sleep(30)
                    
                else:
                    self.logger.error(f"Failed to check job status: {response.status_code}")
                    self.housekeeping_results['job_status_error'] = response.status_code
                    break
                    
        except Exception as e:
            self.logger.error(f"Error checking job status: {e}")
            self.housekeeping_results['job_status_error'] = str(e)
    
    def _verify_configuration_changes(self) -> None:
        """Verify configuration changes were applied"""
        self.logger.info("Verifying configuration changes")
        
        # Get current boot order and compare with requested changes
        if self.processing_results.get('boot_order_changed', False):
            self._verify_boot_order()
            
        # Get current BIOS settings and compare with requested changes
        if self.processing_results.get('bios_settings_changed', False):
            self._verify_bios_settings()
            
        # Summarize verification results
        boot_verified = self.housekeeping_results.get('boot_order_verified', False)
        bios_verified = self.housekeeping_results.get('bios_settings_verified', False)
        
        if self.processing_results.get('boot_order_changed', False) and not boot_verified:
            self.housekeeping_results['warnings'].append("Boot order changes not verified")
            
        if self.processing_results.get('bios_settings_changed', False) and not bios_verified:
            self.housekeeping_results['warnings'].append("BIOS settings changes not verified")
            
        # Set overall verification status
        changes_made = (
            self.processing_results.get('boot_order_changed', False) or 
            self.processing_results.get('bios_settings_changed', False)
        )
        
        if not changes_made:
            # No changes were made, so verification is N/A
            self.housekeeping_results['changes_verified'] = True
            self.logger.info("No changes were made to verify")
        else:
            # Check if all changes were verified
            required_verifications = []
            if self.processing_results.get('boot_order_changed', False):
                required_verifications.append(boot_verified)
            if self.processing_results.get('bios_settings_changed', False):
                required_verifications.append(bios_verified)
                
            all_verified = all(required_verifications)
            self.housekeeping_results['changes_verified'] = all_verified
            
            if all_verified:
                self.logger.info("All configuration changes verified successfully")
            else:
                self.logger.warning("Some configuration changes could not be verified")
    
    def _verify_boot_order(self) -> None:
        """Verify boot order changes"""
        self.logger.info("Verifying boot order changes")
        
        # Get the requested boot order
        requested_boot_order = self.config.get('boot_devices', [])
        
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            # Get current boot order
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'Boot' in data and 'BootOrder' in data['Boot']:
                    current_boot_order = data['Boot']['BootOrder']
                    
                    # Verify if current matches requested
                    match = True
                    for i, device in enumerate(requested_boot_order):
                        if i >= len(current_boot_order) or device != current_boot_order[i]:
                            match = False
                            break
                    
                    self.housekeeping_results['boot_order_verified'] = match
                    
                    if match:
                        self.logger.info("Boot order verified - matches requested configuration")
                    else:
                        self.logger.warning("Boot order does not match requested configuration")
                        self.logger.warning(f"Requested: {requested_boot_order}")
                        self.logger.warning(f"Current: {current_boot_order}")
                        
                else:
                    self.logger.warning("Boot order information not found in system data")
                    self.housekeeping_results['boot_order_verified'] = False
                    
            else:
                self.logger.error(f"Failed to get system data: {response.status_code}")
                self.housekeeping_results['boot_order_verified'] = False
                
        except Exception as e:
            self.logger.error(f"Error verifying boot order: {e}")
            self.housekeeping_results['boot_order_verified'] = False
    
    def _verify_bios_settings(self) -> None:
        """Verify BIOS settings changes"""
        self.logger.info("Verifying BIOS settings changes")
        
        # Get the requested BIOS settings
        requested_settings = self.config.get('bios_settings', {})
        
        try:
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            # Get current BIOS settings
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/Bios"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'Attributes' in data:
                    current_settings = data['Attributes']
                    
                    # Compare requested settings with current
                    mismatches = []
                    for key, value in requested_settings.items():
                        if key in current_settings and current_settings[key] != value:
                            mismatches.append(f"{key}: expected '{value}', got '{current_settings[key]}'")
                    
                    if not mismatches:
                        self.logger.info("BIOS settings verified - match requested configuration")
                        self.housekeeping_results['bios_settings_verified'] = True
                    else:
                        self.logger.warning(f"BIOS settings verification found {len(mismatches)} mismatches")
                        for mismatch in mismatches:
                            self.logger.warning(f"  - {mismatch}")
                        self.housekeeping_results['bios_settings_verified'] = False
                        self.housekeeping_results['bios_settings_mismatches'] = mismatches
                        
                else:
                    self.logger.warning("BIOS attributes not found in response")
                    self.housekeeping_results['bios_settings_verified'] = False
                    
            else:
                self.logger.error(f"Failed to get BIOS settings: {response.status_code}")
                self.housekeeping_results['bios_settings_verified'] = False
                
        except Exception as e:
            self.logger.error(f"Error verifying BIOS settings: {e}")
            self.housekeeping_results['bios_settings_verified'] = False
    
    def _get_final_configuration(self) -> None:
        """Get final server configuration"""
        self.logger.info("Getting final server configuration")
        
        # Simply use the discovery phase methods to get current configuration
        final_config = {}
        
        try:
            # Get system info
            idrac_ip = self.config.get('idrac_ip')
            auth = (self.config.get('idrac_username'), self.config.get('idrac_password'))
            
            # Get power state
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                final_config['power_state'] = data.get('PowerState')
                
                # Get boot order
                if 'Boot' in data and 'BootOrder' in data['Boot']:
                    final_config['boot_order'] = data['Boot']['BootOrder']
            
            # Get BIOS settings
            url = f"https://{idrac_ip}/redfish/v1/Systems/System.Embedded.1/Bios"
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                if 'Attributes' in data:
                    # Only include the settings we modified
                    bios_settings = {}
                    requested_settings = self.config.get('bios_settings', {})
                    
                    for key in requested_settings.keys():
                        if key in data['Attributes']:
                            bios_settings[key] = data['Attributes'][key]
                            
                    final_config['bios_settings'] = bios_settings
            
            self.housekeeping_results['final_state'] = final_config
            
        except Exception as e:
            self.logger.error(f"Error getting final configuration: {e}")
    
    def _store_configuration_details(self) -> None:
        """Store configuration details as artifact"""
        self.logger.info("Storing configuration details")
        
        # Collect configuration details
        config_details = {
            'server_id': self.config.get('server_id'),
            'idrac_ip': self.config.get('idrac_ip'),
            'changes_made': {
                'boot_order_changed': self.processing_results.get('boot_order_changed', False),
                'bios_settings_changed': self.processing_results.get('bios_settings_changed', False),
                'reboot_triggered': self.processing_results.get('reboot_triggered', False)
            },
            'verification': {
                'job_completed': self.housekeeping_results.get('job_completed', False),
                'changes_verified': self.housekeeping_results.get('changes_verified', False)
            },
            'final_state': self.housekeeping_results.get('final_state', {}),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Add artifact
        self.add_artifact('r630_configuration', config_details, {
            'type': 'r630_configuration',
            'server_id': self.config.get('server_id'),
            'hostname': self.config.get('hostname'),
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        self.logger.info("Configuration details stored as artifact")
        self.housekeeping_results['config_details_stored'] = True
