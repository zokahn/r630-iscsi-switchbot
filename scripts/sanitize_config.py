#!/usr/bin/env python3
"""
Sanitize an OpenShift configuration file by removing sensitive information
for safe storage.
"""

import yaml
import sys
import os
from pathlib import Path

def main():
    # Get the values file from environment variable or command line
    if len(sys.argv) > 1:
        values_file = sys.argv[1]
    else:
        values_file = os.environ.get('VALUES_FILE')
        
    if not values_file:
        print("Error: No values file specified")
        sys.exit(1)
    
    # Load the values file
    try:
        with open(values_file, 'r') as f:
            values = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading values file: {e}")
        sys.exit(1)
    
    # Create a sanitized copy for storage
    safe_values = dict(values)
    
    # Remove sensitive information
    if 'pullSecret' in safe_values:
        safe_values['pullSecret'] = '***REDACTED***'
    if 'sshKey' in safe_values:
        safe_values['sshKey'] = '***REDACTED***'
    
    # Handle secretReferences if present
    if 'secretReferences' in safe_values:
        for key, value in safe_values['secretReferences'].items():
            safe_values['secretReferences'][key] = f'***REDACTED {key}***'
    
    # Determine output file path
    output_file = 'safe_config.yaml'
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # Write to the output file
    try:
        with open(output_file, 'w') as f:
            yaml.dump(safe_values, f, sort_keys=False)
        print(f"Sanitized configuration written to {output_file}")
    except Exception as e:
        print(f"Error writing sanitized configuration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
