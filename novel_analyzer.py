import logging

from openai import OpenAI
from typing import Dict, List
import json


class NovelAnalyzer:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openai.qiniu.com/v1"
        )
        self.model = "deepseek/deepseek-v3.1-terminus"
    
    def analyze_novel_text(self, text: str) -> Dict:
        system_prompt = """你是一个专业的小说分析助手。请分析输入的小说文本，提取以下信息：
1. 场景(Scene)：识别文本中的不同场景，包括场景描述、地点、时间等
2. 人物(Characters)：识别所有出现的人物，包括主要角色和次要角色，提取人物的外貌、性格特征
3. 对话(Dialogues)：提取人物之间的对话内容，包括说话者的情绪状态
4. 叙述(Narration)：提取旁白和描述性文本

请以JSON格式返回结果，格式如下：
{
  "scenes": [
    {
      "scene_number": 1,
      "description": "场景描述",
      "location": "地点",
      "time": "时间",
      "characters": ["出现的角色"],
      "narration": "场景叙述文本",
      "dialogues": [
        {"character": "角色名", "text": "对话内容", "emotion": "情绪状态"}
      ]
    }
  ],
  "characters": [
    {
      "name": "角色名",
      "appearance": "外貌描述",
      "personality": "性格特征",
      "role": "主要角色/次要角色"
    }
  ]
}

重要规则：
1. 场景描述应该详细，包含环境、氛围、人物位置等信息
2. 确保场景描述包含统一的画风关键词(如：anime style, consistent art style)
3. **角色一致性要求**：同一场景中角色的服饰、发型、脸型必须完全一致
4. **情绪表达**：对话的emotion字段必须详细描述情绪（如：happy/开心, sad/悲伤, angry/愤怒, surprised/惊讶, worried/担忧等）"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请分析以下小说文本：\n\n{text}"}
                ],
                temperature=0.7,
                max_tokens=8000
            )
            
            result_text = response.choices[0].message.content
            
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                result = self._parse_fallback(result_text)
            
            return result
            
        except Exception as e:
            logging.exception(f"AI分析失败: {e}")
            return self._create_empty_result()
    
    def generate_character_design(self, character_info: Dict) -> Dict:
        name = character_info.get('name', '')
        appearance = character_info.get('appearance', '')
        personality = character_info.get('personality', '')
        
        system_prompt = """你是一个专业的角色设计师。请根据角色信息生成详细的角色设计档案。

请以JSON格式返回，包含以下信息：
{
  "name": "角色名",
  "appearance": {
    "face": "面部特征（脸型、五官）",
    "hair": "发型和发色",
    "eyes": "眼睛颜色和特征",
    "body": "身材特征",
    "clothing": "服装风格和颜色",
    "accessories": "配饰或特殊标记"
  },
  "personality_traits": ["性格特征1", "性格特征2"],
  "visual_keywords": "用于AI绘图的关键词组合"
}

重要：visual_keywords应该包含所有外貌细节，确保角色在所有场景中保持一致。"""

        try:
            char_desc = f"角色名: {name}\n外貌: {appearance}\n性格: {personality}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请为以下角色生成详细设计档案：\n\n{char_desc}"}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content
            
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            design = json.loads(result_text)
            return design
            
        except Exception as e:
            logging.exception(f"角色设计生成失败: {e}")
            return self._create_fallback_design(name, appearance, personality)
    
    def _create_fallback_design(self, name: str, appearance: str, personality: str) -> Dict:
        return {
            "name": name,
            "appearance": {
                "face": appearance,
                "hair": "",
                "eyes": "",
                "body": "",
                "clothing": "",
                "accessories": ""
            },
            "personality_traits": [personality] if personality else [],
            "visual_keywords": f"{name}, {appearance}, 动漫风格"
        }
    
    def generate_character_appearance_prompt(self, character_info: Dict) -> str:
        name = character_info.get('name', '')
        appearance = character_info.get('appearance', '')
        personality = character_info.get('personality', '')
        
        prompt_parts = []
        if name:
            prompt_parts.append(f"角色名：{name}")
        if appearance:
            prompt_parts.append(f"外貌：{appearance}")
        if personality:
            prompt_parts.append(f"性格：{personality}")
        
        if not prompt_parts:
            return name
        
        full_prompt = ", ".join(prompt_parts)
        full_prompt += ", 动漫风格, 角色立绘, 全身像, 高质量, 细节丰富, 一致的角色设计"
        
        return full_prompt
    
    def generate_scene_image_prompt(self, scene_info: Dict, shot_info: Dict = None) -> str:
        description = scene_info.get('description', '')
        location = scene_info.get('location', '')
        characters = scene_info.get('characters', [])
        narration = scene_info.get('narration', '')
        
        prompt_parts = []
        
        if shot_info:
            shot_type = shot_info.get('shot_type', '')
            shot_desc = shot_info.get('description', '')
            shot_focus = shot_info.get('focus', '')
            
            if shot_desc:
                prompt_parts.append(shot_desc)
            if shot_type:
                prompt_parts.append(f"镜头类型：{shot_type}")
            if shot_focus:
                prompt_parts.append(f"焦点：{shot_focus}")
        
        if description:
            prompt_parts.append(description)
        elif narration:
            prompt_parts.append(narration)
        
        if location:
            prompt_parts.append(f"地点：{location}")
        
        if characters:
            char_list = "、".join(characters)
            prompt_parts.append(f"角色：{char_list}")
        
        full_prompt = ", ".join(prompt_parts)
        full_prompt += ", 动漫风格场景, 高质量, 细节丰富的背景"
        
        return full_prompt
    
    def _parse_fallback(self, text: str) -> Dict:
        result = {
            "scenes": [{
                "scene_number": 1,
                "description": text[:500] if len(text) > 500 else text,
                "location": "",
                "time": "",
                "characters": [],
                "narration": text,
                "dialogues": []
            }],
            "characters": []
        }
        return result
    
    def _create_empty_result(self) -> Dict:
        return {
            "scenes": [],
            "characters": []
        }
    
    def split_text_into_chunks(self, text: str, max_chunk_size: int = 2000) -> List[str]:
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(para) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                for i in range(0, len(para), max_chunk_size):
                    chunks.append(para[i:i + max_chunk_size])
            elif len(current_chunk) + len(para) + 1 <= max_chunk_size:
                if current_chunk:
                    current_chunk += "\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def analyze_novel_in_chunks(self, text: str, max_chunks: int = None) -> Dict:
        chunks = self.split_text_into_chunks(text)
        
        if max_chunks:
            chunks = chunks[:max_chunks]
        
        all_scenes = []
        all_characters = {}
        scene_counter = 0
        
        for i, chunk in enumerate(chunks):
            logging.info(f"分析文本块 {i+1}/{len(chunks)}...")
            
            chunk_result = self.analyze_novel_text(chunk)
            
            for scene in chunk_result.get('scenes', []):
                scene['scene_number'] = scene_counter
                scene_counter += 1
                all_scenes.append(scene)
            
            for char in chunk_result.get('characters', []):
                char_name = char.get('name', '')
                if char_name:
                    if char_name not in all_characters:
                        all_characters[char_name] = char
                    else:
                        existing = all_characters[char_name]
                        if not existing.get('appearance') and char.get('appearance'):
                            existing['appearance'] = char['appearance']
                        if not existing.get('personality') and char.get('personality'):
                            existing['personality'] = char['personality']
        
        return {
            "scenes": all_scenes,
            "characters": list(all_characters.values())
        }
