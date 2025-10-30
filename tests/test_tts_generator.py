import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tts_generator import TTSGenerator


class TestTTSGenerator(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = TTSGenerator()
        self.generator.cache_dir = self.temp_dir
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_default_language(self):
        gen = TTSGenerator()
        self.assertEqual(gen.language, 'zh-CN')
    
    def test_init_custom_language(self):
        gen = TTSGenerator(language='en')
        self.assertEqual(gen.language, 'en')
    
    def test_init_creates_cache_dir(self):
        temp_cache = os.path.join(self.temp_dir, 'new_cache')
        gen = TTSGenerator()
        gen.cache_dir = temp_cache
        os.makedirs(gen.cache_dir, exist_ok=True)
        
        self.assertTrue(os.path.exists(temp_cache))
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_basic(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        output_file = os.path.join(self.temp_dir, 'test.mp3')
        result = self.generator.generate_speech("测试文本", output_file)
        
        mock_gtts.assert_called_once_with(text="测试文本", lang='zh-CN', slow=False)
        mock_tts_instance.save.assert_called_once_with(output_file)
        self.assertEqual(result, output_file)
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_auto_filename(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        result = self.generator.generate_speech("测试")
        
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('.mp3'))
        self.assertIn('audio_', result)
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_caching(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        output_file = os.path.join(self.temp_dir, 'cached.mp3')
        
        result1 = self.generator.generate_speech("文本", output_file)
        
        with open(output_file, 'w') as f:
            f.write("cached")
        
        result2 = self.generator.generate_speech("文本", output_file)
        
        self.assertEqual(result1, result2)
        mock_gtts.assert_called_once()
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_exception_handling(self, mock_gtts):
        mock_gtts.side_effect = Exception("API Error")
        
        output_file = os.path.join(self.temp_dir, 'error.mp3')
        result = self.generator.generate_speech("文本", output_file)
        
        self.assertIsNone(result)
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_for_scene(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        result = self.generator.generate_speech_for_scene("场景文本", 5)
        
        self.assertIsNotNone(result)
        self.assertIn('scene_0005.mp3', result)
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_empty_text(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        output_file = os.path.join(self.temp_dir, 'empty.mp3')
        result = self.generator.generate_speech("", output_file)
        
        mock_gtts.assert_called_once_with(text="", lang='zh-CN', slow=False)
        self.assertEqual(result, output_file)
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_long_text(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        long_text = "这是一段很长的文本。" * 100
        output_file = os.path.join(self.temp_dir, 'long.mp3')
        result = self.generator.generate_speech(long_text, output_file)
        
        self.assertEqual(result, output_file)
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_special_characters(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        text = "特殊字符：！@#￥%……&*（）"
        output_file = os.path.join(self.temp_dir, 'special.mp3')
        result = self.generator.generate_speech(text, output_file)
        
        self.assertEqual(result, output_file)
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_for_scene_boundary_index(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        result = self.generator.generate_speech_for_scene("文本", 0)
        self.assertIn('scene_0000.mp3', result)
        
        result = self.generator.generate_speech_for_scene("文本", 9999)
        self.assertIn('scene_9999.mp3', result)
    
    def test_cache_dir_exists_after_init(self):
        self.assertTrue(os.path.exists(self.generator.cache_dir))
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_same_text_same_hash(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        result1 = self.generator.generate_speech("相同文本")
        result2 = self.generator.generate_speech("相同文本")
        
        self.assertEqual(result1, result2)
    
    @patch('tts_generator.gTTS')
    def test_generate_speech_different_text_different_hash(self, mock_gtts):
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        
        result1 = self.generator.generate_speech("文本1")
        result2 = self.generator.generate_speech("文本2")
        
        self.assertNotEqual(result1, result2)


if __name__ == '__main__':
    unittest.main()
