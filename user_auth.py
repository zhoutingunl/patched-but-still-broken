import sqlite3
import hashlib
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
    finally:
        conn.close()

def init_user_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                oauth_provider TEXT,
                oauth_id TEXT,
                email TEXT,
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_oauth_provider_id 
            ON users(oauth_provider, oauth_id)
        ''')
        conn.commit()

def hash_password(password):
    salt = os.urandom(32)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + pwdhash.hex()

def verify_password(stored_password, provided_password):
    salt = bytes.fromhex(stored_password[:64])
    stored_hash = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
    return pwdhash.hex() == stored_hash

def register_user(username, password):
    if not username or not password:
        return False, '用户名和密码不能为空'
    
    if len(username) < 3:
        return False, '用户名至少需要3个字符'
    
    if len(password) < 6:
        return False, '密码至少需要6个字符'
    
    password_hash = hash_password(password)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                         (username, password_hash))
            conn.commit()
            return True, '注册成功'
    except sqlite3.IntegrityError:
        return False, '用户名已存在'
    except Exception as e:
        return False, f'注册失败: {str(e)}'

def login_user(username, password):
    if not username or not password:
        return False, None, '用户名和密码不能为空'
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?',
                         (username,))
            user = cursor.fetchone()
            
            if user and verify_password(user['password_hash'], password):
                return True, {'id': user['id'], 'username': user['username']}, '登录成功'
            else:
                return False, None, '用户名或密码错误'
    except Exception as e:
        return False, None, f'登录失败: {str(e)}'

def get_user_by_id(user_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, created_at FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
    except Exception as e:
        return None

def get_or_create_oauth_user(oauth_provider, oauth_id, email=None, username=None, avatar_url=None):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, username FROM users WHERE oauth_provider = ? AND oauth_id = ?',
                (oauth_provider, oauth_id)
            )
            user = cursor.fetchone()
            
            if user:
                return True, {'id': user['id'], 'username': user['username']}, '登录成功'
            
            if not username:
                username = f"{oauth_provider}_user_{oauth_id[:8]}"
            
            base_username = username
            counter = 1
            while True:
                try:
                    cursor.execute(
                        'INSERT INTO users (username, oauth_provider, oauth_id, email, avatar_url) VALUES (?, ?, ?, ?, ?)',
                        (username, oauth_provider, oauth_id, email, avatar_url)
                    )
                    conn.commit()
                    user_id = cursor.lastrowid
                    return True, {'id': user_id, 'username': username}, '注册成功'
                except sqlite3.IntegrityError:
                    username = f"{base_username}_{counter}"
                    counter += 1
                    if counter > 100:
                        return False, None, '用户名冲突，注册失败'
    except Exception as e:
        return False, None, f'OAuth登录失败: {str(e)}'

init_user_db()
