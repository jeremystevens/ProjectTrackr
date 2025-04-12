"""
Utility module for bulk database operations using MySQL.

This module provides functions for efficiently importing/exporting data and 
performing bulk operations that would be slow with SQLAlchemy ORM.
"""

import io
import csv
import logging
from datetime import datetime
from app import db
from sqlalchemy import text
from db import execute_raw_sql, get_direct_connection

logger = logging.getLogger(__name__)

def bulk_export_pastes(user_id=None, limit=None, format='csv'):
    """
    Export pastes in bulk using MySQL.
    
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
    
    # Build SQL query using proper MySQL syntax
    sql = f"SELECT {', '.join(columns)} FROM pastes"
    
    # Add WHERE clause if needed
    where_clauses = []
    if user_id is not None:
        where_clauses.append(f"user_id = {user_id}")
        
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    
    # Add ORDER BY and LIMIT clauses separately
    sql += " ORDER BY created_at DESC"
    
    if limit is not None:
        sql += f" LIMIT {limit}"
    
    # Execute the query
    conn = get_direct_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(sql)
        
        # Create CSV in memory
        writer = csv.writer(output)
        
        # Write header row
        writer.writerow(columns)
        
        # Write data rows
        for row in cursor:
            # Convert all values to strings and handle None values
            row_values = [str(value) if value is not None else '' for value in row]
            writer.writerow(row_values)
        
        # Reset buffer position for reading
        output.seek(0)
        return output
    finally:
        cursor.close()
        conn.close()

def bulk_import_pastes(file_obj, user_id=None):
    """
    Import pastes in bulk using MySQL.
    
    Args:
        file_obj: File-like object containing CSV data
        user_id: User ID to assign to the imported pastes
    
    Returns:
        Number of pastes imported
    """
    from models import Paste
    
    # Create a temporary table for the import
    execute_raw_sql("""
        CREATE TEMPORARY TABLE temp_pastes (
            title TEXT,
            content TEXT,
            language VARCHAR(50),
            visibility VARCHAR(20),
            expires_at DATETIME
        )
    """, fetch=False)
    
    try:
        # Read CSV data
        csv_reader = csv.DictReader(file_obj)
        row_count = 0
        
        # Process in batches for efficiency
        batch_size = 1000
        batch = []
        
        for row in csv_reader:
            # Prepare values for SQL insertion
            title = row.get('title', '') or 'Untitled Paste'
            content = row.get('content', '')
            language = row.get('language', 'plaintext')
            visibility = row.get('visibility', 'public')
            expires_at = row.get('expires_at')
            
            # Add to batch
            values = f"('{title.replace("'", "''")}', '{content.replace("'", "''")}', '{language}', '{visibility}', "
            values += f"{'NULL' if not expires_at else f"'{expires_at}'"});"
            
            batch.append(f"INSERT INTO temp_pastes (title, content, language, visibility, expires_at) VALUES {values}")
            row_count += 1
            
            if len(batch) >= batch_size:
                # Execute batch
                for sql in batch:
                    execute_raw_sql(sql, fetch=False)
                batch = []
        
        # Insert remaining batch
        if batch:
            for sql in batch:
                execute_raw_sql(sql, fetch=False)
        
        # Generate short IDs and timestamps
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # Insert from temp table to real table with proper user_id and timestamps
        uid_value = user_id if user_id is not None else 'NULL'
        execute_raw_sql(f"""
            INSERT INTO pastes (
                short_id, title, content, language, visibility, 
                created_at, expires_at, user_id, views
            )
            SELECT 
                SUBSTRING(MD5(RAND()), 1, 8),
                title, content, language, visibility,
                '{timestamp}', expires_at, {uid_value}, 0
            FROM temp_pastes
        """, fetch=False)
        
        return row_count
    finally:
        # Clean up the temp table
        execute_raw_sql("DROP TABLE IF EXISTS temp_pastes", fetch=False)

def bulk_delete_expired_pastes():
    """
    Efficiently delete expired pastes using direct SQL.
    
    Returns:
        Number of pastes deleted
    """
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
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
            COALESCE(SUM(views), 0) as total_views
        FROM pastes
    """)[0]
    
    stats['total_pastes'] = counts[0]
    stats['total_users_with_pastes'] = counts[1]
    stats['total_views'] = counts[2]
    
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