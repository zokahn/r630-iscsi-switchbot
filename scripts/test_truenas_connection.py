#!/usr/bin/env python3
# test_truenas_connection.py - Test connection to TrueNAS Scale API

import argparse
import requests
import sys

def test_connection(host, port=None, use_https=True, api_key=None, username=None, password=None):
    """Test connection to TrueNAS Scale API"""
    # Handle port in host
    if ":" in host and not port:
        host, port_str = host.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            pass
    
    # Construct base URL
    protocol = "https" if use_https else "http"
    if port:
        base_url = f"{protocol}://{host}:{port}/api"
    else:
        base_url = f"{protocol}://{host}/api"
    
    # Test different API paths
    api_paths = [
        "/v2.0/system/info",  # v2.0 path
        "/v2.0",              # v2.0 root
        "/v1.0/system/info",  # v1.0 path (fallback)
        "/v1.0",              # v1.0 root
        "",                   # root
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Add authentication
    auth = None
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif username and password:
        auth = (username, password)
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    print(f"Testing connection to TrueNAS Scale at {host}")
    print(f"Authentication: {'API Key' if api_key else 'Username/Password' if auth else 'None'}")
    
    # Try different combinations
    ports_to_try = [port] if port else [None, 80, 443, 444, 8080]
    
    for current_port in ports_to_try:
        for use_ssl in [use_https, not use_https]:
            protocol = "https" if use_ssl else "http"
            
            if current_port:
                current_base = f"{protocol}://{host}:{current_port}/api"
            else:
                current_base = f"{protocol}://{host}/api"
            
            print(f"\nTrying {current_base}...")
            
            for path in api_paths:
                url = current_base + path
                try:
                    print(f"  Testing {url}...")
                    response = requests.get(
                        url, 
                        headers=headers, 
                        auth=auth, 
                        verify=False,  # Skip SSL verification
                        timeout=5
                    )
                    
                    # Handle different status codes
                    if response.status_code == 200:
                        print(f"  ✅ SUCCESS! Got 200 OK from {url}")
                        print(f"  Response: {response.text[:100]}...")
                        return {
                            "success": True,
                            "protocol": protocol,
                            "host": host,
                            "port": current_port,
                            "path": path,
                            "url": url
                        }
                    elif response.status_code == 401:
                        print(f"  ⚠️ Authentication needed for {url}")
                    elif response.status_code == 403:
                        print(f"  ⚠️ Authentication failed for {url}")
                    else:
                        print(f"  ❌ Got status {response.status_code} from {url}")
                
                except requests.exceptions.ConnectionError as e:
                    print(f"  ❌ Connection error: {e.__class__.__name__}")
                except requests.exceptions.Timeout:
                    print(f"  ❌ Timeout connecting to {url}")
                except requests.exceptions.RequestException as e:
                    print(f"  ❌ Request error: {e}")
    
    print("\n❌ Failed to connect to TrueNAS Scale API")
    return {"success": False}

def main():
    parser = argparse.ArgumentParser(description="Test connection to TrueNAS Scale API")
    parser.add_argument("--host", default="192.168.2.245", help="TrueNAS Scale hostname or IP")
    parser.add_argument("--port", type=int, help="Port number (optional)")
    parser.add_argument("--use-http", action="store_true", help="Use HTTP instead of HTTPS")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    
    args = parser.parse_args()
    
    result = test_connection(
        host=args.host,
        port=args.port,
        use_https=not args.use_http,
        api_key=args.api_key,
        username=args.username,
        password=args.password
    )
    
    if result["success"]:
        print("\n✅ Successfully connected to TrueNAS Scale API!")
        print(f"Recommended connection parameters:")
        print(f"  Host: {result['host']}")
        print(f"  Port: {result['port'] or 'default'}")
        print(f"  Protocol: {result['protocol']}")
        print(f"  API Path: {result['path']}")
        
        # Generate command line for truenas_autodiscovery.py
        cmd_args = [
            "--host", result['host']
        ]
        
        if result['port']:
            cmd_args.extend(["--port", str(result['port'])])
        
        if result['protocol'] == 'http':
            cmd_args.append("--use-http")
        
        if args.api_key:
            cmd_args.extend(["--api-key", args.api_key])
        elif args.username:
            cmd_args.extend(["--username", args.username])
            if args.password:
                cmd_args.extend(["--password", args.password])
        
        print("\nCommand line for truenas_autodiscovery.py:")
        print("./scripts/truenas_autodiscovery.py " + " ".join(cmd_args))
        
    else:
        print("\n❌ Failed to connect to TrueNAS Scale API")
        print("Please check the hostname, port, and authentication details")
        sys.exit(1)

if __name__ == "__main__":
    main()
