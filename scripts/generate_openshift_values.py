#!/usr/bin/env python3
# generate_openshift_values.py - Script to generate OpenShift installation values

import argparse
import os
import sys
import yaml
from pathlib import Path
import ipaddress
from datetime import datetime

# Default paths and settings
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
TEMPLATE_FILE = CONFIG_DIR / "openshift_install_values_template.yaml"

def validate_ip_address(ip):
    """Validate if the string is a valid IP address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def validate_domain(domain):
    """Simple domain validation"""
    if len(domain) < 4 or '.' not in domain:
        return False
    return True

def generate_values_file(args):
    """Generate the OpenShift installation values file"""
    
    # Validate inputs
    if not validate_ip_address(args.node_ip):
        print(f"Error: '{args.node_ip}' is not a valid IP address.")
        return False
    
    if not validate_ip_address(args.api_vip):
        print(f"Error: '{args.api_vip}' is not a valid IP address.")
        return False
    
    if not validate_ip_address(args.ingress_vip):
        print(f"Error: '{args.ingress_vip}' is not a valid IP address.")
        return False
    
    if not validate_domain(args.base_domain):
        print(f"Error: '{args.base_domain}' is not a valid domain name.")
        return False
    
    # Read template
    try:
        with open(TEMPLATE_FILE, 'r') as f:
            config = yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"Error loading template file: {e}")
        return False
    
    # Update config with provided values
    config['metadata']['name'] = args.cluster_name
    config['baseDomain'] = args.base_domain
    
    # Update machine network CIDR based on node IP
    network = ipaddress.IPv4Network(f"{args.node_ip}/24", strict=False)
    config['networking']['machineNetwork'][0]['cidr'] = str(network)
    
    # Update SNO specific settings
    if 'sno' not in config:
        config['sno'] = {}
    
    config['sno']['nodeIP'] = args.node_ip
    config['sno']['apiVIP'] = args.api_vip
    config['sno']['ingressVIP'] = args.ingress_vip
    config['sno']['domain'] = f"apps.{args.cluster_name}.{args.base_domain}"
    config['sno']['hostname'] = args.hostname
    
    # Add server ID and timestamp to metadata if provided
    if args.server_id:
        if 'metadata' not in config:
            config['metadata'] = {}
        config['metadata']['server_id'] = args.server_id
    
    # Generate or use provided timestamp
    timestamp = args.timestamp
    if not timestamp:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    config['metadata']['deployment_timestamp'] = timestamp
    
    # Determine output directory and file name
    output_dir = CONFIG_DIR
    if args.output_dir:
        output_dir = Path(args.output_dir)
    
    # Create server-specific directory structure if server ID is provided
    if args.server_id:
        # Create deployments directory under the specified output directory
        deployments_dir = output_dir / "deployments"
        server_dir = deployments_dir / f"r630-{args.server_id}"
        server_dir.mkdir(parents=True, exist_ok=True)
        output_dir = server_dir
        
        # Create deployment ID for the filename
        deployment_id = f"r630-{args.server_id}-{args.cluster_name}-{timestamp}"
        output_file = output_dir / f"{deployment_id}.yaml"
        print(f"Creating deployment configuration: {deployment_id}")
    else:
        # Use traditional naming if no server ID is provided (backward compatibility)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"openshift_install_values_{args.cluster_name}.yaml"
    
    # Write to file
    try:
        with open(output_file, 'w') as f:
            yaml.dump(config, f, sort_keys=False)
        print(f"OpenShift installation values file generated at: {output_file}")
        return True
    except Exception as e:
        print(f"Error writing config file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate OpenShift installation values file")
    
    parser.add_argument("--cluster-name", default="sno", help="Cluster name prefix (default: sno)")
    parser.add_argument("--base-domain", default="example.com", help="Base domain (default: example.com)")
    parser.add_argument("--hostname", default="sno", help="Hostname for the single node (default: sno)")
    parser.add_argument("--node-ip", required=True, help="IP address of the single node")
    parser.add_argument("--api-vip", help="Virtual IP for the API server (default: node_ip + 1)")
    parser.add_argument("--ingress-vip", help="Virtual IP for the ingress controller (default: node_ip + 2)")
    parser.add_argument("--output-dir", help="Output directory (default: config directory)")
    parser.add_argument("--server-id", help="Server identifier (e.g., 01, 02) for multi-server tracking")
    parser.add_argument("--timestamp", help="Deployment timestamp (default: current time, format: YYYYMMDDHHMMSS)")
    
    args = parser.parse_args()
    
    # If API VIP not provided, use node_ip + 1
    if not args.api_vip:
        try:
            node_ip = ipaddress.IPv4Address(args.node_ip)
            args.api_vip = str(node_ip + 1)
            print(f"API VIP not provided, using: {args.api_vip}")
        except (ValueError, ipaddress.AddressValueError):
            print(f"Error: Could not calculate API VIP from '{args.node_ip}'")
            return 1
    
    # If Ingress VIP not provided, use node_ip + 2
    if not args.ingress_vip:
        try:
            node_ip = ipaddress.IPv4Address(args.node_ip)
            args.ingress_vip = str(node_ip + 2)
            print(f"Ingress VIP not provided, using: {args.ingress_vip}")
        except (ValueError, ipaddress.AddressValueError):
            print(f"Error: Could not calculate Ingress VIP from '{args.node_ip}'")
            return 1
    
    success = generate_values_file(args)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
