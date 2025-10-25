import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = 'generation_statistics.db'

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generation_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                client_address TEXT NOT NULL,
                upload_file_count INTEGER NOT NULL DEFAULT 0,
                upload_text_total_chars INTEGER NOT NULL DEFAULT 0,
                upload_content_size INTEGER NOT NULL DEFAULT 0,
                generated_scene_count INTEGER NOT NULL DEFAULT 0,
                generated_content_size INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON generation_statistics(session_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON generation_statistics(created_at)
        ''')

def create_statistics_record(session_id, client_address, upload_file_count, 
                            upload_text_total_chars, upload_content_size):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO generation_statistics 
            (session_id, client_address, upload_file_count, 
             upload_text_total_chars, upload_content_size)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, client_address, upload_file_count, 
              upload_text_total_chars, upload_content_size))
        return cursor.lastrowid

def update_statistics_record(session_id, generated_scene_count, generated_content_size):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE generation_statistics 
            SET generated_scene_count = ?,
                generated_content_size = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (generated_scene_count, generated_content_size, session_id))
        return cursor.rowcount

def get_statistics_by_session(session_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM generation_statistics 
            WHERE session_id = ?
        ''', (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_statistics(limit=100, offset=0):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM generation_statistics 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_statistics_summary():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_tasks,
                SUM(upload_file_count) as total_files,
                SUM(upload_text_total_chars) as total_chars,
                SUM(upload_content_size) as total_upload_size,
                SUM(generated_scene_count) as total_scenes,
                SUM(generated_content_size) as total_generated_size
            FROM generation_statistics
        ''')
        row = cursor.fetchone()
        return dict(row) if row else None

init_db()
