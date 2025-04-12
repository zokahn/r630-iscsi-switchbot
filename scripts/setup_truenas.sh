#!/bin/bash
# setup_truenas.sh - Configure TrueNAS Scale for OpenShift multiboot
# Run this script on the TrueNAS Scale server (192.168.2.245)

# Exit on error
set -e

# Configuration variables
POOL_NAME="tank"  # Change this to your actual pool name
OPENSHIFT_ISO_PATH="$POOL_NAME/openshift_isos"
OPENSHIFT_INSTALLATIONS_PATH="$POOL_NAME/openshift_installations"
HTTP_ROOT="/usr/local/www/apache24/data"  # Default HTTP path

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Function to check if running on TrueNAS Scale
check_truenas() {
    if [ ! -f "/etc/version" ] || ! grep -q "TrueNAS-SCALE" /etc/version; then
        echo -e "${RED}Error: This script should be run on TrueNAS Scale.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Running on TrueNAS Scale. Proceeding with setup...${NC}"
}

# Function to check if dataset exists
dataset_exists() {
    zfs list "$1" >/dev/null 2>&1
}

# Function to create directory structure for OpenShift ISOs
create_directory_structure() {
    echo -e "${YELLOW}Creating directory structure for OpenShift ISOs...${NC}"
    
    # Create main datasets if they don't exist
    if ! dataset_exists "$OPENSHIFT_ISO_PATH"; then
        zfs create "$OPENSHIFT_ISO_PATH"
        echo -e "${GREEN}Created dataset $OPENSHIFT_ISO_PATH${NC}"
    else
        echo -e "${YELLOW}Dataset $OPENSHIFT_ISO_PATH already exists${NC}"
    fi
    
    if ! dataset_exists "$OPENSHIFT_INSTALLATIONS_PATH"; then
        zfs create "$OPENSHIFT_INSTALLATIONS_PATH"
        echo -e "${GREEN}Created dataset $OPENSHIFT_INSTALLATIONS_PATH${NC}"
    else
        echo -e "${YELLOW}Dataset $OPENSHIFT_INSTALLATIONS_PATH already exists${NC}"
    fi
    
    # Create subdirectories for different OpenShift versions
    for version in "4.18" "4.17" "4.16"; do
        VERSION_PATH="$OPENSHIFT_ISO_PATH/${version}"
        if ! dataset_exists "$VERSION_PATH"; then
            zfs create "$VERSION_PATH"
            echo -e "${GREEN}Created dataset $VERSION_PATH${NC}"
        else
            echo -e "${YELLOW}Dataset $VERSION_PATH already exists${NC}"
        fi
    done
    
    # Set appropriate permissions
    chmod -R 755 "/mnt/$OPENSHIFT_ISO_PATH"
    echo -e "${GREEN}Directory structure created successfully${NC}"
}

# Function to create zvols for OpenShift installations
create_zvols() {
    echo -e "${YELLOW}Creating zvols for OpenShift installations...${NC}"
    
    for version in "4.18" "4.17" "4.16"; do
        VERSION_FORMAT=${version//./_}
        ZVOL_NAME="$OPENSHIFT_INSTALLATIONS_PATH/${VERSION_FORMAT}_complete"
        
        if ! zfs list "$ZVOL_NAME" >/dev/null 2>&1; then
            # Create 500GB zvol (adjust size as needed)
            zfs create -V 500G -s "$ZVOL_NAME"
            echo -e "${GREEN}Created zvol $ZVOL_NAME (500GB)${NC}"
        else
            echo -e "${YELLOW}Zvol $ZVOL_NAME already exists${NC}"
        fi
    done
    
    echo -e "${GREEN}Zvols created successfully${NC}"
}

# Function to configure iSCSI service
configure_iscsi() {
    echo -e "${YELLOW}Configuring iSCSI service...${NC}"
    
    # Check if iSCSI service is running
    if ! systemctl is-active --quiet ctld; then
        echo -e "${YELLOW}iSCSI service is not running. Attempting to start it...${NC}"
        systemctl start ctld
        sleep 2
        
        if ! systemctl is-active --quiet ctld; then
            echo -e "${RED}Failed to start iSCSI service. Please enable it in the TrueNAS UI.${NC}"
            echo -e "${YELLOW}Go to Services > iSCSI > Configure > Enable Service${NC}"
            return 1
        fi
    fi
    
    echo -e "${GREEN}iSCSI service is running${NC}"
    
    # Manual creation of iSCSI targets using ctladm (direct TrueNAS Scale method)
    echo -e "${YELLOW}Creating iSCSI targets for OpenShift versions...${NC}"
    
    for version in "4.18" "4.17" "4.16"; do
        VERSION_FORMAT=${version//./_}
        TARGET_NAME="iqn.2005-10.org.freenas.ctl:iscsi.r630.openshift$VERSION_FORMAT"
        ZVOL_PATH="/dev/zvol/$OPENSHIFT_INSTALLATIONS_PATH/${VERSION_FORMAT}_complete"
        EXTENT_NAME="openshift_${VERSION_FORMAT}_extent"
        
        echo -e "${YELLOW}Creating target and extent for OpenShift $version...${NC}"
        
        # Check if target already exists
        EXISTING_TARGET=$(midclt call iscsi.target.query "[{\"name\":\"$TARGET_NAME\"}]" | grep -v "\[\]")
        if [ -n "$EXISTING_TARGET" ]; then
            echo -e "${YELLOW}Target $TARGET_NAME already exists, skipping...${NC}"
            continue
        fi
        
        # Use midclt (TrueNAS middleware client) to create the target
        echo -e "${YELLOW}Creating iSCSI target: $TARGET_NAME${NC}"
        TARGET_ID=$(midclt call iscsi.target.create "{\"name\":\"$TARGET_NAME\",\"alias\":\"OpenShift $version\",\"mode\":\"ISCSI\",\"groups\":[{\"portal\":1,\"initiator\":1,\"auth\":null}]}" | jq '.id')
        
        if [ -z "$TARGET_ID" ] || [ "$TARGET_ID" = "null" ]; then
            echo -e "${RED}Failed to create target $TARGET_NAME${NC}"
            continue
        fi
        
        echo -e "${GREEN}Successfully created target with ID: $TARGET_ID${NC}"
        
        # Create the extent for the zvol
        echo -e "${YELLOW}Creating extent for zvol: $ZVOL_PATH${NC}"
        EXTENT_ID=$(midclt call iscsi.extent.create "{\"name\":\"$EXTENT_NAME\",\"type\":\"DISK\",\"disk\":\"zvol/$OPENSHIFT_INSTALLATIONS_PATH/${VERSION_FORMAT}_complete\",\"blocksize\":512,\"pblocksize\":false,\"comment\":\"OpenShift $version boot image\",\"insecure_tpc\":true,\"xen\":false,\"rpm\":\"SSD\",\"ro\":false}" | jq '.id')
        
        if [ -z "$EXTENT_ID" ] || [ "$EXTENT_ID" = "null" ]; then
            echo -e "${RED}Failed to create extent $EXTENT_NAME${NC}"
            continue
        fi
        
        echo -e "${GREEN}Successfully created extent with ID: $EXTENT_ID${NC}"
        
        # Associate the extent with the target
        echo -e "${YELLOW}Associating extent with target...${NC}"
        TARGETEXTENT_ID=$(midclt call iscsi.targetextent.create "{\"target\":$TARGET_ID,\"extent\":$EXTENT_ID,\"lunid\":0}" | jq '.id')
        
        if [ -z "$TARGETEXTENT_ID" ] || [ "$TARGETEXTENT_ID" = "null" ]; then
            echo -e "${RED}Failed to associate extent with target${NC}"
            continue
        fi
        
        echo -e "${GREEN}Successfully associated extent with target, ID: $TARGETEXTENT_ID${NC}"
        echo -e "${GREEN}Completed iSCSI setup for OpenShift $version${NC}"
    done
    
    echo -e "${GREEN}iSCSI configuration completed${NC}"
}

# Function to configure HTTP access for ISO files
configure_http_access() {
    echo -e "${YELLOW}Configuring HTTP access for ISO files...${NC}"
    
    # Check if nginx is installed (TrueNAS Scale uses nginx)
    if ! command -v nginx >/dev/null; then
        echo -e "${RED}Nginx not found. Please make sure TrueNAS Scale is properly installed.${NC}"
        return 1
    fi
    
    # Create a symbolic link to the OpenShift ISOs directory
    NGINX_ROOT="/var/www/html"
    
    if [ ! -d "$NGINX_ROOT" ]; then
        mkdir -p "$NGINX_ROOT"
    fi
    
    # Create symbolic link if it doesn't exist
    if [ ! -L "$NGINX_ROOT/openshift_isos" ]; then
        ln -s "/mnt/$OPENSHIFT_ISO_PATH" "$NGINX_ROOT/openshift_isos"
        echo -e "${GREEN}Created symbolic link from /mnt/$OPENSHIFT_ISO_PATH to $NGINX_ROOT/openshift_isos${NC}"
    else
        echo -e "${YELLOW}Symbolic link $NGINX_ROOT/openshift_isos already exists${NC}"
    fi
    
    echo -e "${GREEN}HTTP access configured${NC}"
    echo -e "${YELLOW}Note: ISOs will be accessible at http://192.168.2.245/openshift_isos/[version]/${NC}"
}

# Main function
main() {
    echo "===== TrueNAS Scale Setup for OpenShift Multiboot ====="
    check_truenas
    
    create_directory_structure
    create_zvols
    configure_iscsi
    configure_http_access
    
    echo -e "${GREEN}==================================================${NC}"
    echo -e "${GREEN}Setup completed successfully!${NC}"
    echo -e "${GREEN}==================================================${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "${YELLOW}1. Configure iSCSI targets in the TrueNAS UI${NC}"
    echo -e "${YELLOW}2. Generate OpenShift agent-based ISOs and upload them to /mnt/$OPENSHIFT_ISO_PATH/[version]/${NC}"
    echo -e "${YELLOW}3. Run switch_openshift.py script on your management machine to configure the servers${NC}"
}

# Run the main function
main
