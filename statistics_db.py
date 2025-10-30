import pytz
import pymysql
import os
from datetime import datetime
from contextlib import contextmanager
from db_config import DB_CONFIG

@contextmanager
def get_db_connection():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generation_statistics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                client_address VARCHAR(255) NOT NULL,
                upload_file_count INT NOT NULL,
                upload_text_chars INT NOT NULL,
                upload_content_size INT NOT NULL,
                generated_scene_count INT DEFAULT 0,
                generated_content_size INT DEFAULT 0,
                username VARCHAR(255),
                filename VARCHAR(255),
                input_text TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session_id (session_id),
                INDEX idx_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                username VARCHAR(255) NOT NULL,
                input_text TEXT,
                shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session_id (session_id),
                INDEX idx_shared_at (shared_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        conn.commit()

def insert_statistics(session_id, client_address, upload_file_count, upload_text_chars, upload_content_size, username=None, filename=None, input_text=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO generation_statistics 
            (session_id, client_address, upload_file_count, upload_text_chars, upload_content_size, username, filename, input_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (session_id, client_address, upload_file_count, upload_text_chars, upload_content_size, username, filename, input_text))
        conn.commit()
        return cursor.lastrowid

def update_generation_stats(session_id, generated_scene_count, generated_content_size, metadata=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if metadata:
            import json
            metadata_json = json.dumps(metadata, ensure_ascii=False)
            cursor.execute('''
                UPDATE generation_statistics 
                SET generated_scene_count = %s, generated_content_size = %s, metadata = %s
                WHERE session_id = %s
            ''', (generated_scene_count, generated_content_size, metadata_json, session_id))
        else:
            cursor.execute('''
                UPDATE generation_statistics 
                SET generated_scene_count = %s, generated_content_size = %s
                WHERE session_id = %s
            ''', (generated_scene_count, generated_content_size, session_id))
        conn.commit()


def get_statistics(session_id=None, username=None, limit=None):
    with get_db_connection() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        if session_id:
            cursor.execute('SELECT * FROM generation_statistics WHERE session_id = %s', (session_id,))
            result = cursor.fetchone()
            if result and result.get('created_at'):
                result['created_at'] = result['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            return result
        elif username:
            query = 'SELECT * FROM generation_statistics WHERE username = %s ORDER BY created_at DESC'
            if limit:
                query += f' LIMIT {limit}'
            cursor.execute(query, (username,))

            # 转换时间格式为字符串
        else:
            cursor.execute('SELECT * FROM generation_statistics ORDER BY created_at DESC')

        results = cursor.fetchall()
        for result in results:
            if result.get('created_at'):
                dt_utc = result['created_at']
                if dt_utc.tzinfo is None:
                    dt_utc = pytz.utc.localize(dt_utc)
                dt_bj = dt_utc.astimezone(pytz.timezone("Asia/Shanghai"))
                result['created_at'] = dt_bj.strftime('%Y-%m-%d %H:%M:%S')
        return results


def delete_statistics(session_id, username=None):
    """删除指定的统计记录"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if username:
            cursor.execute('SELECT id FROM generation_statistics WHERE session_id = %s AND username = %s', (session_id, username))
            if not cursor.fetchone():
                return False
        
        cursor.execute('DELETE FROM generation_statistics WHERE session_id = %s', (session_id,))
        conn.commit()
        return cursor.rowcount > 0

def share_record(session_id, username):
    with get_db_connection() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT session_id, input_text FROM generation_statistics WHERE session_id = %s AND username = %s', (session_id, username))
        record = cursor.fetchone()
        
        if not record:
            return False, '记录不存在'
        
        cursor.execute('SELECT id FROM shared_records WHERE session_id = %s', (session_id,))
        if cursor.fetchone():
            return False, '记录已经共享过了'
        
        cursor.execute('INSERT INTO shared_records (session_id, username, input_text) VALUES (%s, %s, %s)',
                      (session_id, username, record['input_text']))
        conn.commit()
        return True, '共享成功'

def get_shared_records(limit=50):
    with get_db_connection() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        query = '''
            SELECT sr.session_id, sr.username, sr.input_text, sr.shared_at,
                   gs.generated_scene_count, gs.metadata
            FROM shared_records sr
            LEFT JOIN generation_statistics gs ON sr.session_id = gs.session_id
            WHERE gs.generated_scene_count > 0
            ORDER BY RAND()
            LIMIT %s
        '''
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        for result in results:
            if result.get('shared_at'):
                dt_utc = result['shared_at']
                if dt_utc.tzinfo is None:
                    dt_utc = pytz.utc.localize(dt_utc)
                dt_bj = dt_utc.astimezone(pytz.timezone("Asia/Shanghai"))
                result['shared_at'] = dt_bj.strftime('%Y-%m-%d %H:%M:%S')
        
        return results

init_db()
