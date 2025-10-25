import os
from dotenv import load_dotenv
from novel_parser import NovelParser
from novel_analyzer import NovelAnalyzer
from character_manager import CharacterManager
from image_generator import ImageGenerator
from tts_generator import TTSGenerator
from scene_composer import SceneComposer
from video_generator import VideoGenerator
from typing import List, Dict
import json


class AnimeGenerator:
    def __init__(self, openai_api_key: str = None, provider: str = "qiniu", custom_prompt: str = None, enable_video: bool = False, use_ai_analysis: bool = True):
        load_dotenv()
        
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供 API Key")
        
        self.char_mgr = CharacterManager()
        self.image_gen = ImageGenerator(self.api_key, provider=provider, custom_prompt=custom_prompt)
        self.tts_gen = TTSGenerator()
        
        self.video_gen = None
        if enable_video:
            self.video_gen = VideoGenerator(self.api_key)
        
        self.novel_analyzer = None
        if use_ai_analysis:
            self.novel_analyzer = NovelAnalyzer(self.api_key)
        
        self.scene_composer = SceneComposer(self.image_gen, self.tts_gen, self.char_mgr, self.video_gen)
        
        self.output_dir = "anime_output"
        os.makedirs(self.output_dir, exist_ok=True)
        self.use_ai_analysis = use_ai_analysis
    
    def generate_from_novel(self, novel_path: str, 
                          max_scenes: int = None,
                          character_descriptions: Dict[str, str] = None,
                          generate_video: bool = False,
                          generate_storyboard: bool = True) -> Dict:
        with open(novel_path, 'r', encoding='utf-8') as f:
            novel_text = f.read()
        
        all_scenes = []
        scene_index = 0
        
        if self.use_ai_analysis and self.novel_analyzer:
            print("=== 第一阶段：使用 DeepSeek AI 分析小说文本 ===")
            max_chunks = None
            if max_scenes:
                max_chunks = (max_scenes + 2) // 3
            
            analysis_result = self.novel_analyzer.analyze_novel_in_chunks(novel_text, max_chunks=max_chunks)
            
            analyzed_scenes = analysis_result.get('scenes', [])
            analyzed_characters = analysis_result.get('characters', [])
            
            print(f"AI分析完成，识别到 {len(analyzed_scenes)} 个场景，{len(analyzed_characters)} 个角色")
            
            print("\n=== 第二阶段：为每个角色生成稳定的外观和角色立绘 ===")
            character_portraits = {}
            
            for char_info in analyzed_characters[:10]:
                char_name = char_info.get('name', '')
                if not char_name:
                    continue
                
                self.char_mgr.register_character(
                    char_name,
                    description=char_info.get('personality', ''),
                    appearance={
                        'description': char_info.get('appearance', '')
                    }
                )
                
                print(f"生成角色 '{char_name}' 的立绘...")
                appearance_prompt = self.novel_analyzer.generate_character_appearance_prompt(char_info)
                
                char_seed = self.char_mgr.get_character_seed(char_name)
                portrait_path = self.image_gen.generate_character_image(
                    char_name,
                    appearance_prompt,
                    style="anime",
                    seed=char_seed
                )
                
                if portrait_path:
                    character_portraits[char_name] = portrait_path
                    print(f"✓ 角色 '{char_name}' 立绘生成完成")
                else:
                    print(f"✗ 角色 '{char_name}' 立绘生成失败")
            
            print(f"\n角色立绘生成完成，共生成 {len(character_portraits)} 个角色立绘")
            
            print("\n=== 第三阶段：根据剧情生成对应的画面 ===")
            scenes_to_process = analyzed_scenes
            
            if max_scenes:
                scenes_to_process = analyzed_scenes[:max_scenes]
            
            for scene_idx, scene_info in enumerate(scenes_to_process):
                print(f"\n生成场景 {scene_idx + 1}/{len(scenes_to_process)}...")
                
                scene_metadata = self.scene_composer.create_scene_with_ai_analysis(
                    scene_index=scene_idx,
                    scene_info=scene_info,
                    generate_video=generate_video,
                    generate_storyboard=generate_storyboard
                )
                
                all_scenes.append(scene_metadata)
        else:
            parser = NovelParser(novel_text)
            chapters = parser.parse()
            
            print(f"解析小说完成，共 {len(chapters)} 章")
            
            characters = self.char_mgr.extract_characters(novel_text)
            print(f"提取到主要角色：{', '.join(characters[:10])}")
            
            for char_name in characters[:10]:
                description = ""
                if character_descriptions and char_name in character_descriptions:
                    description = character_descriptions[char_name]
                
                self.char_mgr.register_character(char_name, description)
            
            for chapter_idx, chapter in enumerate(chapters):
                print(f"\n处理章节 {chapter_idx + 1}/{len(chapters)}: {chapter['title']}")
                
                paragraphs = chapter['paragraphs']
                
                if max_scenes and scene_index >= max_scenes:
                    print(f"已达到最大场景数 {max_scenes}，停止生成")
                    break
                
                scenes_to_create = paragraphs
                if max_scenes:
                    remaining = max_scenes - scene_index
                    scenes_to_create = paragraphs[:remaining]
                
                scenes = self.scene_composer.create_scenes_from_paragraphs(
                    scenes_to_create,
                    start_index=scene_index,
                    generate_video=generate_video
                )
                
                all_scenes.extend(scenes)
                scene_index += len(scenes)
        
        character_portraits_data = {}
        if self.use_ai_analysis and self.novel_analyzer and 'character_portraits' in locals():
            character_portraits_data = character_portraits
        
        metadata = {
            'novel_path': novel_path,
            'total_scenes': len(all_scenes),
            'characters': [char['name'] for char in self.char_mgr.get_all_characters()],
            'use_ai_analysis': self.use_ai_analysis,
            'character_portraits': character_portraits_data,
            'scenes': [
                {
                    'scene_index': s['scene_index'],
                    'folder': s['folder'],
                    'characters': s['characters'],
                    'storyboard_shots': s.get('storyboard_shots', [])
                }
                for s in all_scenes
            ]
        }
        
        self._save_project_metadata(metadata)
        
        print(f"\n动漫生成完成！")
        print(f"总场景数：{len(all_scenes)}")
        print(f"输出目录：{self.output_dir}")
        
        return metadata
    
    def _save_project_metadata(self, metadata: Dict):
        metadata_path = os.path.join(self.output_dir, "project_metadata.json")
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"项目元数据已保存到：{metadata_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='从小说生成动漫（图配文+声音）')
    parser.add_argument('novel_path', help='小说文本文件路径')
    parser.add_argument('--max-scenes', type=int, default=None, 
                       help='最大生成场景数（默认：全部）')
    parser.add_argument('--api-key', default=None, 
                       help='OpenAI API Key（也可通过 .env 文件配置）')
    
    args = parser.parse_args()
    
    try:
        generator = AnimeGenerator(openai_api_key=args.api_key)
        generator.generate_from_novel(args.novel_path, max_scenes=args.max_scenes)
    except Exception as e:
        print(f"错误：{e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
