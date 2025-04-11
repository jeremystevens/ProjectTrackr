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
    # Always ignore the release directory itself to prevent recursion
    if path.startswith('./release') or path == './release' or path == 'release' or '/release/' in path:
        return True
    
    # Remove ./ prefix for matching
    rel_path = path[2:] if path.startswith('./') else path
    
    # Explicit check for release directory with different path formats
    if rel_path == 'release' or rel_path.startswith('release/') or '/release/' in rel_path:
        return True
    
    for pattern in ignore_patterns:
        # Handle directory patterns
        if pattern.endswith('/'):
            if rel_path.startswith(pattern) or rel_path + '/' == pattern:
                return True
        # Handle file patterns with wildcards
        elif fnmatch.fnmatch(rel_path, pattern):
            return True
    
    return False

def copy_files(src_dir, dest_dir, ignore_patterns, verbose=False):
    """Copy files from src_dir to dest_dir, excluding those matching ignore_patterns."""
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    total_files = 0
    copied_files = 0
    ignored_files = 0
    
    # First, count total files for progress reporting
    print("Scanning project directory...")
    for _, _, files in os.walk(src_dir):
        total_files += len(files)
    
    print(f"Found {total_files} total files in project")
    
    # Print progress every N files
    progress_interval = max(1, min(100, total_files // 20))
    
    for root, dirs, files in os.walk(src_dir):
        # Convert root to a relative path for pattern matching
        rel_root = '.' + root[len(src_dir):]
        
        # Create corresponding directories in destination
        dirs_to_remove = []
        for i, d in enumerate(dirs):
            src_path = os.path.join(root, d)
            rel_path = os.path.join(rel_root, d)
            
            if should_ignore(rel_path, ignore_patterns):
                # Mark directory for removal to avoid walking into it
                dirs_to_remove.append(d)
                if verbose:
                    print(f"Ignoring directory: {rel_path}")
            else:
                dest_path = os.path.join(dest_dir, os.path.relpath(src_path, src_dir))
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)
                    if verbose:
                        print(f"Created directory: {os.path.relpath(dest_path, dest_dir)}")
        
        # Remove ignored directories from the dirs list to prevent walking into them
        for d in dirs_to_remove:
            dirs.remove(d)
        
        # Copy files
        for f in files:
            src_path = os.path.join(root, f)
            rel_path = os.path.join(rel_root, f)
            
            if should_ignore(rel_path, ignore_patterns):
                ignored_files += 1
                if verbose:
                    print(f"Ignoring file: {rel_path}")
            else:
                dest_path = os.path.join(dest_dir, os.path.relpath(src_path, src_dir))
                # Create parent directories if they don't exist
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src_path, dest_path)
                copied_files += 1
                
                # Show progress periodically
                if copied_files % progress_interval == 0 or copied_files == 1:
                    print(f"Progress: Copied {copied_files}/{total_files-ignored_files} files...")
    
    print(f"Copied {copied_files} files, ignored {ignored_files} files")

def create_zip(src_dir, version):
    """Create a zip file of the release directory with the given version."""
    zip_name = f"release_{version}.zip"
    
    # Make this optional since it might be too large
    try:
        print(f"Creating zip archive (this might take a while for large projects)...")
        total_files = sum(len(files) for _, _, files in os.walk(src_dir))
        print(f"Archiving {total_files} files...")
        
        # Set a file limit to avoid memory issues
        if total_files > 1000:
            print(f"Warning: Large number of files ({total_files}). Zip creation may be slow.")
            print("Consider manually zipping the release directory if this fails.")
        
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            file_count = 0
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, src_dir)
                    zipf.write(file_path, rel_path)
                    file_count += 1
                    
                    # Show progress periodically
                    if file_count % 100 == 0:
                        print(f"Archived {file_count}/{total_files} files...")
        
        print(f"Created zip archive: {zip_name}")
        return zip_name
    except Exception as e:
        print(f"Warning: Could not create zip file: {str(e)}")
        print(f"The release directory is still available at: {src_dir}")
        return None

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
    # Check for debug mode and no-zip mode
    debug_mode = '--debug' in sys.argv
    no_zip_mode = '--no-zip' in sys.argv
    
    # Get the version from command line or generate one
    version_args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    if version_args:
        version = version_args[0]
    else:
        version = get_version()
    
    print(f"Preparing release version: {version}")
    
    # Configure paths
    project_dir = os.path.abspath('.')
    release_dir = os.path.join(project_dir, 'release')
    ignore_file = os.path.join(project_dir, 'release_ignore.txt')
    
    # Read ignore patterns
    ignore_patterns = read_ignore_patterns(ignore_file)
    print(f"Loaded {len(ignore_patterns)} ignore patterns")
    
    if debug_mode:
        print("Ignore patterns:")
        for pattern in ignore_patterns:
            print(f"  - {pattern}")
    
    # Delete existing release directory if it exists
    if os.path.exists(release_dir):
        print(f"Removing existing release directory: {release_dir}")
        shutil.rmtree(release_dir)
    
    # Create a new release directory
    os.makedirs(release_dir)
    print(f"Created fresh release directory: {release_dir}")
    
    # Copy files to the release directory
    print(f"Copying files to {release_dir}...")
    
    # Confirm the release directory is in ignore patterns
    for pattern in ['release', 'release/', '/release', '/release/']:
        if pattern not in ignore_patterns:
            print(f"Warning: '{pattern}' is not explicitly in ignore patterns!")
    
    copy_files(project_dir, release_dir, ignore_patterns, verbose=debug_mode)
    
    # Rename the requirements file
    rename_requirements_file(release_dir)
    
    # Count the number of files in the release directory
    file_count = sum(len(files) for _, _, files in os.walk(release_dir))
    print(f"Release directory contains {file_count} files")
    
    # Verify the release directory doesn't contain itself
    if os.path.exists(os.path.join(release_dir, 'release')):
        print("ERROR: The release directory contains a 'release' subdirectory!")
        print("This indicates a recursion problem in the ignore patterns.")
        return
    
    # Create a release zip file (unless --no-zip is specified)
    if no_zip_mode:
        print("Skipping zip file creation (--no-zip specified)")
        zip_path = None
    else:
        zip_path = create_zip(release_dir, version)
    
    print("\nRelease preparation complete!")
    print(f"Release directory: {release_dir}")
    if zip_path:
        print(f"Release zip: {zip_path}")
    else:
        print("Note: Zip file creation was skipped or failed")
        print(f"You can manually zip the release directory if needed")
    print("\nYou can now deploy these files to your production environment.")

if __name__ == "__main__":
    main()