import os
from dotenv import load_dotenv
from novel_parser import NovelParser
from novel_analyzer import NovelAnalyzer
from storyboard_generator import StoryboardGenerator
from character_manager import CharacterManager
from image_generator import ImageGenerator
from tts_generator import TTSGenerator
from scene_composer import SceneComposer
from video_generator import VideoGenerator
from typing import List, Dict
import json


class AnimeGenerator:
    def __init__(self, openai_api_key: str = None, provider: str = "qiniu", custom_prompt: str = None, enable_video: bool = False, use_ai_analysis: bool = True, session_id: str = None):
        load_dotenv()
        
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供 API Key")
        
        self.session_id = session_id
        self.char_mgr = CharacterManager()
        self.image_gen = ImageGenerator(self.api_key, provider=provider, custom_prompt=custom_prompt)
        self.tts_gen = TTSGenerator()
        
        self.video_gen = None
        if enable_video:
            self.video_gen = VideoGenerator(self.api_key)
        
        self.novel_analyzer = None
        self.storyboard_gen = None
        if use_ai_analysis:
            self.novel_analyzer = NovelAnalyzer(self.api_key)
            self.storyboard_gen = StoryboardGenerator(self.api_key)
        
        self.scene_composer = SceneComposer(self.image_gen, self.tts_gen, self.char_mgr, self.video_gen, session_id=session_id)
        
        if session_id:
            self.output_dir = os.path.join("anime_output", session_id)
        else:
            self.output_dir = "anime_output"
        os.makedirs(self.output_dir, exist_ok=True)
        self.use_ai_analysis = use_ai_analysis
    
    def generate_from_novel(self, novel_path: str, 
                          max_scenes: int = None,
                          character_descriptions: Dict[str, str] = None,
                          generate_video: bool = False,
                          use_storyboard: bool = True,
                          progress_callback = None) -> Dict:
        with open(novel_path, 'r', encoding='utf-8') as f:
            novel_text = f.read()
        
        all_scenes = []
        scene_index = 0
        
        if self.use_ai_analysis and self.novel_analyzer:
            print("=== 第一阶段：使用 DeepSeek AI 分析小说文本 ===")
            if progress_callback:
                progress_callback(10, '正在使用 AI 分析小说内容...')
            
            analysis_result = self.novel_analyzer.analyze_novel_in_chunks(novel_text, max_chunks=None)
            
            analyzed_scenes = analysis_result.get('scenes', [])
            analyzed_characters = analysis_result.get('characters', [])
            
            print(f"AI分析完成，识别到 {len(analyzed_scenes)} 个场景，{len(analyzed_characters)} 个角色")
            if progress_callback:
                progress_callback(20, f'分析完成：识别到 {len(analyzed_scenes)} 个场景，{len(analyzed_characters)} 个角色')
            
            print("\n=== 第二阶段：为主要角色生成详细设计档案 ===")
            character_portraits = {}
            character_designs = {}
            
            total_chars = min(len(analyzed_characters), 10)
            for idx, char_info in enumerate(analyzed_characters[:10]):
                char_name = char_info.get('name', '')
                if not char_name:
                    continue
                
                if progress_callback:
                    char_progress = 20 + int((idx / total_chars) * 15)
                    progress_callback(char_progress, f'正在生成角色 "{char_name}" 的设计档案... ({idx+1}/{total_chars})')
                
                print(f"为角色 '{char_name}' 生成设计档案...")
                design = self.novel_analyzer.generate_character_design(char_info)
                character_designs[char_name] = design
                
                self.char_mgr.register_character(
                    char_name,
                    description=char_info.get('personality', ''),
                    appearance={
                        'description': design.get('visual_keywords', char_info.get('appearance', ''))
                    }
                )
                
                print(f"生成角色 '{char_name}' 的立绘...")
                appearance_prompt = design.get('visual_keywords', '') or self.novel_analyzer.generate_character_appearance_prompt(char_info)
                
                portrait_path = self.image_gen.generate_character_image(
                    char_name,
                    appearance_prompt,
                    style="anime"
                )
                
                if portrait_path:
                    character_portraits[char_name] = portrait_path
                    print(f"✓ 角色 '{char_name}' 设计完成")
                else:
                    print(f"✗ 角色 '{char_name}' 立绘生成失败")
            
            print(f"\n角色设计完成，共生成 {len(character_portraits)} 个角色")
            if progress_callback:
                progress_callback(35, f'角色设计完成：共生成 {len(character_portraits)} 个角色')
            
            if self.session_id and hasattr(progress_callback, '__self__'):
                from web_app import generation_status
                characters_data = []
                for char_name, portrait_path in character_portraits.items():
                    characters_data.append({
                        'name': char_name,
                        'original_image_path': portrait_path,
                        'image_url': f"/api/file/{portrait_path}",
                        'custom_image_path': None
                    })
                
                generation_status[self.session_id] = {
                    'status': 'waiting_for_character_confirmation',
                    'progress': 35,
                    'message': '角色图片已生成，等待确认',
                    'characters': characters_data,
                    'resume_data': {
                        'generator_state': {
                            'api_key': self.api_key,
                            'provider': self.image_gen.provider if hasattr(self.image_gen, 'provider') else 'qiniu',
                            'custom_prompt': self.image_gen.custom_prompt if hasattr(self.image_gen, 'custom_prompt') else None,
                            'enable_video': self.video_gen is not None,
                            'use_ai_analysis': self.use_ai_analysis
                        },
                        'novel_path': novel_path,
                        'max_scenes': max_scenes,
                        'generate_video': generate_video,
                        'use_storyboard': use_storyboard,
                        'analyzed_scenes': analyzed_scenes,
                        'analyzed_characters': analyzed_characters,
                        'character_designs': character_designs,
                        'char_mgr': self.char_mgr,
                        'novel_analyzer': self.novel_analyzer,
                        'storyboard_gen': self.storyboard_gen,
                        'user_id': None
                    }
                }
                
                print("\n=== 等待用户确认角色图片 ===")
                print("请在 Web 界面查看角色图片，如需替换请上传自定义图片，然后点击继续生成")
                return {
                    'status': 'waiting_for_character_confirmation',
                    'characters': characters_data
                }
            
            if use_storyboard and self.storyboard_gen:
                print("\n=== 第三阶段：根据情节生成分镜脚本 ===")
                if progress_callback:
                    progress_callback(40, '正在生成分镜脚本...')
                
                storyboard_result = self.storyboard_gen.generate_storyboard_in_chunks(
                    novel_text, 
                    analyzed_characters
                )
                
                storyboard_panels = storyboard_result.get('storyboard', [])
                success_count = storyboard_result.get('success_count', 0)
                failure_count = storyboard_result.get('failure_count', 0)
                print(f"分镜生成完成，共 {len(storyboard_panels)} 个分镜（成功: {success_count}, 失败: {failure_count}）")
                if progress_callback:
                    progress_callback(50, f'分镜生成完成：共 {len(storyboard_panels)} 个分镜（成功: {success_count}, 失败: {failure_count}）')
                
                print("\n=== 第四阶段：根据分镜生成画面 ===")
                panels_to_process = storyboard_panels
                
                if max_scenes:
                    panels_to_process = storyboard_panels[:max_scenes]
                
                for panel_idx, panel_info in enumerate(panels_to_process):
                    print(f"\n生成分镜 {panel_idx + 1}/{len(panels_to_process)}...")
                    if progress_callback:
                        scene_progress = 50 + int((panel_idx / len(panels_to_process)) * 45)
                        progress_callback(scene_progress, f'正在生成分镜 {panel_idx + 1}/{len(panels_to_process)}...')
                    
                    scene_metadata = self.scene_composer.create_scene_from_storyboard(
                        scene_index=panel_idx,
                        panel_info=panel_info,
                        character_designs={name: design.get('visual_keywords', '') for name, design in character_designs.items()},
                        generate_video=generate_video
                    )
                    
                    all_scenes.append(scene_metadata)
            else:
                print("\n=== 第三阶段：根据场景生成画面（传统模式）===")
                scenes_to_process = analyzed_scenes
                
                if max_scenes:
                    scenes_to_process = analyzed_scenes[:max_scenes]
                
                for scene_idx, scene_info in enumerate(scenes_to_process):
                    print(f"\n生成场景 {scene_idx + 1}/{len(scenes_to_process)}...")
                    if progress_callback:
                        scene_progress = 50 + int((scene_idx / len(scenes_to_process)) * 45)
                        progress_callback(scene_progress, f'正在生成场景 {scene_idx + 1}/{len(scenes_to_process)}...')
                    
                    scene_metadata = self.scene_composer.create_scene_with_ai_analysis(
                        scene_index=scene_idx,
                        scene_info=scene_info,
                        generate_video=generate_video
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
        
        storyboard_stats = {}
        if use_storyboard and 'success_count' in locals():
            storyboard_stats = {
                'storyboard_success_count': success_count,
                'storyboard_failure_count': failure_count
            }
        
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
                    'characters': s['characters']
                }
                for s in all_scenes
            ],
            **storyboard_stats
        }
        
        self._save_project_metadata(metadata)
        
        print(f"\n动漫生成完成！")
        print(f"总场景数：{len(all_scenes)}")
        print(f"输出目录：{self.output_dir}")
        
        return metadata
    
    def continue_from_characters(self, novel_path: str, max_scenes: int, generate_video: bool, 
                                use_storyboard: bool, character_portraits: Dict[str, str],
                                analyzed_scenes: List, analyzed_characters: List, 
                                character_designs: Dict, progress_callback=None) -> Dict:
        with open(novel_path, 'r', encoding='utf-8') as f:
            novel_text = f.read()
        
        all_scenes = []
        
        print("\n=== 继续生成：从分镜脚本开始 ===")
        
        if use_storyboard and self.storyboard_gen:
            print("\n=== 第三阶段：根据情节生成分镜脚本 ===")
            if progress_callback:
                progress_callback(40, '正在生成分镜脚本...')
            
            storyboard_result = self.storyboard_gen.generate_storyboard_in_chunks(
                novel_text, 
                analyzed_characters
            )
            
            storyboard_panels = storyboard_result.get('storyboard', [])
            success_count = storyboard_result.get('success_count', 0)
            failure_count = storyboard_result.get('failure_count', 0)
            print(f"分镜生成完成，共 {len(storyboard_panels)} 个分镜（成功: {success_count}, 失败: {failure_count}）")
            if progress_callback:
                progress_callback(50, f'分镜生成完成：共 {len(storyboard_panels)} 个分镜（成功: {success_count}, 失败: {failure_count}）')
            
            print("\n=== 第四阶段：根据分镜生成画面 ===")
            panels_to_process = storyboard_panels
            
            if max_scenes:
                panels_to_process = storyboard_panels[:max_scenes]
            
            for panel_idx, panel_info in enumerate(panels_to_process):
                print(f"\n生成分镜 {panel_idx + 1}/{len(panels_to_process)}...")
                if progress_callback:
                    scene_progress = 50 + int((panel_idx / len(panels_to_process)) * 45)
                    progress_callback(scene_progress, f'正在生成分镜 {panel_idx + 1}/{len(panels_to_process)}...')
                
                scene_metadata = self.scene_composer.create_scene_from_storyboard(
                    scene_index=panel_idx,
                    panel_info=panel_info,
                    character_designs={name: design.get('visual_keywords', '') for name, design in character_designs.items()},
                    generate_video=generate_video
                )
                
                all_scenes.append(scene_metadata)
        else:
            print("\n=== 第三阶段：根据场景生成画面（传统模式）===")
            scenes_to_process = analyzed_scenes
            
            if max_scenes:
                scenes_to_process = analyzed_scenes[:max_scenes]
            
            for scene_idx, scene_info in enumerate(scenes_to_process):
                print(f"\n生成场景 {scene_idx + 1}/{len(scenes_to_process)}...")
                if progress_callback:
                    scene_progress = 50 + int((scene_idx / len(scenes_to_process)) * 45)
                    progress_callback(scene_progress, f'正在生成场景 {scene_idx + 1}/{len(scenes_to_process)}...')
                
                scene_metadata = self.scene_composer.create_scene_with_ai_analysis(
                    scene_index=scene_idx,
                    scene_info=scene_info,
                    generate_video=generate_video
                )
                
                all_scenes.append(scene_metadata)
        
        storyboard_stats = {}
        if use_storyboard and 'success_count' in locals():
            storyboard_stats = {
                'storyboard_success_count': success_count,
                'storyboard_failure_count': failure_count
            }
        
        metadata = {
            'novel_path': novel_path,
            'total_scenes': len(all_scenes),
            'characters': [char['name'] for char in self.char_mgr.get_all_characters()],
            'use_ai_analysis': self.use_ai_analysis,
            'character_portraits': character_portraits,
            'scenes': [
                {
                    'scene_index': s['scene_index'],
                    'folder': s['folder'],
                    'characters': s['characters']
                }
                for s in all_scenes
            ],
            **storyboard_stats
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
    import uuid
    
    parser = argparse.ArgumentParser(description='从小说生成动漫（图配文+声音）')
    parser.add_argument('novel_path', help='小说文本文件路径')
    parser.add_argument('--max-scenes', type=int, default=None, 
                       help='最大生成场景数（默认：全部）')
    parser.add_argument('--api-key', default=None, 
                       help='OpenAI API Key（也可通过 .env 文件配置）')
    parser.add_argument('--session-id', default=None,
                       help='会话ID（用于隔离不同生成任务，默认自动生成）')
    
    args = parser.parse_args()
    
    session_id = args.session_id or str(uuid.uuid4())
    print(f"会话ID：{session_id}")
    
    try:
        generator = AnimeGenerator(openai_api_key=args.api_key, session_id=session_id)
        generator.generate_from_novel(args.novel_path, max_scenes=args.max_scenes)
    except Exception as e:
        print(f"错误：{e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
