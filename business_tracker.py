import os
from typing import Optional
from influxdb_client import Point
from influx_helper import InfluxV2Helper


class BusinessTracker:
    def __init__(self):
        self.enabled = False
        self.influx_helper = None
        
        influx_url = os.getenv('INFLUX_URL', 'http://121.29.19.131:8086')
        influx_org = os.getenv('INFLUX_ORG', 'myorg')
        influx_token = os.getenv('INFLUX_TOKEN', '')
        influx_bucket = os.getenv('INFLUX_BUCKET', 'mybucket')
        influx_rp = os.getenv('INFLUX_RP', 'autogen')
        
        if influx_token and not influx_token.startswith('替换为'):
            try:
                self.influx_helper = InfluxV2Helper(
                    url=influx_url,
                    org=influx_org,
                    token=influx_token,
                    bucket=influx_bucket,
                    rp=influx_rp,
                    connect_timeout=5000.0,
                    read_timeout=30000.0
                )
                self.enabled = True
                print(f"InfluxDB tracking enabled: {influx_url}")
            except Exception as e:
                print(f"Failed to initialize InfluxDB tracking: {e}")
                self.enabled = False
        else:
            print("InfluxDB tracking disabled: INFLUX_TOKEN not configured")
    
    def track_upload(self, task_id: str, username: Optional[str], filename: str, 
                     file_size: int, text_chars: int, client_address: str):
        if not self.enabled:
            return
        
        try:
            point = (Point("novel_upload")
                    .tag("task_id", task_id)
                    .tag("username", username or "anonymous")
                    .tag("client_address", client_address)
                    .field("filename", filename)
                    .field("file_size", file_size)
                    .field("text_chars", text_chars))
            
            self.influx_helper.write_points([point])
            print(f"Tracked upload: {task_id}")
        except Exception as e:
            print(f"Failed to track upload: {e}")
    
    def track_generation_start(self, task_id: str, username: Optional[str], 
                               max_scenes: Optional[int], use_ai_analysis: bool, 
                               use_storyboard: bool, enable_video: bool, provider: str):
        if not self.enabled:
            return
        
        try:
            point = (Point("generation_start")
                    .tag("task_id", task_id)
                    .tag("username", username or "anonymous")
                    .tag("provider", provider)
                    .field("max_scenes", max_scenes or -1)
                    .field("use_ai_analysis", 1 if use_ai_analysis else 0)
                    .field("use_storyboard", 1 if use_storyboard else 0)
                    .field("enable_video", 1 if enable_video else 0))
            
            self.influx_helper.write_points([point])
            print(f"Tracked generation start: {task_id}")
        except Exception as e:
            print(f"Failed to track generation start: {e}")
    
    def track_generation_progress(self, task_id: str, username: Optional[str], 
                                  progress: int, message: str):
        if not self.enabled:
            return
        
        try:
            point = (Point("generation_progress")
                    .tag("task_id", task_id)
                    .tag("username", username or "anonymous")
                    .field("progress", progress)
                    .field("message", message))
            
            self.influx_helper.write_points([point])
        except Exception as e:
            print(f"Failed to track generation progress: {e}")
    
    def track_generation_complete(self, task_id: str, username: Optional[str], 
                                  scene_count: int, content_size: int, 
                                  duration_seconds: float, success: bool):
        if not self.enabled:
            return
        
        try:
            point = (Point("generation_complete")
                    .tag("task_id", task_id)
                    .tag("username", username or "anonymous")
                    .tag("success", "true" if success else "false")
                    .field("scene_count", scene_count)
                    .field("content_size", content_size)
                    .field("duration_seconds", duration_seconds))
            
            self.influx_helper.write_points([point])
            print(f"Tracked generation complete: {task_id} (success={success})")
        except Exception as e:
            print(f"Failed to track generation complete: {e}")
    
    def track_scene_generation(self, task_id: str, scene_index: int, 
                              scene_type: str, has_video: bool):
        if not self.enabled:
            return
        
        try:
            point = (Point("scene_generation")
                    .tag("task_id", task_id)
                    .tag("scene_type", scene_type)
                    .field("scene_index", scene_index)
                    .field("has_video", 1 if has_video else 0))
            
            self.influx_helper.write_points([point])
        except Exception as e:
            print(f"Failed to track scene generation: {e}")
    
    def track_video_generation(self, task_id: str, video_duration: int, 
                              success: bool, error_message: Optional[str] = None):
        if not self.enabled:
            return
        
        try:
            point = (Point("video_generation")
                    .tag("task_id", task_id)
                    .tag("success", "true" if success else "false")
                    .field("video_duration", video_duration)
                    .field("error_message", error_message or ""))
            
            self.influx_helper.write_points([point])
        except Exception as e:
            print(f"Failed to track video generation: {e}")
    
    def track_error(self, task_id: str, username: Optional[str], 
                   error_type: str, error_message: str):
        if not self.enabled:
            return
        
        try:
            point = (Point("generation_error")
                    .tag("task_id", task_id)
                    .tag("username", username or "anonymous")
                    .tag("error_type", error_type)
                    .field("error_message", error_message))
            
            self.influx_helper.write_points([point])
            print(f"Tracked error: {task_id} - {error_type}")
        except Exception as e:
            print(f"Failed to track error: {e}")


_tracker_instance = None

def get_tracker() -> BusinessTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = BusinessTracker()
    return _tracker_instance
