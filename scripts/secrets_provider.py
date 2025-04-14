#!/usr/bin/env python3
"""
Secrets Provider Utility

This script provides a simplified interface for accessing secrets from various sources:
1. Hashicorp Vault (preferred when available)
2. Environment variables (fallback)
3. .env files (fallback for local development)

It supports secret reference resolution in configuration files.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, Union

# Try to import dotenv for .env file support
try:
    from dotenv import load_dotenv
    dotenv_available = True
except ImportError:
    dotenv_available = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("secrets_provider")

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize variables
vault_component = None
initialized = False
vault_available = False

def init(
    vault_addr: Optional[str] = None,
    vault_token: Optional[str] = None,
    vault_role_id: Optional[str] = None,
    vault_secret_id: Optional[str] = None,
    vault_mount_point: str = 'secret',
    vault_path_prefix: str = 'r630-switchbot',
    env_file: Optional[str] = None,
    verify_permissions: bool = True
) -> bool:
    """
    Initialize the secrets provider with configuration options.
    
    Args:
        vault_addr: Vault server address
        vault_token: Vault token for authentication
        vault_role_id: Vault AppRole role_id
        vault_secret_id: Vault AppRole secret_id
        vault_mount_point: Mount point for KV secrets engine
        vault_path_prefix: Path prefix for secrets
        env_file: Path to .env file to load
        verify_permissions: Whether to verify Vault permissions
        
    Returns:
        True if initialized successfully, False otherwise
    """
    global vault_component, initialized, vault_available
    
    # Load environment variables from .env file if specified
    if dotenv_available and env_file:
        env_path = os.path.expanduser(env_file)
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
            logger.info(f"Loaded environment variables from {env_file}")
        else:
            logger.warning(f"Specified .env file not found: {env_file}")
    
    # If no Vault address is provided, check environment variable
    if not vault_addr:
        vault_addr = os.environ.get('VAULT_ADDR')
    
    # If no token/credentials provided, check environment variables
    if not vault_token:
        vault_token = os.environ.get('VAULT_TOKEN')
    
    if not vault_role_id:
        vault_role_id = os.environ.get('VAULT_ROLE_ID')
    
    if not vault_secret_id:
        vault_secret_id = os.environ.get('VAULT_SECRET_ID')
    
    # If we have a Vault address and either token or AppRole credentials,
    # initialize Vault component
    if vault_addr and (vault_token or (vault_role_id and vault_secret_id)):
        try:
            # Import component dynamically to avoid circular dependencies
            from framework.components.vault_component import VaultComponent
            
            auth_method = 'token' if vault_token else 'approle'
            
            config = {
                'vault_addr': vault_addr,
                'vault_token': vault_token,
                'vault_role_id': vault_role_id,
                'vault_secret_id': vault_secret_id,
                'vault_auth_method': auth_method,
                'vault_mount_point': vault_mount_point,
                'vault_path_prefix': vault_path_prefix
            }
            
            logger.info(f"Initializing Vault component with {auth_method} authentication")
            vault_component = VaultComponent(config)
            
            # Run discovery to check connectivity
            discovery_results = vault_component.discover()
            
            # Check if authentication was successful
            if not discovery_results.get('token_valid', False):
                logger.warning("Vault authentication failed - falling back to environment variables")
                vault_available = False
            else:
                # If requested, verify permissions by running process phase
                if verify_permissions:
                    process_results = vault_component.process()
                    if process_results.get('permissions_verified', False):
                        logger.info("Vault permissions verified successfully")
                    else:
                        logger.warning("Vault permission verification failed - falling back to environment variables")
                        vault_available = False
                        return False
                vault_available = True
                logger.info(f"Vault component initialized successfully at {vault_addr}")
                
        except ImportError:
            logger.warning("VaultComponent not available - falling back to environment variables")
            vault_available = False
        except Exception as e:
            logger.error(f"Error initializing Vault component: {e}")
            vault_available = False
    else:
        logger.info("Vault configuration not provided - using environment variables for secrets")
        vault_available = False
    
    initialized = True
    return True

def get_secret(path: str, key: Optional[str] = None) -> Any:
    """
    Get a secret from the configured secrets provider.
    
    Will try Vault first, then fall back to environment variables.
    
    Args:
        path: Path to the secret (Vault path or environment variable prefix)
        key: Optional specific key within the secret
        
    Returns:
        The secret value, or None if not found
    """
    global initialized, vault_component, vault_available
    
    # Initialize if not already done
    if not initialized:
        init()
    
    # Try Vault first if available
    if vault_available and vault_component:
        try:
            secret_data = vault_component.get_secret(path, key)
            if secret_data is not None:
                return secret_data
            # If no value found, fall through to environment variables
        except Exception as e:
            logger.error(f"Error getting secret from Vault: {e}")
            # Fall through to environment variables
    
    # Fall back to environment variables
    try:
        # Convert path to environment variable format
        env_key = path.replace('/', '_').upper()
        if key:
            env_key = f"{env_key}_{key.upper()}"
        
        # Get from environment
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value
    except Exception as e:
        logger.error(f"Error getting secret from environment: {e}")
    
    # Return None if not found in any source
    return None

def put_secret(path: str, data: Dict[str, Any]) -> bool:
    """
    Store a secret using the configured secrets provider.
    
    Currently only supports storing in Vault, not environment variables.
    
    Args:
        path: Path where to store the secret
        data: Dictionary of key/value pairs to store
        
    Returns:
        True if successful, False otherwise
    """
    global initialized, vault_component, vault_available
    
    # Initialize if not already done
    if not initialized:
        init()
    
    # Can only store in Vault
    if vault_available and vault_component:
        try:
            result = vault_component.put_secret(path, data)
            return result
        except Exception as e:
            logger.error(f"Error storing secret in Vault: {e}")
            return False
    else:
        logger.warning("Cannot store secrets: Vault not available")
        return False

def process_references(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process secret references in configuration data.
    
    Secret references have the format:
    - "secret:path/to/secret" - returns entire secret dictionary
    - "secret:path/to/secret:key" - returns specific key from secret
    
    Args:
        data: Configuration dictionary potentially containing secret references
        
    Returns:
        Processed configuration with resolved secret references
    """
    if not isinstance(data, dict):
        if isinstance(data, str) and data.startswith('secret:'):
            # This is a secret reference: secret:path:key or secret:path
            parts = data[7:].split(':')
            path = parts[0]
            key = parts[1] if len(parts) > 1 else None
            return get_secret(path, key)
        return data
    
    # Process each key in the dictionary
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = process_references(value)
        elif isinstance(value, list):
            # Process lists that might contain dictionaries
            result[key] = [
                process_references(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str) and value.startswith('secret:'):
            # Process secret reference
            parts = value[7:].split(':')
            path = parts[0]
            key = parts[1] if len(parts) > 1 else None
            result[key] = get_secret(path, key)
        else:
            # Pass through other values unchanged
            result[key] = value
    
    return result

def clear_cache():
    """
    Clear any cached secrets.
    
    Currently a no-op, but may be implemented in the future if caching is added.
    """
    pass

if __name__ == "__main__":
    # Example usage - can be used as a CLI tool as well
    import argparse
    
    parser = argparse.ArgumentParser(description="Secret Provider Utility")
    parser.add_argument('--get', metavar='PATH[:KEY]', help='Get a secret')
    parser.add_argument('--put', metavar='PATH', help='Put a secret (requires --data)')
    parser.add_argument('--data', metavar='JSON', help='JSON data for put operation')
    parser.add_argument('--init', action='store_true', help='Just initialize the provider')
    parser.add_argument('--env-file', help='Path to .env file')
    parser.add_argument('--vault-addr', help='Vault server address')
    parser.add_argument('--vault-token', help='Vault token')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Initialize
    init(vault_addr=args.vault_addr, vault_token=args.vault_token, env_file=args.env_file)
    
    if args.init:
        print(f"Initialized: Vault {'available' if vault_available else 'not available'}")
    
    # Get secret
    if args.get:
        parts = args.get.split(':')
        path = parts[0]
        key = parts[1] if len(parts) > 1 else None
        value = get_secret(path, key)
        if value is not None:
            if isinstance(value, dict):
                print(json.dumps(value, indent=2))
            else:
                print(value)
        else:
            print(f"Secret not found: {args.get}")
    
    # Put secret
    if args.put and args.data:
        try:
            data = json.loads(args.data)
            if not isinstance(data, dict):
                print("Error: Data must be a JSON object")
                sys.exit(1)
            
            success = put_secret(args.put, data)
            if success:
                print(f"Secret stored successfully at {args.put}")
            else:
                print(f"Failed to store secret at {args.put}")
                sys.exit(1)
        except json.JSONDecodeError:
            print("Error: Invalid JSON data")
            sys.exit(1)
