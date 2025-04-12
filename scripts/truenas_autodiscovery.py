#!/usr/bin/env python3
# truenas_autodiscovery.py - Discover and configure TrueNAS Scale for OpenShift multiboot

import argparse
import json
import os
import sys
import requests
import getpass
from pprint import pprint
import time
from urllib.parse import urljoin

class TrueNASClient:
    """Client for interacting with TrueNAS Scale API"""
    
    def __init__(self, host, username, password=None, api_key=None, ssl_verify=False, use_https=True, port=None):
        # Handle custom port
        if ":" in host and not port:
            host, port_str = host.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                pass
        
        # Set protocol
        protocol = "https" if use_https else "http"
        
        # Format URL with optional port
        if port:
            self.base_url = f"{protocol}://{host}:{port}/api/v2.0/"
        else:
            self.base_url = f"{protocol}://{host}/api/v2.0/"
            
        print(f"Connecting to TrueNAS API at: {self.base_url}")
        
        self.session = requests.Session()
        self.session.verify = ssl_verify
        
        # Disable SSL warnings if verification is disabled
        if not ssl_verify:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        if api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {api_key}"
            })
        elif password:
            self.session.auth = (username, password)
        else:
            raise ValueError("Either password or api_key must be provided")
            
        # Add common headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        # Test connection
        try:
            self.get("system/info")
            print(f"✅ Successfully connected to TrueNAS Scale at {host}")
        except Exception as e:
            print(f"❌ Failed to connect to TrueNAS Scale: {e}")
            raise
    
    def get(self, endpoint, params=None):
        """Make a GET request to the TrueNAS API"""
        url = urljoin(self.base_url, endpoint)
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint, data):
        """Make a POST request to the TrueNAS API"""
        url = urljoin(self.base_url, endpoint)
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def put(self, endpoint, data):
        """Make a PUT request to the TrueNAS API"""
        url = urljoin(self.base_url, endpoint)
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def delete(self, endpoint):
        """Make a DELETE request to the TrueNAS API"""
        url = urljoin(self.base_url, endpoint)
        response = self.session.delete(url)
        response.raise_for_status()
        return response.json()

class TrueNASDiscovery:
    """Class to discover and configure TrueNAS for OpenShift multiboot"""
    
    def __init__(self, client):
        self.client = client
        self.system_info = None
        self.pools = None
        self.datasets = None
        self.zvols = None
        self.iscsi_targets = None
        self.iscsi_extents = None
        self.sharing_nfs = None
        self.openshift_versions = ["4.16", "4.17", "4.18"]  # Versions we want to support
    
    def discover_system(self):
        """Get basic system information"""
        print("\n🔍 Discovering TrueNAS system information...")
        self.system_info = self.client.get("system/info")
        print(f"System: {self.system_info['hostname']} ({self.system_info['system_product']})")
        print(f"Version: {self.system_info['version']}")
        return self.system_info
    
    def discover_pools(self):
        """Discover ZFS pools"""
        print("\n🔍 Discovering ZFS pools...")
        self.pools = self.client.get("pool")
        
        if not self.pools:
            print("❌ No ZFS pools found")
            return None
        
        print(f"Found {len(self.pools)} ZFS pools:")
        for pool in self.pools:
            status = "✅ Online" if pool["status"] == "ONLINE" else f"❌ {pool['status']}"
            print(f"- {pool['name']}: {status}, Size: {format_size(pool['size'])}")
        
        return self.pools
    
    def discover_datasets(self):
        """Discover ZFS datasets"""
        print("\n🔍 Discovering ZFS datasets...")
        self.datasets = self.client.get("pool/dataset")
        
        if not self.datasets:
            print("No ZFS datasets found")
            return None
        
        print(f"Found {len(self.datasets)} ZFS datasets")
        return self.datasets
    
    def discover_zvols(self):
        """Discover ZFS zvols"""
        print("\n🔍 Discovering ZFS zvols...")
        self.zvols = []
        
        for dataset in self.datasets:
            if dataset.get("type") == "VOLUME":
                self.zvols.append(dataset)
        
        if not self.zvols:
            print("No ZFS zvols found")
        else:
            print(f"Found {len(self.zvols)} ZFS zvols:")
            for zvol in self.zvols:
                print(f"- {zvol['name']}: Size: {format_size(zvol['volsize']['parsed'])}")
        
        return self.zvols
    
    def discover_iscsi_configuration(self):
        """Discover iSCSI configuration"""
        print("\n🔍 Discovering iSCSI configuration...")
        
        # Check if iSCSI service is running
        services = self.client.get("service")
        iscsi_service = next((s for s in services if s["service"] == "iscsitarget"), None)
        
        if not iscsi_service:
            print("❌ iSCSI service not found")
            return None
        
        if not iscsi_service["enable"]:
            print("⚠️ iSCSI service is not enabled")
        
        if not iscsi_service["state"] == "RUNNING":
            print("⚠️ iSCSI service is not running")
        else:
            print("✅ iSCSI service is running")
        
        # Get iSCSI targets
        self.iscsi_targets = self.client.get("iscsi/target")
        print(f"Found {len(self.iscsi_targets)} iSCSI targets")
        
        # Get iSCSI extents
        self.iscsi_extents = self.client.get("iscsi/extent")
        print(f"Found {len(self.iscsi_extents)} iSCSI extents")
        
        return {
            "service": iscsi_service,
            "targets": self.iscsi_targets,
            "extents": self.iscsi_extents
        }
    
    def discover_nfs_shares(self):
        """Discover NFS shares"""
        print("\n🔍 Discovering NFS shares...")
        try:
            self.sharing_nfs = self.client.get("sharing/nfs")
            
            if not self.sharing_nfs:
                print("No NFS shares found")
            else:
                print(f"Found {len(self.sharing_nfs)} NFS shares:")
                for share in self.sharing_nfs:
                    # Handle different API structures safely
                    paths = []
                    if isinstance(share.get("paths"), list):
                        paths = share["paths"]
                    elif "path" in share:
                        paths = [share["path"]]
                    
                    if paths:
                        paths_str = ", ".join(paths)
                        enabled = share.get("enabled", False)
                        print(f"- {paths_str} (Enabled: {'✅' if enabled else '❌'})")
                    else:
                        print(f"- {share.get('id', 'Unknown')} (Path info unavailable)")
            
            return self.sharing_nfs
        except Exception as e:
            print(f"⚠️ Error discovering NFS shares: {e}")
            return []
    
    def discover_all(self):
        """Run all discovery functions"""
        self.discover_system()
        self.discover_pools()
        self.discover_datasets()
        self.discover_zvols()
        self.discover_iscsi_configuration()
        self.discover_nfs_shares()
        
        return {
            "system_info": self.system_info,
            "pools": self.pools,
            "datasets": self.datasets,
            "zvols": self.zvols,
            "iscsi": {
                "targets": self.iscsi_targets,
                "extents": self.iscsi_extents
            },
            "nfs_shares": self.sharing_nfs
        }
    
    def analyze_configuration(self):
        """Analyze current configuration and compare with required configuration"""
        if not self.pools:
            self.discover_pools()
        
        if not self.datasets:
            self.discover_datasets()
        
        if not self.zvols:
            self.discover_zvols()
        
        if not self.iscsi_targets:
            self.discover_iscsi_configuration()
        
        print("\n📊 Analyzing configuration for OpenShift multiboot compatibility...")
        
        # Check for suitable pool
        if not self.pools:
            print("❌ No ZFS pools available for OpenShift multiboot")
            return False
        
        # Find the largest pool for our configuration
        largest_pool = max(self.pools, key=lambda p: p["size"])
        print(f"Selected pool '{largest_pool['name']}' for OpenShift multiboot configuration")
        
        # Check for openshift_isos dataset
        openshift_isos_dataset = None
        for dataset in self.datasets:
            if dataset["name"].endswith("/openshift_isos"):
                openshift_isos_dataset = dataset
                break
        
        if not openshift_isos_dataset:
            print(f"⚠️ Missing dataset '{largest_pool['name']}/openshift_isos'")
        else:
            print(f"✅ Found dataset '{openshift_isos_dataset['name']}'")
        
        # Check for openshift_installations dataset
        openshift_installations_dataset = None
        for dataset in self.datasets:
            if dataset["name"].endswith("/openshift_installations"):
                openshift_installations_dataset = dataset
                break
        
        if not openshift_installations_dataset:
            print(f"⚠️ Missing dataset '{largest_pool['name']}/openshift_installations'")
        else:
            print(f"✅ Found dataset '{openshift_installations_dataset['name']}'")
        
        # Check for version-specific datasets
        for version in self.openshift_versions:
            version_dataset = None
            for dataset in self.datasets:
                if dataset["name"].endswith(f"/openshift_isos/{version}"):
                    version_dataset = dataset
                    break
            
            if not version_dataset:
                print(f"⚠️ Missing dataset '{largest_pool['name']}/openshift_isos/{version}'")
            else:
                print(f"✅ Found dataset '{version_dataset['name']}'")
        
        # Check for zvols
        for version in self.openshift_versions:
            version_fmt = version.replace(".", "_")
            version_zvol = None
            for zvol in self.zvols:
                if zvol["name"].endswith(f"/openshift_installations/{version_fmt}_complete"):
                    version_zvol = zvol
                    break
            
            if not version_zvol:
                print(f"⚠️ Missing zvol '{largest_pool['name']}/openshift_installations/{version_fmt}_complete'")
            else:
                print(f"✅ Found zvol '{version_zvol['name']}'")
        
        # Check for iSCSI targets
        for version in self.openshift_versions:
            version_fmt = version.replace(".", "_")
            version_target = None
            for target in self.iscsi_targets:
                if f"openshift{version_fmt}" in target["name"] or f"openshift_{version_fmt}" in target["name"]:
                    version_target = target
                    break
            
            if not version_target:
                print(f"⚠️ Missing iSCSI target for OpenShift {version}")
            else:
                print(f"✅ Found iSCSI target '{version_target['name']}' for OpenShift {version}")
        
        # Generate configuration plan
        print("\n📋 Configuration Plan:")
        
        config_plan = {
            "pool": largest_pool["name"],
            "missing_datasets": [],
            "missing_zvols": [],
            "missing_iscsi_targets": []
        }
        
        # Check for missing datasets
        if not openshift_isos_dataset:
            config_plan["missing_datasets"].append(f"{largest_pool['name']}/openshift_isos")
        
        if not openshift_installations_dataset:
            config_plan["missing_datasets"].append(f"{largest_pool['name']}/openshift_installations")
        
        for version in self.openshift_versions:
            version_dataset = None
            for dataset in self.datasets:
                if dataset["name"].endswith(f"/openshift_isos/{version}"):
                    version_dataset = dataset
                    break
            
            if not version_dataset:
                config_plan["missing_datasets"].append(f"{largest_pool['name']}/openshift_isos/{version}")
        
        # Check for missing zvols
        for version in self.openshift_versions:
            version_fmt = version.replace(".", "_")
            version_zvol = None
            for zvol in self.zvols:
                if zvol["name"].endswith(f"/openshift_installations/{version_fmt}_complete"):
                    version_zvol = zvol
                    break
            
            if not version_zvol:
                config_plan["missing_zvols"].append({
                    "name": f"{largest_pool['name']}/openshift_installations/{version_fmt}_complete",
                    "volsize": 500 * 1024 * 1024 * 1024  # 500GB
                })
        
        # Check for missing iSCSI targets
        for version in self.openshift_versions:
            version_fmt = version.replace(".", "_")
            version_target = None
            for target in self.iscsi_targets:
                if f"openshift{version_fmt}" in target["name"] or f"openshift_{version_fmt}" in target["name"]:
                    version_target = target
                    break
            
            if not version_target:
                config_plan["missing_iscsi_targets"].append({
                    "name": f"openshift_{version_fmt}",
                    "alias": f"OpenShift {version}",
                    "iqn": f"iqn.2005-10.org.freenas.ctl:iscsi.r630.openshift{version_fmt}"
                })
        
        return config_plan
    
    def apply_configuration(self, config_plan, confirm=True):
        """Apply the configuration plan to TrueNAS"""
        if confirm:
            print("\n⚠️ About to apply the following configuration changes:")
            
            if config_plan["missing_datasets"]:
                print("\nDatasets to create:")
                for dataset in config_plan["missing_datasets"]:
                    print(f"- {dataset}")
            
            if config_plan["missing_zvols"]:
                print("\nZvols to create:")
                for zvol in config_plan["missing_zvols"]:
                    print(f"- {zvol['name']} (Size: {format_size(zvol['volsize'])})")
            
            if config_plan["missing_iscsi_targets"]:
                print("\niSCSI targets to create:")
                for target in config_plan["missing_iscsi_targets"]:
                    print(f"- {target['name']} ({target['iqn']})")
            
            proceed = input("\nDo you want to proceed with these changes? (y/n): ")
            if proceed.lower() != "y":
                print("Configuration cancelled")
                return False
        
        # Create missing datasets
        for dataset_name in config_plan["missing_datasets"]:
            print(f"Creating dataset {dataset_name}...")
            try:
                dataset_data = {
                    "name": dataset_name,
                    "type": "FILESYSTEM",
                    "sync": "STANDARD",
                    "compression": "LZ4"
                }
                self.client.post("pool/dataset", dataset_data)
                print(f"✅ Created dataset {dataset_name}")
            except Exception as e:
                print(f"❌ Failed to create dataset {dataset_name}: {e}")
        
        # Create missing zvols
        for zvol in config_plan["missing_zvols"]:
            print(f"Creating zvol {zvol['name']}...")
            try:
                zvol_data = {
                    "name": zvol["name"],
                    "type": "VOLUME",
                    "volsize": zvol["volsize"],
                    "sync": "STANDARD",
                    "compression": "LZ4",
                    "sparse": True
                }
                self.client.post("pool/dataset", zvol_data)
                print(f"✅ Created zvol {zvol['name']}")
            except Exception as e:
                print(f"❌ Failed to create zvol {zvol['name']}: {e}")
        
        # Create missing iSCSI targets
        if config_plan["missing_iscsi_targets"]:
            # First check if the iSCSI service is running
            services = self.client.get("service")
            iscsi_service = next((s for s in services if s["service"] == "iscsitarget"), None)
            
            if not iscsi_service or not iscsi_service["state"] == "RUNNING":
                print("⚠️ iSCSI service is not running. Targets will be created but may not be accessible.")
        
        for target in config_plan["missing_iscsi_targets"]:
            print(f"Creating iSCSI target {target['name']}...")
            try:
                # First check if a portal exists
                portals = self.client.get("iscsi/portal")
                if not portals:
                    print("⚠️ No iSCSI portals found. Creating a default portal...")
                    portal_data = {
                        "comment": "Default portal for OpenShift multiboot",
                        "discovery_authmethod": "NONE",
                        "discovery_authgroup": None,
                        "listen": [
                            {
                                "ip": "0.0.0.0",
                                "port": 3260
                            }
                        ]
                    }
                    try:
                        portal_result = self.client.post("iscsi/portal", portal_data)
                        print(f"✅ Created default iSCSI portal")
                        portal_id = portal_result["id"]
                    except Exception as e:
                        print(f"❌ Failed to create iSCSI portal: {e}")
                        portal_id = 1  # Try with default portal ID
                else:
                    portal_id = portals[0]["id"]
                    print(f"✅ Using existing iSCSI portal ID {portal_id}")
                
                # First check if initiator groups exist
                initiator_groups = self.client.get("iscsi/initiator")
                if not initiator_groups:
                    print("⚠️ No iSCSI initiator groups found. Creating a default group...")
                    initiator_data = {
                        "comment": "Default initiator group for OpenShift multiboot",
                        "initiators": ["ALL"],
                    }
                    try:
                        initiator_result = self.client.post("iscsi/initiator", initiator_data)
                        print(f"✅ Created default iSCSI initiator group")
                        initiator_id = initiator_result["id"]
                    except Exception as e:
                        print(f"❌ Failed to create iSCSI initiator group: {e}")
                        initiator_id = 1  # Try with default initiator ID
                else:
                    initiator_id = initiator_groups[0]["id"]
                    print(f"✅ Using existing iSCSI initiator group ID {initiator_id}")
                
                # The IQN must be in the correct format with colons intact
                iqn = target["iqn"].replace(" ", "-")
                
                # Create the target with correct format according to TrueNAS SCALE 24.10
                target_data = {
                    "name": iqn,
                    "alias": target["alias"],
                    "mode": "ISCSI",
                    "groups": [
                        {
                            "portal": portal_id,
                            "initiator": initiator_id,
                            "auth": None,  # No authentication
                            "authmethod": "NONE"
                        }
                    ]
                }
                
                print(f"Sending iSCSI target creation request: {json.dumps(target_data, indent=2)}")
                target_result = self.client.post("iscsi/target", target_data)
                print(f"✅ Created iSCSI target {target['name']}")
                
                # Get the new target ID
                target_id = target_result["id"]
                
                # Now we need to create an extent and bind it to the target
                # First, find the zvol for this target
                version = target["name"].split("_")[-1].replace("_", ".")
                version_fmt = version.replace(".", "_")
                zvol_name = f"{config_plan['pool']}/openshift_installations/{version_fmt}_complete"
                
                # Create an extent for the zvol
                extent_data = {
                    "name": f"openshift_{version_fmt}_extent",
                    "type": "DISK",
                    "disk": f"zvol/{zvol_name}",
                    "blocksize": 512,
                    "pblocksize": False,
                    "avail_threshold": None,
                    "comment": f"OpenShift {version} boot image",
                    "insecure_tpc": True,
                    "xen": False,
                    "rpm": "SSD",
                    "ro": False
                }
                
                extent_result = self.client.post("iscsi/extent", extent_data)
                print(f"✅ Created iSCSI extent for {zvol_name}")
                
                # Bind the extent to the target
                targetextent_data = {
                    "target": target_id,
                    "extent": extent_result["id"],
                    "lunid": 0
                }
                
                self.client.post("iscsi/targetextent", targetextent_data)
                print(f"✅ Bound extent to target {target['name']}")
                
            except Exception as e:
                print(f"❌ Failed to create iSCSI target {target['name']}: {e}")
        
        print("\n✅ Configuration applied successfully")
        return True

def format_size(size_in_bytes):
    """Format size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size_in_bytes < 1024.0 or unit == 'PB':
            break
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} {unit}"

def main():
    parser = argparse.ArgumentParser(description="Discover and configure TrueNAS Scale for OpenShift multiboot")
    parser.add_argument("--host", default="192.168.2.245", help="TrueNAS Scale hostname or IP (can include port, e.g. 192.168.2.245:444)")
    parser.add_argument("--port", type=int, default=444, help="TrueNAS Scale port (default: 444)")
    parser.add_argument("--username", default="root", help="TrueNAS Scale username")
    parser.add_argument("--password", help="TrueNAS Scale password (omit for prompt)")
    parser.add_argument("--api-key", help="TrueNAS Scale API key (alternative to username/password)")
    parser.add_argument("--discover-only", action="store_true", help="Only discover current configuration")
    parser.add_argument("--apply", action="store_true", help="Apply configuration changes without confirmation")
    parser.add_argument("--ssl-verify", action="store_true", help="Verify SSL certificate")
    parser.add_argument("--use-http", action="store_true", help="Use HTTP instead of HTTPS")
    parser.add_argument("--output", help="Output discovery results to JSON file")
    
    args = parser.parse_args()
    
    # Get password if not provided
    password = args.password
    if not password and not args.api_key:
        password = getpass.getpass(f"Password for {args.username}@{args.host}: ")
    
    try:
        # Connect to TrueNAS
        client = TrueNASClient(
            host=args.host,
            username=args.username,
            password=password,
            api_key=args.api_key,
            ssl_verify=args.ssl_verify,
            use_https=not args.use_http,
            port=args.port
        )
        
        # Create discovery object
        discovery = TrueNASDiscovery(client)
        
        # Run discovery
        discovery_results = discovery.discover_all()
        
        # Save results if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(discovery_results, f, indent=2)
            print(f"\nDiscovery results saved to {args.output}")
        
        if not args.discover_only:
            # Analyze configuration
            config_plan = discovery.analyze_configuration()
            
            # Check if changes are needed
            has_changes = (
                len(config_plan["missing_datasets"]) > 0 or
                len(config_plan["missing_zvols"]) > 0 or
                len(config_plan["missing_iscsi_targets"]) > 0
            )
            
            if not has_changes:
                print("\n✅ TrueNAS is already properly configured for OpenShift multiboot")
            else:
                # Apply configuration if requested
                if args.apply:
                    discovery.apply_configuration(config_plan, confirm=False)
                else:
                    discovery.apply_configuration(config_plan, confirm=True)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
