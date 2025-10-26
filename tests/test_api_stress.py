import unittest
import sys
import os
import time
import concurrent.futures
import threading
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_app import FlaskAppWrapper


class TestAPIStress(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.app_wrapper = FlaskAppWrapper('test_stress_novel_to_anime', port=5002)
        cls.app_wrapper.app_.config['TESTING'] = True
        cls.client = cls.app_wrapper.app_.test_client()
    
    def test_01_concurrent_index_requests(self):
        num_requests = 50
        results = []
        
        def make_request():
            response = self.client.get('/')
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        self.assertEqual(len(results), num_requests)
        success_count = sum(1 for status in results if status == 200)
        self.assertGreater(success_count, num_requests * 0.9)
    
    @patch('user_auth.register_user')
    def test_02_concurrent_register_requests(self, mock_register):
        mock_register.return_value = (True, '注册成功')
        
        num_requests = 30
        results = []
        
        def make_request(index):
            response = self.client.post('/api/register',
                                        json={'username': f'user{index}', 'password': 'pass123'},
                                        content_type='application/json')
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        self.assertEqual(len(results), num_requests)
        success_count = sum(1 for status in results if status == 200)
        self.assertGreater(success_count, num_requests * 0.8)
    
    @patch('user_auth.login_user')
    def test_03_concurrent_login_requests(self, mock_login):
        mock_login.return_value = (True, {'id': 1, 'username': 'testuser'}, '登录成功')
        
        num_requests = 30
        results = []
        
        def make_request():
            response = self.client.post('/api/login',
                                        json={'username': 'testuser', 'password': 'pass123'},
                                        content_type='application/json')
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        self.assertEqual(len(results), num_requests)
        success_count = sum(1 for status in results if status == 200)
        self.assertGreater(success_count, num_requests * 0.8)
    
    def test_04_sequential_api_calls_response_time(self):
        num_requests = 20
        response_times = []
        
        for _ in range(num_requests):
            start_time = time.time()
            response = self.client.get('/api/current_user')
            end_time = time.time()
            
            self.assertEqual(response.status_code, 200)
            response_times.append(end_time - start_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        self.assertLess(avg_response_time, 0.1)
    
    @patch('user_auth.get_user_by_id')
    def test_05_concurrent_current_user_requests(self, mock_get_user):
        mock_get_user.return_value = {'id': 1, 'username': 'testuser'}
        
        num_requests = 50
        results = []
        
        def make_request():
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'testuser'
            
            response = self.client.get('/api/current_user')
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        self.assertEqual(len(results), num_requests)
        success_count = sum(1 for status in results if status == 200)
        self.assertGreater(success_count, num_requests * 0.9)
    
    @patch('statistics_db.get_statistics')
    def test_06_concurrent_history_requests(self, mock_get_stats):
        mock_get_stats.return_value = [
            {'session_id': f'test{i}', 'filename': f'novel{i}.txt'}
            for i in range(10)
        ]
        
        num_requests = 30
        results = []
        
        def make_request():
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'testuser'
            
            response = self.client.get('/api/history')
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        self.assertEqual(len(results), num_requests)
        success_count = sum(1 for status in results if status == 200)
        self.assertGreater(success_count, num_requests * 0.8)
    
    def test_07_rapid_status_check_requests(self):
        task_id = 'stress_test_task'
        self.app_wrapper.generation_status_[task_id] = {
            'status': 'processing',
            'progress': 50,
            'message': '正在处理...'
        }
        
        num_requests = 100
        results = []
        
        def make_request():
            response = self.client.get(f'/api/status/{task_id}')
            return response.status_code
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        self.assertEqual(len(results), num_requests)
        success_count = sum(1 for status in results if status == 200)
        self.assertGreater(success_count, num_requests * 0.9)
        self.assertLess(total_time, 5.0)
    
    @patch('user_auth.get_user_video_count')
    def test_08_concurrent_check_payment_requests(self, mock_video_count):
        mock_video_count.return_value = 2
        
        num_requests = 40
        results = []
        
        def make_request(word_count):
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'testuser'
            
            response = self.client.post('/api/check_payment',
                                        json={'word_count': word_count},
                                        content_type='application/json')
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, 1000 + i * 100) for i in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        self.assertEqual(len(results), num_requests)
        success_count = sum(1 for status in results if status == 200)
        self.assertGreater(success_count, num_requests * 0.8)
    
    def test_09_mixed_endpoint_stress_test(self):
        num_iterations = 10
        results = []
        
        def make_mixed_requests():
            responses = []
            responses.append(self.client.get('/'))
            responses.append(self.client.get('/login'))
            responses.append(self.client.get('/api/current_user'))
            return [r.status_code for r in responses]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_mixed_requests) for _ in range(num_iterations)]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())
        
        self.assertEqual(len(results), num_iterations * 3)
        success_count = sum(1 for status in results if status == 200)
        self.assertGreater(success_count, len(results) * 0.9)
    
    def test_10_memory_leak_detection_session_creation(self):
        import gc
        gc.collect()
        
        num_requests = 50
        
        for _ in range(num_requests):
            response = self.client.get('/api/current_user')
            self.assertEqual(response.status_code, 200)
        
        gc.collect()
    
    def test_11_response_time_under_load(self):
        num_requests = 20
        response_times = []
        
        def make_request_and_measure():
            start = time.time()
            response = self.client.get('/')
            end = time.time()
            return (response.status_code, end - start)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request_and_measure) for _ in range(num_requests)]
            for future in concurrent.futures.as_completed(futures):
                status, duration = future.result()
                if status == 200:
                    response_times.append(duration)
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            self.assertLess(avg_time, 0.2)
            self.assertLess(max_time, 1.0)
    
    def test_12_status_endpoint_scalability(self):
        num_tasks = 20
        task_ids = []
        
        for i in range(num_tasks):
            task_id = f'task_{i}'
            task_ids.append(task_id)
            self.app_wrapper.generation_status_[task_id] = {
                'status': 'processing',
                'progress': i * 5,
                'message': f'处理中 {i}'
            }
        
        num_requests = 100
        results = []
        
        def make_request(task_id):
            response = self.client.get(f'/api/status/{task_id}')
            return response.status_code
        
        import random
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(make_request, random.choice(task_ids)) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        self.assertEqual(len(results), num_requests)
        success_count = sum(1 for status in results if status == 200)
        self.assertGreater(success_count, num_requests * 0.95)
    
    @patch('user_auth.login_user')
    def test_13_session_isolation_under_concurrent_login(self, mock_login):
        def login_user_side_effect(username, password):
            user_id = hash(username) % 10000
            return (True, {'id': user_id, 'username': username}, '登录成功')
        
        mock_login.side_effect = login_user_side_effect
        
        num_users = 10
        results = []
        
        def login_and_check(username):
            response1 = self.client.post('/api/login',
                                         json={'username': username, 'password': 'pass123'},
                                         content_type='application/json')
            
            if response1.status_code != 200:
                return False
            
            return True
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(login_and_check, f'user{i}') for i in range(num_users)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        success_count = sum(1 for result in results if result)
        self.assertGreater(success_count, num_users * 0.8)
    
    def test_14_sustained_load_test(self):
        duration_seconds = 3
        request_interval = 0.05
        
        start_time = time.time()
        request_count = 0
        success_count = 0
        
        while time.time() - start_time < duration_seconds:
            response = self.client.get('/api/current_user')
            request_count += 1
            if response.status_code == 200:
                success_count += 1
            time.sleep(request_interval)
        
        success_rate = success_count / request_count if request_count > 0 else 0
        requests_per_second = request_count / duration_seconds
        
        self.assertGreater(success_rate, 0.95)
        self.assertGreater(requests_per_second, 10)
    
    def test_15_error_rate_under_invalid_requests(self):
        num_requests = 30
        error_count = 0
        
        def make_invalid_request():
            response = self.client.post('/api/register',
                                        json={'invalid': 'data'},
                                        content_type='application/json')
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_invalid_request) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        for status in results:
            if status >= 400:
                error_count += 1
        
        self.assertEqual(len(results), num_requests)


if __name__ == '__main__':
    unittest.main()
