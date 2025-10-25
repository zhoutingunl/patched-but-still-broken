import os
from typing import List, Dict, Optional
from image_generator import ImageGenerator
from tts_generator import TTSGenerator
from character_manager import CharacterManager
import re


class SceneComposer:
    def __init__(self, image_generator: ImageGenerator, 
                 tts_generator: TTSGenerator,
                 character_manager: CharacterManager,
                 video_generator = None):
        self.image_gen = image_generator
        self.tts_gen = tts_generator
        self.char_mgr = character_manager
        self.video_gen = video_generator
        self.output_dir = "output_scenes"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def create_scene(self, scene_index: int, scene_text: str, 
                    scene_description: Optional[str] = None,
                    generate_video: bool = False) -> Dict:
        scene_folder = os.path.join(self.output_dir, f"scene_{scene_index:04d}")
        os.makedirs(scene_folder, exist_ok=True)
        
        characters_in_scene = self._extract_characters_from_text(scene_text)
        
        if not scene_description:
            scene_description = self._generate_scene_description(scene_text, characters_in_scene)
        
        character_prompts = [self.char_mgr.get_character_prompt(char) 
                           for char in characters_in_scene 
                           if self.char_mgr.get_character(char)]
        
        character_seeds = {char: self.char_mgr.get_character_seed(char) 
                          for char in characters_in_scene 
                          if self.char_mgr.get_character(char)}
        
        for char in characters_in_scene:
            if self.char_mgr.get_character(char):
                self.char_mgr.increment_appearance_count(char)
        
        scene_image = self.image_gen.generate_scene_image(
            scene_description,
            characters=character_prompts,
            character_seeds=character_seeds
        )
        
        if scene_image:
            output_image = os.path.join(scene_folder, "scene.png")
            
            self.image_gen.create_text_overlay(
                scene_image,
                scene_text,
                output_image
            )
        else:
            output_image = None
        
        audio_file = self.tts_gen.generate_speech_for_scene(scene_text, scene_index)
        
        if audio_file:
            output_audio = os.path.join(scene_folder, "narration.mp3")
            if audio_file != output_audio:
                import shutil
                shutil.copy(audio_file, output_audio)
        else:
            output_audio = None
        
        output_video = None
        if generate_video and self.video_gen and scene_image:
            video_file = self.video_gen.generate_video(
                prompt=scene_description,
                image_path=scene_image
            )
            if video_file:
                output_video = os.path.join(scene_folder, "scene.mp4")
                if video_file != output_video:
                    import shutil
                    shutil.copy(video_file, output_video)
        
        metadata = {
            'scene_index': scene_index,
            'text': scene_text,
            'description': scene_description,
            'characters': characters_in_scene,
            'image_path': output_image,
            'audio_path': output_audio,
            'video_path': output_video,
            'folder': scene_folder
        }
        
        self._save_metadata(scene_folder, metadata)
        
        return metadata
    
    def _extract_characters_from_text(self, text: str) -> List[str]:
        all_characters = self.char_mgr.get_all_characters()
        found_characters = []
        
        for char in all_characters:
            if char['name'] in text:
                found_characters.append(char['name'])
        
        return found_characters
    
    def _generate_scene_description(self, text: str, characters: List[str]) -> str:
        text_snippet = text[:500] if len(text) > 500 else text
        
        char_list = "、".join(characters) if characters else "人物"
        
        description = f"场景中有{char_list}，{text_snippet}"
        
        return description
    
    def _save_metadata(self, folder: str, metadata: Dict):
        import json
        metadata_path = os.path.join(folder, "metadata.json")
        
        serializable_metadata = {
            'scene_index': metadata['scene_index'],
            'text': metadata['text'],
            'description': metadata['description'],
            'characters': metadata['characters'],
            'image_path': metadata.get('image_path'),
            'audio_path': metadata.get('audio_path'),
            'video_path': metadata.get('video_path')
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_metadata, f, ensure_ascii=False, indent=2)
    
    def create_scene_with_ai_analysis(self, scene_index: int, 
                                     scene_info: Dict,
                                     generate_video: bool = False,
                                     generate_storyboard: bool = True) -> Dict:
        scene_folder = os.path.join(self.output_dir, f"scene_{scene_index:04d}")
        os.makedirs(scene_folder, exist_ok=True)
        
        scene_text = scene_info.get('narration', '')
        scene_description = scene_info.get('description', '')
        characters_in_scene = scene_info.get('characters', [])
        
        character_prompts = []
        for char in characters_in_scene:
            if self.char_mgr.get_character(char):
                character_prompts.append(self.char_mgr.get_character_prompt(char))
        
        character_seeds = {char: self.char_mgr.get_character_seed(char) 
                          for char in characters_in_scene 
                          if self.char_mgr.get_character(char)}
        
        for char in characters_in_scene:
            if self.char_mgr.get_character(char):
                self.char_mgr.increment_appearance_count(char)
        
        scene_image = self.image_gen.generate_scene_image(
            scene_description,
            characters=character_prompts,
            character_seeds=character_seeds
        )
        
        output_image = None
        if scene_image:
            output_image = os.path.join(scene_folder, "scene.png")
            
            self.image_gen.create_text_overlay(
                scene_image,
                scene_text,
                output_image
            )
        
        audio_file = self.tts_gen.generate_speech_for_scene(scene_text, scene_index)
        
        if audio_file:
            output_audio = os.path.join(scene_folder, "narration.mp3")
            if audio_file != output_audio:
                import shutil
                shutil.copy(audio_file, output_audio)
        else:
            output_audio = None
        
        output_video = None
        if generate_video and self.video_gen and scene_image:
            video_file = self.video_gen.generate_video(
                prompt=scene_description,
                image_path=scene_image
            )
            if video_file:
                output_video = os.path.join(scene_folder, "scene.mp4")
                if video_file != output_video:
                    import shutil
                    shutil.copy(video_file, output_video)
        
        metadata = {
            'scene_index': scene_index,
            'text': scene_text,
            'description': scene_description,
            'characters': characters_in_scene,
            'image_path': output_image,
            'audio_path': output_audio,
            'video_path': output_video,
            'folder': scene_folder
        }
        
        self._save_metadata(scene_folder, metadata)
        
        return metadata
    
    def create_scenes_from_paragraphs(self, paragraphs: List[str], 
                                     start_index: int = 0,
                                     generate_video: bool = False) -> List[Dict]:
        scenes = []
        
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
            
            print(f"创建场景 {start_index + i + 1}/{start_index + len(paragraphs)}...")
            
            scene = self.create_scene(start_index + i, paragraph, generate_video=generate_video)
            scenes.append(scene)
        
        return scenes
