#!/usr/bin/env python3
"""
Export Release Script for FlaskBin

This script prepares a clean release version of the FlaskBin application 
by copying only the necessary files to a /release directory,
which can then be deployed to production.

Usage:
  python export_release.py [version]

  If version is provided, the release folder will be zipped with that version number.
  Otherwise, it will use the current date as the version.
"""

import os
import sys
import shutil
import fnmatch
import datetime
import zipfile
import subprocess

def get_git_commit_hash():
    """Get the current git commit hash, if available."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

def get_version():
    """Generate a version string based on date and optionally git commit."""
    date = datetime.datetime.now().strftime("%Y%m%d")
    commit = get_git_commit_hash()
    if commit:
        return f"{date}-{commit}"
    return date

def read_ignore_patterns(ignore_file):
    """Read the patterns to ignore from the given file."""
    if not os.path.exists(ignore_file):
        print(f"Warning: {ignore_file} does not exist. No patterns will be ignored.")
        return []
    
    with open(ignore_file, 'r') as f:
        lines = f.readlines()
    
    # Filter out comments and empty lines
    patterns = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
    return patterns

def should_ignore(path, ignore_patterns):
    """Check if the given path should be ignored based on the ignore patterns."""
    # Always ignore the release directory itself
    if path.startswith('./release/') or path == './release':
        return True
    
    # Remove ./ prefix for matching
    rel_path = path[2:] if path.startswith('./') else path
    
    for pattern in ignore_patterns:
        # Handle directory patterns
        if pattern.endswith('/'):
            if rel_path.startswith(pattern) or rel_path + '/' == pattern:
                return True
        # Handle file patterns with wildcards
        elif fnmatch.fnmatch(rel_path, pattern):
            return True
    
    return False

def copy_files(src_dir, dest_dir, ignore_patterns):
    """Copy files from src_dir to dest_dir, excluding those matching ignore_patterns."""
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    for root, dirs, files in os.walk(src_dir):
        # Convert root to a relative path for pattern matching
        rel_root = '.' + root[len(src_dir):]
        
        # Create corresponding directories in destination
        for d in dirs:
            src_path = os.path.join(root, d)
            rel_path = os.path.join(rel_root, d)
            
            if not should_ignore(rel_path, ignore_patterns):
                dest_path = os.path.join(dest_dir, os.path.relpath(src_path, src_dir))
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)
        
        # Copy files
        for f in files:
            src_path = os.path.join(root, f)
            rel_path = os.path.join(rel_root, f)
            
            if not should_ignore(rel_path, ignore_patterns):
                dest_path = os.path.join(dest_dir, os.path.relpath(src_path, src_dir))
                # Create parent directories if they don't exist
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src_path, dest_path)

def create_zip(src_dir, version):
    """Create a zip file of the release directory with the given version."""
    zip_name = f"release_{version}.zip"
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, src_dir))
    
    print(f"Created zip archive: {zip_name}")
    return zip_name

def rename_requirements_file(release_dir):
    """Rename release_requirements.txt to requirements.txt in the release directory."""
    src = os.path.join(release_dir, 'release_requirements.txt')
    dst = os.path.join(release_dir, 'requirements.txt')
    
    if os.path.exists(src):
        shutil.copy2(src, dst)
        os.remove(src)
        print("Renamed release_requirements.txt to requirements.txt in release directory")

def main():
    """Main function."""
    # Get the version from command line or generate one
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        version = get_version()
    
    print(f"Preparing release version: {version}")
    
    # Configure paths
    project_dir = os.path.abspath('.')
    release_dir = os.path.join(project_dir, 'release')
    ignore_file = os.path.join(project_dir, 'release_ignore.txt')
    
    # Read ignore patterns
    ignore_patterns = read_ignore_patterns(ignore_file)
    
    # Delete existing release directory if it exists
    if os.path.exists(release_dir):
        print(f"Removing existing release directory: {release_dir}")
        shutil.rmtree(release_dir)
    
    # Create a new release directory
    os.makedirs(release_dir)
    
    # Copy files to the release directory
    print(f"Copying files to {release_dir}...")
    copy_files(project_dir, release_dir, ignore_patterns)
    
    # Rename the requirements file
    rename_requirements_file(release_dir)
    
    # Create a release zip file
    zip_path = create_zip(release_dir, version)
    
    print("\nRelease preparation complete!")
    print(f"Release directory: {release_dir}")
    print(f"Release zip: {zip_path}")
    print("\nYou can now deploy these files to your production environment.")

if __name__ == "__main__":
    main()