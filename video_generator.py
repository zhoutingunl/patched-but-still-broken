import logging
import os
import requests
import time
import hashlib
from typing import Optional, Dict
import json


class VideoGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openai.qiniu.com/v1"
        from common import get_base_dir
        
        self.cache_dir = os.path.join(get_base_dir(), "video_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def generate_video(self, 
                      prompt: str,
                      image_path: Optional[str] = None,
                      duration: int = 8,
                      aspect_ratio: str = "16:9",
                      default_keywords: str = None,
                      max_retries: int = 10) -> Optional[str]:
        if default_keywords:
            full_prompt = f"{prompt}, {default_keywords}"
        else:
            full_prompt = f"{prompt}, 动漫角色统一，声音与剧情匹配，每帧切换时，角色风格保持连贯，有流畅的过渡动画"
        
        cache_key = hashlib.md5(f"{full_prompt}_{aspect_ratio}".encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"video_{cache_key}.mp4")
        
        if os.path.exists(cache_path):
            logging.info(f"使用缓存的视频: {cache_path}")
            return cache_path
        
        for attempt in range(max_retries):
            try:
                logging.info(f"尝试生成视频 (第 {attempt + 1}/{max_retries} 次)...")
                task_id = self._create_video_task(full_prompt, image_path, duration, aspect_ratio)
                
                if not task_id:
                    logging.info(f"创建视频任务失败 (第 {attempt + 1}/{max_retries} 次)")
                    if attempt < max_retries - 1:
                        logging.warning(f"将在 5 秒后重试...")
                        time.sleep(5)
                        continue
                    return None
                
                logging.info(f"视频生成任务已创建，任务ID: {task_id}")
                logging.info("等待视频生成完成...")
                
                video_url = self._wait_for_completion(task_id)
                
                if not video_url:
                    logging.warning(f"视频生成失败 (第 {attempt + 1}/{max_retries} 次)")
                    if attempt < max_retries - 1:
                        logging.warning(f"将在 5 秒后重试...")
                        time.sleep(5)
                        continue
                    return None
                
                logging.info(f"视频生成完成，正在下载...")
                download_success = self._download_video(video_url, cache_path)
                
                if download_success:
                    logging.info(f"视频下载成功 (第 {attempt + 1}/{max_retries} 次尝试)")
                    return cache_path
                else:
                    logging.warning(f"视频下载失败 (第 {attempt + 1}/{max_retries} 次)")
                    if attempt < max_retries - 1:
                        logging.warning(f"将在 5 秒后重试...")
                        time.sleep(5)
                        continue
                    return None
                
            except Exception as e:
                logging.exception(f"生成视频失败 (第 {attempt + 1}/{max_retries} 次): {e}")
                if attempt < max_retries - 1:
                    logging.warning(f"将在 5 秒后重试...")
                    time.sleep(5)
                    continue
                return None
        
        return None
    
    def _create_video_task(self, prompt: str, image_path: Optional[str], 
                          duration: int, aspect_ratio: str) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        instances = [{"prompt": prompt}]
        
        payload = {
            "instances": instances,
            "parameters": {
                "durationSeconds": duration,
                "sampleCount": 1,
                "aspectRatio": aspect_ratio,
                "generateAudio": True,
                "personGeneration": "allow_adult"
            },
            "model": "veo-3.1-fast-generate-preview"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/videos/generations",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get("id")
            
        except Exception as e:
            logging.exception(f"创建视频任务失败: {e}")
            return None
    
    def _wait_for_completion(self, task_id: str, max_wait: int = 600, 
                           poll_interval: int = 10) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.base_url}/videos/generations/{task_id}",
                    headers=headers,
                    timeout=30
                )
                
                response.raise_for_status()
                result = response.json()
                
                status = result.get("status")
                logging.info(f"当前状态: {status}")
                
                if status == "Completed":
                    data = result.get("data", {})
                    videos = data.get("videos", [])
                    if videos and len(videos) > 0:
                        return videos[0].get("url")
                    else:
                        logging.error("未找到生成的视频")
                        return None
                
                elif status in ["Failed", "Rejected"]:
                    logging.error(f"视频生成失败: {status}")
                    return None
                
                time.sleep(poll_interval)
                
            except Exception as e:
                logging.exception(f"查询任务状态失败: {e}")
                time.sleep(poll_interval)
        
        logging.error("等待超时")
        return None
    
    def _download_video(self, video_url: str, output_path: str) -> bool:
        try:
            response = requests.get(video_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logging.info(f"视频已保存到: {output_path}")
            return True
            
        except Exception as e:
            logging.exception(f"下载视频失败: {e}")
            return False
    
    def generate_video_from_scenes(self, scenes: list, 
                                   default_keywords: str = None) -> Optional[str]:
        if not scenes:
            return None
        
        combined_prompt = " ".join([s.get('text', '') for s in scenes[:3]])
        
        first_scene_image = None
        if scenes and 'image_path' in scenes[0]:
            first_scene_image = scenes[0]['image_path']
        
        return self.generate_video(
            prompt=combined_prompt,
            image_path=first_scene_image,
            default_keywords=default_keywords
        )
