# Public Repository Preparation Guide

This guide explains the process and tools for making this repository public. It covers scanning for sensitive information, organizing the repository structure, and creating a new public GitHub repository.

## Overview

Making a repository public requires careful preparation to ensure:

1. No sensitive information or secrets are exposed
2. The repository structure is well-organized and user-friendly
3. Documentation is complete and consistent
4. Branding and messaging are consistent
5. History is clean and doesn't contain sensitive information

## Preparation Toolkit

We've created a set of scripts to help with this process:

- `scripts/make_repo_public.sh` - Main script that guides you through the entire process
- `scripts/prepare_for_public.py` - Scans the repository for secrets and consistency issues
- `scripts/organize_repo_structure.py` - Organizes documentation by moving files to appropriate directories
- `scripts/create_public_repo.sh` - Creates a new public GitHub repository and transfers content

### Prerequisites

- Python 3.6+
- Bash shell
- GitHub CLI (`gh`) installed and authenticated (for creating a new public repository)

## Step-by-Step Process

### 1. Run the Main Script

The easiest way to start is by running the main script, which will guide you through the entire process:

```bash
./scripts/make_repo_public.sh
```

This script will present you with options to:
- Scan the repository for secrets and consistency
- Organize the repository structure
- Create a new public GitHub repository

### 2. Scanning for Secrets

The script `prepare_for_public.py` scans the repository for:

- Potential secrets or sensitive information in code
- Files in Git history that might contain sensitive data
- Logo and branding consistency
- Files in the root directory that could be better organized

```bash
# Run the scan manually if needed
python3 scripts/prepare_for_public.py
```

This tool is non-destructive and only analyzes, not modifies, your repository.

#### What It Detects

- Hardcoded credentials, API keys, tokens
- Files with sensitive patterns in the Git history
- Missing logo files or inconsistent branding
- Markdown files that should be in the docs directory

### 3. Organizing Repository Structure

The script `organize_repo_structure.py` helps organize your repository by:

- Moving documentation files from the root directory to the docs directory
- Updating references to moved files in other documents
- Updating MkDocs configuration if necessary
- Creating a record of changes for reference

```bash
# Organize the repository structure manually if needed
python3 scripts/organize_repo_structure.py
```

This script will:
1. Identify markdown files in the root directory that should be moved
2. Ask for confirmation before making changes
3. Move the files and update references
4. Create a `REPOSITORY_CHANGES.md` file documenting the changes

### 4. Creating a Public GitHub Repository

The script `create_public_repo.sh` creates a new public GitHub repository and transfers your content:

- Creates a new public repository on GitHub
- Copies files from your current repository (excluding sensitive files)
- Sets up GitHub Pages for documentation (if MkDocs is used)
- Adds standard files like LICENSE and CONTRIBUTING.md if they don't exist

```bash
# Create a new public repository manually if needed
./scripts/create_public_repo.sh
```

This approach uses a fresh repository without previous history, ensuring any accidentally committed sensitive information is not transferred.

## Manual Checks

While the scripts automate much of the process, some aspects should be manually checked:

1. **Documentation Review**:
   - Ensure all documentation is up-to-date
   - Check that installation and usage instructions are clear
   - Verify links are working properly

2. **License and Attribution**:
   - Ensure the repository has an appropriate license
   - Check for proper attribution of third-party software

3. **Branding Consistency**:
   - Confirm logo and project name are used consistently
   - Check that README reflects the project's current state

4. **Final Security Review**:
   - Review GitHub Actions workflows for potential secrets
   - Ensure example files don't contain real credentials
   - Verify .gitignore is correctly excluding sensitive files

## What to Do If Sensitive Information Is Found

If the scanning tool finds sensitive information:

1. **In Current Files**:
   - Remove the sensitive information
   - Replace with placeholders or references to environment variables
   - Consider using the secrets provider system

2. **In Git History**:
   - The safest approach is creating a new repository without the history
   - Alternatively, use `git filter-repo` to remove sensitive files from history
   - Update remote references after cleaning history

## Ongoing Maintenance

Once the repository is public:

1. Set up branch protection rules for the main branch
2. Ensure GitHub Pages is configured correctly
3. Consider setting up automated security scanning
4. Review and update documentation regularly

## Conclusion

Making a repository public requires careful planning and preparation. These tools help automate much of the process, but final manual review is always recommended to ensure everything is properly prepared for public release.
