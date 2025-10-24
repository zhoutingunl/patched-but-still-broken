import os
from dotenv import load_dotenv
from src.parsers.novel_parser import NovelParser
from src.managers.character_manager import CharacterManager
from src.generators.image_generator import ImageGenerator
from src.generators.tts_generator import TTSGenerator
from src.core.scene_composer import SceneComposer
from typing import List, Dict
import json


class AnimeGenerator:
    def __init__(self, openai_api_key: str = None, provider: str = "qiniu"):
        load_dotenv()
        
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供 API Key")
        
        self.char_mgr = CharacterManager()
        self.image_gen = ImageGenerator(self.api_key, provider=provider)
        self.tts_gen = TTSGenerator()
        self.scene_composer = SceneComposer(self.image_gen, self.tts_gen, self.char_mgr)
        
        self.output_dir = "anime_output"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_from_novel(self, novel_path: str, 
                          max_scenes: int = None,
                          character_descriptions: Dict[str, str] = None) -> Dict:
        with open(novel_path, 'r', encoding='utf-8') as f:
            novel_text = f.read()
        
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
        
        all_scenes = []
        scene_index = 0
        
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
                start_index=scene_index
            )
            
            all_scenes.extend(scenes)
            scene_index += len(scenes)
        
        metadata = {
            'novel_path': novel_path,
            'total_chapters': len(chapters),
            'total_scenes': len(all_scenes),
            'characters': [char['name'] for char in self.char_mgr.get_all_characters()],
            'scenes': [
                {
                    'scene_index': s['scene_index'],
                    'folder': s['folder'],
                    'characters': s['characters']
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
