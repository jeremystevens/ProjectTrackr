"""
Utility module for bulk database operations using PostgreSQL's COPY command.

This module provides functions for efficiently importing/exporting data and 
performing bulk operations that would be slow with SQLAlchemy ORM.
"""

import io
import csv
import logging
from datetime import datetime
from db import copy_from_csv, copy_to_csv, execute_raw_sql

logger = logging.getLogger(__name__)

def bulk_export_pastes(user_id=None, limit=None, format='csv'):
    """
    Export pastes in bulk using PostgreSQL's COPY command.
    
    Args:
        user_id: Optional user ID to filter by
        limit: Optional limit for number of pastes to export
        format: Export format (csv or json)
    
    Returns:
        File-like object containing the exported data
    """
    output = io.StringIO()
    
    # Define the columns to export
    columns = [
        'id', 'short_id', 'title', 'content', 'language', 
        'created_at', 'expires_at', 'views', 'visibility'
    ]
    
    # Create WHERE clause if needed
    where_clause = None
    if user_id is not None:
        where_clause = f"user_id = {user_id}"
    
    if limit is not None:
        limit_clause = f"LIMIT {limit}"
        where_clause = f"{where_clause} {limit_clause}" if where_clause else limit_clause
    
    # Use the COPY command to export data
    copy_to_csv(output, 'pastes', columns, delimiter=',', where_clause=where_clause)
    
    # Reset the cursor to the beginning of the stream
    output.seek(0)
    return output

def bulk_import_pastes(file_obj, user_id=None):
    """
    Import pastes in bulk using PostgreSQL's COPY command.
    
    Args:
        file_obj: File-like object containing CSV data
        user_id: User ID to assign to the imported pastes
    
    Returns:
        Number of pastes imported
    """
    # Create a temporary table for the import
    execute_raw_sql("""
        CREATE TEMP TABLE temp_pastes (
            title TEXT,
            content TEXT,
            language TEXT,
            visibility TEXT,
            expires_at TIMESTAMP
        )
    """, fetch=False)
    
    try:
        # Use COPY to import the data into the temp table
        rows_imported = copy_from_csv(
            file_obj, 
            'temp_pastes', 
            columns=['title', 'content', 'language', 'visibility', 'expires_at'], 
            delimiter=','
        )
        
        # Generate short IDs and timestamps
        timestamp = datetime.utcnow()
        
        # Insert from temp table to real table with proper user_id and timestamps
        uid_value = user_id if user_id is not None else 'NULL'
        execute_raw_sql(f"""
            INSERT INTO pastes (
                short_id, title, content, language, visibility, 
                created_at, expires_at, user_id, views
            )
            SELECT 
                substr(md5(random()::text), 1, 8),
                title, content, language, visibility,
                '{timestamp}', expires_at, {uid_value}, 0
            FROM temp_pastes
        """, fetch=False)
        
        return rows_imported
    finally:
        # Clean up the temp table
        execute_raw_sql("DROP TABLE IF EXISTS temp_pastes", fetch=False)

def bulk_delete_expired_pastes():
    """
    Efficiently delete expired pastes using direct SQL.
    
    Returns:
        Number of pastes deleted
    """
    now = datetime.utcnow()
    result = execute_raw_sql(
        "DELETE FROM pastes WHERE expires_at IS NOT NULL AND expires_at < %s",
        (now,),
        fetch=False
    )
    logger.info(f"Deleted {result} expired pastes")
    return result

def bulk_update_view_counts(paste_ids):
    """
    Efficiently increment view counts for multiple pastes at once.
    
    Args:
        paste_ids: List of paste IDs to update
    
    Returns:
        Number of pastes updated
    """
    if not paste_ids:
        return 0
        
    # Convert list to string format for SQL IN clause
    id_list = ','.join(str(id) for id in paste_ids)
    
    result = execute_raw_sql(
        f"UPDATE pastes SET views = views + 1 WHERE id IN ({id_list})",
        fetch=False
    )
    
    return result

def generate_paste_stats_report():
    """
    Generate statistics report directly with SQL for efficiency.
    
    Returns:
        Dictionary containing various statistics
    """
    stats = {}
    
    # Get total counts
    counts = execute_raw_sql("""
        SELECT 
            COUNT(*) as total_pastes,
            COUNT(DISTINCT user_id) as total_users_with_pastes,
            SUM(views) as total_views
        FROM pastes
    """)[0]
    
    stats['total_pastes'] = counts[0]
    stats['total_users_with_pastes'] = counts[1]
    stats['total_views'] = counts[2] or 0
    
    # Get language distribution
    languages = execute_raw_sql("""
        SELECT language, COUNT(*) as count
        FROM pastes
        WHERE language IS NOT NULL AND language != ''
        GROUP BY language
        ORDER BY count DESC
        LIMIT 10
    """)
    
    stats['top_languages'] = [
        {'language': lang, 'count': count}
        for lang, count in languages
    ]
    
    # Get visibility distribution
    visibility = execute_raw_sql("""
        SELECT visibility, COUNT(*) as count
        FROM pastes
        GROUP BY visibility
        ORDER BY count DESC
    """)
    
    stats['visibility_distribution'] = {
        vis: count for vis, count in visibility
    }
    
    return stats