#!/bin/bash
# setup_github_secrets.sh - Helper script to set up required GitHub secrets for the R630 iSCSI SwitchBot project

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Repository information
REPO_NAME=$(git remote get-url origin | sed -n 's/.*github.com[:/]\(.*\).git/\1/p')

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}== GitHub Secrets Setup Helper${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}ERROR: GitHub CLI (gh) is not installed. Please install it first:${NC}"
    echo -e "${YELLOW}https://cli.github.com/manual/installation${NC}"
    exit 1
fi

# Check GitHub authentication
if ! gh auth status &> /dev/null; then
    echo -e "${RED}ERROR: GitHub CLI is not authenticated. Please run:${NC}"
    echo -e "${YELLOW}gh auth login${NC}"
    exit 1
fi

echo -e "${GREEN}✓ GitHub CLI is installed and authenticated${NC}"
echo -e "${GREEN}✓ Using repository: $REPO_NAME${NC}"

# Function to check if a secret exists
check_secret() {
    local secret_name=$1
    if gh secret list -R "$REPO_NAME" 2>/dev/null | grep -q "$secret_name"; then
        echo -e "${GREEN}✓ Secret '$secret_name' already exists${NC}"
        return 0
    else
        echo -e "${YELLOW}! Secret '$secret_name' not found${NC}"
        return 1
    fi
}

# Function to set a secret from file
set_secret_from_file() {
    local secret_name=$1
    local file_path=$2
    
    if [ ! -f "$file_path" ]; then
        echo -e "${RED}ERROR: File not found: $file_path${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Setting secret '$secret_name' from file: $file_path${NC}"
    gh secret set "$secret_name" -R "$REPO_NAME" < "$file_path"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Secret '$secret_name' set successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to set secret '$secret_name'${NC}"
        return 1
    fi
}

# Function to set a secret from user input
set_secret_from_input() {
    local secret_name=$1
    local prompt_text=$2
    local temp_file=$(mktemp)
    
    echo -e "${BLUE}$prompt_text${NC}"
    read -p "Press ENTER to open editor and paste the content" answer
    
    ${EDITOR:-vi} "$temp_file"
    
    if [ ! -s "$temp_file" ]; then
        echo -e "${RED}No content provided. Secret not set.${NC}"
        rm "$temp_file"
        return 1
    fi
    
    gh secret set "$secret_name" -R "$REPO_NAME" < "$temp_file"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Secret '$secret_name' set successfully${NC}"
        rm "$temp_file"
        return 0
    else
        echo -e "${RED}✗ Failed to set secret '$secret_name'${NC}"
        rm "$temp_file"
        return 1
    fi
}

# Function to generate an SSH key and set related secrets
generate_ssh_key_and_secrets() {
    local key_name=$1
    local host=$2
    local key_file="$key_name"
    local pub_file="${key_name}.pub"
    
    echo -e "${BLUE}Generating SSH key pair for: $host${NC}"
    ssh-keygen -t ed25519 -f "$key_file" -N "" -C "GitHub Actions for r630-iscsi-switchbot"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to generate SSH key pair${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Do you want to add this key to $host? (requires password)${NC}"
    read -p "Enter y/n: " add_key_answer
    
    if [[ "$add_key_answer" == "y" || "$add_key_answer" == "Y" ]]; then
        ssh-copy-id -i "$pub_file" "root@$host"
    else
        echo -e "${YELLOW}! Key not added to remote host${NC}"
        echo -e "${YELLOW}  You'll need to manually add the following public key to the host:${NC}"
        cat "$pub_file"
    fi
    
    # Set the SSH key secret
    gh secret set "TRUENAS_SSH_KEY" -R "$REPO_NAME" < "$key_file"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Secret 'TRUENAS_SSH_KEY' set successfully${NC}"
    else
        echo -e "${RED}✗ Failed to set secret 'TRUENAS_SSH_KEY'${NC}"
    fi
    
    # Generate and set known hosts
    echo -e "${BLUE}Generating known hosts entry for: $host${NC}"
    ssh-keyscan -H "$host" > known_hosts
    
    if [ $? -eq 0 ]; then
        gh secret set "TRUENAS_KNOWN_HOSTS" -R "$REPO_NAME" < known_hosts
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Secret 'TRUENAS_KNOWN_HOSTS' set successfully${NC}"
        else
            echo -e "${RED}✗ Failed to set secret 'TRUENAS_KNOWN_HOSTS'${NC}"
        fi
    else
        echo -e "${RED}✗ Failed to generate known hosts entry${NC}"
    fi
    
    # Cleanup
    echo -e "${BLUE}Cleaning up temporary files...${NC}"
    read -p "Do you want to keep the SSH key files ($key_file and $pub_file)? (y/n): " keep_keys
    
    if [[ "$keep_keys" != "y" && "$keep_keys" != "Y" ]]; then
        rm -f "$key_file" "$pub_file" "known_hosts"
        echo -e "${GREEN}✓ Temporary files removed${NC}"
    else
        echo -e "${GREEN}✓ SSH key files kept for reference${NC}"
    fi
}

# Main menu
echo -e "\n${BLUE}This script will help you set up the required GitHub secrets for the R630 iSCSI SwitchBot project.${NC}"
echo -e "${BLUE}The following secrets are needed:${NC}"
echo -e "  ${YELLOW}1. OPENSHIFT_PULL_SECRET${NC} - Red Hat OpenShift pull secret"
echo -e "  ${YELLOW}2. TRUENAS_SSH_KEY${NC} - SSH private key for TrueNAS access"
echo -e "  ${YELLOW}3. TRUENAS_KNOWN_HOSTS${NC} - SSH known hosts entry for TrueNAS"

echo -e "\n${BLUE}Checking for existing secrets...${NC}"
check_secret "OPENSHIFT_PULL_SECRET"
check_secret "TRUENAS_SSH_KEY"
check_secret "TRUENAS_KNOWN_HOSTS"

echo -e "\n${BLUE}What would you like to do?${NC}"
echo -e "  ${YELLOW}1. Set up OPENSHIFT_PULL_SECRET${NC}"
echo -e "  ${YELLOW}2. Generate SSH keys and set up TRUENAS secrets${NC}"
echo -e "  ${YELLOW}3. Set up individual secrets manually${NC}"
echo -e "  ${YELLOW}4. Exit${NC}"

read -p "Enter your choice (1-4): " menu_choice

case "$menu_choice" in
    1)
        echo -e "\n${BLUE}Setting up OPENSHIFT_PULL_SECRET...${NC}"
        echo -e "${YELLOW}Visit https://console.redhat.com/openshift/install/pull-secret to get your pull secret${NC}"
        set_secret_from_input "OPENSHIFT_PULL_SECRET" "Please paste your OpenShift pull secret (JSON format) in the editor that will open:"
        ;;
    2)
        echo -e "\n${BLUE}Setting up TRUENAS secrets...${NC}"
        read -p "Enter TrueNAS IP address [192.168.2.245]: " truenas_ip
        truenas_ip=${truenas_ip:-192.168.2.245}
        
        generate_ssh_key_and_secrets "truenas_key" "$truenas_ip"
        ;;
    3)
        echo -e "\n${BLUE}Manual secret setup...${NC}"
        echo -e "${YELLOW}Which secret would you like to set up?${NC}"
        echo -e "  ${YELLOW}1. OPENSHIFT_PULL_SECRET${NC}"
        echo -e "  ${YELLOW}2. TRUENAS_SSH_KEY${NC}"
        echo -e "  ${YELLOW}3. TRUENAS_KNOWN_HOSTS${NC}"
        echo -e "  ${YELLOW}4. Back to main menu${NC}"
        
        read -p "Enter your choice (1-4): " secret_choice
        
        case "$secret_choice" in
            1)
                set_secret_from_input "OPENSHIFT_PULL_SECRET" "Please paste your OpenShift pull secret (JSON format) in the editor that will open:"
                ;;
            2)
                set_secret_from_input "TRUENAS_SSH_KEY" "Please paste your SSH private key in the editor that will open:"
                ;;
            3)
                set_secret_from_input "TRUENAS_KNOWN_HOSTS" "Please paste your SSH known hosts entry in the editor that will open:"
                ;;
            4)
                echo -e "${YELLOW}Returning to main menu...${NC}"
                ;;
            *)
                echo -e "${RED}Invalid choice${NC}"
                ;;
        esac
        ;;
    4)
        echo -e "${GREEN}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        ;;
esac

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${BLUE}== Setup Complete${NC}"
echo -e "${BLUE}======================================================================${NC}"

echo -e "\n${BLUE}Checking for secrets again...${NC}"
check_secret "OPENSHIFT_PULL_SECRET"
check_secret "TRUENAS_SSH_KEY"
check_secret "TRUENAS_KNOWN_HOSTS"

echo -e "\n${GREEN}To verify everything is set up correctly, run:${NC}"
echo -e "  ${YELLOW}./scripts/test_github_actions.sh${NC}"

echo -e "\n${GREEN}Once all secrets are configured, you can test the workflows:${NC}"
echo -e "  ${YELLOW}gh workflow run generate_iso.yml -R \"$REPO_NAME\" -f version=\"4.18\" -f rendezvous_ip=\"192.168.2.230\" -f truenas_ip=\"192.168.2.245\"${NC}"
