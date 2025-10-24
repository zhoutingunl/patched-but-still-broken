# Parsers 解析器模块

## 功能说明

文本解析模块，负责将小说文本解析为结构化数据。

## 模块列表

### novel_parser.py
- **功能**: 小说解析器
- **职责**:
  - 解析小说文本，识别章节标题
  - 将章节分割为段落
  - 支持多种章节标题格式（第X章、第X回、第X节等）
  - 返回结构化的章节和段落数据

## 使用示例

```python
from src.parsers.novel_parser import NovelParser

with open('novel.txt', 'r', encoding='utf-8') as f:
    novel_text = f.read()

parser = NovelParser(novel_text)
chapters = parser.parse()
```
