import json
import logging
from openai import OpenAI
from typing import Dict, List


class StoryboardGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openai.qiniu.com/v1"
        )
        self.model = "deepseek/deepseek-v3.1-terminus"
    
    def generate_storyboard_from_novel(self, text: str, characters: List[Dict]) -> Dict:
        character_info = "\n".join([
            f"- {char.get('name', '')}: {char.get('appearance', '')}, {char.get('personality', '')}"
            for char in characters
        ])
        
        system_prompt = f"""你是一个专业的漫画分镜师。请根据输入的小说文本生成详细的分镜脚本。

已知主要角色：
{character_info}

请生成包含以下信息的分镜脚本：

1. **分镜编号** (Panel Number)
2. **镜头类型** (Shot Type)：
   - 特写(Close-up): 聚焦角色面部表情
   - 中景(Medium shot): 展示角色上半身和动作
   - 全景(Full shot): 展示角色全身
   - 远景(Long shot): 展示场景环境
   - 过肩镜头(Over-the-shoulder): 对话场景
3. **画面描述** (Visual Description)：详细描述画面内容、角色位置、动作、表情
4. **对话内容** (Dialogue)：角色对话及说话者
5. **旁白** (Narration)：场景描述或心理活动
6. **角色列表** (Characters)：该分镜中出现的角色
7. **情感基调** (Mood)：happy/sad/tense/calm/surprised/angry等
8. **场景位置** (Location)：场景发生的地点

请以JSON格式返回，格式如下：
{{
  "storyboard": [
    {{
      "panel_number": 1,
      "shot_type": "特写",
      "visual_description": "画面描述，包含角色外貌特征保持一致性",
      "dialogue": [{{"character": "角色名", "text": "对话内容", "emotion": "情绪"}}],
      "narration": "旁白文本",
      "characters": ["角色1", "角色2"],
      "mood": "happy",
      "location": "场景地点"
    }}
  ]
}}

重要规则：
1. 角色外貌必须与角色设定完全一致
2. 根据情节发展自然过渡
3. 合理运用不同镜头类型来增强叙事效果
4. 每个分镜聚焦一个关键情节点
5. 确保角色对话符合人物性格"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请为以下小说文本生成分镜脚本：\n\n{text}"}
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
                result = self._create_fallback_storyboard(text)
            
            return result
            
        except Exception as e:
            logging.exception(f"分镜生成失败: {e}")
            return self._create_fallback_storyboard(text)
    
    def generate_storyboard_in_chunks(self, text: str, characters: List[Dict], max_chunk_size: int = 2000, max_retries: int = 3) -> Dict:
        chunks = self._split_text_into_chunks(text, max_chunk_size)
        
        all_panels = []
        panel_counter = 0
        success_count = 0
        failure_count = 0
        
        for i, chunk in enumerate(chunks):
            logging.info(f"生成分镜 {i+1}/{len(chunks)}...")
            
            chunk_result = None
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    chunk_result = self.generate_storyboard_from_novel(chunk, characters)
                    
                    if chunk_result and chunk_result.get('storyboard'):
                        success_count += 1
                        break
                    else:
                        retry_count += 1
                        if retry_count < max_retries:
                            logging.warning(f"分镜 {i+1} 生成结果为空，重试 {retry_count}/{max_retries}...")
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logging.error(f"分镜 {i+1} 生成失败: {e}，重试 {retry_count}/{max_retries}...")
                    else:
                        logging.exception(f"分镜 {i+1} 生成失败，已达到最大重试次数: {e}")
            
            if chunk_result and chunk_result.get('storyboard'):
                for panel in chunk_result.get('storyboard', []):
                    panel['panel_number'] = panel_counter
                    panel_counter += 1
                    all_panels.append(panel)
            else:
                failure_count += 1
                logging.error(f"分镜 {i+1} 最终生成失败")
        
        return {
            "storyboard": all_panels,
            "total_panels": len(all_panels),
            "success_count": success_count,
            "failure_count": failure_count
        }
    
    def _split_text_into_chunks(self, text: str, max_chunk_size: int) -> List[str]:
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
    
    def _create_fallback_storyboard(self, text: str) -> Dict:
        return {
            "storyboard": [{
                "panel_number": 0,
                "shot_type": "中景",
                "visual_description": text[:300] if len(text) > 300 else text,
                "dialogue": [],
                "narration": text,
                "characters": [],
                "mood": "neutral",
                "location": ""
            }]
        }
    
    def generate_panel_image_prompt(self, panel: Dict, character_designs: Dict[str, str]) -> str:
        shot_type = panel.get('shot_type', '中景')
        visual_desc = panel.get('visual_description', '')
        characters = panel.get('characters', [])
        location = panel.get('location', '')
        mood = panel.get('mood', 'neutral')
        
        prompt_parts = []
        
        prompt_parts.append(f"镜头类型: {shot_type}")
        
        if visual_desc:
            prompt_parts.append(visual_desc)
        
        if location:
            prompt_parts.append(f"场景: {location}")
        
        for char_name in characters:
            if char_name in character_designs:
                prompt_parts.append(f"{char_name}: {character_designs[char_name]}")
        
        mood_keywords = {
            'happy': '明亮, 欢快的氛围',
            'sad': '阴暗, 忧郁的氛围',
            'tense': '紧张, 戏剧性的氛围',
            'calm': '平静, 宁和的氛围',
            'surprised': '震惊, 突然的氛围',
            'angry': '激烈, 冲突的氛围'
        }
        
        if mood in mood_keywords:
            prompt_parts.append(mood_keywords[mood])
        
        full_prompt = ", ".join(prompt_parts)
        full_prompt += ", 漫画分镜风格, 动漫风格, 高质量, 细节丰富"
        
        return full_prompt
