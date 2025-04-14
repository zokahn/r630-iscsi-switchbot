#!/usr/bin/env python3
"""
Python 3.12 Helper Functions

This module demonstrates Python 3.12 type annotation features
that can be used throughout the codebase.
"""

from typing import TypedDict, Optional, Dict, List, Any, Callable, Generic, TypeVar


# TypeVar and Generic with simplified 3.12 syntax
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# TypedDict classes for common data structures
class ServerMetadata(TypedDict):
    """Metadata for an iSCSI server."""
    server_id: str
    hostname: str
    ip_address: str
    reboot_required: bool
    last_update: str  # ISO format timestamp


class ISOMetadata(TypedDict):
    """Metadata for an ISO image."""
    version: str
    server_id: str
    hostname: str
    timestamp: str
    md5: str
    size: int


# Python 3.12 Generic class syntax
class Cache[KeyType, ValueType]:
    """
    A generic cache implementation using Python 3.12 syntax.
    
    This demonstrates the new type parameter syntax from PEP 695.
    """
    
    def __init__(self, max_size: int = 100):
        self._cache: Dict[KeyType, ValueType] = {}
        self._max_size = max_size
    
    def get(self, key: KeyType) -> Optional[ValueType]:
        """Get a value from the cache."""
        return self._cache.get(key)
    
    def set(self, key: KeyType, value: ValueType) -> None:
        """Set a value in the cache."""
        # Implement LRU eviction if needed
        if len(self._cache) >= self._max_size:
            # Remove oldest item (first key)
            if self._cache:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
        
        self._cache[key] = value
    
    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()


# Utility function for improved f-string formatting
def format_metadata(metadata: Dict[str, Any]) -> str:
    """
    Format metadata using Python 3.12 enhanced f-strings.
    
    This demonstrates the f-string improvements from PEP 701.
    """
    lines = []
    
    # Python 3.12 allows arbitrary expressions in f-strings
    for key, value in metadata.items():
        formatted_value = (
            f"{value:.2f}" if isinstance(value, float) else
            f"{value}" if value is not None else
            "N/A"
        )
        
        # Python 3.12 allows quotes without escaping
        lines.append(f'{key}: "{formatted_value}"')
    
    return "\n".join(lines)


# Performance-optimized function using comprehensions
def filter_and_transform(items: List[Dict[str, Any]], 
                         filter_key: str,
                         filter_value: Any) -> List[Dict[str, Any]]:
    """
    Filter and transform items using optimized comprehensions.
    
    This demonstrates the comprehension optimizations from PEP 709.
    """
    # Python 3.12 optimizes list comprehensions to be up to 2x faster
    filtered = [item for item in items if item.get(filter_key) == filter_value]
    
    # Python 3.12 optimizes nested comprehensions
    transformed = [{
        k: v.upper() if isinstance(v, str) else v
        for k, v in item.items()
    } for item in filtered]
    
    return transformed


# Usage example
if __name__ == "__main__":
    # Create a server cache
    server_cache = Cache[str, ServerMetadata]()
    
    # Add a server
    server_cache.set("server1", {
        "server_id": "01",
        "hostname": "r630-01",
        "ip_address": "192.168.1.101",
        "reboot_required": False,
        "last_update": "2025-04-14T10:30:00"
    })
    
    # Get server
    server = server_cache.get("server1")
    if server:
        print(format_metadata(server))
