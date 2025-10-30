import os
import logging
from dotenv import load_dotenv
from novel_parser import NovelParser
from novel_analyzer import NovelAnalyzer
from storyboard_generator import StoryboardGenerator
from character_manager import CharacterManager
from image_generator import ImageGenerator
from tts_generator import TTSGenerator
from scene_composer import SceneComposer
from typing import List, Dict
import json
import concurrent.futures
import threading


class AnimeGenerator:
    def __init__(self, openai_api_key: str = None, provider: str = "qiniu", custom_prompt: str = None, use_ai_analysis: bool = True, session_id: str = None):
        load_dotenv()
        
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供 API Key")
        
        self.session_id = session_id
        self.char_mgr = CharacterManager()
        self.image_gen = ImageGenerator(self.api_key, provider=provider, custom_prompt=custom_prompt)
        self.tts_gen = TTSGenerator(session_id=session_id)
        
        
        self.novel_analyzer = None
        self.storyboard_gen = None
        if use_ai_analysis:
            self.novel_analyzer = NovelAnalyzer(self.api_key)
            self.storyboard_gen = StoryboardGenerator(self.api_key)
        
        self.scene_composer = SceneComposer(self.image_gen, self.tts_gen, self.char_mgr, session_id=session_id)
        
        from common import get_base_dir
        
        if session_id:
            self.output_dir = os.path.join(get_base_dir(), str(session_id), "anime_output")
        else:
            self.output_dir = os.path.join(get_base_dir(), "default", "anime_output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.use_ai_analysis = use_ai_analysis

    def _run_scenes_concurrently(self, total, items, worker_fn, progress_callback=None, base=50, ceil=95, stage_label="场景"):
        """
        通用并发执行器：
        - items: list[Any] 输入项
        - worker_fn: (idx, item, per_scene_progress_cb) -> (idx, metadata)
        - total: len(items)
        - progress_callback: (percent, message) -> None
        - base..ceil: 将并发阶段映射到 [base, ceil] 的全局进度区间
        """
        if total == 0:
            return []

        # 共享状态
        lock = threading.Lock()
        completed = 0
        per_scene_progress = [0.0] * total  # 每个场景的内部进度(0~1)
        results = [None] * total

        def update_global_progress():
            avg = sum(per_scene_progress) / total if total > 0 else 1.0
            global_progress = base + int(avg * (ceil - base))
            if progress_callback:
                progress_callback(global_progress, f'正在生成{stage_label}（并发中）{completed}/{total}...')

        def make_scene_progress_cb(idx):
            def _cb(local_ratio_or_percent, message=None):
                if local_ratio_or_percent is None:
                    return
                try:
                    ratio = float(local_ratio_or_percent)
                except Exception:
                    return
                if ratio > 1.0:
                    ratio = max(0.0, min(1.0, ratio / 100.0))
                else:
                    ratio = max(0.0, min(1.0, ratio))
                with lock:
                    per_scene_progress[idx] = ratio
                    update_global_progress()
            return _cb

        if progress_callback:
            progress_callback(base, f'开始并发生成 {total} 个{stage_label}...')

        # 根据资源情况选择线程数；如启用视频生成，调用方可降低 base/ceil 或 max_workers
        max_workers = min(8, max(2, os.cpu_count() or 4))

        def _submit(executor):
            futures = []
            for idx, item in enumerate(items):
                scene_progress_cb = make_scene_progress_cb(idx)
                futures.append(executor.submit(worker_fn, idx, item, scene_progress_cb))
            return futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = _submit(executor)
            for fut in concurrent.futures.as_completed(futures):
                idx, scene_metadata = fut.result()
                with lock:
                    results[idx] = scene_metadata
                    completed += 1
                    # 完成一个后更新一次，全局更及时
                    update_global_progress()

        return results

    def generate_from_novel(self, novel_path: str, 
                          max_scenes: int = None,
                          character_descriptions: Dict[str, str] = None,
                          use_storyboard: bool = True,
                          progress_callback = None) -> Dict:
        with open(novel_path, 'r', encoding='utf-8') as f:
            novel_text = f.read()
        
        all_scenes = []
        scene_index = 0
        
        if self.use_ai_analysis and self.novel_analyzer:
            logging.info("=== 第一阶段：使用 DeepSeek AI 分析小说文本 ===")
            if progress_callback:
                progress_callback(10, '正在使用 AI 分析小说内容...')

            logging.debug(f"novel_text={novel_text}")
            analysis_result = self.novel_analyzer.analyze_novel_in_chunks(novel_text, max_chunks=None)
            
            analyzed_scenes = analysis_result.get('scenes', [])
            analyzed_characters = analysis_result.get('characters', [])
            
            logging.info(f"AI分析完成，识别到 {len(analyzed_scenes)} 个场景，{len(analyzed_characters)} 个角色")
            if progress_callback:
                progress_callback(20, f'分析完成：识别到 {len(analyzed_scenes)} 个场景，{len(analyzed_characters)} 个角色')
            
            logging.info("=== 第二阶段：为主要角色生成详细设计档案 ===")
            character_portraits = {}
            character_designs = {}
            
            total_chars = min(len(analyzed_characters), 10)
            for idx, char_info in enumerate(analyzed_characters[:10]):
                char_name = char_info.get('name', '')
                if not char_name:
                    continue
                
                if progress_callback:
                    char_progress = 20 + int((idx / max(1, total_chars)) * 15)
                    progress_callback(char_progress, f'正在生成角色 "{char_name}" 的设计档案... ({idx+1}/{total_chars})')
                
                logging.info(f"为角色 '{char_name}' 生成设计档案...")
                design = self.novel_analyzer.generate_character_design(char_info)
                character_designs[char_name] = design
                
                self.char_mgr.register_character(
                    char_name,
                    description=char_info.get('personality', ''),
                    appearance={
                        'description': design.get('visual_keywords', char_info.get('appearance', ''))
                    }
                )
                
                logging.info(f"生成角色 '{char_name}' 的立绘...")
                appearance_prompt = design.get('visual_keywords', '') or self.novel_analyzer.generate_character_appearance_prompt(char_info)
                
                portrait_path = self.image_gen.generate_character_image(
                    char_name,
                    appearance_prompt,
                    style="anime"
                )
                
                if portrait_path:
                    character_portraits[char_name] = portrait_path
                    logging.info(f"✓ 角色 '{char_name}' 设计完成")
                else:
                    logging.error(f"✗ 角色 '{char_name}' 立绘生成失败")
            
            logging.info(f"角色设计完成，共生成 {len(character_portraits)} 个角色")
            if progress_callback:
                progress_callback(35, f'角色设计完成：共生成 {len(character_portraits)} 个角色')
            
            if use_storyboard and self.storyboard_gen:
                logging.info("=== 第三阶段：根据情节生成分镜脚本 ===")
                if progress_callback:
                    progress_callback(40, '正在生成分镜脚本...')
                
                storyboard_result = self.storyboard_gen.generate_storyboard_in_chunks(
                    novel_text, 
                    analyzed_characters
                )
                
                storyboard_panels = storyboard_result.get('storyboard', [])
                success_count = storyboard_result.get('success_count', 0)
                failure_count = storyboard_result.get('failure_count', 0)
                logging.info(f"分镜生成完成，共 {len(storyboard_panels)} 个分镜（成功: {success_count}, 失败: {failure_count}）")
                if progress_callback:
                    progress_callback(50, f'分镜生成完成：共 {len(storyboard_panels)} 个分镜（成功: {success_count}, 失败: {failure_count}）')
                
                logging.info("=== 第四阶段：根据分镜生成画面（并发） ===")
                panels_to_process = storyboard_panels
                if max_scenes:
                    panels_to_process = storyboard_panels[:max_scenes]

                total = len(panels_to_process)

                def worker_panel(panel_idx, panel_info, per_scene_cb):
                    logging.info(f"生成分镜 {panel_idx + 1}/{total}...")
                    # 如 SceneComposer 支持内部进度，可传 per_scene_cb 下去
                    scene_metadata = self.scene_composer.create_scene_from_storyboard(
                        scene_index=panel_idx,
                        panel_info=panel_info,
                        character_designs={name: design.get('visual_keywords', '') for name, design in character_designs.items()}
                        # , progress_callback=per_scene_cb  # 若支持请取消注释
                    )
                    # 如未支持内部进度，完成时置为 1.0
                    per_scene_cb(1.0)
                    return (panel_idx, scene_metadata)

                results = self._run_scenes_concurrently(
                    total=total,
                    items=panels_to_process,
                    worker_fn=worker_panel,
                    progress_callback=progress_callback,
                    base=50, ceil=95,
                    stage_label="分镜"
                )

                for item in results:
                    if item is not None:
                        all_scenes.append(item)

            else:
                logging.info("=== 第三阶段：根据场景生成画面（传统模式并发）===")
                scenes_to_process = analyzed_scenes
                if max_scenes:
                    scenes_to_process = analyzed_scenes[:max_scenes]

                total = len(scenes_to_process)

                def worker_scene(scene_idx, scene_info, per_scene_cb):
                    logging.info(f"生成场景 {scene_idx + 1}/{total}...")
                    scene_metadata = self.scene_composer.create_scene_with_ai_analysis(
                        scene_index=scene_idx,
                        scene_info=scene_info,
                        progress_callback=per_scene_cb  # 若支持请取消注释
                    )
                    per_scene_cb(1.0)
                    return (scene_idx, scene_metadata)

                results = self._run_scenes_concurrently(
                    total=total,
                    items=scenes_to_process,
                    worker_fn=worker_scene,
                    progress_callback=progress_callback,
                    base=50, ceil=95,
                    stage_label="场景"
                )

                for item in results:
                    if item is not None:
                        all_scenes.append(item)
        else:
            parser = NovelParser(novel_text)
            chapters = parser.parse()
            
            logging.info(f"解析小说完成，共 {len(chapters)} 章")
            
            characters = self.char_mgr.extract_characters(novel_text)
            logging.info(f"提取到主要角色：{', '.join(characters[:10])}")
            
            for char_name in characters[:10]:
                description = ""
                if character_descriptions and char_name in character_descriptions:
                    description = character_descriptions[char_name]
                
                self.char_mgr.register_character(char_name, description)
            
            # 将每章的段落汇总成一个“场景任务列表”，保持原顺序索引
            tasks = []
            for chapter_idx, chapter in enumerate(chapters):
                paragraphs = chapter['paragraphs']
                for p in paragraphs:
                    tasks.append(p)

            if max_scenes:
                tasks = tasks[:max_scenes]

            total = len(tasks)
            if total > 0 and progress_callback:
                # 进入非 AI 模式的场景生成阶段，把基线设为 50，以对齐 UI 习惯
                progress_callback(50, f'开始并发生成 {total} 个场景...')

            def worker_non_ai(idx, paragraph, per_scene_cb):
                # 非 AI 模式直接使用从段落创建场景的接口
                # 由于 create_scenes_from_paragraphs 是批量方法，我们这里构造单条列表，保持接口复用
                scenes = self.scene_composer.create_scenes_from_paragraphs(
                    [paragraph],
                    start_index=idx
                )
                # 这里 scenes 应该只有一个
                scene_metadata = scenes[0] if scenes else {
                    'scene_index': idx,
                    'folder': '',
                    'characters': []
                }
                per_scene_cb(1.0)
                return (idx, scene_metadata)

            if total > 0:
                results = self._run_scenes_concurrently(
                    total=total,
                    items=tasks,
                    worker_fn=worker_non_ai,
                    progress_callback=progress_callback,
                    base=50, ceil=95,
                    stage_label="场景"
                )
                for item in results:
                    if item is not None:
                        all_scenes.append(item)
        
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
        
        logging.info(f"动漫生成完成！")
        logging.info(f"总场景数：{len(all_scenes)}")
        logging.info(f"输出目录：{self.output_dir}")

        # 收尾把进度推到 100%
        if 'progress_callback' in locals() and progress_callback:
            progress_callback(100, f'生成完成：共 {len(all_scenes)} 个场景')
        
        return metadata
    
    def _save_project_metadata(self, metadata: Dict):
        metadata_path = os.path.join(self.output_dir, "project_metadata.json")
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logging.info(f"项目元数据已保存到：{metadata_path}")


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
    logging.info(f"会话ID：{session_id}")
    
    try:
        generator = AnimeGenerator(openai_api_key=args.api_key, session_id=session_id)
        generator.generate_from_novel(args.novel_path, max_scenes=args.max_scenes)
    except Exception as e:
        logging.exception(f"错误：{e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
