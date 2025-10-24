import os
from gtts import gTTS
from typing import Optional
import hashlib


class TTSGenerator:
    def __init__(self, language: str = 'zh-cn'):
        self.language = language
        self.cache_dir = "audio_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def generate_speech(self, text: str, output_filename: Optional[str] = None) -> Optional[str]:
        if not output_filename:
            cache_key = hashlib.md5(text.encode()).hexdigest()
            output_filename = os.path.join(self.cache_dir, f"audio_{cache_key}.mp3")
        
        if os.path.exists(output_filename):
            return output_filename
        
        try:
            tts = gTTS(text=text, lang=self.language, slow=False)
            tts.save(output_filename)
            return output_filename
        except Exception as e:
            print(f"生成语音失败: {e}")
            return None
    
    def generate_speech_for_scene(self, scene_text: str, scene_index: int) -> Optional[str]:
        output_path = os.path.join(self.cache_dir, f"scene_{scene_index:04d}.mp3")
        return self.generate_speech(scene_text, output_path)
