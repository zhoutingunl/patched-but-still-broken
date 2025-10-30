import pymysql
import hashlib
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

def init_user_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                video_generation_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
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
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (%s, %s)',
                         (username, password_hash))
            conn.commit()
            return True, '注册成功'
    except pymysql.IntegrityError:
        return False, '用户名已存在'
    except Exception as e:
        return False, f'注册失败: {str(e)}'

def login_user(username, password):
    if not username or not password:
        return False, None, '用户名和密码不能为空'
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT id, username, password_hash FROM users WHERE username = %s',
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
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT id, username, created_at FROM users WHERE id = %s', (user_id,))
            user = cursor.fetchone()
            return user
    except Exception as e:
        return None

def get_user_video_count(user_id):
    return 0

def increment_user_video_count(user_id):
    return True

init_user_db()
