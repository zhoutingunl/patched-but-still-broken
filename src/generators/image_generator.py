import os
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from typing import Optional, Dict
import hashlib
import base64


class ImageGenerator:
    def __init__(self, api_key: str, provider: str = "qiniu"):
        self.provider = provider
        
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
                                style: str = "anime") -> Optional[str]:
        cache_key = hashlib.md5(f"{character_name}_{character_prompt}_{self.provider}".encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"char_{cache_key}.png")
        
        if os.path.exists(cache_path):
            return cache_path
        
        full_prompt = f"{style} style, {character_prompt}, high quality, detailed, consistent character design"
        
        try:
            if self.provider == "qiniu":
                response = self.client.images.generate(
                    model="gemini-2.5-flash-image",
                    prompt=full_prompt,
                    size="1024x1024",
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
                            style: str = "anime") -> Optional[str]:
        cache_key = hashlib.md5(f"{scene_description}_{self.provider}".encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"scene_{cache_key}.png")
        
        if os.path.exists(cache_path):
            return cache_path
        
        full_prompt = f"{style} style scene: {scene_description}, high quality, detailed background"
        
        if characters:
            char_desc = ", ".join(characters)
            full_prompt += f", featuring characters: {char_desc}"
        
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
            print(f"生成场景图像失败: {e}")
            return None
    
    def create_text_overlay(self, image_path: str, text: str, 
                          output_path: str, position: str = "bottom") -> bool:
        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            img_width, img_height = img.size
            
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
            except:
                font = ImageFont.load_default()
            
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
