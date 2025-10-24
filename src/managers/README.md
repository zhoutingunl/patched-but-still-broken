# Managers 管理模块

## 功能说明

管理模块，负责角色信息的提取、存储和管理。

## 模块列表

### character_manager.py
- **功能**: 角色管理器
- **职责**:
  - 从小说文本中自动提取主要角色
  - 基于词频分析识别角色（出现3次以上）
  - 过滤常见词汇，避免误识别
  - 为每个角色分配唯一的种子值，确保角色外观一致性
  - 管理角色描述和外貌信息
  - 生成角色提示词（prompt）用于图片生成

## 使用示例

```python
from src.managers.character_manager import CharacterManager

char_mgr = CharacterManager()

# 提取角色
characters = char_mgr.extract_characters(novel_text, min_frequency=3)

# 注册角色
char_mgr.register_character("张三", description="主人公，年轻男子")

# 获取角色信息
char_info = char_mgr.get_character("张三")

# 生成角色提示词
prompt = char_mgr.get_character_prompt("张三")
```
