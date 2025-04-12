#!/usr/bin/env python3
"""
Create MySQL Migration Zip

This script creates a zip file from the release directory
for easy MySQL migration package distribution.
"""
import os
import zipfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mysql_migration_zip():
    """Create a zip file from the release directory."""
    release_dir = "release"
    output_zip = "mysql_migration.zip"
    
    if not os.path.exists(release_dir):
        logger.error(f"Release directory '{release_dir}' not found.")
        return False
    
    try:
        logger.info(f"Creating MySQL migration zip file: {output_zip}")
        
        # Count files to show progress
        file_count = sum(len(files) for _, _, files in os.walk(release_dir))
        logger.info(f"Found {file_count} files to archive")
        
        # Create zip file
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            file_processed = 0
            
            for root, _, files in os.walk(release_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Get relative path within release directory
                    rel_path = os.path.relpath(file_path, release_dir)
                    
                    # Add file to zip
                    zipf.write(file_path, rel_path)
                    file_processed += 1
                    
                    # Log progress every 50 files
                    if file_processed % 50 == 0 or file_processed == file_count:
                        logger.info(f"Progress: {file_processed}/{file_count} files")
        
        zip_size_mb = os.path.getsize(output_zip) / (1024 * 1024)
        logger.info(f"Successfully created {output_zip} ({zip_size_mb:.2f} MB)")
        return True
    
    except Exception as e:
        logger.error(f"Error creating zip file: {e}")
        return False

if __name__ == "__main__":
    logger.info("Creating MySQL migration zip file...")
    if create_mysql_migration_zip():
        logger.info("MySQL migration zip file created successfully!")
    else:
        logger.error("Failed to create MySQL migration zip file.")