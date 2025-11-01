import unittest
import sys
import os
import json
import tempfile
import time
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_app import FlaskAppWrapper


class TestAPIFunctional(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.app_wrapper = FlaskAppWrapper('test_novel_to_anime', port=5001)
        cls.app_wrapper.app_.config['TESTING'] = True
        cls.client = cls.app_wrapper.app_.test_client()
    
    def setUp(self):
        with self.client.session_transaction() as sess:
            sess.clear()
    
    def test_01_index_endpoint(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'html', response.data.lower())
    
    def test_02_login_page_endpoint(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'html', response.data.lower())
    
    def test_03_settings_page_endpoint(self):
        response = self.client.get('/settings')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'html', response.data.lower())
    
    def test_04_favicon_endpoint(self):
        response = self.client.get('/favicon.ico')
        self.assertIn(response.status_code, [200, 404])
    
    @patch('user_auth.register_user')
    def test_05_register_api_success(self, mock_register):
        mock_register.return_value = (True, '注册成功')
        
        response = self.client.post('/api/register',
                                    json={'username': 'testuser', 'password': 'password123'},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], '注册成功')
    
    @patch('user_auth.register_user')
    def test_06_register_api_missing_username(self, mock_register):
        response = self.client.post('/api/register',
                                    json={'password': 'password123'},
                                    content_type='application/json')
        
        data = response.get_json()
        self.assertIsNotNone(data)
    
    @patch('user_auth.register_user')
    def test_07_register_api_missing_password(self, mock_register):
        response = self.client.post('/api/register',
                                    json={'username': 'testuser'},
                                    content_type='application/json')
        
        data = response.get_json()
        self.assertIsNotNone(data)
    
    @patch('user_auth.register_user')
    def test_08_register_api_duplicate_user(self, mock_register):
        mock_register.return_value = (False, '用户名已存在')
        
        response = self.client.post('/api/register',
                                    json={'username': 'existinguser', 'password': 'password123'},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], '用户名已存在')
    
    @patch('user_auth.login_user')
    def test_09_login_api_success(self, mock_login):
        mock_login.return_value = (True, {'id': 1, 'username': 'testuser'}, '登录成功')
        
        response = self.client.post('/api/login',
                                    json={'username': 'testuser', 'password': 'password123'},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], '登录成功')
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')
    
    @patch('user_auth.login_user')
    def test_10_login_api_wrong_credentials(self, mock_login):
        mock_login.return_value = (False, None, '用户名或密码错误')
        
        response = self.client.post('/api/login',
                                    json={'username': 'wronguser', 'password': 'wrongpass'},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], '用户名或密码错误')
    
    def test_11_logout_api_success(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.post('/api/logout')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['message'], '已退出登录')
    
    def test_12_current_user_api_not_logged_in(self):
        response = self.client.get('/api/current_user')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('user', data)
        self.assertIsNone(data['user'])
    
    @patch('user_auth.get_user_by_id')
    def test_13_current_user_api_logged_in(self, mock_get_user):
        mock_get_user.return_value = {'id': 1, 'username': 'testuser'}
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.get('/api/current_user')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('user', data)
        self.assertIsNotNone(data['user'])
        self.assertEqual(data['user']['username'], 'testuser')
    
    def test_14_history_api_not_logged_in(self):
        response = self.client.get('/api/history')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    @patch('statistics_db.get_statistics')
    def test_15_history_api_logged_in(self, mock_get_stats):
        mock_get_stats.return_value = [
            {'session_id': 'test1', 'filename': 'novel1.txt'},
            {'session_id': 'test2', 'filename': 'novel2.txt'}
        ]
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.get('/api/history')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('history', data)
        self.assertEqual(len(data['history']), 2)
    
    def test_16_check_payment_not_logged_in(self):
        response = self.client.post('/api/check_payment',
                                    json={'word_count': 1000},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
    
    @patch('user_auth.get_user_video_count')
    def test_17_check_payment_free_tier(self, mock_video_count):
        mock_video_count.return_value = 1
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.post('/api/check_payment',
                                    json={'word_count': 1000},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('requires_payment', data)
        self.assertFalse(data['requires_payment'])
        self.assertEqual(data['video_count'], 1)
        self.assertEqual(data['remaining_free'], 2)
    
    @patch('user_auth.get_user_video_count')
    def test_18_check_payment_paid_tier(self, mock_video_count):
        mock_video_count.return_value = 5
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.post('/api/check_payment',
                                    json={'word_count': 1000},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('requires_payment', data)
        self.assertTrue(data['requires_payment'])
        self.assertEqual(data['video_count'], 5)
        self.assertEqual(data['word_count'], 1000)
        self.assertEqual(data['payment_amount'], 1.0)
    
    def test_19_upload_novel_not_logged_in(self):
        response = self.client.post('/api/upload')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_20_upload_novel_no_file(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.post('/api/upload')
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    @patch('statistics_db.insert_statistics')
    @patch('threading.Thread')
    def test_21_upload_novel_success(self, mock_thread, mock_insert_stats):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('这是一个测试小说。\n第一章 测试章节\n这是测试内容。')
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = self.client.post('/api/upload',
                                           data={
                                               'novel': (f, 'test_novel.txt'),
                                               'max_scenes': '5',
                                               'api_key': 'test_api_key',
                                               'api_provider': 'qiniu',
                                               'enable_video': 'false',
                                               'use_ai_analysis': 'true',
                                               'use_storyboard': 'true'
                                           },
                                           content_type='multipart/form-data')
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('task_id', data)
            self.assertIn('message', data)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_22_upload_novel_invalid_file_type(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write('test content')
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = self.client.post('/api/upload',
                                           data={
                                               'novel': (f, 'test_novel.pdf'),
                                               'api_key': 'test_api_key'
                                           },
                                           content_type='multipart/form-data')
            
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertIn('error', data)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_23_get_status_nonexistent_task(self):
        response = self.client.get('/api/status/nonexistent_task_id')
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_24_get_status_existing_task(self):
        task_id = 'test_task_123'
        self.app_wrapper.generation_status_[task_id] = {
            'status': 'processing',
            'progress': 50,
            'message': '正在处理...'
        }
        
        response = self.client.get(f'/api/status/{task_id}')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'processing')
        self.assertEqual(data['progress'], 50)
    
    def test_25_get_scenes_nonexistent_task(self):
        response = self.client.get('/api/scenes/nonexistent_task_id')
        
        self.assertIn(response.status_code, [404, 400])
    
    def test_26_get_scenes_incomplete_task(self):
        task_id = 'test_task_456'
        self.app_wrapper.generation_status_[task_id] = {
            'status': 'processing',
            'progress': 50,
            'message': '正在处理...'
        }
        
        response = self.client.get(f'/api/scenes/{task_id}')
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_27_download_content_nonexistent_task(self):
        response = self.client.get('/api/download/nonexistent_task_id')
        
        self.assertIn(response.status_code, [404, 400])
    
    def test_28_api_endpoints_cors_headers(self):
        response = self.client.get('/api/current_user')
        
        self.assertIn('Access-Control-Allow-Credentials', response.headers)
    
    def test_29_api_json_content_type(self):
        response = self.client.get('/api/current_user')
        
        self.assertIn('application/json', response.content_type)
    
    @patch('user_auth.login_user')
    def test_30_session_persistence_after_login(self, mock_login):
        mock_login.return_value = (True, {'id': 1, 'username': 'testuser'}, '登录成功')
        
        response = self.client.post('/api/login',
                                    json={'username': 'testuser', 'password': 'password123'},
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        response2 = self.client.get('/api/current_user')
        self.assertEqual(response2.status_code, 200)


if __name__ == '__main__':
    unittest.main()
