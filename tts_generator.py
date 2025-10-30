import logging
import os
from gtts import gTTS
from typing import Optional, List, Dict
import hashlib
import shutil


class TTSGenerator:
    def __init__(self, session_id='',  language: str = 'zh-CN'):
        self.language = language
        from common import get_base_dir
        
        self.cache_dir_ = os.path.join(get_base_dir(), "audio_cache", session_id)
        os.makedirs(self.cache_dir_, exist_ok=True)
        
        self.tld_map = {
            'male': 'com.au',
            'female': 'co.uk',
            'narrator': 'com',
            'default': 'com'
        }
        
        self.character_voice_mapping = {}
    
    def assign_voice_to_character(self, character_name: str, voice_type: str = 'default'):
        if voice_type not in self.tld_map:
            voice_type = 'default'
        self.character_voice_mapping[character_name] = voice_type
    
    def generate_speech(self, text: str, output_filename: Optional[str] = None, 
                       voice_type: str = 'default', slow: bool = False) -> Optional[str]:
        if not output_filename:
            cache_key = hashlib.md5(f"{text}_{voice_type}".encode()).hexdigest()
            output_filename = os.path.join(self.cache_dir_, f"audio_{cache_key}.mp3")
        
        if os.path.exists(output_filename):
            return output_filename

        if text == '' or text == '\n':
            silent_mp3_path = os.path.join('templates', 'slient_2s.mp3')
            shutil.copy(silent_mp3_path, output_filename)
            logging.error('text is empty, return silent_mp3!')
            return output_filename

        try:
            tld = self.tld_map.get(voice_type, 'com')
            tts = gTTS(text=text, lang=self.language, slow=slow, tld=tld)
            tts.save(output_filename)
            return output_filename
        except Exception as e:
            logging.exception(f"生成语音失败 (voice_type={voice_type}): {e}, text={text}")
            try:
                tts = gTTS(text=text, lang=self.language, slow=slow)
                tts.save(output_filename)
                return output_filename
            except Exception as fallback_e:
                logging.exception(f"降级生成语音也失败: {fallback_e},  text={text}")
                return None
    
    def generate_speech_for_scene(self, scene_text: str, scene_index: int, 
                                  voice_type: str = 'narrator') -> Optional[str]:
        output_path = os.path.join(self.cache_dir_, f"scene_{scene_index:04d}.mp3")
        return self.generate_speech(scene_text, output_path, voice_type=voice_type)
    
    def generate_dialogue_speech(self, character_name: str, dialogue_text: str, 
                                 emotion: str = 'neutral') -> Optional[str]:
        voice_type = self.character_voice_mapping.get(character_name, 'default')
        
        slow = (emotion in ['sad', 'calm'])
        
        cache_key = hashlib.md5(f"{character_name}_{dialogue_text}_{emotion}".encode()).hexdigest()
        output_filename = os.path.join(self.cache_dir_, f"dialogue_{cache_key}.mp3")
        
        return self.generate_speech(dialogue_text, output_filename, voice_type=voice_type, slow=slow)
    
    def generate_multi_voice_scene(self, narration: str, dialogues: List[Dict], scene_index: int) -> Optional[str]:
        audio_segments = []
        
        if narration:
            narration_audio = self.generate_speech(
                narration, 
                voice_type='narrator'
            )
            if narration_audio:
                audio_segments.append(narration_audio)
        
        for dialogue in dialogues:
            character = dialogue.get('character', '')
            text = dialogue.get('text', '')
            emotion = dialogue.get('emotion', 'neutral')
            
            if character and text:
                dialogue_audio = self.generate_dialogue_speech(character, text, emotion)
                if dialogue_audio:
                    audio_segments.append(dialogue_audio)
        
        if not audio_segments:
            return None
        
        if len(audio_segments) == 1:
            output_path = os.path.join(self.cache_dir_, f"scene_{scene_index:04d}.mp3")
            shutil.copy(audio_segments[0], output_path)
            return output_path
        
        try:
            from pydub import AudioSegment
            
            combined = AudioSegment.empty()
            
            for audio_file in audio_segments:
                segment = AudioSegment.from_mp3(audio_file)
                combined += segment
                combined += AudioSegment.silent(duration=500)
            
            output_path = os.path.join(self.cache_dir_, f"scene_{scene_index:04d}.mp3")
            combined.export(output_path, format="mp3")
            
            return output_path
            
        except ImportError:
            logging.exception("警告: pydub未安装，使用简单拼接。安装pydub以获得更好的音频合成效果。")
            
            output_path = os.path.join(self.cache_dir_, f"scene_{scene_index:04d}.mp3")
            shutil.copy(audio_segments[0], output_path)
            return output_path
        except Exception as e:
            logging.exception(f"合成多音轨失败: {e}")
            if audio_segments:
                output_path = os.path.join(self.cache_dir_, f"scene_{scene_index:04d}.mp3")
                shutil.copy(audio_segments[0], output_path)
                return output_path
            return None
