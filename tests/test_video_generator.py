import unittest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from video_generator import VideoGenerator


class TestVideoGenerator(unittest.TestCase):
    
    def setUp(self):
        self.api_key = "test_api_key"
    
    @patch('video_generator.os.makedirs')
    def test_init(self, mock_makedirs):
        generator = VideoGenerator(self.api_key)
        
        self.assertEqual(generator.api_key, self.api_key)
        self.assertEqual(generator.base_url, "https://openai.qiniu.com/v1")
        self.assertEqual(generator.base_image_url, "http://localhost")
        mock_makedirs.assert_called_once_with(generator.cache_dir, exist_ok=True)
    
    @patch('video_generator.os.makedirs')
    def test_init_with_custom_base_url(self, mock_makedirs):
        generator = VideoGenerator(self.api_key, base_image_url="https://example.com")
        
        self.assertEqual(generator.base_image_url, "https://example.com")
        mock_makedirs.assert_called_once_with(generator.cache_dir, exist_ok=True)
    
    @patch('video_generator.os.path.exists', return_value=True)
    @patch('video_generator.os.makedirs')
    def test_generate_video_from_cache(self, mock_makedirs, mock_exists):
        generator = VideoGenerator(self.api_key)
        
        result = generator.generate_video("测试提示")
        
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith(generator.cache_dir))
    
    @patch('video_generator.os.path.exists', return_value=False)
    @patch('video_generator.requests.post')
    @patch('video_generator.os.makedirs')
    def test_create_video_task_success(self, mock_makedirs, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "task_123"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        generator = VideoGenerator(self.api_key)
        task_id = generator._create_video_task("测试提示", None, 8, "16:9")
        
        self.assertEqual(task_id, "task_123")
        mock_post.assert_called_once()
    
    @patch('video_generator.os.path.abspath', return_value="/absolute/path/to/image.png")
    @patch('video_generator.os.path.exists', return_value=False)
    @patch('video_generator.requests.post')
    @patch('video_generator.os.makedirs')
    def test_create_video_task_with_image(self, mock_makedirs, mock_post, mock_exists, mock_abspath):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "task_456"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        generator = VideoGenerator(self.api_key, base_image_url="http://example.com")
        task_id = generator._create_video_task("测试提示", "/path/to/image.png", 8, "16:9")
        
        self.assertEqual(task_id, "task_456")
        mock_post.assert_called_once()
        
        call_args = mock_post.call_args
        payload = call_args.kwargs['json']
        
        self.assertIn('instances', payload)
        self.assertEqual(len(payload['instances']), 1)
        instance = payload['instances'][0]
        
        self.assertIn('image', instance)
        self.assertEqual(instance['image']['uri'], "http://example.com/api/file//absolute/path/to/image.png")
        self.assertEqual(instance['image']['mimeType'], "image/png")
    
    @patch('video_generator.requests.post', side_effect=Exception("API Error"))
    @patch('video_generator.os.makedirs')
    def test_create_video_task_exception(self, mock_makedirs, mock_post):
        generator = VideoGenerator(self.api_key)
        task_id = generator._create_video_task("测试", None, 8, "16:9")
        
        self.assertIsNone(task_id)
    
    @patch('video_generator.requests.get')
    @patch('video_generator.time.sleep')
    @patch('video_generator.os.makedirs')
    def test_wait_for_completion_success(self, mock_makedirs, mock_sleep, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "Completed",
            "data": {
                "videos": [{"url": "http://example.com/video.mp4"}]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        generator = VideoGenerator(self.api_key)
        video_url = generator._wait_for_completion("task_123")
        
        self.assertEqual(video_url, "http://example.com/video.mp4")
    
    @patch('video_generator.requests.get')
    @patch('video_generator.time.sleep')
    @patch('video_generator.os.makedirs')
    def test_wait_for_completion_failed(self, mock_makedirs, mock_sleep, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "Failed"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        generator = VideoGenerator(self.api_key)
        video_url = generator._wait_for_completion("task_123")
        
        self.assertIsNone(video_url)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('video_generator.requests.get')
    @patch('video_generator.os.makedirs')
    def test_download_video_success(self, mock_makedirs, mock_get, mock_file):
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b'chunk1', b'chunk2']
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        generator = VideoGenerator(self.api_key)
        result = generator._download_video("http://example.com/video.mp4", "/path/output.mp4")
        
        self.assertTrue(result)
        mock_file.assert_called_once_with("/path/output.mp4", 'wb')
    
    @patch('video_generator.requests.get', side_effect=Exception("Download error"))
    @patch('video_generator.os.makedirs')
    def test_download_video_exception(self, mock_makedirs, mock_get):
        generator = VideoGenerator(self.api_key)
        result = generator._download_video("http://example.com/video.mp4", "/path/output.mp4")
        
        self.assertFalse(result)
    
    @patch('video_generator.os.makedirs')
    def test_convert_path_to_uri_http(self, mock_makedirs):
        generator = VideoGenerator(self.api_key, base_image_url="http://example.com")
        uri = generator._convert_path_to_uri("http://already.a.url/image.png")
        
        self.assertEqual(uri, "http://already.a.url/image.png")
    
    @patch('video_generator.os.path.abspath', return_value="/absolute/path/to/image.png")
    @patch('video_generator.os.makedirs')
    def test_convert_path_to_uri_local(self, mock_makedirs, mock_abspath):
        generator = VideoGenerator(self.api_key, base_image_url="http://example.com")
        uri = generator._convert_path_to_uri("/some/local/path/image.png")
        
        self.assertEqual(uri, "http://example.com/api/file//absolute/path/to/image.png")
    
    @patch('video_generator.os.makedirs')
    def test_get_mime_type(self, mock_makedirs):
        generator = VideoGenerator(self.api_key)
        
        self.assertEqual(generator._get_mime_type("image.jpg"), "image/jpeg")
        self.assertEqual(generator._get_mime_type("image.jpeg"), "image/jpeg")
        self.assertEqual(generator._get_mime_type("image.png"), "image/png")
        self.assertEqual(generator._get_mime_type("image.gif"), "image/gif")
        self.assertEqual(generator._get_mime_type("image.webp"), "image/webp")
        self.assertEqual(generator._get_mime_type("image.unknown"), "image/jpeg")
    
    @patch('video_generator.os.makedirs')
    def test_generate_video_from_scenes_empty(self, mock_makedirs):
        generator = VideoGenerator(self.api_key)
        result = generator.generate_video_from_scenes([])
        
        self.assertIsNone(result)
    
    @patch.object(VideoGenerator, 'generate_video')
    @patch('video_generator.os.makedirs')
    def test_generate_video_from_scenes_success(self, mock_makedirs, mock_gen_video):
        mock_gen_video.return_value = "/path/to/video.mp4"
        
        generator = VideoGenerator(self.api_key)
        scenes = [
            {'text': '场景1', 'image_path': '/path/to/image1.png'},
            {'text': '场景2', 'image_path': '/path/to/image2.png'}
        ]
        result = generator.generate_video_from_scenes(scenes)
        
        self.assertIsNotNone(result)
        mock_gen_video.assert_called_once()


if __name__ == '__main__':
    unittest.main()
