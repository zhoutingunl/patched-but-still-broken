import sys
import os
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_app import FlaskAppWrapper


class LoadTestResult:
    def __init__(self, endpoint_name):
        self.endpoint_name = endpoint_name
        self.response_times = []
        self.status_codes = []
        self.errors = []
    
    def add_result(self, response_time, status_code, error=None):
        self.response_times.append(response_time)
        self.status_codes.append(status_code)
        if error:
            self.errors.append(error)
    
    def get_stats(self):
        if not self.response_times:
            return {
                'endpoint': self.endpoint_name,
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'error_rate': 0,
                'errors': self.errors
            }
        
        successful = sum(1 for code in self.status_codes if 200 <= code < 300)
        failed = len(self.status_codes) - successful
        
        return {
            'endpoint': self.endpoint_name,
            'total_requests': len(self.response_times),
            'successful_requests': successful,
            'failed_requests': failed,
            'error_rate': (failed / len(self.response_times)) * 100,
            'avg_response_time': statistics.mean(self.response_times),
            'min_response_time': min(self.response_times),
            'max_response_time': max(self.response_times),
            'median_response_time': statistics.median(self.response_times),
            'p95_response_time': self._percentile(self.response_times, 0.95),
            'p99_response_time': self._percentile(self.response_times, 0.99),
            'requests_per_second': len(self.response_times) / sum(self.response_times),
            'errors': self.errors[:10]
        }
    
    @staticmethod
    def _percentile(data, percentile):
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]


class APILoadTest:
    
    def __init__(self, num_requests=100, num_workers=10):
        self.flask_wrapper = FlaskAppWrapper(__name__, port=5003)
        self.app = self.flask_wrapper.app_
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.num_requests = num_requests
        self.num_workers = num_workers
    
    def _make_request(self, method, endpoint, **kwargs):
        start_time = time.time()
        try:
            if method == 'GET':
                response = self.client.get(endpoint, **kwargs)
            elif method == 'POST':
                response = self.client.post(endpoint, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = time.time()
            return end_time - start_time, response.status_code, None
        except Exception as e:
            end_time = time.time()
            return end_time - start_time, 500, str(e)
    
    def load_test_endpoint(self, method, endpoint, test_name, **kwargs):
        print(f"\n{'='*60}")
        print(f"Load Testing: {test_name}")
        print(f"Endpoint: {method} {endpoint}")
        print(f"Requests: {self.num_requests} | Workers: {self.num_workers}")
        print(f"{'='*60}")
        
        result = LoadTestResult(test_name)
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(self._make_request, method, endpoint, **kwargs)
                for _ in range(self.num_requests)
            ]
            
            for i, future in enumerate(as_completed(futures), 1):
                response_time, status_code, error = future.result()
                result.add_result(response_time, status_code, error)
                
                if i % 10 == 0:
                    print(f"Progress: {i}/{self.num_requests} requests completed")
        
        stats = result.get_stats()
        self._print_stats(stats)
        
        return stats
    
    def _print_stats(self, stats):
        print(f"\n{'-'*60}")
        print(f"Results for: {stats['endpoint']}")
        print(f"{'-'*60}")
        print(f"Total Requests:       {stats['total_requests']}")
        print(f"Successful:           {stats['successful_requests']}")
        print(f"Failed:               {stats['failed_requests']}")
        print(f"Error Rate:           {stats['error_rate']:.2f}%")
        
        if 'avg_response_time' in stats:
            print(f"\nResponse Times (seconds):")
            print(f"  Average:            {stats['avg_response_time']:.4f}")
            print(f"  Median:             {stats['median_response_time']:.4f}")
            print(f"  Min:                {stats['min_response_time']:.4f}")
            print(f"  Max:                {stats['max_response_time']:.4f}")
            print(f"  95th Percentile:    {stats['p95_response_time']:.4f}")
            print(f"  99th Percentile:    {stats['p99_response_time']:.4f}")
            print(f"\nThroughput:           {stats['requests_per_second']:.2f} req/s")
        
        if stats['errors']:
            print(f"\nSample Errors:")
            for error in stats['errors'][:5]:
                print(f"  - {error}")
    
    @patch('user_auth.register_user')
    def test_register_endpoint(self, mock_register):
        mock_register.return_value = (True, '注册成功')
        
        return self.load_test_endpoint(
            'POST',
            '/api/register',
            'User Registration',
            json={'username': 'loadtest_user', 'password': 'testpass123'}
        )
    
    @patch('user_auth.login_user')
    def test_login_endpoint(self, mock_login):
        mock_login.return_value = (True, {'id': 1, 'username': 'testuser'}, '登录成功')
        
        return self.load_test_endpoint(
            'POST',
            '/api/login',
            'User Login',
            json={'username': 'testuser', 'password': 'password123'}
        )
    
    def test_logout_endpoint(self):
        def make_request_with_session():
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'testuser'
            return self._make_request('POST', '/api/logout')
        
        print(f"\n{'='*60}")
        print(f"Load Testing: User Logout")
        print(f"Endpoint: POST /api/logout")
        print(f"Requests: {self.num_requests} | Workers: {self.num_workers}")
        print(f"{'='*60}")
        
        result = LoadTestResult('User Logout')
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(make_request_with_session)
                for _ in range(self.num_requests)
            ]
            
            for i, future in enumerate(as_completed(futures), 1):
                response_time, status_code, error = future.result()
                result.add_result(response_time, status_code, error)
                
                if i % 10 == 0:
                    print(f"Progress: {i}/{self.num_requests} requests completed")
        
        stats = result.get_stats()
        self._print_stats(stats)
        
        return stats
    
    def test_current_user_endpoint(self):
        return self.load_test_endpoint(
            'GET',
            '/api/current_user',
            'Get Current User'
        )
    
    @patch('statistics_db.get_statistics')
    def test_get_history_endpoint(self, mock_get_stats):
        mock_get_stats.return_value = [
            {'session_id': f'test{i}', 'novel_name': f'novel{i}'}
            for i in range(10)
        ]
        
        def make_request_with_session():
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
            return self._make_request('GET', '/api/history')
        
        print(f"\n{'='*60}")
        print(f"Load Testing: Get User History")
        print(f"Endpoint: GET /api/history")
        print(f"Requests: {self.num_requests} | Workers: {self.num_workers}")
        print(f"{'='*60}")
        
        result = LoadTestResult('Get User History')
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(make_request_with_session)
                for _ in range(self.num_requests)
            ]
            
            for i, future in enumerate(as_completed(futures), 1):
                response_time, status_code, error = future.result()
                result.add_result(response_time, status_code, error)
                
                if i % 10 == 0:
                    print(f"Progress: {i}/{self.num_requests} requests completed")
        
        stats = result.get_stats()
        self._print_stats(stats)
        
        return stats
    
    def test_index_page(self):
        return self.load_test_endpoint(
            'GET',
            '/',
            'Index Page'
        )
    
    def test_login_page(self):
        return self.load_test_endpoint(
            'GET',
            '/login',
            'Login Page'
        )
    
    def run_all_tests(self):
        print("\n" + "="*60)
        print("Starting API Load Tests")
        print(f"Configuration: {self.num_requests} requests with {self.num_workers} workers")
        print("="*60)
        
        all_results = []
        
        all_results.append(self.test_index_page())
        all_results.append(self.test_login_page())
        all_results.append(self.test_register_endpoint())
        all_results.append(self.test_login_endpoint())
        all_results.append(self.test_logout_endpoint())
        all_results.append(self.test_current_user_endpoint())
        all_results.append(self.test_get_history_endpoint())
        
        print("\n" + "="*60)
        print("Load Test Summary")
        print("="*60)
        
        for stats in all_results:
            success_rate = (stats['successful_requests'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
            avg_time = stats.get('avg_response_time', 0)
            print(f"{stats['endpoint']:30s} | Success: {success_rate:6.2f}% | Avg Time: {avg_time:.4f}s")
        
        return all_results


def main():
    num_requests = int(os.environ.get('LOAD_TEST_REQUESTS', 100))
    num_workers = int(os.environ.get('LOAD_TEST_WORKERS', 10))
    
    print("\nAPI Load Testing Tool")
    print("="*60)
    print(f"Configuration:")
    print(f"  Requests per endpoint: {num_requests}")
    print(f"  Concurrent workers: {num_workers}")
    print(f"\nSet LOAD_TEST_REQUESTS and LOAD_TEST_WORKERS to customize")
    print("="*60)
    
    load_test = APILoadTest(num_requests=num_requests, num_workers=num_workers)
    results = load_test.run_all_tests()
    
    results_file = 'load_test_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {results_file}")


if __name__ == '__main__':
    main()
