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
        
        storyboard_panels = []
        if generate_storyboard:
            storyboard_panels = self.generate_storyboard_panels(scene_info, scene_folder)
        
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
            'storyboard_panels': storyboard_panels,
            'image_path': output_image,
            'audio_path': output_audio,
            'video_path': output_video,
            'folder': scene_folder
        }
        
        self._save_metadata(scene_folder, metadata)
        
        return metadata
    
    def generate_storyboard_panels(self, scene_info: Dict, scene_folder: str) -> List[Dict]:
        """
        为场景生成连续的漫画分镜
        """
        panels = []
        
        scene_description = scene_info.get('description', '')
        location = scene_info.get('location', '')
        narration = scene_info.get('narration', '')
        dialogues = scene_info.get('dialogues', [])
        characters_in_scene = scene_info.get('characters', [])
        
        panels_folder = os.path.join(scene_folder, "storyboard")
        os.makedirs(panels_folder, exist_ok=True)
        
        character_seeds = {char: self.char_mgr.get_character_seed(char) 
                          for char in characters_in_scene 
                          if self.char_mgr.get_character(char)}
        
        print(f"  生成故事板分镜...")
        
        panel_index = 0
        
        if narration:
            establishing_shot = self._generate_storyboard_panel(
                panel_index,
                panels_folder,
                scene_description,
                "wide shot",
                narration[:200] if len(narration) > 200 else narration,
                characters_in_scene,
                character_seeds
            )
            if establishing_shot:
                panels.append(establishing_shot)
                panel_index += 1
        
        for dialogue in dialogues:
            character = dialogue.get('character', '')
            text = dialogue.get('text', '')
            emotion = dialogue.get('emotion', '')
            
            shot_type = self._determine_shot_type(emotion, text)
            
            dialogue_description = f"{scene_description}, {character}正在说话"
            if emotion:
                dialogue_description += f", 表情{emotion}"
            
            panel = self._generate_storyboard_panel(
                panel_index,
                panels_folder,
                dialogue_description,
                shot_type,
                f"{character}: {text}",
                [character] if character else [],
                {character: character_seeds.get(character)} if character in character_seeds else {}
            )
            
            if panel:
                panels.append(panel)
                panel_index += 1
        
        print(f"  ✓ 生成了 {len(panels)} 个故事板分镜")
        
        return panels
    
    def _determine_shot_type(self, emotion: str, text: str) -> str:
        """
        根据情绪和对话内容决定镜头类型
        """
        emotion_lower = emotion.lower() if emotion else ""
        
        if any(word in emotion_lower for word in ['惊讶', 'surprised', '震惊', 'shocked']):
            return "close-up"
        elif any(word in emotion_lower for word in ['愤怒', 'angry', '生气', '激动']):
            return "close-up"
        elif any(word in emotion_lower for word in ['悲伤', 'sad', '难过', '哭泣']):
            return "medium close-up"
        elif len(text) > 50:
            return "medium shot"
        else:
            return "medium close-up"
    
    def _generate_storyboard_panel(self, panel_index: int, panels_folder: str,
                                   scene_description: str, shot_type: str,
                                   text: str, characters: List[str],
                                   character_seeds: Dict) -> Optional[Dict]:
        """
        生成单个故事板分镜
        """
        shot_descriptions = {
            "wide shot": "全景镜头, 展现整体环境",
            "medium shot": "中景镜头, 半身像",
            "medium close-up": "中特写镜头, 胸部以上",
            "close-up": "特写镜头, 面部表情",
            "extreme close-up": "大特写镜头, 眼睛或细节"
        }
        
        shot_desc = shot_descriptions.get(shot_type, "medium shot")
        
        prompt_parts = [scene_description, shot_desc]
        
        if characters:
            char_list = "、".join(characters)
            prompt_parts.append(f"角色: {char_list}")
        
        character_prompts = []
        for char in characters:
            if self.char_mgr.get_character(char):
                character_prompts.append(self.char_mgr.get_character_prompt(char))
        
        full_prompt = ", ".join(prompt_parts)
        full_prompt += ", 漫画分镜风格, 动态构图, 高质量, 细节丰富"
        
        panel_image = self.image_gen.generate_scene_image(
            full_prompt,
            characters=character_prompts,
            character_seeds=character_seeds
        )
        
        if panel_image:
            output_image = os.path.join(panels_folder, f"panel_{panel_index:03d}.png")
            
            self.image_gen.create_text_overlay(
                panel_image,
                text,
                output_image
            )
            
            return {
                'panel_index': panel_index,
                'shot_type': shot_type,
                'text': text,
                'characters': characters,
                'image_path': output_image
            }
        
        return None
    
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
