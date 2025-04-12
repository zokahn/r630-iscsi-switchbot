#!/bin/bash
# create_public_repo.sh - Script to create a new public GitHub repository
# and transfer content from the current repository

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
print_header() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}GitHub CLI (gh) is not installed. Please install it first:${NC}"
    echo -e "${YELLOW}https://cli.github.com/manual/installation${NC}"
    exit 1
fi

# Check if authenticated with GitHub
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Not authenticated with GitHub. Please run:${NC}"
    echo -e "${YELLOW}gh auth login${NC}"
    exit 1
fi

# Repository information
print_header "Repository Information"
echo -e "${YELLOW}This script will create a new public GitHub repository and transfer content.${NC}"

# Get current repository information
CURRENT_REPO=$(git remote get-url origin 2>/dev/null | sed -n 's/.*github.com[:/]\(.*\).git/\1/p')
if [ -z "$CURRENT_REPO" ]; then
    CURRENT_REPO="unknown/unknown"
fi

# Get default repository name
DEFAULT_REPO_NAME="two-r630-iscsi"
DEFAULT_REPO_OWNER=$(echo "$CURRENT_REPO" | cut -d'/' -f1)

echo -e "${YELLOW}Please provide information for the new repository:${NC}"
read -p "Repository owner (GitHub username or organization) [$DEFAULT_REPO_OWNER]: " REPO_OWNER
REPO_OWNER=${REPO_OWNER:-$DEFAULT_REPO_OWNER}

read -p "Repository name [$DEFAULT_REPO_NAME]: " REPO_NAME
REPO_NAME=${REPO_NAME:-$DEFAULT_REPO_NAME}

read -p "Repository description [Dell PowerEdge R630 OpenShift Multiboot System]: " REPO_DESC
REPO_DESC=${REPO_DESC:-"Dell PowerEdge R630 OpenShift Multiboot System"}

# Check if the target repository already exists
if gh repo view "$REPO_OWNER/$REPO_NAME" &> /dev/null; then
    echo -e "${RED}Repository $REPO_OWNER/$REPO_NAME already exists.${NC}"
    read -p "Do you want to use this repository anyway? (y/n): " USE_EXISTING
    if [ "$USE_EXISTING" != "y" ]; then
        echo -e "${YELLOW}Operation cancelled.${NC}"
        exit 1
    fi
    NEW_REPO_CREATED=false
else
    # Create the repository
    print_header "Creating Repository"
    echo -e "${YELLOW}Creating new public repository: $REPO_OWNER/$REPO_NAME${NC}"
    
    if gh repo create "$REPO_OWNER/$REPO_NAME" --public --description "$REPO_DESC"; then
        echo -e "${GREEN}✓ Repository created successfully${NC}"
        NEW_REPO_CREATED=true
    else
        echo -e "${RED}Failed to create repository.${NC}"
        exit 1
    fi
fi

# Create a temporary directory for the new repository
TEMP_DIR=$(mktemp -d)
echo -e "\n${YELLOW}Using temporary directory: $TEMP_DIR${NC}"

# Clone the new repository
print_header "Cloning Repository"
echo -e "${YELLOW}Cloning the new repository...${NC}"
if ! git clone "https://github.com/$REPO_OWNER/$REPO_NAME.git" "$TEMP_DIR"; then
    echo -e "${RED}Failed to clone repository.${NC}"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Prepare the list of files to copy (excluding sensitive files and git-related files)
print_header "Copying Files"
echo -e "${YELLOW}Copying files from current repository to the new repository...${NC}"

# Get current repository files
cd "$(git rev-parse --show-toplevel)" || exit 1
CURRENT_DIR=$(pwd)

# Create a list of files to copy, excluding patterns from .gitignore
# and other sensitive files/directories
EXCLUDE_PATTERNS=(
    ".git"
    ".git*"
    "*.key"
    "*.pem"
    "*.crt"
    "*.p12"
    "*.pfx"
    "*.cer"
    "*password*"
    "*secret*"
    "*credential*"
    "*api_key*"
    "*apikey*"
    ".env"
    "pull-secret.txt"
    ".truenas_auth"
    ".truenas_config"
    "__pycache__"
    "*.pyc"
    "node_modules"
    "venv"
    ".venv"
    "temp"
    "tmp"
    ".DS_Store"
    "site/"
)

# Build rsync exclude pattern
RSYNC_EXCLUDE=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    RSYNC_EXCLUDE="$RSYNC_EXCLUDE --exclude='$pattern'"
done

# Copy files to new repository, preserving directory structure
# shellcheck disable=SC2086
eval "rsync -av $RSYNC_EXCLUDE --progress . $TEMP_DIR/"

# Generate a new LICENSE file if it doesn't exist
if [ ! -f "$TEMP_DIR/LICENSE" ]; then
    print_header "Creating LICENSE File"
    echo -e "${YELLOW}No LICENSE file found. Creating MIT License...${NC}"
    
    CURRENT_YEAR=$(date +%Y)
    
    cat > "$TEMP_DIR/LICENSE" << EOF
MIT License

Copyright (c) $CURRENT_YEAR $REPO_OWNER

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
    echo -e "${GREEN}✓ LICENSE file created${NC}"
fi

# Ensure CONTRIBUTING.md exists
if [ ! -f "$TEMP_DIR/CONTRIBUTING.md" ]; then
    print_header "Creating CONTRIBUTING.md"
    echo -e "${YELLOW}No CONTRIBUTING.md found. Creating a basic one...${NC}"
    
    cat > "$TEMP_DIR/CONTRIBUTING.md" << EOF
# Contributing to $REPO_NAME

Thank you for your interest in contributing to this project! We welcome contributions from everyone.

## How to Contribute

1. **Fork the Repository**: Start by forking this repository to your GitHub account.

2. **Clone Your Fork**: Clone your fork to your local machine.
   \`\`\`
   git clone https://github.com/YOUR_USERNAME/$REPO_NAME.git
   cd $REPO_NAME
   \`\`\`

3. **Create a Branch**: Create a branch for your changes.
   \`\`\`
   git checkout -b feature/your-feature-name
   \`\`\`

4. **Make Your Changes**: Implement your changes, following the project's coding standards.

5. **Test Your Changes**: Ensure your changes don't break existing functionality.

6. **Commit Your Changes**: Commit your changes with a clear message.
   \`\`\`
   git commit -m "Add feature: description of your changes"
   \`\`\`

7. **Push to GitHub**: Push your changes to your fork.
   \`\`\`
   git push origin feature/your-feature-name
   \`\`\`

8. **Create a Pull Request**: Submit a pull request from your fork to this repository.

## Pull Request Guidelines

- Give your PR a clear title and description.
- Include any relevant issue numbers in the PR description.
- Ensure your code follows the project's coding standards.
- Be ready to address review feedback.

## Code Standards

- Follow existing code style and formatting.
- Write clear, maintainable code.
- Add appropriate tests and documentation for new features.

## Need Help?

If you have questions or need help, please open an issue with your question.

Thank you for contributing!
EOF
    echo -e "${GREEN}✓ CONTRIBUTING.md created${NC}"
fi

# Make sure README.md shows it's a public repository
if [ -f "$TEMP_DIR/README.md" ]; then
    print_header "Updating README.md"
    
    # Only add GitHub Pages badge if mkdocs.yml exists
    if [ -f "$TEMP_DIR/mkdocs.yml" ]; then
        echo -e "${YELLOW}Adding GitHub Pages badge to README.md...${NC}"
        
        # Add badges beneath the first heading if not already present
        if ! grep -q "gh-pages" "$TEMP_DIR/README.md"; then
            HEADING_LINE=$(grep -n "^#" "$TEMP_DIR/README.md" | head -1 | cut -d: -f1)
            
            if [ -n "$HEADING_LINE" ]; then
                # Insert after the heading line
                sed -i "$((HEADING_LINE+1))i\\
\\
[![GitHub Pages](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://$REPO_OWNER.github.io/$REPO_NAME/)
" "$TEMP_DIR/README.md"
            else
                # Insert at the beginning if no heading found
                sed -i "1i\\
# $REPO_NAME\\
\\
[![GitHub Pages](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://$REPO_OWNER.github.io/$REPO_NAME/)
" "$TEMP_DIR/README.md"
            fi
        fi
    fi
    
    echo -e "${GREEN}✓ README.md updated${NC}"
fi

# Create GitHub workflow for GitHub Pages if MkDocs is used
if [ -f "$TEMP_DIR/mkdocs.yml" ]; then
    print_header "Setting up GitHub Pages"
    echo -e "${YELLOW}Creating GitHub workflow for GitHub Pages with MkDocs...${NC}"
    
    mkdir -p "$TEMP_DIR/.github/workflows"
    
    cat > "$TEMP_DIR/.github/workflows/mkdocs.yml" << EOF
name: Deploy MkDocs to GitHub Pages

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install mkdocs mkdocs-material
          
      - name: Build documentation
        run: mkdocs build
        
      - name: Deploy to GitHub Pages
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: \${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
EOF
    echo -e "${GREEN}✓ GitHub Pages workflow created${NC}"
fi

# Commit and push changes to the new repository
print_header "Committing and Pushing Changes"
echo -e "${YELLOW}Committing files to the new repository...${NC}"

cd "$TEMP_DIR" || exit 1

git add .
git config user.name "Repository Setup Script"
git config user.email "noreply@example.com"
git commit -m "Initial public repository setup"

echo -e "\n${YELLOW}Pushing to GitHub...${NC}"
if git push origin main; then
    echo -e "${GREEN}✓ Changes pushed successfully${NC}"
else
    echo -e "${RED}Failed to push changes.${NC}"
    exit 1
fi

# Enable GitHub Pages if MkDocs is used
if [ -f "$TEMP_DIR/mkdocs.yml" ]; then
    print_header "Enabling GitHub Pages"
    echo -e "${YELLOW}Enabling GitHub Pages with GitHub Actions...${NC}"
    
    # Use gh CLI to enable GitHub Pages
    gh api \
      --method PUT \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "/repos/$REPO_OWNER/$REPO_NAME/pages" \
      -f "source.branch"="gh-pages" \
      -f "source.path"="/"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ GitHub Pages enabled${NC}"
    else
        echo -e "${YELLOW}Could not enable GitHub Pages via API. Please enable it manually in repository settings.${NC}"
    fi
fi

# Clean up
cd "$CURRENT_DIR" || exit 1
rm -rf "$TEMP_DIR"

# Success!
print_header "Repository Creation Complete"
echo -e "${GREEN}✓ New public repository is ready: https://github.com/$REPO_OWNER/$REPO_NAME${NC}"

if [ -f "$CURRENT_DIR/mkdocs.yml" ]; then
    echo -e "${YELLOW}GitHub Pages will be available at: https://$REPO_OWNER.github.io/$REPO_NAME/${NC}"
    echo -e "${YELLOW}(It may take a few minutes for the first GitHub Pages deployment to complete)${NC}"
fi

echo -e "\n${BLUE}Next steps:${NC}"
echo "1. Review the new repository and ensure all content looks good"
echo "2. Set up branch protection rules for the main branch"
echo "3. Add collaborators if needed"
echo "4. Update local git remote if you want to continue working with the new repository:"
echo "   git remote set-url origin https://github.com/$REPO_OWNER/$REPO_NAME.git"

echo -e "\n${GREEN}Repository is now ready for public access!${NC}"
