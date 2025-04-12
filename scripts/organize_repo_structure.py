#!/usr/bin/env python3
"""
Repository Structure Organizer

This script helps organize the repository structure by:
1. Moving documentation files from root to docs directory
2. Updating references to these files in other documents
3. Creating a record of changes for reference
"""

import os
import sys
import re
import shutil
from pathlib import Path

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

# Files to exclude from moving (common root files)
EXCLUDE_FROM_MOVING = [
    'README.md',
    'LICENSE',
    'CONTRIBUTING.md',
    'CODE_OF_CONDUCT.md',
    'SECURITY.md',
    'CHANGELOG.md',
    '.gitignore',
    'mkdocs.yml',
]

# Files to always move to docs (unless excluded above)
ROOT_MD_FILES_TO_MOVE = [
    'MULTIBOOT_IMPLEMENTATION.md',
    'NETBOOT_IMPLEMENTATION.md',
    'IMPLEMENTATION_SUMMARY.md',
    'TEST_PLAN.md',
    'TEST_RESULTS.md',
    'ENHANCEMENT_PLAN.md',
    'FINAL_REPORT.md',
    'PROJECT_COMPLETION.md',
]

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_section(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'-' * len(text)}{Colors.ENDC}")

def find_markdown_links(content):
    """Find markdown links in content and return a list of targets"""
    # Match [text](link.md) pattern
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    links = link_pattern.findall(content)
    return [link for _, link in links if link.endswith('.md')]

def update_markdown_links(content, old_path, new_path):
    """Update markdown links in content to reflect new file locations"""
    if old_path == new_path:
        return content
    
    old_filename = os.path.basename(old_path)
    new_filename = os.path.basename(new_path)
    
    # Match [text](old_filename) pattern and replace with [text](docs/new_filename)
    link_pattern = re.compile(r'\[([^\]]+)\]\((' + re.escape(old_filename) + r')\)')
    new_content = link_pattern.sub(r'[\1](docs/' + new_filename + r')', content)
    
    return new_content

def find_files_to_move():
    """Find markdown files in the root directory that should be moved to docs"""
    root_files = [f for f in os.listdir('.') if os.path.isfile(f)]
    markdown_files = [f for f in root_files if f.endswith('.md') and f not in EXCLUDE_FROM_MOVING]
    
    # Prioritize explicitly listed files
    files_to_move = []
    for file in ROOT_MD_FILES_TO_MOVE:
        if file in markdown_files:
            files_to_move.append(file)
            markdown_files.remove(file)
    
    # Add remaining markdown files
    files_to_move.extend(markdown_files)
    
    return files_to_move

def update_references(files_moved):
    """Update references to moved files in other markdown files"""
    print_section("Updating references to moved files")
    
    # Files to check for references (include both root and docs directory)
    files_to_check = []
    
    # Add root markdown files
    root_md_files = [f for f in os.listdir('.') if f.endswith('.md') and os.path.isfile(f)]
    files_to_check.extend(root_md_files)
    
    # Add docs markdown files
    if os.path.exists('docs'):
        docs_md_files = [os.path.join('docs', f) for f in os.listdir('docs') 
                         if f.endswith('.md') and os.path.isfile(os.path.join('docs', f))]
        files_to_check.extend(docs_md_files)
    
    # Add docs_mkdocs markdown files
    if os.path.exists('docs_mkdocs'):
        for root, _, files in os.walk('docs_mkdocs'):
            docs_mkdocs_md_files = [os.path.join(root, f) for f in files if f.endswith('.md')]
            files_to_check.extend(docs_mkdocs_md_files)
    
    changes_made = []
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            updated_content = content
            changes_in_file = False
            
            for old_path, new_path in files_moved:
                if old_path == file_path:
                    continue  # Skip the file itself
                updated_content = update_markdown_links(updated_content, old_path, new_path)
                if updated_content != content:
                    changes_in_file = True
                    changes_made.append(f"Updated references in {file_path} to {os.path.basename(new_path)}")
            
            if changes_in_file:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                print(f"{Colors.GREEN}Updated references in {file_path}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error updating references in {file_path}: {str(e)}{Colors.ENDC}")
    
    if not changes_made:
        print(f"{Colors.YELLOW}No references needed to be updated.{Colors.ENDC}")
    else:
        print(f"\n{Colors.GREEN}Updated {len(changes_made)} references:{Colors.ENDC}")
        for change in changes_made:
            print(f"- {change}")
    
    return changes_made

def update_mkdocs_config(files_moved):
    """Update mkdocs.yml configuration to reflect new file locations"""
    print_section("Updating MkDocs configuration")
    
    if not os.path.exists('mkdocs.yml'):
        print(f"{Colors.YELLOW}mkdocs.yml not found, skipping MkDocs configuration update.{Colors.ENDC}")
        return False
    
    try:
        with open('mkdocs.yml', 'r', encoding='utf-8') as f:
            mkdocs_content = f.read()
        
        updated_content = mkdocs_content
        changes_made = False
        
        for old_path, new_path in files_moved:
            old_filename = os.path.basename(old_path)
            new_rel_path = new_path.replace('./', '')  # Remove leading ./ if present
            
            # Look for references like: "- Implementation: MULTIBOOT_IMPLEMENTATION.md"
            # And replace with: "- Implementation: docs/MULTIBOOT_IMPLEMENTATION.md"
            pattern = r'(\s+- [^:]+:\s+)' + re.escape(old_filename)
            replacement = r'\1docs/' + old_filename
            new_content = re.sub(pattern, replacement, updated_content)
            
            if new_content != updated_content:
                updated_content = new_content
                changes_made = True
                print(f"{Colors.GREEN}Updated MkDocs reference to {old_filename}{Colors.ENDC}")
        
        if changes_made:
            with open('mkdocs.yml', 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"{Colors.GREEN}MkDocs configuration updated.{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.YELLOW}No changes needed in MkDocs configuration.{Colors.ENDC}")
            return False
    
    except Exception as e:
        print(f"{Colors.RED}Error updating MkDocs configuration: {str(e)}{Colors.ENDC}")
        return False

def create_change_record(files_moved, reference_changes, mkdocs_updated):
    """Create a record of changes made for reference"""
    print_section("Creating change record")
    
    if not files_moved and not reference_changes and not mkdocs_updated:
        print(f"{Colors.YELLOW}No changes were made, skipping change record.{Colors.ENDC}")
        return
    
    try:
        with open('REPOSITORY_CHANGES.md', 'w', encoding='utf-8') as f:
            f.write("# Repository Structure Changes\n\n")
            f.write("This document records the changes made to the repository structure ")
            f.write("when preparing for public release.\n\n")
            
            if files_moved:
                f.write("## Files Moved\n\n")
                for old_path, new_path in files_moved:
                    f.write(f"- `{old_path}` → `{new_path}`\n")
                f.write("\n")
            
            if reference_changes:
                f.write("## References Updated\n\n")
                for change in reference_changes:
                    f.write(f"- {change}\n")
                f.write("\n")
            
            if mkdocs_updated:
                f.write("## MkDocs Configuration Updated\n\n")
                f.write("- Updated file paths in `mkdocs.yml` to reflect new file locations\n\n")
            
            f.write("## How to Use This Information\n\n")
            f.write("If you need to find a file that has been moved, consult the 'Files Moved' section above.\n")
            f.write("All internal documentation links have been updated to point to the new locations.\n")
        
        print(f"{Colors.GREEN}Change record created: REPOSITORY_CHANGES.md{Colors.ENDC}")
    
    except Exception as e:
        print(f"{Colors.RED}Error creating change record: {str(e)}{Colors.ENDC}")

def main():
    print_header("Repository Structure Organization")
    
    # Check if docs directory exists, create if not
    if not os.path.exists('docs'):
        os.makedirs('docs')
        print(f"{Colors.GREEN}Created docs directory{Colors.ENDC}")
    
    # Find markdown files to move
    files_to_move = find_files_to_move()
    
    if not files_to_move:
        print(f"{Colors.GREEN}No files need to be moved from root to docs.{Colors.ENDC}")
        return
    
    print_section(f"Found {len(files_to_move)} files to move to docs directory")
    for file in files_to_move:
        print(f"- {file}")
    
    # Confirm with user
    print(f"\n{Colors.YELLOW}Do you want to proceed with moving these files? (y/n){Colors.ENDC}")
    choice = input("> ").strip().lower()
    
    if choice != 'y':
        print(f"{Colors.YELLOW}Operation cancelled.{Colors.ENDC}")
        return
    
    # Move files and record source and destination
    files_moved = []
    print_section("Moving files")
    
    for file in files_to_move:
        source = file
        destination = os.path.join('docs', file)
        
        try:
            shutil.move(source, destination)
            print(f"{Colors.GREEN}Moved {source} → {destination}{Colors.ENDC}")
            files_moved.append((source, destination))
        except Exception as e:
            print(f"{Colors.RED}Error moving {source}: {str(e)}{Colors.ENDC}")
    
    # Update references in other files
    reference_changes = update_references(files_moved)
    
    # Update MkDocs configuration
    mkdocs_updated = update_mkdocs_config(files_moved)
    
    # Create a record of changes
    create_change_record(files_moved, reference_changes, mkdocs_updated)
    
    print_section("Summary")
    print(f"{Colors.GREEN}Moved {len(files_moved)} files to docs directory{Colors.ENDC}")
    if reference_changes:
        print(f"{Colors.GREEN}Updated {len(reference_changes)} references in documentation{Colors.ENDC}")
    if mkdocs_updated:
        print(f"{Colors.GREEN}Updated MkDocs configuration{Colors.ENDC}")
    
    print(f"\n{Colors.YELLOW}Next steps:{Colors.ENDC}")
    print("1. Review the changes in REPOSITORY_CHANGES.md")
    print("2. Test that documentation links still work correctly")
    print("3. Run 'mkdocs build' to verify the documentation builds correctly")
    print("4. Commit the changes with a message describing the repository organization")

if __name__ == "__main__":
    main()
