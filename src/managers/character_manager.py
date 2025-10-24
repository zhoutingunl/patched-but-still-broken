import re
import jieba
from typing import List, Dict, Set
from collections import Counter


class CharacterManager:
    def __init__(self):
        self.characters = {}
        self.name_frequency = Counter()
        
    def extract_characters(self, text: str, min_frequency: int = 3) -> List[str]:
        chinese_name_pattern = r'[\\u4e00-\\u9fa5]{2,4}'
        potential_names = re.findall(chinese_name_pattern, text)
        
        self.name_frequency.update(potential_names)
        
        main_characters = [name for name, count in self.name_frequency.items() 
                          if count >= min_frequency and len(name) >= 2]
        
        main_characters = self._filter_common_words(main_characters)
        
        return sorted(main_characters, key=lambda x: self.name_frequency[x], reverse=True)
    
    def _filter_common_words(self, names: List[str]) -> List[str]:
        common_words = {
            '这个', '那个', '什么', '怎么', '为什么', '可以', '不是', '是的',
            '但是', '然而', '因为', '所以', '如果', '虽然', '而且', '或者',
            '自己', '我们', '他们', '她们', '它们', '大家', '人们', '东西',
            '地方', '时候', '现在', '之前', '以后', '一直', '已经', '还是'
        }
        return [name for name in names if name not in common_words]
    
    def register_character(self, name: str, description: str = "", 
                          appearance: Dict = None, image_seed: int = None):
        if name not in self.characters:
            self.characters[name] = {
                'name': name,
                'description': description,
                'appearance': appearance or {},
                'image_seed': image_seed or hash(name) % 1000000,
                'appearances': []
            }
    
    def get_character(self, name: str) -> Dict:
        return self.characters.get(name, None)
    
    def get_all_characters(self) -> List[Dict]:
        return list(self.characters.values())
    
    def update_character_appearance(self, name: str, appearance_description: str):
        if name in self.characters:
            if 'appearance_descriptions' not in self.characters[name]:
                self.characters[name]['appearance_descriptions'] = []
            self.characters[name]['appearance_descriptions'].append(appearance_description)
    
    def get_character_prompt(self, name: str) -> str:
        char = self.get_character(name)
        if not char:
            return f"角色：{name}"
        
        prompt_parts = [f"角色：{name}"]
        
        if char.get('description'):
            prompt_parts.append(f"描述：{char['description']}")
        
        if char.get('appearance'):
            appearance = char['appearance']
            prompt_parts.append(f"外貌：{', '.join(f'{k}: {v}' for k, v in appearance.items())}")
        
        prompt_parts.append(f"种子值：{char['image_seed']}")
        
        return ', '.join(prompt_parts)
