#!/bin/bash
# make_repo_public.sh - Master script to prepare repository for public release
# This script orchestrates the entire process of making a repository public

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Print header
print_header() {
    echo -e "\n${PURPLE}=================================================${NC}"
    echo -e "${PURPLE}   $1${NC}"
    echo -e "${PURPLE}=================================================${NC}\n"
}

# Print section header
print_section() {
    echo -e "\n${BLUE}---- $1 ----${NC}\n"
}

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Print welcome message
clear
print_header "REPOSITORY PUBLIC RELEASE TOOLKIT"

echo -e "This script will guide you through the process of preparing your repository"
echo -e "for public release. The process consists of multiple steps that will help you:"
echo -e ""
echo -e "  1. ${YELLOW}Scan for secrets and sensitive information${NC}"
echo -e "  2. ${YELLOW}Check for consistency in branding and documentation${NC}"
echo -e "  3. ${YELLOW}Organize the repository structure${NC}"
echo -e "  4. ${YELLOW}Create a new public GitHub repository${NC}"
echo -e ""
echo -e "You can choose which steps to perform and in what order."
echo -e "Let's get started!"

# Confirm with user
echo -e "\n${BLUE}Press Enter to continue or Ctrl+C to exit...${NC}"
read -r

# STEP 1: Scan the repository
print_header "STEP 1: REPOSITORY SCAN"

echo -e "This step will scan your repository for:"
echo -e "  - Potential secrets or sensitive information"
echo -e "  - Files in Git history that might contain sensitive data"
echo -e "  - Logo and branding consistency"
echo -e "  - Files in the root directory that could be better organized"
echo -e ""
echo -e "${YELLOW}This is a non-destructive operation and will only analyze, not modify, your repository.${NC}"
echo -e ""

read -p "Do you want to run the repository scan? (y/n): " RUN_SCAN
if [[ $RUN_SCAN == "y" ]]; then
    print_section "Running Repository Scan"
    python3 "$SCRIPT_DIR/prepare_for_public.py"
    
    # Capture the exit code
    SCAN_EXIT_CODE=$?
    
    if [ $SCAN_EXIT_CODE -ne 0 ]; then
        echo -e "\n${RED}Repository scan encountered issues.${NC}"
        echo -e "${YELLOW}You should address these issues before proceeding.${NC}"
        read -p "Do you want to continue with the next steps anyway? (y/n): " CONTINUE
        if [[ $CONTINUE != "y" ]]; then
            echo -e "${YELLOW}Exiting. Run this script again after addressing the issues.${NC}"
            exit 1
        fi
    else
        echo -e "\n${GREEN}Repository scan completed successfully.${NC}"
    fi
else
    echo -e "${YELLOW}Skipping repository scan.${NC}"
fi

# STEP 2: Organize repository structure
print_header "STEP 2: ORGANIZE REPOSITORY STRUCTURE"

echo -e "This step will help you organize your repository structure by:"
echo -e "  - Moving documentation files from the root directory to the docs directory"
echo -e "  - Updating references to moved files in other documents"
echo -e "  - Updating the MkDocs configuration if necessary"
echo -e "  - Creating a record of changes for reference"
echo -e ""
echo -e "${YELLOW}This operation will modify your repository. It's recommended to commit any"
echo -e "pending changes before proceeding, or work on a separate branch.${NC}"
echo -e ""

read -p "Do you want to organize the repository structure? (y/n): " RUN_ORGANIZE
if [[ $RUN_ORGANIZE == "y" ]]; then
    print_section "Organizing Repository Structure"
    python3 "$SCRIPT_DIR/organize_repo_structure.py"
    
    # Capture the exit code
    ORGANIZE_EXIT_CODE=$?
    
    if [ $ORGANIZE_EXIT_CODE -ne 0 ]; then
        echo -e "\n${RED}Repository organization encountered issues.${NC}"
        echo -e "${YELLOW}You may need to manually organize some files.${NC}"
    else
        echo -e "\n${GREEN}Repository organization completed successfully.${NC}"
    fi
else
    echo -e "${YELLOW}Skipping repository organization.${NC}"
fi

# STEP 3: Create a new public repository
print_header "STEP 3: CREATE PUBLIC REPOSITORY"

echo -e "This step will create a new public GitHub repository and transfer your content:"
echo -e "  - Create a new public repository on GitHub"
echo -e "  - Copy files from your current repository (excluding sensitive files)"
echo -e "  - Set up GitHub Pages for documentation (if MkDocs is used)"
echo -e "  - Add standard files like LICENSE and CONTRIBUTING.md if they don't exist"
echo -e ""
echo -e "${YELLOW}This operation requires the GitHub CLI (gh) to be installed and authenticated.${NC}"
echo -e ""

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}GitHub CLI (gh) is not installed. You need to install it first:${NC}"
    echo -e "${BLUE}https://cli.github.com/manual/installation${NC}"
    echo -e ""
    echo -e "${YELLOW}After installing, authenticate with: gh auth login${NC}"
    echo -e "${YELLOW}Then run this script again.${NC}"
    
    read -p "Do you want to continue without creating a public repository? (y/n): " CONTINUE_WITHOUT_GH
    if [[ $CONTINUE_WITHOUT_GH != "y" ]]; then
        echo -e "${YELLOW}Exiting. Install GitHub CLI and run this script again.${NC}"
        exit 1
    fi
    CREATE_REPO="n"
else
    # Check if authenticated with GitHub
    if ! gh auth status &> /dev/null; then
        echo -e "${RED}Not authenticated with GitHub. Please run:${NC}"
        echo -e "${YELLOW}gh auth login${NC}"
        echo -e "${YELLOW}Then run this script again.${NC}"
        
        read -p "Do you want to continue without creating a public repository? (y/n): " CONTINUE_WITHOUT_AUTH
        if [[ $CONTINUE_WITHOUT_AUTH != "y" ]]; then
            echo -e "${YELLOW}Exiting. Authenticate with GitHub and run this script again.${NC}"
            exit 1
        fi
        CREATE_REPO="n"
    else
        read -p "Do you want to create a new public repository? (y/n): " CREATE_REPO
    fi
fi

if [[ $CREATE_REPO == "y" ]]; then
    print_section "Creating Public Repository"
    "$SCRIPT_DIR/create_public_repo.sh"
    
    # Capture the exit code
    REPO_EXIT_CODE=$?
    
    if [ $REPO_EXIT_CODE -ne 0 ]; then
        echo -e "\n${RED}Repository creation encountered issues.${NC}"
        echo -e "${YELLOW}You may need to create the repository manually.${NC}"
    else
        echo -e "\n${GREEN}Public repository created successfully.${NC}"
    fi
else
    echo -e "${YELLOW}Skipping public repository creation.${NC}"
fi

# COMPLETION
print_header "PROCESS COMPLETE"

echo -e "${GREEN}The repository public release preparation process is complete.${NC}"
echo -e ""
echo -e "Summary of actions taken:"
if [[ $RUN_SCAN == "y" ]]; then
    echo -e "  - ${GREEN}✓${NC} Repository scan for secrets and consistency"
else
    echo -e "  - ${YELLOW}✗${NC} Repository scan (skipped)"
fi

if [[ $RUN_ORGANIZE == "y" ]]; then
    echo -e "  - ${GREEN}✓${NC} Repository structure organization"
else
    echo -e "  - ${YELLOW}✗${NC} Repository structure organization (skipped)"
fi

if [[ $CREATE_REPO == "y" ]]; then
    echo -e "  - ${GREEN}✓${NC} Public repository creation"
else
    echo -e "  - ${YELLOW}✗${NC} Public repository creation (skipped)"
fi

echo -e ""
echo -e "Next steps you might want to take:"
echo -e "  1. Verify that all sensitive information has been removed"
echo -e "  2. Test that the documentation builds correctly with mkdocs"
echo -e "  3. Set up branch protection for the main branch"
echo -e "  4. Add collaborators to the new repository"
echo -e ""

echo -e "${BLUE}Thank you for using the Repository Public Release Toolkit!${NC}"
