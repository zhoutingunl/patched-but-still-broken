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
        dialogues = scene_info.get('dialogues', [])
        
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
        
        dialogue_images = self._generate_dialogue_images(
            scene_folder,
            dialogues,
            scene_description,
            character_prompts,
            character_seeds
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
            'dialogues': dialogues,
            'dialogue_images': dialogue_images,
            'image_path': output_image,
            'audio_path': output_audio,
            'video_path': output_video,
            'folder': scene_folder
        }
        
        self._save_metadata(scene_folder, metadata)
        
        return metadata
    
    def _generate_dialogue_images(self, scene_folder: str, 
                                   dialogues: List[Dict],
                                   scene_description: str,
                                   character_prompts: List[str],
                                   character_seeds: Dict) -> List[Dict]:
        dialogue_images = []
        
        if not dialogues:
            return dialogue_images
        
        dialogues_folder = os.path.join(scene_folder, "dialogues")
        os.makedirs(dialogues_folder, exist_ok=True)
        
        print(f"  生成 {len(dialogues)} 个对话图片...")
        
        for idx, dialogue in enumerate(dialogues):
            character = dialogue.get('character', '')
            text = dialogue.get('text', '')
            emotion = dialogue.get('emotion', '')
            
            dialogue_prompt = self._build_dialogue_prompt(
                scene_description, 
                character, 
                text, 
                emotion
            )
            
            char_seed = character_seeds.get(character) if character in character_seeds else None
            
            dialogue_image = self.image_gen.generate_scene_image(
                dialogue_prompt,
                characters=[self.char_mgr.get_character_prompt(character)] if self.char_mgr.get_character(character) else [],
                character_seeds={character: char_seed} if char_seed else {}
            )
            
            if dialogue_image:
                output_image = os.path.join(dialogues_folder, f"dialogue_{idx:03d}.png")
                
                self.image_gen.create_text_overlay(
                    dialogue_image,
                    f"{character}: {text}",
                    output_image
                )
                
                dialogue_images.append({
                    'index': idx,
                    'character': character,
                    'text': text,
                    'emotion': emotion,
                    'image_path': output_image
                })
                
                print(f"    ✓ 对话 {idx + 1}/{len(dialogues)} 生成完成: {character}")
            else:
                print(f"    ✗ 对话 {idx + 1}/{len(dialogues)} 生成失败: {character}")
        
        return dialogue_images
    
    def _build_dialogue_prompt(self, scene_description: str, 
                              character: str, 
                              text: str, 
                              emotion: str) -> str:
        prompt_parts = [scene_description]
        
        if character:
            prompt_parts.append(f"角色：{character}")
        
        if emotion:
            prompt_parts.append(f"情绪：{emotion}")
        
        if text:
            text_snippet = text[:100] if len(text) > 100 else text
            prompt_parts.append(f"对话：{text_snippet}")
        
        full_prompt = ", ".join(prompt_parts)
        full_prompt += ", 动漫风格, 对话场景, 角色特写, 表情丰富, 高质量"
        
        return full_prompt
    
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
