import re
import jieba
from typing import List, Dict


class NovelParser:
    def __init__(self, novel_text: str):
        self.novel_text = novel_text
        self.chapters = []
        
    def parse(self) -> List[Dict]:
        self.chapters = self._split_into_chapters()
        return self.chapters
    
    def _split_into_chapters(self) -> List[Dict]:
        chapter_pattern = r'第[一二三四五六七八九十百千\d]+[章回节].*'
        parts = re.split(f'({chapter_pattern})', self.novel_text)
        
        chapters = []
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                chapter_title = parts[i].strip()
                chapter_content = parts[i + 1].strip()
                
                paragraphs = [p.strip() for p in chapter_content.split('\n') if p.strip()]
                
                chapters.append({
                    'title': chapter_title,
                    'content': chapter_content,
                    'paragraphs': paragraphs
                })
        
        if not chapters and self.novel_text.strip():
            paragraphs = [p.strip() for p in self.novel_text.split('\n') if p.strip()]
            chapters.append({
                'title': '全文',
                'content': self.novel_text,
                'paragraphs': paragraphs
            })
        
        return chapters
    
    def get_chapter(self, index: int) -> Dict:
        if 0 <= index < len(self.chapters):
            return self.chapters[index]
        return None
    
    def get_total_chapters(self) -> int:
        return len(self.chapters)
