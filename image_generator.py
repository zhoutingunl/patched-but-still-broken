import os
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from typing import Optional, Dict
import hashlib
import base64


class ImageGenerator:
    def __init__(self, api_key: str, provider: str = "qiniu", custom_prompt: str = None):
        self.provider = provider
        self.custom_prompt = custom_prompt
        self.style_consistency_keywords = "anime style, consistent art style, unified visual style, coherent character design, same clothing, same hairstyle, same face shape, identical environment, consistent background"
        
        if provider == "qiniu":
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://openai.qiniu.com/v1"
            )
        else:
            self.client = OpenAI(api_key=api_key)
            
        self.cache_dir = "image_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def generate_character_image(self, character_name: str, 
                                character_prompt: str,
                                style: str = "anime",
                                seed: int = None) -> Optional[str]:
        cache_key = hashlib.md5(f"{character_name}_{character_prompt}_{self.provider}".encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"char_{cache_key}.png")
        
        if os.path.exists(cache_path):
            return cache_path
        
        if self.custom_prompt:
            full_prompt = f"{self.custom_prompt}, {character_prompt}"
        else:
            full_prompt = f"{self.style_consistency_keywords}, {character_prompt}, high quality, detailed, character reference sheet"
        
        try:
            if self.provider == "qiniu":
                kwargs = {
                    "model": "gemini-2.5-flash-image",
                    "prompt": full_prompt,
                    "size": "1024x1024",
                    "n": 1,
                    "response_format": "b64_json"
                }
                if seed is not None:
                    kwargs["seed"] = seed
                response = self.client.images.generate(**kwargs)
                
                img_data = base64.b64decode(response.data[0].b64_json)
                img = Image.open(BytesIO(img_data))
                img.save(cache_path)
            else:
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=full_prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                
                image_url = response.data[0].url
                img_response = requests.get(image_url)
                img = Image.open(BytesIO(img_response.content))
                img.save(cache_path)
            
            return cache_path
            
        except Exception as e:
            print(f"生成角色图像失败: {e}")
            return None
    
    def generate_scene_image(self, scene_description: str, 
                            characters: list = None,
                            style: str = "anime",
                            character_seeds: dict = None) -> Optional[str]:
        cache_key = hashlib.md5(f"{scene_description}_{self.provider}".encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"scene_{cache_key}.png")
        
        if os.path.exists(cache_path):
            return cache_path
        
        if self.custom_prompt:
            full_prompt = f"{self.custom_prompt}, scene: {scene_description}"
            if characters:
                char_desc = ", ".join(characters)
                full_prompt += f", featuring characters: {char_desc}"
        else:
            full_prompt = f"{self.style_consistency_keywords}, scene: {scene_description}, high quality, detailed background, cinematic lighting"
            if characters:
                char_desc = ", ".join(characters)
                full_prompt += f", featuring characters: {char_desc}"
        
        try:
            if self.provider == "qiniu":
                kwargs = {
                    "model": "gemini-2.5-flash-image",
                    "prompt": full_prompt,
                    "size": "1792x1024",
                    "n": 1,
                    "response_format": "b64_json"
                }
                if character_seeds and characters:
                    for char_name, seed_val in character_seeds.items():
                        if any(char_name in char for char in characters):
                            kwargs["seed"] = seed_val
                            break
                response = self.client.images.generate(**kwargs)
                
                img_data = base64.b64decode(response.data[0].b64_json)
                img = Image.open(BytesIO(img_data))
                img.save(cache_path)
            else:
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=full_prompt,
                    size="1792x1024",
                    quality="standard",
                    n=1,
                )
                
                image_url = response.data[0].url
                img_response = requests.get(image_url)
                img = Image.open(BytesIO(img_response.content))
                img.save(cache_path)
            
            return cache_path
            
        except Exception as e:
            print(f"生成场景图像失败: {e}")
            return None
    
    def generate_storyboard_shot(self, shot_description: str, 
                                 shot_index: int,
                                 characters: list = None,
                                 style: str = "anime",
                                 speaking_character: str = None,
                                 dialogue_text: str = None,
                                 emotion: str = None) -> Optional[str]:
        cache_key = hashlib.md5(f"{shot_description}_{shot_index}_{speaking_character}_{self.provider}".encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"shot_{cache_key}.png")
        
        if os.path.exists(cache_path):
            return cache_path
        
        if self.custom_prompt:
            full_prompt = f"{self.custom_prompt}, {shot_description}"
            if characters:
                char_desc = ", ".join(characters)
                full_prompt += f", featuring characters: {char_desc}"
            if speaking_character:
                emotion_desc = f", {emotion} expression" if emotion else ""
                full_prompt += f", focus on {speaking_character}{emotion_desc}, facial expression emphasis"
        else:
            full_prompt = f"{self.style_consistency_keywords}, {shot_description}, cinematic composition, high quality, detailed"
            if characters:
                char_desc = ", ".join(characters)
                full_prompt += f", featuring characters: {char_desc}"
            if speaking_character:
                emotion_desc = f" with {emotion} expression" if emotion else ""
                full_prompt += f", close-up focus on {speaking_character}{emotion_desc}, character portrait, detailed facial expression, same character design, consistent appearance"
        
        try:
            if self.provider == "qiniu":
                response = self.client.images.generate(
                    model="gemini-2.5-flash-image",
                    prompt=full_prompt,
                    size="1792x1024",
                    n=1,
                    response_format="b64_json"
                )
                
                img_data = base64.b64decode(response.data[0].b64_json)
                img = Image.open(BytesIO(img_data))
                img.save(cache_path)
            else:
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=full_prompt,
                    size="1792x1024",
                    quality="standard",
                    n=1,
                )
                
                image_url = response.data[0].url
                img_response = requests.get(image_url)
                img = Image.open(BytesIO(img_response.content))
                img.save(cache_path)
            
            return cache_path
            
        except Exception as e:
            print(f"生成分镜图像失败: {e}")
            return None
    
    def create_text_overlay(self, image_path: str, text: str, 
                          output_path: str, position: str = "bottom") -> bool:
        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            img_width, img_height = img.size
            
            font = self._load_chinese_font(40)
            
            max_width = img_width - 100
            lines = self._wrap_text(text, font, max_width, draw)
            
            line_height = 50
            total_text_height = len(lines) * line_height + 40
            
            if position == "bottom":
                y_start = img_height - total_text_height - 20
            else:
                y_start = 20
            
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(
                [(0, y_start - 20), (img_width, y_start + total_text_height)],
                fill=(0, 0, 0, 180)
            )
            
            img = Image.alpha_composite(img.convert('RGBA'), overlay)
            draw = ImageDraw.Draw(img)
            
            y = y_start
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (img_width - text_width) // 2
                draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
                y += line_height
            
            img = img.convert('RGB')
            img.save(output_path)
            return True
            
        except Exception as e:
            print(f"添加文字叠加失败: {e}")
            return False
    
    def _load_chinese_font(self, size: int):
        chinese_fonts = [
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/arphic/uming.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        
        for font_path in chinese_fonts:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        
        try:
            return ImageFont.load_default()
        except:
            return None
    
    def _wrap_text(self, text: str, font, max_width: int, draw) -> list:
        lines = []
        current_line = ""
        
        for char in text:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
        
        return lines
