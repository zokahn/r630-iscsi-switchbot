#!/bin/bash
# truenas_wrapper.sh - Secure wrapper for TrueNAS Scale API access
# This script reads credentials from a secure configuration file

# Exit on error
set -e

# Configuration
AUTH_DIR="$HOME/.config/truenas"
AUTH_FILE="$AUTH_DIR/auth.json"
DEFAULT_HOST="192.168.2.245"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed.${NC}"
    echo "Please install jq with your package manager:"
    echo "  - Debian/Ubuntu: sudo apt install jq"
    echo "  - RHEL/CentOS: sudo yum install jq"
    echo "  - macOS: brew install jq"
    exit 1
fi

# Function to create config file if it doesn't exist
create_config() {
    echo -e "${YELLOW}No authentication file found at $AUTH_FILE${NC}"
    echo -e "Let's create one now...\n"
    
    read -p "TrueNAS Scale hostname or IP [$DEFAULT_HOST]: " host
    host=${host:-$DEFAULT_HOST}
    
    echo -e "\nAuthentication method:"
    echo "1) API Key (Recommended)"
    echo "2) Username/Password"
    read -p "Select authentication method [1]: " auth_method
    auth_method=${auth_method:-1}
    
    if [ "$auth_method" = "1" ]; then
        echo -e "\nYou selected API Key authentication."
        echo -e "${YELLOW}To create an API key in TrueNAS Scale:${NC}"
        echo "1. Log in to the TrueNAS Scale web interface"
        echo "2. Navigate to Credentials → API Keys"
        echo "3. Click Add"
        echo "4. Provide a name (e.g., 'OpenShift Multiboot Automation')"
        echo "5. Click Save and copy the generated key"
        echo ""
        read -p "Enter your API key: " api_key
        
        # Create the config file with API key
        mkdir -p "$AUTH_DIR"
        cat > "$AUTH_FILE" << EOF
{
  "host": "$host",
  "api_key": "$api_key"
}
EOF

    elif [ "$auth_method" = "2" ]; then
        echo -e "\nYou selected Username/Password authentication."
        read -p "Username [root]: " username
        username=${username:-root}
        read -s -p "Password: " password
        echo ""
        
        # Create the config file with username/password
        mkdir -p "$AUTH_DIR"
        cat > "$AUTH_FILE" << EOF
{
  "host": "$host",
  "username": "$username",
  "password": "$password"
}
EOF
    else
        echo -e "${RED}Invalid selection.${NC}"
        exit 1
    fi
    
    # Set secure permissions
    chmod 600 "$AUTH_FILE"
    echo -e "\n${GREEN}Authentication file created at $AUTH_FILE${NC}"
    echo -e "${YELLOW}Note: This file contains sensitive information and is readable only by your user.${NC}"
}

# Check if config file exists
if [ ! -f "$AUTH_FILE" ]; then
    create_config
fi

# Read authentication details from config file
HOST=$(jq -r '.host' < "$AUTH_FILE")
API_KEY=$(jq -r '.api_key // "null"' < "$AUTH_FILE")
USERNAME=$(jq -r '.username // "null"' < "$AUTH_FILE")
PASSWORD=$(jq -r '.password // "null"' < "$AUTH_FILE")

# Build authentication arguments
AUTH_ARGS=""
if [ "$API_KEY" != "null" ]; then
    AUTH_ARGS="--host $HOST --api-key $API_KEY"
elif [ "$USERNAME" != "null" ] && [ "$PASSWORD" != "null" ]; then
    AUTH_ARGS="--host $HOST --username $USERNAME --password $PASSWORD"
else
    echo -e "${RED}Error: Invalid configuration in $AUTH_FILE${NC}"
    echo "The file should contain either api_key or both username and password."
    exit 1
fi

# Determine which script to run
SCRIPT_DIR="$(dirname "$0")"
SCRIPT_NAME="${1:-autodiscovery}"
shift 2>/dev/null || true  # Shift if there are arguments, ignore error if not

case "$SCRIPT_NAME" in
    "autodiscovery"|"auto")
        # We've discovered that port 444 over HTTPS is the correct connection method
        # Unless a port is already specified in the host
        if grep -q ":" <<< "$HOST"; then
            # Host includes port, no need to add it
            PORT_ARGS=""
        else
            PORT_ARGS="--port 444"
        fi
        
        SCRIPT="$SCRIPT_DIR/truenas_autodiscovery.py $PORT_ARGS"
        ;;
    "setup")
        # For setup_truenas.sh, we need to use SSH
        echo -e "${YELLOW}Running setup script via SSH on $HOST...${NC}"
        scp "$SCRIPT_DIR/setup_truenas.sh" "root@$HOST:/tmp/"
        ssh "root@$HOST" "bash /tmp/setup_truenas.sh"
        exit $?
        ;;
    *)
        echo -e "${RED}Unknown script: $SCRIPT_NAME${NC}"
        echo "Available options:"
        echo "  - autodiscovery (default): Run truenas_autodiscovery.py"
        echo "  - setup: Run setup_truenas.sh on the TrueNAS server"
        exit 1
        ;;
esac

# Execute the script with the authentication arguments
echo -e "${GREEN}Running: $SCRIPT $AUTH_ARGS $@${NC}"
eval "$SCRIPT $AUTH_ARGS $@"
