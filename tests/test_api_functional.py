import unittest
import sys
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_app import FlaskAppWrapper


class TestAPIFunctional(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.flask_wrapper = FlaskAppWrapper(__name__, port=5001)
        cls.app = cls.flask_wrapper.app_
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_01_index_endpoint(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', response.data)
    
    def test_02_login_page_endpoint(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', response.data)
    
    def test_03_settings_page_endpoint(self):
        response = self.client.get('/settings')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', response.data)
    
    @patch('user_auth.register_user')
    def test_04_register_success(self, mock_register):
        mock_register.return_value = (True, '注册成功')
        
        response = self.client.post('/api/register',
                                    json={'username': 'newuser', 'password': 'securepass123'})
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['message'], '注册成功')
    
    @patch('user_auth.register_user')
    def test_05_register_missing_username(self, mock_register):
        response = self.client.post('/api/register',
                                    json={'password': 'securepass123'})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    @patch('user_auth.register_user')
    def test_06_register_missing_password(self, mock_register):
        response = self.client.post('/api/register',
                                    json={'username': 'testuser'})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    @patch('user_auth.register_user')
    def test_07_register_duplicate_user(self, mock_register):
        mock_register.return_value = (False, '用户名已存在')
        
        response = self.client.post('/api/register',
                                    json={'username': 'existinguser', 'password': 'password123'})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['error'], '用户名已存在')
    
    @patch('user_auth.login_user')
    def test_08_login_success(self, mock_login):
        mock_login.return_value = (True, {'id': 1, 'username': 'testuser'}, '登录成功')
        
        response = self.client.post('/api/login',
                                    json={'username': 'testuser', 'password': 'password123'})
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['message'], '登录成功')
        self.assertIn('user', data)
    
    @patch('user_auth.login_user')
    def test_09_login_invalid_credentials(self, mock_login):
        mock_login.return_value = (False, None, '用户名或密码错误')
        
        response = self.client.post('/api/login',
                                    json={'username': 'wronguser', 'password': 'wrongpass'})
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data['error'], '用户名或密码错误')
    
    @patch('user_auth.login_user')
    def test_10_login_missing_username(self, mock_login):
        response = self.client.post('/api/login',
                                    json={'password': 'password123'})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    @patch('user_auth.login_user')
    def test_11_login_missing_password(self, mock_login):
        response = self.client.post('/api/login',
                                    json={'username': 'testuser'})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_12_logout_success(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.post('/api/logout')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['message'], '已退出登录')
    
    def test_13_logout_not_logged_in(self):
        response = self.client.post('/api/logout')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['message'], '已退出登录')
    
    @patch('user_auth.get_user_by_id')
    def test_14_current_user_logged_in(self, mock_get_user):
        mock_get_user.return_value = {'id': 1, 'username': 'testuser'}
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.get('/api/current_user')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsNotNone(data['user'])
        self.assertEqual(data['user']['username'], 'testuser')
    
    def test_15_current_user_not_logged_in(self):
        response = self.client.get('/api/current_user')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsNone(data['user'])
    
    @patch('statistics_db.get_statistics')
    def test_16_get_history_success(self, mock_get_stats):
        mock_get_stats.return_value = [
            {'session_id': 'test1', 'novel_name': 'novel1'},
            {'session_id': 'test2', 'novel_name': 'novel2'}
        ]
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        
        response = self.client.get('/api/history')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['history']), 2)
    
    def test_17_get_history_not_logged_in(self):
        response = self.client.get('/api/history')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    @patch('user_auth.get_user_video_count')
    def test_18_check_payment_sufficient_quota(self, mock_get_count):
        mock_get_count.return_value = 5
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        
        response = self.client.post('/api/check_payment',
                                    json={'max_scenes': 3})
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['has_quota'])
    
    @patch('user_auth.get_user_video_count')
    def test_19_check_payment_insufficient_quota(self, mock_get_count):
        mock_get_count.return_value = 0
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        
        response = self.client.post('/api/check_payment',
                                    json={'max_scenes': 3})
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['has_quota'])
    
    def test_20_check_payment_not_logged_in(self):
        response = self.client.post('/api/check_payment',
                                    json={'max_scenes': 3})
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_21_upload_not_logged_in(self):
        response = self.client.post('/api/upload')
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_22_upload_no_file(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        
        response = self.client.post('/api/upload',
                                    data={})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    @patch('user_auth.get_user_video_count')
    def test_23_upload_invalid_file_type(self, mock_get_count):
        mock_get_count.return_value = 10
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        
        data = {
            'file': (tempfile.NamedTemporaryFile(suffix='.pdf', delete=False), 'test.pdf'),
            'max_scenes': '5',
            'api_key': 'test-key'
        }
        
        response = self.client.post('/api/upload',
                                    data=data,
                                    content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        response_data = response.get_json()
        self.assertIn('error', response_data)
    
    def test_24_get_status_invalid_task(self):
        response = self.client.get('/api/status/invalid_task_id')
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_25_get_scenes_invalid_task(self):
        response = self.client.get('/api/scenes/invalid_task_id')
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)


class TestAPIEdgeCases(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.flask_wrapper = FlaskAppWrapper(__name__, port=5002)
        cls.app = cls.flask_wrapper.app_
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_26_register_empty_json(self):
        response = self.client.post('/api/register',
                                    json={})
        
        self.assertEqual(response.status_code, 400)
    
    def test_27_login_empty_json(self):
        response = self.client.post('/api/login',
                                    json={})
        
        self.assertEqual(response.status_code, 400)
    
    def test_28_register_invalid_content_type(self):
        response = self.client.post('/api/register',
                                    data='username=test&password=test')
        
        self.assertIn(response.status_code, [400, 415])
    
    def test_29_login_invalid_content_type(self):
        response = self.client.post('/api/login',
                                    data='username=test&password=test')
        
        self.assertIn(response.status_code, [400, 415])
    
    @patch('user_auth.register_user')
    def test_30_register_special_characters(self, mock_register):
        mock_register.return_value = (True, '注册成功')
        
        response = self.client.post('/api/register',
                                    json={'username': 'test@#$%', 'password': 'pass!@#$%'})
        
        self.assertIn(response.status_code, [200, 400])
    
    @patch('user_auth.login_user')
    def test_31_login_sql_injection_attempt(self, mock_login):
        mock_login.return_value = (False, None, '用户名或密码错误')
        
        response = self.client.post('/api/login',
                                    json={'username': "admin' OR '1'='1", 'password': 'password'})
        
        self.assertEqual(response.status_code, 401)
    
    def test_32_get_status_sql_injection_attempt(self):
        response = self.client.get("/api/status/test' OR '1'='1")
        
        self.assertEqual(response.status_code, 404)
    
    @patch('user_auth.get_user_video_count')
    def test_33_check_payment_negative_scenes(self, mock_get_count):
        mock_get_count.return_value = 10
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        
        response = self.client.post('/api/check_payment',
                                    json={'max_scenes': -5})
        
        self.assertIn(response.status_code, [200, 400])
    
    @patch('user_auth.get_user_video_count')
    def test_34_check_payment_zero_scenes(self, mock_get_count):
        mock_get_count.return_value = 10
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        
        response = self.client.post('/api/check_payment',
                                    json={'max_scenes': 0})
        
        self.assertEqual(response.status_code, 200)
    
    @patch('user_auth.get_user_video_count')
    def test_35_check_payment_extremely_large_scenes(self, mock_get_count):
        mock_get_count.return_value = 10
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        
        response = self.client.post('/api/check_payment',
                                    json={'max_scenes': 999999})
        
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
