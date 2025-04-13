#!/usr/bin/env python3
"""
create_iscsi_target_api.py - Create iSCSI target on TrueNAS Scale using the REST API

This script implements an intelligent workflow for managing iSCSI targets on TrueNAS:
1. Verify TrueNAS connectivity and system health
2. Discover existing resources (pools, zvols, targets, etc.)
3. Analyze required actions based on discovery results
4. Execute required operations in the correct sequence
5. Perform optional housekeeping and cleanup

Uses API key authentication for secure access.
"""

import argparse
import json
import os
import sys
import time
import requests
import urllib3
import datetime
import logging
from pprint import pformat

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Create iSCSI target on TrueNAS Scale using REST API")
    parser.add_argument("--server-id", required=True, help="Server ID (e.g., 01, 02)")
    parser.add_argument("--hostname", required=True, help="Server hostname")
    parser.add_argument("--openshift-version", default="stable", help="OpenShift version (default: stable)")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--zvol-size", default="500G", help="Size of the zvol to create")
    parser.add_argument("--zfs-pool", default="test", help="ZFS pool name (default: test)")
    parser.add_argument("--api-key", required=True, help="TrueNAS API key")
    parser.add_argument("--dry-run", action="store_true", help="Show API calls without executing them")
    
    return parser.parse_args()

def get_api_session(args):
    """Set up API session with authentication"""
    session = requests.Session()
    
    # Set up API URL (TrueNAS SCALE uses port 444 for the API)
    api_url = f"https://{args.truenas_ip}:444/api/v2.0"
    
    # Add API key authentication
    session.headers.update({"Authorization": f"Bearer {args.api_key}"})
    
    # Disable SSL verification for self-signed certs
    session.verify = False
    
    return session, api_url

def check_truenas_connectivity(session, api_url):
    """Check if TrueNAS API is accessible and verify credentials"""
    try:
        # Try to get basic system information to validate connection and credentials
        response = session.get(f"{api_url}/system/info")
        response.raise_for_status()
        
        system_info = response.json()
        print(f"✅ Connected to TrueNAS {system_info.get('version', 'unknown version')}")
        print(f"✅ System: {system_info.get('hostname', 'unknown')} ({system_info.get('system_product', 'unknown')})")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Unable to connect to TrueNAS API")
        print(f"   Check if TrueNAS is running and accessible at https://{api_url}")
        return False
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ Authentication Error: Invalid API key")
        else:
            print(f"❌ HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking TrueNAS connectivity: {e}")
        return False

def check_iscsi_service(session, api_url):
    """Check if iSCSI service is running"""
    try:
        response = session.get(f"{api_url}/service/id/iscsitarget")
        response.raise_for_status()
        
        service_data = response.json()
        if service_data.get('state') == 'RUNNING':
            print("✅ iSCSI service is running")
            return True
        else:
            print("⚠️  iSCSI service is not running")
            return False
    except Exception as e:
        print(f"❌ Error checking iSCSI service: {e}")
        return False

def check_system_health(session, api_url):
    """Check TrueNAS system health and resources"""
    try:
        # Check system resources
        response = session.get(f"{api_url}/reporting/get_data?graphs=cpu,memory,swap")
        response.raise_for_status()
        
        resource_data = response.json()
        if 'cpu' in resource_data:
            cpu_usage = resource_data['cpu'][0]['data'][-1][1] if resource_data['cpu'][0]['data'] else 0
            print(f"ℹ️  CPU Usage: {cpu_usage:.1f}%")
        
        if 'memory' in resource_data:
            memory_usage = resource_data['memory'][0]['data'][-1][1] if resource_data['memory'][0]['data'] else 0
            memory_total = resource_data['memory'][0]['data'][-1][2] if resource_data['memory'][0]['data'] else 0
            if memory_total > 0:
                memory_percent = (memory_usage / memory_total) * 100
                print(f"ℹ️  Memory Usage: {memory_percent:.1f}% ({memory_usage/(1024*1024*1024):.1f}GB / {memory_total/(1024*1024*1024):.1f}GB)")
        
        # Check alerts
        response = session.get(f"{api_url}/alert/list")
        response.raise_for_status()
        
        alerts = response.json()
        critical_alerts = [a for a in alerts if a.get('level') == 'CRITICAL']
        if critical_alerts:
            print(f"⚠️  {len(critical_alerts)} critical alerts found")
            for alert in critical_alerts[:3]:  # Show first 3 critical alerts
                print(f"   - {alert.get('formatted')}")
        else:
            print("✅ No critical alerts found")
        
        return True
    except Exception as e:
        print(f"❌ Error checking system health: {e}")
        return False

def format_size(size_str):
    """Convert a size string like 500G to bytes for the API"""
    if size_str.endswith('G'):
        return int(size_str[:-1]) * 1024 * 1024 * 1024
    elif size_str.endswith('M'):
        return int(size_str[:-1]) * 1024 * 1024
    elif size_str.endswith('T'):
        return int(size_str[:-1]) * 1024 * 1024 * 1024 * 1024
    elif size_str.endswith('K'):
        return int(size_str[:-1]) * 1024
    else:
        return int(size_str)

def create_directory_structure(session, api_url, path, dry_run=False):
    """Create a directory structure recursively"""
    # Split path into components
    parts = path.split('/')
    
    # Create each level of the directory structure
    current_path = parts[0]  # Start with the pool name
    
    for i in range(1, len(parts)):
        # Build the path up to this point
        current_path = f"{current_path}/{parts[i]}"
        
        # Skip if this is the whole path (we'll create the final item separately)
        if current_path == path:
            continue
            
        if not create_single_directory(session, api_url, current_path, dry_run):
            return False
            
    return True

def create_single_directory(session, api_url, dir_path, dry_run=False):
    """Create a single directory (dataset) if it doesn't exist"""
    url = f"{api_url}/pool/dataset"
    payload = {
        "name": dir_path,
        "type": "FILESYSTEM",
        "compression": "lz4",  # Match existing datasets
        "atime": "off",        # Match existing datasets
        "exec": "on"           # Match existing datasets
    }
    
    if dry_run:
        print(f"\nDRY RUN: Would create directory with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return True
    
    try:
        # First check if directory already exists
        check_url = f"{api_url}/pool/dataset/id/{dir_path}"
        check_response = session.get(check_url)
        
        if check_response.status_code == 200:
            print(f"Directory {dir_path} already exists - using existing directory")
            return True
            
        # Create the directory if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        print(f"Successfully created directory {dir_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error creating directory {dir_path}: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
            try:
                print(f"Response JSON: {json.dumps(e.response.json(), indent=2)}")
            except:
                print("Could not parse response as JSON")
        return False

def create_zvol(session, api_url, zvol_name, size_str, dry_run=False):
    """Create a ZFS volume using TrueNAS API"""
    # Format the size from human-readable to bytes
    size_bytes = format_size(size_str)
    
    # First ensure parent directory exists
    parent_path = zvol_name.rsplit('/', 1)[0]
    if not create_directory_structure(session, api_url, parent_path, dry_run):
        print(f"Failed to create parent directory structure {parent_path}")
        return False
    
    url = f"{api_url}/pool/dataset"
    payload = {
        "name": zvol_name,
        "type": "VOLUME",
        "volsize": size_bytes,
        "sparse": True
    }
    
    if dry_run:
        print(f"\nDRY RUN: Would create zvol with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return True
    
    try:
        # First check if zvol already exists
        check_url = f"{api_url}/pool/dataset/id/{zvol_name}"
        check_response = session.get(check_url)
        
        if check_response.status_code == 200:
            print(f"ZVOL {zvol_name} already exists - using existing zvol")
            return True
            
        # Create the zvol if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        print(f"Successfully created zvol {zvol_name}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error creating zvol: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return False

def create_iscsi_target(session, api_url, target_name, hostname, dry_run=False):
    """Create an iSCSI target using TrueNAS API"""
    url = f"{api_url}/iscsi/target"
    payload = {
        "name": target_name,
        "alias": f"OpenShift {hostname}",
        "mode": "ISCSI",
        "groups": [{"portal": 3, "initiator": 3, "auth": None}]  # Portal ID 3 and Initiator ID 3 based on system config
    }
    
    if dry_run:
        print(f"\nDRY RUN: Would create target with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return 1  # Return a dummy ID for dry run
        
    try:
        # First check if target already exists
        query_url = f"{api_url}/iscsi/target?name={target_name}"
        query_response = session.get(query_url)
        
        if query_response.status_code == 200 and query_response.json():
            targets = query_response.json()
            if targets:
                target_id = targets[0]['id']
                print(f"Target {target_name} already exists with ID {target_id} - reusing")
                return target_id
        
        # Create the target if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        target_id = response.json()['id']
        print(f"Successfully created target {target_name} with ID {target_id}")
        return target_id
    except requests.exceptions.RequestException as e:
        print(f"Error creating iSCSI target: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return None

def create_iscsi_extent(session, api_url, extent_name, zvol_name, hostname, dry_run=False):
    """Create an iSCSI extent using TrueNAS API"""
    url = f"{api_url}/iscsi/extent"
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
    
    if dry_run:
        print(f"\nDRY RUN: Would create extent with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return 1  # Return a dummy ID for dry run
    
    try:
        # First check if extent already exists
        query_url = f"{api_url}/iscsi/extent?name={extent_name}"
        query_response = session.get(query_url)
        
        if query_response.status_code == 200 and query_response.json():
            extents = query_response.json()
            if extents:
                extent_id = extents[0]['id']
                print(f"Extent {extent_name} already exists with ID {extent_id} - reusing")
                return extent_id
        
        # Create the extent if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        extent_id = response.json()['id']
        print(f"Successfully created extent {extent_name} with ID {extent_id}")
        return extent_id
    except requests.exceptions.RequestException as e:
        print(f"Error creating iSCSI extent: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return None

def associate_target_extent(session, api_url, target_id, extent_id, dry_run=False):
    """Associate an iSCSI target with an extent using TrueNAS API"""
    url = f"{api_url}/iscsi/targetextent"
    payload = {
        "target": target_id,
        "extent": extent_id,
        "lunid": 0
    }
    
    if dry_run:
        print(f"\nDRY RUN: Would associate target-extent with API call:")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return True
    
    try:
        # First check if association already exists
        query_url = f"{api_url}/iscsi/targetextent?target={target_id}&extent={extent_id}"
        query_response = session.get(query_url)
        
        if query_response.status_code == 200 and query_response.json():
            associations = query_response.json()
            if associations:
                print(f"Target-extent association already exists - skipping")
                return True
        
        # Create the association if it doesn't exist
        response = session.post(url, json=payload)
        response.raise_for_status()
        print(f"Successfully associated target {target_id} with extent {extent_id}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error creating target-extent association: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return False

def ensure_parent_directory_exists(session, api_url, parent_path, dry_run=False):
    """Make sure the parent directory structure exists"""
    # Split the parent path into components
    parts = parent_path.split('/')
    
    # Start with the pool name
    current_path = parts[0]
    
    # Check and create each directory level
    for i in range(1, len(parts)):
        current_path = f"{current_path}/{parts[i]}"
        
        # Check if this level exists
        check_url = f"{api_url}/pool/dataset/id/{current_path}"
        check_response = session.get(check_url)
        
        if check_response.status_code == 200:
            print(f"Dataset {current_path} already exists")
            continue
        
        # If it doesn't exist, create it
        print(f"Creating dataset {current_path}...")
        
        payload = {
            "name": current_path,
            "type": "FILESYSTEM",
            "compression": "lz4"
        }
        
        if dry_run:
            print(f"DRY RUN: Would create dataset {current_path}")
            continue
        
        try:
            url = f"{api_url}/pool/dataset"
            response = session.post(url, json=payload)
            response.raise_for_status()
            print(f"Successfully created dataset {current_path}")
        except requests.exceptions.HTTPError as e:
            print(f"Error creating dataset {current_path}: {e}")
            # If we get a 422 error, it might be because the dataset already exists
            if e.response.status_code == 422:
                print("Dataset might already exist, continuing anyway")
            else:
                raise
    
    return True

def create_zvol_api(session, api_url, zvol_name, size_str, dry_run=False):
    """Create a ZFS volume using direct API calls"""
    # Format the size from human-readable to bytes
    size_bytes = format_size(size_str)
    
    # Ensure parent directory exists
    parent_path = zvol_name.rsplit('/', 1)[0]
    try:
        ensure_parent_directory_exists(session, api_url, parent_path, dry_run)
    except Exception as e:
        print(f"Error ensuring parent directory exists: {e}")
        # Continue anyway - the zvol creation might still succeed
    
    # Check if zvol already exists
    check_url = f"{api_url}/pool/dataset/id/{zvol_name}"
    check_response = session.get(check_url)
    
    if check_response.status_code == 200:
        print(f"ZVOL {zvol_name} already exists - using existing zvol")
        return True
    
    print(f"Creating zvol {zvol_name}...")
    url = f"{api_url}/pool/dataset"
    payload = {
        "name": zvol_name,
        "type": "VOLUME",
        "volsize": size_bytes,
        "sparse": True
    }
    
    if dry_run:
        print(f"DRY RUN: Would create zvol {zvol_name}")
        return True
    
    try:
        response = session.post(url, json=payload)
        response.raise_for_status()
        print(f"Successfully created zvol {zvol_name}")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"Error creating zvol: {e}")
        # Check if the error is a 422 - zvol might already exist
        if hasattr(e, 'response') and e.response.status_code == 422:
            print("ZVOL might already exist, continuing anyway")
            return True
        return False
    except Exception as e:
        print(f"Unexpected error creating zvol: {e}")
        return False

def create_iscsi_resources_api(session, api_url, zvol_name, target_name, extent_name, hostname, dry_run=False):
    """Create iSCSI target, extent and association using direct API calls"""
    # Get or create target
    target_id = create_iscsi_target(session, api_url, target_name, hostname, dry_run)
    if not target_id:
        print("Failed to create iSCSI target")
        return False
        
    # Get or create extent
    extent_id = create_iscsi_extent(session, api_url, extent_name, zvol_name, hostname, dry_run)
    if not extent_id:
        print("Failed to create iSCSI extent")
        return False
        
    # Associate target with extent
    if not associate_target_extent(session, api_url, target_id, extent_id, dry_run):
        print("Failed to associate target with extent")
        return False
    
    # Make sure iSCSI service is running
    print("Ensuring iSCSI service is running...")
    service_url = f"{api_url}/service/id/iscsitarget"
    service_response = session.get(service_url)
    
    if service_response.status_code == 200:
        service_data = service_response.json()
        service_running = service_data.get('state') == 'RUNNING'
        
        if not service_running:
            print("Starting iSCSI service...")
            start_url = f"{api_url}/service/start"
            start_payload = {"service": "iscsitarget"}
            
            if dry_run:
                print("DRY RUN: Would start iSCSI service")
            else:
                try:
                    start_response = session.post(start_url, json=start_payload)
                    start_response.raise_for_status()
                    print("Successfully started iSCSI service")
                except Exception as e:
                    print(f"Error starting iSCSI service: {e}")
                    # Continue anyway - the service might already be running
        else:
            print("iSCSI service is already running")
    else:
        print(f"Warning: Could not check iSCSI service status: {service_response.status_code}")
    
    return (target_id, extent_id)

def discover_resources(session, api_url):
    """Discover TrueNAS resources related to iSCSI setup"""
    discovery_results = {
        "pools": [],
        "zvols": [],
        "targets": [],
        "extents": [],
        "portals": [],
        "initiators": [],
        "targetextents": []
    }
    
    try:
        # Discover storage pools
        print("\n📊 Discovering storage pools...")
        response = session.get(f"{api_url}/pool")
        if response.status_code == 200:
            pools = response.json()
            discovery_results["pools"] = pools
            for pool in pools:
                pool_name = pool.get('name')
                free_bytes = pool.get('free', 0)
                free_gb = free_bytes / (1024**3)
                print(f"  ➤ Pool: {pool_name} ({free_gb:.1f} GB free)")
        
        # Discover existing zvols (volumes)
        print("\n📊 Discovering existing zvols...")
        response = session.get(f"{api_url}/pool/dataset?type=VOLUME")
        if response.status_code == 200:
            zvols = response.json()
            discovery_results["zvols"] = zvols
            if zvols:
                for zvol in zvols:
                    zvol_name = zvol.get('name')
                    zvol_size = zvol.get('volsize', {}).get('parsed', 0)
                    zvol_size_gb = zvol_size / (1024**3)
                    print(f"  ➤ Zvol: {zvol_name} ({zvol_size_gb:.1f} GB)")
            else:
                print("  No zvols found")
        
        # Discover iSCSI targets
        print("\n📊 Discovering iSCSI targets...")
        response = session.get(f"{api_url}/iscsi/target")
        if response.status_code == 200:
            targets = response.json()
            discovery_results["targets"] = targets
            if targets:
                for target in targets:
                    target_id = target.get('id')
                    target_name = target.get('name')
                    print(f"  ➤ Target: {target_name} (ID: {target_id})")
            else:
                print("  No targets found")
        
        # Discover iSCSI extents
        print("\n📊 Discovering iSCSI extents...")
        response = session.get(f"{api_url}/iscsi/extent")
        if response.status_code == 200:
            extents = response.json()
            discovery_results["extents"] = extents
            if extents:
                for extent in extents:
                    extent_id = extent.get('id')
                    extent_name = extent.get('name')
                    extent_type = extent.get('type')
                    extent_path = extent.get('disk')
                    print(f"  ➤ Extent: {extent_name} (ID: {extent_id}, Type: {extent_type}, Path: {extent_path})")
            else:
                print("  No extents found")
        
        # Discover iSCSI portals
        print("\n📊 Discovering iSCSI portals...")
        response = session.get(f"{api_url}/iscsi/portal")
        if response.status_code == 200:
            portals = response.json()
            discovery_results["portals"] = portals
            if portals:
                for portal in portals:
                    portal_id = portal.get('id')
                    portal_listen = portal.get('listen', [])
                    listen_addresses = [f"{l.get('ip')}:{l.get('port')}" for l in portal_listen]
                    print(f"  ➤ Portal: ID {portal_id} (Listening on: {', '.join(listen_addresses)})")
            else:
                print("  No portals found")
        
        # Discover iSCSI initiators
        print("\n📊 Discovering iSCSI initiators...")
        response = session.get(f"{api_url}/iscsi/initiator")
        if response.status_code == 200:
            initiators = response.json()
            discovery_results["initiators"] = initiators
            if initiators:
                for initiator in initiators:
                    initiator_id = initiator.get('id')
                    initiator_comment = initiator.get('comment', 'No comment')
                    print(f"  ➤ Initiator: ID {initiator_id} (Comment: {initiator_comment})")
            else:
                print("  No initiators found")
        
        # Discover target-extent associations
        print("\n📊 Discovering target-extent associations...")
        response = session.get(f"{api_url}/iscsi/targetextent")
        if response.status_code == 200:
            targetextents = response.json()
            discovery_results["targetextents"] = targetextents
            if targetextents:
                for te in targetextents:
                    te_id = te.get('id')
                    target_id = te.get('target')
                    extent_id = te.get('extent')
                    lun_id = te.get('lunid')
                    print(f"  ➤ Association: ID {te_id} (Target: {target_id}, Extent: {extent_id}, LUN: {lun_id})")
            else:
                print("  No target-extent associations found")
        
        return discovery_results
    
    except Exception as e:
        print(f"Error during discovery: {e}")
        return discovery_results

def check_storage_capacity(session, api_url, pool_name, required_size_str):
    """Check if the storage pool has enough free space"""
    required_bytes = format_size(required_size_str)
    
    try:
        response = session.get(f"{api_url}/pool")
        response.raise_for_status()
        
        pools = response.json()
        for pool in pools:
            if pool.get('name') == pool_name:
                free_bytes = pool.get('free', 0)
                free_gb = free_bytes / (1024**3)
                required_gb = required_bytes / (1024**3)
                
                print(f"\n📊 Storage capacity check:")
                print(f"  ➤ Pool: {pool_name}")
                print(f"  ➤ Free space: {free_gb:.1f} GB")
                print(f"  ➤ Required space: {required_gb:.1f} GB")
                
                if free_bytes >= required_bytes:
                    print(f"✅ Pool {pool_name} has enough free space")
                    return True
                else:
                    print(f"⚠️  Pool {pool_name} has insufficient free space")
                    print(f"   Need {required_gb:.1f} GB but only {free_gb:.1f} GB available")
                    return False
        
        print(f"❌ Pool {pool_name} not found")
        return False
    
    except Exception as e:
        print(f"Error checking storage capacity: {e}")
        return False

def perform_housekeeping(session, api_url, min_days_old=30, dry_run=True):
    """Find and optionally cleanup unused iSCSI resources"""
    try:
        print("\n📊 Performing housekeeping check...")
        
        # Get all extents
        response = session.get(f"{api_url}/iscsi/extent")
        response.raise_for_status()
        extents = response.json()
        
        # Get all target-extent mappings
        response = session.get(f"{api_url}/iscsi/targetextent")
        response.raise_for_status()
        mappings = response.json()
        
        # Find extents that are not associated with any target
        extent_ids_in_use = set(mapping.get('extent') for mapping in mappings)
        unused_extents = [extent for extent in extents if extent.get('id') not in extent_ids_in_use]
        
        if unused_extents:
            print(f"Found {len(unused_extents)} unused extents:")
            for extent in unused_extents:
                extent_id = extent.get('id')
                extent_name = extent.get('name')
                disk_path = extent.get('disk', 'Unknown path')
                print(f"  ➤ Unused extent: {extent_name} (ID: {extent_id}, Path: {disk_path})")
                
                # If not in dry run mode, delete the unused extent
                if not dry_run:
                    try:
                        delete_response = session.delete(f"{api_url}/iscsi/extent/id/{extent_id}")
                        delete_response.raise_for_status()
                        print(f"    ✅ Deleted unused extent {extent_name}")
                    except Exception as e:
                        print(f"    ❌ Failed to delete extent {extent_name}: {e}")
        else:
            print("No unused extents found.")
        
        # Find unused targets (not associated with any extent)
        response = session.get(f"{api_url}/iscsi/target")
        response.raise_for_status()
        targets = response.json()
        
        target_ids_in_use = set(mapping.get('target') for mapping in mappings)
        unused_targets = [target for target in targets if target.get('id') not in target_ids_in_use]
        
        if unused_targets:
            print(f"Found {len(unused_targets)} unused targets:")
            for target in unused_targets:
                target_id = target.get('id')
                target_name = target.get('name')
                print(f"  ➤ Unused target: {target_name} (ID: {target_id})")
                
                # If not in dry run mode, delete the unused target
                if not dry_run:
                    try:
                        delete_response = session.delete(f"{api_url}/iscsi/target/id/{target_id}")
                        delete_response.raise_for_status()
                        print(f"    ✅ Deleted unused target {target_name}")
                    except Exception as e:
                        print(f"    ❌ Failed to delete target {target_name}: {e}")
        else:
            print("No unused targets found.")
            
        return True
    
    except Exception as e:
        print(f"Error during housekeeping: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Create iSCSI target on TrueNAS Scale using REST API")
    parser.add_argument("--server-id", required=True, help="Server ID (e.g., 01, 02)")
    parser.add_argument("--hostname", required=True, help="Server hostname")
    parser.add_argument("--openshift-version", default="stable", help="OpenShift version (default: stable)")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--zvol-size", default="500G", help="Size of the zvol to create")
    parser.add_argument("--zfs-pool", default="test", help="ZFS pool name (default: test)")
    parser.add_argument("--api-key", required=True, help="TrueNAS API key")
    parser.add_argument("--discover-only", action="store_true", help="Only perform discovery without making changes")
    parser.add_argument("--housekeeping", action="store_true", help="Perform housekeeping check for unused resources")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup unused resources (use with caution)")
    parser.add_argument("--dry-run", action="store_true", help="Show API calls without executing them")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Format the zvol name and target name
    server_id = args.server_id
    version_format = args.openshift_version.replace(".", "_")
    zvol_name = f"{args.zfs_pool}/openshift_installations/r630_{server_id}_{version_format}"
    target_name = f"iqn.2005-10.org.freenas.ctl:iscsi.r630-{server_id}.openshift{version_format}"
    extent_name = f"openshift_r630_{server_id}_{version_format}_extent"
    
    # Set up API session
    session, api_url = get_api_session(args)
    
    # Display header
    print("\n" + "=" * 70)
    print(f"  TrueNAS iSCSI Target Management - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Check connectivity to TrueNAS
    print("\n🔍 Checking TrueNAS connectivity...")
    if not check_truenas_connectivity(session, api_url):
        print("❌ Cannot connect to TrueNAS - exiting")
        return 1
    
    # Check system health
    print("\n🔍 Checking TrueNAS system health...")
    check_system_health(session, api_url)
    
    # Check iSCSI service status
    print("\n🔍 Checking iSCSI service status...")
    check_iscsi_service(session, api_url)
    
    # Discover resources
    print("\n🔍 Discovering TrueNAS resources...")
    resources = discover_resources(session, api_url)
    
    # If in discovery-only mode, exit here
    if args.discover_only:
        print("\n✅ Discovery completed successfully")
        return 0
    
    # Perform housekeeping check if requested
    if args.housekeeping:
        perform_housekeeping(session, api_url, dry_run=not args.cleanup)
        if args.housekeeping and not args.cleanup:
            print("\n⚠️  Housekeeping check completed in dry-run mode")
            print("   Re-run with --cleanup to actually remove unused resources")
    
    # Skip creation if only housekeeping was requested
    if args.housekeeping and not args.cleanup and not args.discover_only:
        return 0
    
    # Display setup information
    print("\n" + "=" * 70)
    print(f"📋 iSCSI Target Setup Information:")
    print(f"  ➤ Server: {args.hostname} (ID: {server_id})")
    print(f"  ➤ OpenShift Version: {args.openshift_version}")
    print(f"  ➤ Zvol: {zvol_name}")
    print(f"  ➤ Size: {args.zvol_size}")
    print(f"  ➤ Target: {target_name}")
    print(f"  ➤ Extent: {extent_name}")
    print("=" * 70)
    
    # Check if the pool has enough space
    if not check_storage_capacity(session, api_url, args.zfs_pool, args.zvol_size):
        print("⚠️  Insufficient storage space - proceeding with caution")
    
    # Create zvol using direct API calls
    print("\n🔧 Creating zvol...")
    if not create_zvol_api(session, api_url, zvol_name, args.zvol_size, args.dry_run):
        print("\n❌ Failed to create zvol via API")
        return 1
    
    # Create all iSCSI resources using direct API calls
    print("\n🔧 Creating iSCSI resources...")
    result = create_iscsi_resources_api(session, api_url, zvol_name, target_name, extent_name, args.hostname, args.dry_run)
    if not result or not isinstance(result, tuple):
        print("\n❌ Failed to create iSCSI resources via API")
        return 1
    
    target_id, extent_id = result
    print("\n✅ Success! iSCSI target created successfully")
    print(f"  ➤ Target: {target_name} (ID: {target_id})")
    print(f"  ➤ Extent: {extent_name} (ID: {extent_id})")
    print(f"  ➤ Connection: {args.truenas_ip}:3260/{target_name}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
