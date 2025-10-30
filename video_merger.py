import os
import logging
from typing import List, Optional
from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip

from common import get_base_dir


class VideoMerger:
    def __init__(self):
        self.temp_dir_ = os.path.join(get_base_dir(), "temp_videos")
        os.makedirs(self.temp_dir_, exist_ok=True)
    
    def merge_scene_videos(self, scene_folders: List[str], output_path: str) -> bool:
        try:
            video_clips = []
            
            for scene_folder in scene_folders:
                video_path = os.path.join(scene_folder, 'scene.mp4')
                
                if os.path.exists(video_path):
                    clip = VideoFileClip(video_path)
                    video_clips.append(clip)
                else:
                    image_path = os.path.join(scene_folder, 'scene.png')
                    audio_path = os.path.join(scene_folder, 'narration.mp3')
                    
                    if os.path.exists(image_path) and os.path.exists(audio_path):
                        clip = self._create_video_from_image_audio(image_path, audio_path)
                        if clip:
                            video_clips.append(clip)
            
            if not video_clips:
                logging.error("没有可合并的视频片段")
                return False
            
            final_video = concatenate_videoclips(video_clips, method="compose")
            
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=24,
                preset='medium',
                threads=4
            )
            
            for clip in video_clips:
                clip.close()
            final_video.close()
            
            logging.info(f"视频合并完成: {output_path}")
            return True
            
        except Exception as e:
            logging.exception(f"视频合并失败: {e}")
            return False
    
    def _create_video_from_image_audio(self, image_path: str, audio_path: str) -> Optional[VideoFileClip]:
        try:
            audio = AudioFileClip(audio_path)
            duration = audio.duration
            
            image_clip = ImageClip(image_path).set_duration(duration)
            
            video_clip = image_clip.set_audio(audio)
            
            return video_clip
            
        except Exception as e:
            logging.exception(f"从图片和音频创建视频失败: {e}")
            return None
    
    def cleanup_temp_files(self):
        try:
            if os.path.exists(self.temp_dir_):
                for file in os.listdir(self.temp_dir_):
                    file_path = os.path.join(self.temp_dir_, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        except Exception as e:
            logging.error(f"清理临时文件失败: {e}")
