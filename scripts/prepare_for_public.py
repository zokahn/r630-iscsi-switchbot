#!/usr/bin/env python3
"""
Repository Preparation Script for Public Release

This script performs several checks to prepare a repository for public release:
1. Scans for potential secrets or sensitive information in code
2. Checks for consistency in branding/logo usage
3. Analyzes files in root directory to determine if they should be moved
4. Creates a report with findings and recommendations
"""

import os
import re
import sys
import subprocess
from pathlib import Path
import json

# ANSI color codes for output formatting
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Patterns that might indicate secrets or sensitive information
SECRET_PATTERNS = [
    r'password\s*=\s*["\'](?!YOUR_PASSWORD_HERE|null)[^"\']+["\']',
    r'passwd\s*=\s*["\'](?!YOUR_PASSWORD_HERE|null)[^"\']+["\']',
    r'pwd\s*=\s*["\'](?!YOUR_PASSWORD_HERE|null)[^"\']+["\']',
    r'secret\s*=\s*["\'](?!YOUR_SECRET_HERE|null)[^"\']+["\']',
    r'api.?key\s*=\s*["\'](?!YOUR_API_KEY_HERE|null)[^"\']+["\']',
    r'token\s*=\s*["\'](?!YOUR_TOKEN_HERE|null)[^"\']+["\']',
    r'auth\s*=\s*["\'](?!YOUR_AUTH_HERE|null)[^"\']+["\']',
    r'pass:\s*["\'](?!YOUR_PASSWORD_HERE|null)[^"\']+["\']',
    r'username\s*=\s*["\'](?!YOUR_USERNAME_HERE|root|null)[^"\']+["\']',
]

# Files/directories to exclude from scanning
EXCLUDE_PATHS = [
    '.git',
    '.github',
    'site',
    '.vscode',
    '__pycache__',
    '*.pyc',
    'node_modules',
    'temp',
    'tmp',
    'docs/examples',
]

# Logo/branding files
LOGO_FILES = [
    'docs_mkdocs/docs/assets/images/r630-iscsi-switchrobot-logo.png',
]

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_section(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'-' * len(text)}{Colors.ENDC}")

def is_excluded(path):
    for exclude in EXCLUDE_PATHS:
        if exclude.endswith('*'):
            if path.startswith(exclude[:-1]):
                return True
        elif exclude in path:
            return True
    return False

def check_for_secrets(root_dir='.'):
    """Scan files for potential secrets or sensitive information"""
    print_section("Scanning for potential secrets or sensitive information")
    
    findings = []
    file_count = 0
    for root, dirs, files in os.walk(root_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d))]
        
        for file in files:
            file_path = os.path.join(root, file)
            if is_excluded(file_path):
                continue
                
            # Skip binary files and focus on text files most likely to contain secrets
            if os.path.splitext(file)[1].lower() in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.bin', '.pyc', '.so', '.dll', '.exe']:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    file_count += 1
                    
                    # Check for potential secrets
                    for pattern in SECRET_PATTERNS:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            context_start = max(0, match.start() - 50)
                            context_end = min(len(content), match.end() + 50)
                            context = content[context_start:context_end].replace('\n', ' ')
                            
                            # Avoid reporting false positives like template strings or examples
                            if any(x in context.lower() for x in ['example', 'template', 'placeholder', 'demo']):
                                continue
                                
                            findings.append({
                                'file': file_path,
                                'pattern': pattern,
                                'context': context,
                                'line_number': content[:match.start()].count('\n') + 1
                            })
            except Exception as e:
                print(f"{Colors.YELLOW}Warning: Could not scan {file_path}: {str(e)}{Colors.ENDC}")
    
    # Report findings
    if findings:
        print(f"{Colors.RED}Found {len(findings)} potential secrets in {file_count} files:{Colors.ENDC}")
        for i, finding in enumerate(findings, 1):
            print(f"\n{Colors.RED}{i}. File: {finding['file']} (Line {finding['line_number']}){Colors.ENDC}")
            print(f"   {Colors.YELLOW}Context: ...{finding['context']}...{Colors.ENDC}")
    else:
        print(f"{Colors.GREEN}No potential secrets found in {file_count} files.{Colors.ENDC}")
    
    return findings

def check_git_history_for_secrets():
    """Check git history for potential secrets that might have been committed"""
    print_section("Checking git history for sensitive information")
    
    try:
        # Get a list of all committed files in history
        all_files = subprocess.check_output(
            ['git', 'log', '--pretty=format:', '--name-only', '--diff-filter=A'], 
            stderr=subprocess.STDOUT, 
            text=True
        ).splitlines()
        
        # Remove duplicates
        all_files = list(set(filter(None, all_files)))
        
        # Check if sensitive files were committed but later removed
        sensitive_patterns = [
            '*.key', '*.pem', '*.crt', '*.p12', '*.pfx', '*.cer',
            '*password*', '*secret*', '*credential*', '*api_key*', '*apikey*',
            '.env', 'pull-secret.txt', '.truenas_auth', '.truenas_config'
        ]
        
        potential_issues = []
        
        for pattern in sensitive_patterns:
            pattern = pattern.replace('.', '\\.').replace('*', '.*')
            regex = re.compile(pattern)
            
            for file in all_files:
                if regex.search(file):
                    # Check if the file is still in the repository
                    still_exists = os.path.exists(file)
                    potential_issues.append({
                        'file': file,
                        'pattern': pattern,
                        'still_exists': still_exists
                    })
        
        # Report findings
        if potential_issues:
            print(f"{Colors.YELLOW}Found {len(potential_issues)} files in git history that match sensitive patterns:{Colors.ENDC}")
            for i, issue in enumerate(potential_issues, 1):
                status = "still exists" if issue['still_exists'] else "has been removed"
                print(f"{i}. {issue['file']} - {status}")
            
            print(f"\n{Colors.YELLOW}Recommendation: Consider using git-filter-repo to remove sensitive files from history{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.GREEN}No obvious sensitive files found in git history.{Colors.ENDC}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}Error checking git history: {e.output}{Colors.ENDC}")
        return False

def check_logo_consistency():
    """Check for consistency in logo usage across documentation"""
    print_section("Checking for logo consistency")
    
    # Check if logo files exist
    missing_logos = []
    for logo_file in LOGO_FILES:
        if not os.path.exists(logo_file):
            missing_logos.append(logo_file)
    
    if missing_logos:
        print(f"{Colors.RED}Missing logo files:{Colors.ENDC}")
        for logo in missing_logos:
            print(f"- {logo}")
    else:
        print(f"{Colors.GREEN}All expected logo files exist.{Colors.ENDC}")
    
    # Check references to the logo in documentation
    try:
        # Looking for references to the logo in markdown files
        grep_output = subprocess.check_output(
            ['grep', '-r', 'r630-iscsi-switchrobot-logo', '--include="*.md"', '.'],
            stderr=subprocess.STDOUT,
            text=True
        )
        
        print(f"{Colors.GREEN}Logo is referenced in documentation:{Colors.ENDC}")
        for line in grep_output.splitlines():
            print(f"- {line}")
    except subprocess.CalledProcessError:
        print(f"{Colors.YELLOW}No references to the logo found in documentation.{Colors.ENDC}")
    
    # Check logo reference in mkdocs.yml
    try:
        with open('mkdocs.yml', 'r') as f:
            content = f.read()
            if 'r630-iscsi-switchrobot-logo' in content:
                print(f"{Colors.GREEN}Logo is referenced in mkdocs.yml{Colors.ENDC}")
            else:
                print(f"{Colors.YELLOW}Logo is not referenced in mkdocs.yml{Colors.ENDC}")
    except FileNotFoundError:
        print(f"{Colors.YELLOW}mkdocs.yml not found{Colors.ENDC}")

def analyze_root_files():
    """Analyze files in the root directory to determine if they should be moved"""
    print_section("Analyzing files in root directory")
    
    root_files = [f for f in os.listdir('.') if os.path.isfile(f)]
    markdown_files = [f for f in root_files if f.endswith('.md')]
    
    print(f"Found {len(root_files)} files in root directory, including {len(markdown_files)} markdown files.")
    
    if markdown_files:
        print(f"\n{Colors.YELLOW}Consider moving these markdown files to the docs directory:{Colors.ENDC}")
        for md_file in markdown_files:
            # Skip README.md which is common in root
            if md_file.lower() == 'readme.md':
                continue
            print(f"- {md_file}")
    
    # Identify other files that might be moved or cleaned up
    other_files = [f for f in root_files if not f.endswith('.md') and 
                  f not in ['.gitignore', 'LICENSE', 'setup.py', 'requirements.txt', 'pyproject.toml']]
    
    if other_files:
        print(f"\n{Colors.YELLOW}Other files in root directory to consider organizing:{Colors.ENDC}")
        for file in other_files:
            print(f"- {file}")

def create_new_public_repo_steps():
    """Generate steps for creating a new public repository"""
    print_section("Steps for creating a new public repository")
    
    print(f"{Colors.GREEN}To create a new public repository:{Colors.ENDC}")
    print("\n1. Sanitize the repository")
    print("   - Address all issues found by this script")
    print("   - Remove any sensitive information")
    
    print("\n2. Create a new public repository on GitHub")
    print("   - Use the GitHub web interface or the GitHub CLI:")
    print("     gh repo create owner/two-r630-iscsi --public")
    
    print("\n3. Push the sanitized code to the new repository")
    print("   - Option 1: Clone the new repository and copy files manually")
    print("     git clone https://github.com/owner/two-r630-iscsi.git")
    print("     cp -R ./[files] ./two-r630-iscsi/")
    print("     cd two-r630-iscsi")
    print("     git add .")
    print("     git commit -m \"Initial public release\"")
    print("     git push")
    
    print("\n   - Option 2: If history isn't a concern, reinitialize the repo")
    print("     cd ./two-r630-iscsi")
    print("     rm -rf .git")
    print("     git init")
    print("     git add .")
    print("     git commit -m \"Initial public release\"")
    print("     git branch -M main")
    print("     git remote add origin https://github.com/owner/two-r630-iscsi.git")
    print("     git push -u origin main")
    
    print("\n4. Set up GitHub Pages for documentation")
    print("   - Enable GitHub Pages in the repository settings")
    print("   - Configure to deploy from a GitHub Action")
    
    print("\n5. Set up branch protection for the main branch")
    print("   - Go to repository settings")
    print("   - Branches → Add rule")
    print("   - Enter 'main' as the branch name pattern")
    print("   - Enable 'Require pull request reviews before merging'")
    print("   - Enable 'Require status checks to pass before merging'")

def main():
    print_header("Repository Public Release Preparation")
    
    # Run the checks
    secret_findings = check_for_secrets()
    history_has_secrets = check_git_history_for_secrets()
    check_logo_consistency()
    analyze_root_files()
    create_new_public_repo_steps()
    
    # Final recommendations
    print_section("Final Recommendations")
    
    if secret_findings or history_has_secrets:
        print(f"{Colors.RED}⚠️ ATTENTION NEEDED: Sensitive information found!{Colors.ENDC}")
        print(f"{Colors.RED}Address all issues above before making the repository public.{Colors.ENDC}")
        
        if history_has_secrets:
            print(f"\n{Colors.YELLOW}To remove sensitive information from git history, consider:{Colors.ENDC}")
            print("1. Create a fresh repository (safest option)")
            print("2. Use git-filter-repo to remove sensitive files from history:")
            print("   pip install git-filter-repo")
            print("   git filter-repo --path path/to/sensitive/file --invert-paths")
    else:
        print(f"{Colors.GREEN}✅ No critical issues found!{Colors.ENDC}")
        print(f"{Colors.GREEN}The repository seems ready to be made public after addressing documentation organization.{Colors.ENDC}")
    
    print(f"\n{Colors.BLUE}{Colors.BOLD}Next steps:{Colors.ENDC}")
    print("1. Review the full report and address any issues")
    print("2. Run any necessary cleanup scripts")
    print("3. Follow the steps to create a new public repository")
    print("4. Set up GitHub Pages and branch protection")

if __name__ == "__main__":
    main()
