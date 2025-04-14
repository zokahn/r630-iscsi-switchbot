#!/usr/bin/env python3
"""
Configuration for testing with Docker services.

This file provides configurations for component tests that connect to
the actual Docker services instead of using mocks.
"""

def get_s3_docker_config():
    """
    Get S3 configuration that connects to the Docker MinIO service.
    """
    return {
        'endpoint': 'localhost:9000',  # Endpoint without protocol
        'access_key': 'minioadmin',
        'secret_key': 'minioadmin',
        'private_bucket': 'r630-switchbot-private',
        'public_bucket': 'r630-switchbot-public',
        'component_id': 's3-docker-test',
        'create_buckets_if_missing': True,
        'secure': False  # Disable SSL matching S3Component parameter
    }

def get_vault_docker_config():
    """
    Get Vault configuration that connects to the Docker Vault service.
    """
    return {
        'vault_addr': 'http://localhost:8200',
        'vault_token': 'devtoken',
        'secret_path': 'r630-switchbot',
        'component_id': 'vault-docker-test'
    }
